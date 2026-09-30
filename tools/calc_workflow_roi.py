"""Deterministic cost, ROI, cash-flow and payback math for /workflow-builder.

Reads one JSON file describing the recommended tools, the one-time and recurring
costs, the automated tasks (with human review and rework), and any other
benefits gathered in discovery. Writes a results JSON plus a Markdown summary
whose formula lines can be copied into roi-calculations.md. With --schedule-out
it also writes the monthly cash-flow schedule that tools/build_payback_report.py
consumes. Free, no API calls.

Usage:
    .venv/bin/python tools/calc_workflow_roi.py --in output/workflow-builder/<slug>/roi-inputs.json \
        --out output/workflow-builder/<slug>/roi-results.json \
        --schedule-out output/workflow-builder/<slug>/payback-schedule.json

Rules live in .claude/skills/workflow-builder/roi-method.md. Every block except
"tools" is optional, so older input files (tools + benefits only) still run and
give the same numbers as before; missing cost blocks are reported as warnings.

Input shape:
{
  "client": "Acme",
  "workflow": "Lead follow-up automation",
  "weeks_per_year": 52,
  "tools": [
    {"name": "n8n Cloud", "plan": "Starter", "monthly_cost": 50, "pricing_status": "verified",
     "source_url": "https://n8n.io/pricing", "basis": "monthly billing",
     "consumption": {"runs_per_month": 3000, "units_per_run": 1, "unit": "executions", "plan_included_units": 10000}},
    {"name": "LLM API", "pricing_status": "estimated", "source_url": "...",
     "llm_usage": {"runs_per_month": 350, "input_tokens_per_run": 4000, "output_tokens_per_run": 1000,
                   "input_price_per_mtok": 2.5, "output_price_per_mtok": 10.0}}
     # "scales_with_volume": true|false  (default: true for llm_usage tools, false otherwise)
  ],
  "implementation": {                      # one-time; pick ONE pricing form
    "mode": "self" | "freelancer" | "agency" | "undecided",
    "fixed_quote": 6000,                                   # or
    "hourly_rate": 90, "hours": 60,                        # or
    "hourly_rate": 90, "phase_hours": {"discovery": 10, "build": 16, "testing": 16, "handoff": 6, "hypercare": 12},
    "contingency_pct": 0,                                  # optional buffer on an estimate, never on a quote
    "source": "client" | "assumption" | "benchmark", "source_url": "...", "basis": "..."
  },
  "adoption": {"hours": 20, "hourly_cost": 50, "source": "client", "basis": "4 people x 5 h"},
              # or {"pct_of_implementation": 15, "source": "benchmark", "source_url": "..."}
  "maintenance": {"retainer_monthly": 300} | {"hours_per_month": 4, "hourly_rate": 90}
                 | {"pct_of_build_per_year": 20}   (+ "source", "source_url", "basis"),
  "tasks": [                               # automated work, valued net of review and rework
    {"label": "CRM record sync", "type": "avoided_labor" | "capacity",
     "gross_hours_per_week": 10, "hourly_cost": 30, "units_per_week": 200, "unit": "records",
     "reviewer_hourly_cost": 40, "source": "client", "basis": "...",
     "review_source": "benchmark", "review_source_url": "...", "review_basis": "...",
     "ramp":   {"review_share": 0.10, "review_minutes_per_unit": 3, "rework_pct": 5},
     "steady": {"review_share": 0.05, "review_minutes_per_unit": 3, "rework_pct": 0}}
     # instead of share x minutes: "review_hours_per_week"; instead of rework_pct: "rework_hours_per_week"
  ],
  "benefits": [                            # non-task benefits (and the legacy format)
    {"label": "Replaced tool", "type": "cost_reduction", "monthly_value": 99, "source": "client"},
    {"label": "Faster follow-up", "type": "revenue", "annual_value": 30000, "source": "assumption",
     "include_in_roi": false, "basis": "..."}
  ],
  "timing": {"go_live_month": 1, "one_time_months": [0], "ramp_months": 3, "recurring_start_month": 1},
  "scenarios": [                           # ONLY ranges the user confirmed
    {"name": "Conservative", "basis": "...", "labor_benefit_multiplier": 0.8,
     "one_time_multiplier": 1.2, "recurring_multiplier": 1.0}
  ]
}

Benefit types:
  avoided_labor   hard savings (labor cost actually avoided)       -> counted in gross savings
  cost_reduction  hard savings (other costs removed)                -> counted in gross savings
  capacity        hours freed and redeployed, not a cash saving     -> hours counted, value reported separately
  revenue         revenue upside                                    -> reported separately; only in ROI if include_in_roi

Rounding (same as the skill): money to whole dollars (half up) before it enters the
schedule, percentages to whole numbers, hours to one decimal, payback months to one
decimal (interpolated within the month), break-even unit counts rounded up.
"""

import argparse
import json
import math
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HARD_TYPES = {"avoided_labor", "cost_reduction"}
ALL_TYPES = HARD_TYPES | {"capacity", "revenue"}
TASK_TYPES = {"avoided_labor", "capacity"}
SOURCES = {"client", "assumption", "benchmark"}
SOURCE_LABELS = {"client": "Client-stated", "assumption": "Confirmed assumption", "benchmark": "Benchmark"}
MODES = {"self", "freelancer", "agency", "undecided"}
BASE_HORIZON, MAX_HORIZON = 24, 36
MAINT_PCT_RANGE = (15, 25)  # cost-benchmarks.md, % of build cost per year


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def r0(x: float) -> int:
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def r1(x: float) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def money(x: float) -> str:
    return f"-${abs(r0(x)):,}" if x < 0 else f"${r0(x):,}"


def pct(x: float) -> str:
    return f"{r0(x):,}%"


def hrs(x: float) -> str:
    return f"{r1(x):,.1f}".rstrip("0").rstrip(".")


def check_source(block: dict, name: str, key: str = "source", url_key: str = "source_url") -> str:
    src = block.get(key)
    if src not in SOURCES:
        fail(f"{name}: {key} must be one of {sorted(SOURCES)}")
    if src == "benchmark" and not block.get(url_key):
        fail(f"{name}: a benchmark {key} needs a {url_key} (use cost-benchmarks.md)")
    return src


# ---------------------------------------------------------------- subscriptions

def price_tool(t: dict, warnings: list) -> dict:
    name = t.get("name") or fail("every tool needs a name")
    status = t.get("pricing_status")
    if status not in {"verified", "estimated"}:
        fail(f"{name}: pricing_status must be 'verified' or 'estimated'")
    if status == "verified" and not t.get("source_url"):
        fail(f"{name}: verified pricing needs a source_url")

    llm = t.get("llm_usage")
    if llm:
        runs = llm["runs_per_month"]
        cost = runs * (
            llm["input_tokens_per_run"] * llm["input_price_per_mtok"]
            + llm["output_tokens_per_run"] * llm["output_price_per_mtok"]
        ) / 1_000_000
        cost += t.get("monthly_cost", 0)  # e.g. a fixed platform fee on top of usage
        # Token volumes are always an estimate, even when the per-token price is verified.
        status = "estimated"
        calc = (f"{runs:,} runs x ({llm['input_tokens_per_run']:,} in x ${llm['input_price_per_mtok']}/M"
                f" + {llm['output_tokens_per_run']:,} out x ${llm['output_price_per_mtok']}/M)")
    elif "monthly_cost" in t:
        cost = float(t["monthly_cost"])
        calc = None
    else:
        fail(f"{name}: needs monthly_cost or llm_usage")

    c = t.get("consumption")
    usage = None
    if c:
        needed = c["runs_per_month"] * c["units_per_run"]
        included = c.get("plan_included_units")
        usage = {"units_needed": needed, "unit": c.get("unit", "units"), "plan_included_units": included}
        if included is not None and needed > included:
            warnings.append(f"{name}: needs {needed:,} {usage['unit']}/month but the plan includes {included:,}. "
                            "Pick a bigger plan or add overage cost.")
        elif included is not None and needed > 0.8 * included:
            warnings.append(f"{name}: uses {needed / included:.0%} of plan {usage['unit']}. Little headroom for growth.")

    return {
        "name": name,
        "plan": t.get("plan"),
        "monthly_cost": round(cost, 2),
        "pricing_status": status,
        "source_url": t.get("source_url"),
        "basis": t.get("basis"),
        "llm_calc": calc,
        "usage": usage,
        "scales_with_volume": bool(t.get("scales_with_volume", bool(llm))),
    }


# ---------------------------------------------------------------- one-time + maintenance

def cost_implementation(imp: dict | None, assumptions: list, formulas: list, warnings: list) -> dict:
    if not imp:
        warnings.append("No implementation cost given. One-time costs are not modeled; payback and first-year "
                        "TCO understate the real cost unless the client truly has none.")
        return {"mode": None, "cost": 0}
    mode = imp.get("mode")
    if mode not in MODES:
        fail(f"implementation.mode must be one of {sorted(MODES)}")
    src = check_source(imp, "implementation")
    contingency = float(imp.get("contingency_pct", 0))
    if "fixed_quote" in imp:
        base = float(imp["fixed_quote"])
        calc = f"fixed quote {money(base)}"
        if contingency:
            warnings.append("implementation: contingency_pct ignored on a fixed quote (the quote is the price).")
            contingency = 0
        hours = None
    elif "hourly_rate" in imp and ("hours" in imp or "phase_hours" in imp):
        rate = float(imp["hourly_rate"])
        if "phase_hours" in imp:
            ph = imp["phase_hours"]
            hours = sum(ph.values())
            calc = (f"({' + '.join(f'{hrs(v)} {k}' for k, v in ph.items())} = {hrs(hours)} h)"
                    f" x ${rate:,.0f}/h")
        else:
            hours = float(imp["hours"])
            calc = f"{hrs(hours)} h x ${rate:,.0f}/h"
        base = hours * rate
    else:
        fail("implementation needs fixed_quote, or hourly_rate with hours or phase_hours")
    cost = r0(base * (1 + contingency / 100))
    if contingency:
        calc += f" x (1 + {contingency:g}% contingency)"
    formulas.append(f"Implementation ({mode}): {calc} = {money(cost)}")
    assumptions.append({"input": f"Implementation cost ({mode})", "value": money(cost), "source": src,
                        "basis": imp.get("basis"), "source_url": imp.get("source_url")})
    return {"mode": mode, "cost": cost, "hours": hours, "calc": calc}


def cost_adoption(ad: dict | None, impl_cost: int, assumptions: list, formulas: list, warnings: list) -> int:
    if not ad:
        warnings.append("No adoption/training cost given. Confirm with the user that it is truly zero.")
        return 0
    src = check_source(ad, "adoption")
    if "hours" in ad and "hourly_cost" in ad:
        cost = r0(ad["hours"] * ad["hourly_cost"])
        calc = f"{hrs(ad['hours'])} h x ${ad['hourly_cost']:,.0f}/h"
    elif "pct_of_implementation" in ad:
        cost = r0(impl_cost * ad["pct_of_implementation"] / 100)
        calc = f"{ad['pct_of_implementation']:g}% x {money(impl_cost)} implementation"
    elif "fixed" in ad:
        cost = r0(ad["fixed"])
        calc = "fixed"
    else:
        fail("adoption needs hours + hourly_cost, pct_of_implementation, or fixed")
    formulas.append(f"Adoption and training: {calc} = {money(cost)}")
    assumptions.append({"input": "Adoption and training", "value": money(cost), "source": src,
                        "basis": ad.get("basis"), "source_url": ad.get("source_url")})
    return cost


def cost_maintenance(mt: dict | None, build_cost: int, assumptions: list, formulas: list, warnings: list) -> int:
    if not mt:
        warnings.append("No maintenance cost given. Confirm who maintains the workflow and what that costs.")
        return 0
    src = check_source(mt, "maintenance")
    if "retainer_monthly" in mt:
        cost = r0(mt["retainer_monthly"])
        calc = "retainer"
    elif "hours_per_month" in mt and "hourly_rate" in mt:
        cost = r0(mt["hours_per_month"] * mt["hourly_rate"])
        calc = f"{hrs(mt['hours_per_month'])} h/month x ${mt['hourly_rate']:,.0f}/h"
    elif "pct_of_build_per_year" in mt:
        if not build_cost:
            fail("maintenance.pct_of_build_per_year needs an implementation cost")
        cost = r0(build_cost * mt["pct_of_build_per_year"] / 100 / 12)
        calc = f"{mt['pct_of_build_per_year']:g}% x {money(build_cost)} build / 12"
    else:
        fail("maintenance needs retainer_monthly, hours_per_month + hourly_rate, or pct_of_build_per_year")
    formulas.append(f"Maintenance: {calc} = {money(cost)}/month")
    if build_cost:
        annual_pct = cost * 12 / build_cost * 100
        lo, hi = MAINT_PCT_RANGE
        if not lo <= annual_pct <= hi:
            warnings.append(f"Maintenance is {annual_pct:.0f}% of build cost per year, outside the {lo}-{hi}% "
                            "published benchmark. Fine if client-stated; otherwise explain the basis.")
    assumptions.append({"input": "Maintenance (monthly)", "value": money(cost), "source": src,
                        "basis": mt.get("basis"), "source_url": mt.get("source_url")})
    return cost


# ---------------------------------------------------------------- benefits

def review_hours(t: dict, phase: dict, label: str, which: str) -> tuple:
    if "review_hours_per_week" in phase:
        rev = float(phase["review_hours_per_week"])
        rcalc = f"{hrs(rev)} h"
    elif "review_share" in phase:
        units = t.get("units_per_week") or fail(f"{label}: review_share needs units_per_week")
        mins = phase.get("review_minutes_per_unit") or fail(f"{label}: review_share needs review_minutes_per_unit")
        rev = units * phase["review_share"] * mins / 60
        rcalc = f"{units:g} x {phase['review_share'] * 100:g}% x {mins:g} min / 60 = {hrs(rev)} h"
    else:
        fail(f"{label}: {which} needs review_hours_per_week or review_share + review_minutes_per_unit")
    gross = t["gross_hours_per_week"]
    if "rework_hours_per_week" in phase:
        rw = float(phase["rework_hours_per_week"])
        wcalc = f"{hrs(rw)} h"
    else:
        rw = gross * phase.get("rework_pct", 0) / 100
        wcalc = f"{phase.get('rework_pct', 0):g}% x {hrs(gross)} h = {hrs(rw)} h"
    return rev, rw, rcalc, wcalc


def value_task(t: dict, weeks: float, assumptions: list) -> dict:
    label = t.get("label") or fail("every task needs a label")
    ttype = t.get("type")
    if ttype not in TASK_TYPES:
        fail(f"{label}: task type must be one of {sorted(TASK_TYPES)}")
    src = check_source(t, label)
    rsrc = check_source(t, f"{label} review", "review_source", "review_source_url")
    gross = float(t.get("gross_hours_per_week") or fail(f"{label}: needs gross_hours_per_week"))
    rate = float(t.get("hourly_cost", 0))
    if ttype == "avoided_labor" and not rate:
        fail(f"{label}: avoided_labor needs hourly_cost")
    reviewer = float(t.get("reviewer_hourly_cost", rate))
    out = {"label": label, "type": ttype, "gross_hours_per_week": gross, "hourly_cost": rate,
           "reviewer_hourly_cost": reviewer, "units_per_week": t.get("units_per_week"), "unit": t.get("unit")}
    for which in ("ramp", "steady"):
        phase = t.get(which) or fail(f"{label}: needs a '{which}' review block")
        rev, rw, rcalc, wcalc = review_hours(t, phase, label, which)
        net = gross - rev - rw
        weekly_value = gross * rate - (rev + rw) * reviewer if ttype == "avoided_labor" else 0.0
        out[which] = {"review_hours_per_week": rev, "rework_hours_per_week": rw, "net_hours_per_week": net,
                      "weekly_value": weekly_value, "review_calc": rcalc, "rework_calc": wcalc}
    assumptions.append({"input": f"{label}: gross hours automated", "value": f"{hrs(gross)} h/week",
                        "source": src, "basis": t.get("basis"), "source_url": t.get("source_url")})
    if ttype == "avoided_labor":
        assumptions.append({"input": f"{label}: hourly cost of automated work", "value": f"${rate:,.2f}/h".replace(".00/", "/"),
                            "source": src, "basis": t.get("basis"), "source_url": t.get("source_url")})
        assumptions.append({"input": f"{label}: reviewer hourly cost", "value": f"${reviewer:,.2f}/h".replace(".00/", "/"),
                            "source": t.get("reviewer_source", src), "basis": t.get("reviewer_basis"),
                            "source_url": t.get("reviewer_source_url")})
    for which, name in (("ramp", "ramp"), ("steady", "steady state")):
        p = out[which]
        assumptions.append({"input": f"{label}: review + rework ({name})",
                            "value": f"{hrs(p['review_hours_per_week'])} h + {hrs(p['rework_hours_per_week'])} h per week",
                            "source": rsrc, "basis": t.get("review_basis"), "source_url": t.get("review_source_url")})
    return out


def value_benefit(b: dict, weeks: float) -> dict:
    label = b.get("label") or fail("every benefit needs a label")
    btype = b.get("type")
    if btype not in ALL_TYPES:
        fail(f"{label}: type must be one of {sorted(ALL_TYPES)}")
    if b.get("source") not in SOURCES:
        fail(f"{label}: source must be one of {sorted(SOURCES)}")

    hours_week = b.get("hours_per_week")
    annual_hours = hours_week * weeks if hours_week is not None else None
    if "annual_value" in b:
        annual_value = float(b["annual_value"])
        calc = None
    elif "monthly_value" in b:
        annual_value = float(b["monthly_value"]) * 12
        calc = f"{money(b['monthly_value'])}/month x 12"
    elif hours_week is not None and "hourly_cost" in b:
        annual_value = hours_week * b["hourly_cost"] * weeks
        calc = f"{hours_week:g} h/week x ${b['hourly_cost']:,.2f}/h x {weeks:g} weeks"
    elif btype == "capacity" and hours_week is not None:
        annual_value = 0.0
        calc = None
    else:
        fail(f"{label}: needs annual_value, monthly_value, or hours_per_week + hourly_cost")

    return {
        "label": label,
        "type": btype,
        "source": b["source"],
        "basis": b.get("basis"),
        "hours_per_week": hours_week,
        "annual_hours": annual_hours,
        "annual_value": round(annual_value, 2),
        "calc": calc,
        "include_in_roi": btype in HARD_TYPES or bool(b.get("include_in_roi")),
    }


# ---------------------------------------------------------------- schedule + payback

def spread(total: int, months: list) -> dict:
    """Split an integer amount evenly over months; the remainder lands in the last month."""
    if not total:
        return {}
    each = total // len(months)
    parts = {m: each for m in months}
    parts[months[-1]] += total - each * len(months)
    return parts


def build_schedule(p: dict, horizon: int) -> list:
    one_time = spread(p["one_time"], p["one_time_months"])
    rows, cum = [], 0
    for m in range(horizon + 1):
        ot = one_time.get(m, 0)
        rec = p["recurring"] if m >= p["recurring_start"] else 0
        if m < p["go_live"]:
            ben, phase = 0, "build"
        elif m < p["go_live"] + p["ramp_months"]:
            ben, phase = p["benefit_ramp"], "ramp"
        else:
            ben, phase = p["benefit_steady"], "steady"
        net = ben - ot - rec
        cum += net
        rows.append({"month": m, "phase": phase, "one_time_cost": ot, "recurring_cost": rec,
                     "net_benefit": ben, "net_cash_flow": net, "cumulative": cum})
    return rows


def find_payback(p: dict) -> dict:
    """Payback per roi-method.md: first month with cumulative >= 0, interpolated to 0.1."""
    if p["benefit_steady"] - p["recurring"] <= 0:
        return {"status": "never", "months": None, "schedule": build_schedule(p, BASE_HORIZON),
                "text": "Never breaks even at these numbers"}
    for horizon in (BASE_HORIZON, MAX_HORIZON):
        rows = build_schedule(p, horizon)
        for r in rows:
            # Cumulative can be >= 0 before any money is spent (e.g. spread one-time costs); only count
            # payback once every one-time cost has been paid.
            if r["cumulative"] >= 0 and r["month"] >= max(p["one_time_months"]):
                m = r["month"]
                if m == 0 or rows[m - 1]["cumulative"] >= 0:
                    months = float(m)
                else:
                    months = (m - 1) + (-rows[m - 1]["cumulative"]) / r["net_cash_flow"]
                months = r1(months)
                text = "Immediate (no one-time costs)" if months == 0 else f"{months:g} months"
                return {"status": "reached", "months": months, "month_index": m, "schedule": rows,
                        "horizon": horizon, "text": text}
    return {"status": "not_reached", "months": None, "schedule": build_schedule(p, MAX_HORIZON),
            "horizon": MAX_HORIZON, "text": f"Not reached within {MAX_HORIZON} months"}


def scenario_params(base: dict, labor_mult: float = 1.0, one_time_mult: float = 1.0,
                    recurring_mult: float = 1.0, steady_labor=None) -> dict:
    p = dict(base)
    ramp_labor = base["labor_ramp"] * labor_mult
    steady = (base["labor_steady"] if steady_labor is None else steady_labor) * labor_mult
    p["benefit_ramp"] = r0(ramp_labor) + base["other_monthly"]
    p["benefit_steady"] = r0(steady) + base["other_monthly"]
    p["one_time"] = r0(base["one_time"] * one_time_mult)
    p["recurring"] = r0(base["recurring"] * recurring_mult)
    return p


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--schedule-out", type=Path, help="write the cash-flow schedule JSON for build_payback_report.py")
    args = ap.parse_args()

    data = json.loads(args.inp.read_text())
    weeks = float(data.get("weeks_per_year", 52))
    wpm = weeks / 12  # weeks per month
    warnings: list = []
    assumptions: list = []
    formulas: list = []

    # --- recurring subscriptions
    tools = [price_tool(t, warnings) for t in data.get("tools", [])]
    if not tools:
        fail("no tools given")
    subs_exact = sum(t["monthly_cost"] for t in tools)
    subs = r0(subs_exact)
    variable_monthly = r0(sum(t["monthly_cost"] for t in tools if t["scales_with_volume"]))
    for t in tools:
        assumptions.append({"input": f"{t['name']}{' (' + t['plan'] + ')' if t['plan'] else ''} subscription",
                            "value": f"{money(t['monthly_cost']) if t['monthly_cost'] >= 1 else '$' + format(t['monthly_cost'], '.2f')}/month",
                            "source": "verified price" if t["pricing_status"] == "verified" else "estimated",
                            "basis": t["llm_calc"] or t["basis"], "source_url": t["source_url"]})

    # --- one-time + maintenance
    formulas_cost: list = []
    impl = cost_implementation(data.get("implementation"), assumptions, formulas_cost, warnings)
    adoption = cost_adoption(data.get("adoption"), impl["cost"], assumptions, formulas_cost, warnings)
    maint = cost_maintenance(data.get("maintenance"), impl["cost"], assumptions, formulas_cost, warnings)
    one_time = impl["cost"] + adoption
    recurring = subs + maint

    # --- benefits
    tasks = [value_task(t, weeks, assumptions) for t in data.get("tasks", [])]
    benefits = [value_benefit(b, weeks) for b in data.get("benefits", [])]
    if not tasks and not benefits:
        fail("no tasks or benefits given")
    for b in benefits:
        assumptions.append({"input": b["label"], "value": f"{money(b['annual_value'])}/year" if b["annual_value"] else
                            f"{hrs(b['hours_per_week'] or 0)} h/week", "source": b["source"], "basis": b["basis"],
                            "source_url": None})
        if b["type"] in {"avoided_labor", "capacity"} and b["hours_per_week"]:
            warnings.append(f"'{b['label']}' is a legacy hours benefit: human review and rework are NOT deducted. "
                            "Move it to 'tasks' to model net hours.")

    labor_tasks = [t for t in tasks if t["type"] == "avoided_labor"]
    labor_ramp = sum(t["ramp"]["weekly_value"] for t in labor_tasks) * wpm
    labor_steady = sum(t["steady"]["weekly_value"] for t in labor_tasks) * wpm
    legacy_hard = [b for b in benefits if b["type"] in HARD_TYPES]
    soft_in_roi = [b for b in benefits if b["type"] not in HARD_TYPES and b["include_in_roi"]]
    other_annual = sum(b["annual_value"] for b in legacy_hard + soft_in_roi)
    other_monthly = r0(other_annual / 12)

    base = {"one_time": one_time, "one_time_months": data.get("timing", {}).get("one_time_months", [0]),
            "recurring": recurring, "labor_ramp": labor_ramp, "labor_steady": labor_steady,
            "other_monthly": other_monthly}
    timing = data.get("timing", {})
    base["go_live"] = int(timing.get("go_live_month", 1))
    base["ramp_months"] = int(timing.get("ramp_months", 3))
    base["recurring_start"] = int(timing.get("recurring_start_month", base["go_live"]))
    p = scenario_params(base)
    benefit_ramp, benefit_steady = p["benefit_ramp"], p["benefit_steady"]
    if not tasks:
        warnings.append("No 'tasks' given: benefits have no ramp and no review/rework deduction.")

    # --- hours
    gross_week = sum(t["gross_hours_per_week"] for t in tasks) + sum(
        b["hours_per_week"] or 0 for b in benefits if b["type"] in {"avoided_labor", "capacity"})
    legacy_hours = sum(b["hours_per_week"] or 0 for b in benefits if b["type"] in {"avoided_labor", "capacity"})
    net_ramp_week = sum(t["ramp"]["net_hours_per_week"] for t in tasks) + legacy_hours
    net_steady_week = sum(t["steady"]["net_hours_per_week"] for t in tasks) + legacy_hours
    ramp_n = base["ramp_months"]
    first_year_net_hours = (min(ramp_n, 12) * net_ramp_week + max(12 - ramp_n, 0) * net_steady_week) * wpm

    # --- headline figures
    gross_savings_annual = r0(sum(t["gross_hours_per_week"] * t["hourly_cost"] for t in labor_tasks) * weeks
                              + sum(b["annual_value"] for b in legacy_hard))
    first_year_recurring = 12 * recurring
    tco1 = one_time + first_year_recurring
    ben1 = min(ramp_n, 12) * benefit_ramp + max(12 - ramp_n, 0) * benefit_steady
    net1 = ben1 - tco1
    roi1 = net1 / tco1 * 100 if tco1 else None
    steady_cost = 12 * recurring
    steady_ben = 12 * benefit_steady
    net2 = steady_ben - steady_cost
    roi2 = net2 / steady_cost * 100 if steady_cost else None

    payback = find_payback(p)

    # --- operating break-even: scale factor s on task volume where monthly benefit = recurring cost
    fixed = recurring - variable_monthly
    labor_steady_r = r0(labor_steady)
    margin = labor_steady_r - variable_monthly
    steady_labor_net_hours_month = sum(t["steady"]["net_hours_per_week"] for t in labor_tasks) * wpm
    obe = {"fixed_monthly_cost": fixed, "variable_monthly_cost": variable_monthly,
           "labor_benefit_steady_monthly": labor_steady_r, "other_benefit_monthly": other_monthly}
    if not labor_tasks:
        obe.update(status="not_applicable", text="No volume-driven labor benefit to compute a break-even volume")
    elif margin <= 0:
        obe.update(status="never", text="Labor value per unit is below the usage cost per unit: no volume covers the running costs")
    else:
        s = max((fixed - other_monthly) / margin, 0.0)
        units = [{"label": t["label"], "unit": t["unit"],
                  "expected_per_month": r1(t["units_per_week"] * wpm),
                  "break_even_per_month": math.ceil(s * t["units_per_week"] * wpm - 1e-9)}
                 for t in labor_tasks if t.get("units_per_week")]
        obe.update(status="reached" if s <= 1 else "above_expected", share_of_expected_volume_pct=r0(s * 100),
                   net_hours_per_month=r1(s * steady_labor_net_hours_month),
                   expected_net_hours_per_month=r1(steady_labor_net_hours_month), units=units,
                   text=f"{hrs(s * steady_labor_net_hours_month)} net hours/month"
                        + "".join(f", about {u['break_even_per_month']:,} {u['unit']}/month" for u in units))

    # --- sensitivity (computed, never estimated)
    sens = []
    for label, kw in (("Net hours saved 25% lower", {"labor_mult": 0.75}),
                      ("Review stays at ramp-period levels", {"steady_labor": labor_ramp})):
        sp = scenario_params(base, **kw)
        pb = find_payback(sp)
        sens.append({"label": label, "benefit_ramp_monthly": sp["benefit_ramp"],
                     "benefit_steady_monthly": sp["benefit_steady"], "payback_status": pb["status"],
                     "payback_months": pb["months"], "payback_text": pb["text"]})

    # --- confirmed scenarios
    scenarios = []
    for sc in data.get("scenarios", []):
        if not sc.get("basis"):
            fail(f"scenario {sc.get('name')}: needs a basis (only draw ranges the user confirmed)")
        sp = scenario_params(base, sc.get("labor_benefit_multiplier", 1.0), sc.get("one_time_multiplier", 1.0),
                             sc.get("recurring_multiplier", 1.0))
        pb = find_payback(sp)
        scenarios.append({"name": sc["name"], "basis": sc["basis"], "payback_status": pb["status"],
                          "payback_months": pb["months"], "payback_text": pb["text"],
                          "one_time": sp["one_time"], "recurring": sp["recurring"],
                          "benefit_ramp": sp["benefit_ramp"], "benefit_steady": sp["benefit_steady"],
                          "cumulative": [r["cumulative"] for r in pb["schedule"]]})

    # --- formula lines (the order roi-calculations.md uses)
    formulas.append(("Monthly subscriptions: " + " + ".join(money(t["monthly_cost"]) if t["monthly_cost"] >= 1
                     else f"${t['monthly_cost']:.2f}" for t in tools) + f" = {money(subs)}") if len(tools) > 1
                    else f"Monthly subscriptions: {money(subs)}")
    formulas.extend(formulas_cost)
    formulas.append(f"One-time costs: {money(impl['cost'])} implementation + {money(adoption)} adoption = {money(one_time)}")
    formulas.append(f"Monthly recurring cost: {money(subs)} subscriptions + {money(maint)} maintenance = {money(recurring)}")
    for t in tasks:
        for which, name in (("ramp", "ramp"), ("steady", "steady")):
            q = t[which]
            line = (f"{t['label']} ({name}): {hrs(t['gross_hours_per_week'])} h gross - review ({q['review_calc']})"
                    f" - rework ({q['rework_calc']}) = {hrs(q['net_hours_per_week'])} h/week net")
            if t["type"] == "avoided_labor":
                line += (f"; value {hrs(t['gross_hours_per_week'])} x ${t['hourly_cost']:g} - "
                         f"{hrs(q['review_hours_per_week'] + q['rework_hours_per_week'])} x ${t['reviewer_hourly_cost']:g}"
                         f" = ${q['weekly_value']:,.2f}/week")
            else:
                line += " (capacity: hours only, not in ROI)"
            formulas.append(line)
    wv_r = sum(t["ramp"]["weekly_value"] for t in labor_tasks)
    wv_s = sum(t["steady"]["weekly_value"] for t in labor_tasks)
    if labor_tasks:
        formulas.append(f"Monthly labor benefit, ramp: ${wv_r:,.2f}/week x {weeks:g} / 12 = {money(labor_ramp)}")
        formulas.append(f"Monthly labor benefit, steady: ${wv_s:,.2f}/week x {weeks:g} / 12 = {money(labor_steady)}")
    if other_monthly:
        formulas.append(f"Other benefits counted in ROI: {money(other_annual)}/year / 12 = {money(other_monthly)}/month")
    formulas.append(f"Monthly net benefit: ramp {money(benefit_ramp)}, steady state {money(benefit_steady)}")
    formulas.append(f"Weekly hours: {hrs(gross_week)} gross; net {hrs(net_ramp_week)} (ramp), "
                    f"{hrs(net_steady_week)} (steady state)")
    formulas.append(f"Annual hours: {hrs(gross_week)} x {weeks:g} = {r0(gross_week * weeks):,} gross; "
                    f"{hrs(net_steady_week)} x {weeks:g} = {r0(net_steady_week * weeks):,} net at steady state")
    formulas.append(f"First-year net hours: ({min(ramp_n, 12)} x {hrs(net_ramp_week)} + {max(12 - ramp_n, 0)} x "
                    f"{hrs(net_steady_week)}) x {weeks:g} / 12 = {r0(first_year_net_hours):,}")
    formulas.append(f"Annual gross savings (before review, rework and costs): {money(gross_savings_annual)}")
    formulas.append(f"First-year TCO: {money(one_time)} + 12 x {money(recurring)} = {money(tco1)}")
    formulas.append(f"First-year benefit: {min(ramp_n, 12)} x {money(benefit_ramp)} + {max(12 - ramp_n, 0)} x "
                    f"{money(benefit_steady)} = {money(ben1)}")
    formulas.append(f"First-year net benefit: {money(ben1)} - {money(tco1)} = {money(net1)}")
    if roi1 is not None:
        formulas.append(f"First-year ROI: {money(net1)} / {money(tco1)} x 100 = {pct(roi1)}")
    formulas.append(f"Steady-state annual cost: 12 x {money(recurring)} = {money(steady_cost)}")
    formulas.append(f"Steady-state annual benefit: 12 x {money(benefit_steady)} = {money(steady_ben)}")
    formulas.append(f"Steady-state net annual benefit: {money(steady_ben)} - {money(steady_cost)} = {money(net2)}")
    if roi2 is not None:
        formulas.append(f"Steady-state (year 2) ROI: {money(net2)} / {money(steady_cost)} x 100 = {pct(roi2)}")
    formulas.append(f"Payback period: {payback['text']}")
    if obe.get("status") in {"reached", "above_expected"}:
        formulas.append(f"Operating break-even: ({money(fixed)} fixed - {money(other_monthly)} other benefit) / "
                        f"({money(labor_steady_r)} labor benefit - {money(variable_monthly)} usage cost) = "
                        f"{r0(obe['share_of_expected_volume_pct'])}% of expected volume = {obe['text']}")
    else:
        formulas.append(f"Operating break-even: {obe['text']}")

    if any(a["source"] in {"assumption", "benchmark"} for a in assumptions):
        warnings.append("Some inputs are assumptions or benchmarks. Label them on every deliverable.")
    if soft_in_roi:
        warnings.append("ROI includes non-hard benefits (" + ", ".join(b["label"] for b in soft_in_roi)
                        + "). State this explicitly next to the ROI figure.")
    if any(t["pricing_status"] == "estimated" for t in tools):
        warnings.append("Some tool pricing is estimated. Mark those cards 'Estimated' on the pricing infographic.")

    revenue_upside = sum(b["annual_value"] for b in benefits if b["type"] == "revenue" and not b["include_in_roi"])
    capacity_value = sum(b["annual_value"] for b in benefits if b["type"] == "capacity" and not b["include_in_roi"])
    capacity_hours_steady = sum(t["steady"]["net_hours_per_week"] for t in tasks if t["type"] == "capacity")

    totals = {
        "monthly_subscriptions": subs,
        "monthly_software_cost": subs,               # legacy key
        "annual_software_cost": subs * 12,           # legacy key
        "implementation_cost": impl["cost"],
        "implementation_mode": impl["mode"],
        "adoption_cost": adoption,
        "one_time_total": one_time,
        "monthly_maintenance": maint,
        "monthly_recurring_cost": recurring,
        "monthly_benefit_ramp": benefit_ramp,
        "monthly_benefit_steady": benefit_steady,
        "monthly_net_cash_flow_ramp": benefit_ramp - recurring,
        "monthly_net_cash_flow_steady": benefit_steady - recurring,
        "annual_gross_savings": gross_savings_annual,
        "first_year_tco": tco1,
        "first_year_benefit": ben1,
        "first_year_net_benefit": net1,
        "first_year_roi_pct": r0(roi1) if roi1 is not None else None,
        "steady_state_annual_cost": steady_cost,
        "steady_state_annual_benefit": steady_ben,
        "net_annual_benefit": net2,                  # steady state
        "steady_state_roi_pct": r0(roi2) if roi2 is not None else None,
        "weekly_hours_gross": r1(gross_week),
        "weekly_hours_net_ramp": r1(net_ramp_week),
        "weekly_hours_net_steady": r1(net_steady_week),
        "weekly_hours_saved": r1(net_steady_week),   # legacy key, now net
        "annual_hours_gross": r0(gross_week * weeks),
        "annual_hours_net_steady": r0(net_steady_week * weeks),
        "annual_hours_saved": r0(net_steady_week * weeks),  # legacy key, now net
        "first_year_net_hours": r0(first_year_net_hours),
        "weekly_capacity_hours_not_in_roi": r1(capacity_hours_steady),
        "annual_revenue_upside_not_in_roi": r0(revenue_upside),
        "annual_capacity_value_not_in_roi": r0(capacity_value),
        "payback_status": payback["status"],
        "payback_months": payback["months"],
        "payback_text": payback["text"],
    }
    result = {
        "client": data.get("client"),
        "workflow": data.get("workflow"),
        "weeks_per_year": weeks,
        "timing": {k: base[k] for k in ("go_live", "ramp_months", "recurring_start", "one_time_months")},
        "tools": tools,
        "implementation": impl,
        "tasks": tasks,
        "benefits": benefits,
        "totals": totals,
        "operating_break_even": obe,
        "sensitivity": sens,
        "scenarios": scenarios,
        "schedule": payback["schedule"],
        "assumptions": [{**a, "source_label": SOURCE_LABELS.get(a["source"], a["source"].capitalize())}
                        for a in assumptions],
        "formulas": formulas,
        "warnings": warnings,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2))
    if args.schedule_out:
        args.schedule_out.parent.mkdir(parents=True, exist_ok=True)
        args.schedule_out.write_text(json.dumps(result, indent=2))

    print("## Pricing")
    for t in tools:
        tag = "Verified" if t["pricing_status"] == "verified" else "Estimated"
        print(f"- {t['name']}{' (' + t['plan'] + ')' if t['plan'] else ''}: ${t['monthly_cost']:,.2f}/month [{tag}]"
              + (f"  <- {t['llm_calc']}" if t["llm_calc"] else ""))
    print("\n## Formulas (copy into roi-calculations.md)")
    for f in formulas:
        print(f"- {f}")
    if revenue_upside:
        print(f"- Revenue upside, not counted in ROI: {money(revenue_upside)}/year")
    if capacity_value:
        print(f"- Value of redeployed capacity, not counted in ROI: {money(capacity_value)}/year")
    print("\n## Sensitivity")
    for s in sens:
        print(f"- {s['label']}: payback {s['payback_text']}")
    for sc in scenarios:
        print(f"- Scenario {sc['name']}: payback {sc['payback_text']}")
    print("\n## Cash-flow schedule")
    print("| Month | Phase | One-time | Recurring | Net benefit | Net cash flow | Cumulative |")
    print("|---|---|---|---|---|---|---|")
    for r in payback["schedule"]:
        print(f"| {r['month']} | {r['phase']} | {money(r['one_time_cost'])} | {money(r['recurring_cost'])} | "
              f"{money(r['net_benefit'])} | {money(r['net_cash_flow'])} | {money(r['cumulative'])} |")
    if warnings:
        print("\n## Warnings")
        for w in warnings:
            print(f"- {w}")
    print(f"\nSaved: {args.out}" + (f" and {args.schedule_out}" if args.schedule_out else ""))


if __name__ == "__main__":
    main()
