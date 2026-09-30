"""Payback and break-even report for /workflow-builder.

Reads the schedule JSON written by tools/calc_workflow_roi.py (--schedule-out) and
produces a plain-language report for a non-finance reader:
  payback-chart.png    cumulative net position by month (matplotlib, exact values, no credits)
  payback-report.html  self-contained report with the chart embedded; prints cleanly to PDF

Every number comes from the schedule JSON; this script does no new math beyond
formatting. Rules and the approval flow are in
.claude/skills/workflow-builder/payback-report-guide.md.

Usage:
    # 1. Preview the bottom line and key numbers for user approval (writes nothing)
    .venv/bin/python tools/build_payback_report.py --schedule <dir>/payback-schedule.json --preview

    # 2. Generate, checking every key figure appears in roi-calculations.md
    .venv/bin/python tools/build_payback_report.py --schedule <dir>/payback-schedule.json \
        --check <dir>/roi-calculations.md --out-dir <dir> [--bottom-line-file approved.txt]

--check stops with exit code 2 if any key figure is missing from roi-calculations.md.
--bottom-line-file replaces the generated bottom line with the user-approved wording.
"""

import argparse
import base64
import html
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

# Colors: expected line in blue; loss/gain tints are also told apart by hatching so they survive grayscale.
INK, INK_2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
LINE = "#2a78d6"
LOSS, GAIN, RAMP = "#e34948", "#1baf7a", "#f0efec"
SCENARIO_STYLES = [(INK_2, (0, (6, 3))), (INK_2, (0, (1, 2.5))), (MUTED, (0, (3, 2, 1, 2)))]


def money(x: float) -> str:
    x = int(round(x))
    return f"-${abs(x):,}" if x < 0 else f"${x:,}"


def pct(x) -> str:
    return "n/a" if x is None else f"{x:,}%"


def esc(s) -> str:
    return html.escape("" if s is None else str(s))


# ------------------------------------------------------------------ text

def bottom_line(d: dict) -> str:
    t, tim = d["totals"], d["timing"]
    one_time, rec = money(t["one_time_total"]), money(t["monthly_recurring_cost"])
    steady_net = money(t["monthly_net_cash_flow_steady"])
    status = t["payback_status"]
    if status == "reached":
        return (f"This workflow pays for itself in about {t['payback_months']:g} months. "
                f"It costs {one_time} up front and {rec} a month to run. "
                f"Once it settles in (after the first {tim['ramp_months']} months), it returns about "
                f"{steady_net} a month after running costs.")
    if status == "not_reached":
        return (f"This workflow does not pay for itself within 36 months. It costs {one_time} up front and "
                f"{rec} a month to run, and once settled it returns only about {steady_net} a month after "
                "running costs, so recovering the setup cost takes longer than three years.")
    obe = d["operating_break_even"]
    need = (f" To cover its running costs it would need about {obe['share_of_expected_volume_pct']}% of the "
            f"expected volume ({obe['text']})." if obe.get("share_of_expected_volume_pct") else "")
    return (f"At these numbers this workflow never pays for itself. Once running it saves about "
            f"{money(t['monthly_benefit_steady'])} a month but costs {rec} a month to run, so the "
            f"{one_time} setup cost is never recovered.{need}")


def key_numbers(d: dict) -> list:
    t, obe = d["totals"], d["operating_break_even"]
    return [
        ("Total one-time cost", money(t["one_time_total"]),
         f"Implementation {money(t['implementation_cost'])} + adoption and training {money(t['adoption_cost'])}"),
        ("Monthly recurring cost", money(t["monthly_recurring_cost"]),
         f"Subscriptions {money(t['monthly_subscriptions'])} + maintenance {money(t['monthly_maintenance'])}"),
        ("Monthly net benefit, first months", money(t["monthly_benefit_ramp"]),
         f"Months 1-{d['timing']['ramp_months']}, while review is heavier"),
        ("Monthly net benefit, once settled", money(t["monthly_benefit_steady"]), "Steady state"),
        ("Payback period", t["payback_text"], "When cumulative savings cover every cost so far"),
        ("Operating break-even", obe["text"], "Minimum use to cover the monthly running cost"),
        ("First-year return (ROI)", pct(t["first_year_roi_pct"]),
         f"On first-year total cost of {money(t['first_year_tco'])}"),
        ("Ongoing yearly return (ROI)", pct(t["steady_state_roi_pct"]),
         f"Year 2 on, on running costs of {money(t['steady_state_annual_cost'])}/year"),
    ]


def break_even_text(d: dict) -> str:
    t, obe = d["totals"], d["operating_break_even"]
    one_time, rec = money(t["one_time_total"]), money(t["monthly_recurring_cost"])
    part1 = (f"<p><strong>Payback</strong> is when the savings have repaid everything spent so far, including the "
             f"{one_time} setup cost. Here that is <strong>{esc(t['payback_text'])}</strong>.</p>")
    if obe.get("share_of_expected_volume_pct") is not None:
        part2 = (f"<p><strong>Operating break-even</strong> is the minimum use at which the workflow covers its own "
                 f"running cost of {rec} a month, ignoring the setup cost. Here that is "
                 f"<strong>{esc(obe['text'])}</strong>, about {obe['share_of_expected_volume_pct']}% of the volume "
                 f"expected. Below that level it costs more to run than it saves; above it, every extra unit adds "
                 f"to the savings.</p>")
    else:
        part2 = f"<p><strong>Operating break-even:</strong> {esc(obe['text'])}.</p>"
    return part1 + part2


# ------------------------------------------------------------------ chart

def draw_chart(d: dict, out: Path) -> None:
    sched = d["schedule"]
    t, tim = d["totals"], d["timing"]
    months = [r["month"] for r in sched]
    cum = [r["cumulative"] for r in sched]
    horizon = months[-1]

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15})
    fig, ax = plt.subplots(figsize=(12, 6.6), dpi=200)
    fig.patch.set_facecolor("white")

    # Ramp period: the months after go-live, drawn as the span that leads up to each month-end point.
    r0 = tim["go_live"] - 1
    ax.axvspan(r0, r0 + tim["ramp_months"], color=RAMP, zorder=0, lw=0)

    ax.fill_between(months, cum, 0, where=[c <= 0 for c in cum], interpolate=True,
                    facecolor=LOSS, alpha=0.14, edgecolor=LOSS, hatch="///", linewidth=0, zorder=1)
    ax.fill_between(months, cum, 0, where=[c >= 0 for c in cum], interpolate=True,
                    facecolor=GAIN, alpha=0.18, linewidth=0, zorder=1)
    ax.axhline(0, color=INK, lw=1.4, zorder=2)

    for i, sc in enumerate(d.get("scenarios", [])):
        color, dash = SCENARIO_STYLES[i % len(SCENARIO_STYLES)]
        ys = sc["cumulative"][: horizon + 1]
        ax.plot(months[: len(ys)], ys, color=color, lw=2, linestyle=dash, zorder=3,
                label=f"{sc['name']} (payback: {sc['payback_text'].lower()})")
    ax.plot(months, cum, color=LINE, lw=3, marker="o", markersize=5, zorder=4,
            label=f"Expected (payback: {t['payback_text'].lower()})")

    lo, hi = min(cum + [0]), max(cum + [0])
    for sc in d.get("scenarios", []):
        lo, hi = min(lo, *sc["cumulative"]), max(hi, *sc["cumulative"])
    span = (hi - lo) or 1
    late_pb = t["payback_status"] == "reached" and t["payback_months"] > horizon * 0.55
    ax.set_ylim(lo - 0.12 * span, hi + (0.34 if late_pb else 0.18) * span)
    ax.set_xlim(0, horizon + 0.3)
    ymin, ymax = ax.get_ylim()

    # Labels: text sits on a white chip so reference lines pass behind it. Labels go on the side away from
    # the payback crossing so they never collide with the callout.
    chip = {"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "none", "alpha": 0.9}
    status = t["payback_status"]
    pb = t["payback_months"] if status == "reached" else None
    late = pb is not None and pb > horizon * 0.55
    ax.text(horizon if not late else r0 + tim["ramp_months"] + 0.3, 0, " Break-even ",
            ha="right" if not late else "left", va="bottom", fontsize=14, color=INK, fontweight="bold",
            bbox=chip, zorder=6)
    if lo < 0:
        ax.text(0.25, ymin + 0.03 * span, "Net loss (never recovered)" if status == "never" else "Recovering setup cost",
                ha="left", va="bottom", fontsize=14, color=LOSS, fontweight="bold", bbox=chip, zorder=6)
    ax.text(r0 + tim["ramp_months"] / 2, ymax - 0.02 * span, "Ramp-up\n(heavier review)", ha="center",
            va="top", fontsize=12, color=INK_2, zorder=6)

    if pb is not None:
        ax.axvline(pb, color=INK, lw=1.4, linestyle=(0, (4, 3)), zorder=3)
        ty = ymax - 0.03 * span if late else max(ymax - 0.2 * span, 0.35 * span)
        ax.annotate(f"Pays back in month {pb:g}", xy=(pb, 0), xytext=(pb - 0.8 if late else pb + 0.8, ty),
                    fontsize=16, fontweight="bold", color=INK, ha="right" if late else "left", va="top",
                    bbox=chip, zorder=7, arrowprops={"arrowstyle": "->", "color": INK, "lw": 1.4})
    else:
        ax.text(horizon / 2, ymax - 0.06 * span, "Does not pay back" + (
            " at these numbers" if status == "never" else f" within {horizon} months"),
            ha="center", va="top", fontsize=16, fontweight="bold", color=LOSS, bbox=chip, zorder=7)

    end = cum[-1]
    end_text = (f"Net gain: {money(end)} after {horizon} months" if end >= 0
                else f"{money(end)} after {horizon} months")
    ax.annotate(end_text, xy=(horizon, end), xytext=(-10, 14 if end >= 0 else -14), textcoords="offset points",
                ha="right", va="bottom" if end >= 0 else "top", fontsize=14, fontweight="bold",
                color="#0d7a55" if end >= 0 else LOSS, bbox=chip, zorder=8)

    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: money(v)))
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=13))
    ax.set_xlabel("Months after the project starts", fontsize=15, color=INK_2, labelpad=8)
    ax.set_ylabel("Total savings minus total costs", fontsize=15, color=INK_2, labelpad=8)
    ax.tick_params(colors=INK_2, labelsize=13, length=0)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)

    title = "When the investment pays for itself"
    sub = " · ".join(x for x in (d.get("client"), d.get("workflow")) if x)
    fig.text(0.07, 0.965, title, fontsize=21, fontweight="bold", color=INK, ha="left", va="top")
    if sub:
        fig.text(0.07, 0.905, sub, fontsize=14, color=INK_2, ha="left", va="top")
    if d.get("scenarios"):
        ax.legend(loc="lower right", frameon=False, fontsize=12)
    fig.subplots_adjust(left=0.13, right=0.97, top=0.84, bottom=0.12)
    fig.savefig(out, facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ html

CSS = """
:root { --ink:#0b0b0b; --ink2:#52514e; --muted:#8a8984; --line:#e6e5e0; --bg:#ffffff; --tint:#f6f6f3;
        --accent:#2a78d6; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font:16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width: 880px; margin: 0 auto; padding: 40px 16px 64px; }
h1 { font-size: 28px; margin: 0 0 4px; }
.sub { color: var(--ink2); margin: 0 0 28px; }
h2 { font-size: 19px; margin: 36px 0 10px; padding-top: 8px; border-top: 1px solid var(--line); }
.bottom { font-size: 19px; line-height: 1.5; background: var(--tint); border-left: 4px solid var(--accent);
          padding: 16px 20px; border-radius: 6px; }
figure { margin: 0; }
figure img { width: 100%; height: auto; display: block; }
figcaption { color: var(--ink2); font-size: 14px; margin-top: 6px; }
table { width: 100%; border-collapse: collapse; font-size: 15px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--ink2); font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: .03em; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.kn td:first-child { font-weight: 600; }
.kn td.val { font-size: 17px; font-weight: 700; white-space: nowrap; }
.note { color: var(--ink2); font-size: 14px; }
.tag { display:inline-block; font-size: 12px; padding: 1px 8px; border-radius: 10px; border: 1px solid var(--muted);
       color: var(--ink2); white-space: nowrap; }
.neg { color: #b42c2b; }
.table-wrap { overflow-x: auto; }
a { color: var(--accent); word-break: break-all; }
@media print {
  main { padding: 0; max-width: none; }
  h2 { break-after: avoid; }
  figure, .kn, .bottom { break-inside: avoid; }
  tr { break-inside: avoid; }
  a { color: var(--ink); }
}
"""


def build_html(d: dict, chart_png: Path, bottom: str) -> str:
    t, tim = d["totals"], d["timing"]
    img = base64.b64encode(chart_png.read_bytes()).decode()
    title = "Payback and Break-Even"
    sub = " · ".join(esc(x) for x in (d.get("client"), d.get("workflow")) if x)

    kn_rows = "".join(f"<tr><td>{esc(a)}</td><td class='val'>{esc(b)}</td><td class='note'>{esc(c)}</td></tr>"
                      for a, b, c in key_numbers(d))

    base_pb = t["payback_text"]
    sens_rows = f"<tr><td>Expected case</td><td class='num'>{money(t['monthly_benefit_steady'])}</td><td class='num'>{esc(base_pb)}</td></tr>"
    for s in d["sensitivity"]:
        sens_rows += (f"<tr><td>{esc(s['label'])}</td><td class='num'>{money(s['benefit_steady_monthly'])}</td>"
                      f"<td class='num'>{esc(s['payback_text'])}</td></tr>")
    for sc in d.get("scenarios", []):
        sens_rows += (f"<tr><td>{esc(sc['name'])} (confirmed range: {esc(sc['basis'])})</td>"
                      f"<td class='num'>{money(sc['benefit_steady'])}</td><td class='num'>{esc(sc['payback_text'])}</td></tr>")

    def src_cell(a):
        label = a.get("source_label") or a["source"]
        link = f"<br><a href='{esc(a['source_url'])}'>{esc(a['source_url'])}</a>" if a.get("source_url") else ""
        return f"<span class='tag'>{esc(label)}</span>{link}"

    as_rows = "".join(f"<tr><td>{esc(a['input'])}</td><td class='num'>{esc(a['value'])}</td><td>{src_cell(a)}</td>"
                      f"<td class='note'>{esc(a.get('basis'))}</td></tr>" for a in d["assumptions"])

    phase_names = {"build": "Setup", "ramp": "Ramp-up", "steady": "Steady"}
    sched_rows = "".join(
        f"<tr><td class='num'>{r['month']}</td><td>{phase_names.get(r['phase'], r['phase'])}</td>"
        f"<td class='num'>{money(r['one_time_cost'])}</td><td class='num'>{money(r['recurring_cost'])}</td>"
        f"<td class='num'>{money(r['net_benefit'])}</td>"
        f"<td class='num{' neg' if r['net_cash_flow'] < 0 else ''}'>{money(r['net_cash_flow'])}</td>"
        f"<td class='num{' neg' if r['cumulative'] < 0 else ''}'>{money(r['cumulative'])}</td></tr>"
        for r in d["schedule"])

    caption = ("The line shows total savings minus total costs so far. Below the black line the setup cost is "
               "still being recovered; where the line crosses it, the workflow has paid for itself.")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head>
<body><main>
<h1>{title}</h1>
<p class="sub">{sub}</p>

<h2>The bottom line</h2>
<p class="bottom">{esc(bottom)}</p>

<h2>The chart</h2>
<figure><img src="data:image/png;base64,{img}" alt="Cumulative net position by month. {esc(t['payback_text'])}.">
<figcaption>{caption}</figcaption></figure>

<h2>Key numbers</h2>
<table class="kn"><tbody>{kn_rows}</tbody></table>
<p class="note">Savings are net of the time people spend reviewing and fixing the workflow's output. Payback is
interpolated within the month to one decimal place.</p>

<h2>What break-even means here</h2>
{break_even_text(d)}

<h2>What could change the timeline</h2>
<table><thead><tr><th>If…</th><th class="num">Monthly benefit once settled</th><th class="num">Payback</th></tr></thead>
<tbody>{sens_rows}</tbody></table>
<p class="note">Each line is recalculated month by month, not estimated. "Review stays at ramp-period levels" means
the heavier review of the first {tim['ramp_months']} months never drops.</p>

<h2>Assumptions</h2>
<div class="table-wrap"><table><thead><tr><th>Input</th><th class="num">Value</th><th>Source</th><th>Basis</th></tr></thead>
<tbody>{as_rows}</tbody></table></div>

<h2>Month-by-month</h2>
<div class="table-wrap"><table><thead><tr><th class="num">Month</th><th>Phase</th><th class="num">One-time cost</th>
<th class="num">Running cost</th><th class="num">Net benefit</th><th class="num">Net cash flow</th>
<th class="num">Running total</th></tr></thead><tbody>{sched_rows}</tbody></table></div>
</main></body></html>
"""


# ------------------------------------------------------------------ check

def check_against(d: dict, calc_md: Path) -> list:
    """Key figures that must appear verbatim in roi-calculations.md."""
    t = d["totals"]
    text = calc_md.read_text()
    needed = {
        "one-time total": money(t["one_time_total"]),
        "monthly recurring cost": money(t["monthly_recurring_cost"]),
        "monthly benefit (ramp)": money(t["monthly_benefit_ramp"]),
        "monthly benefit (steady)": money(t["monthly_benefit_steady"]),
        "first-year TCO": money(t["first_year_tco"]),
        "payback": t["payback_text"],
    }
    if t["first_year_roi_pct"] is not None:
        needed["first-year ROI"] = pct(t["first_year_roi_pct"])
    if t["steady_state_roi_pct"] is not None:
        needed["steady-state ROI"] = pct(t["steady_state_roi_pct"])
    return [f"{k}: {v}" for k, v in needed.items() if v not in text]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schedule", required=True, type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--check", type=Path, help="roi-calculations.md; stop if a key figure is missing from it")
    ap.add_argument("--bottom-line-file", type=Path, help="user-approved bottom-line text")
    ap.add_argument("--preview", action="store_true", help="print the bottom line and key numbers only")
    args = ap.parse_args()

    d = json.loads(args.schedule.read_text())
    bottom = args.bottom_line_file.read_text().strip() if args.bottom_line_file else bottom_line(d)

    if args.preview:
        print("## Bottom line\n" + bottom + "\n\n## Key numbers")
        for a, b, c in key_numbers(d):
            print(f"- {a}: {b}  ({c})")
        return

    if not args.out_dir:
        sys.exit("ERROR: --out-dir is required unless --preview")
    if args.check:
        missing = check_against(d, args.check)
        if missing:
            print("STOP: these figures from the tool are not in " + str(args.check) + ":", file=sys.stderr)
            for m in missing:
                print(f"  - {m}", file=sys.stderr)
            print("Resolve the difference before producing the report.", file=sys.stderr)
            sys.exit(2)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    png = args.out_dir / "payback-chart.png"
    draw_chart(d, png)
    page = args.out_dir / "payback-report.html"
    page.write_text(build_html(d, png, bottom))
    print(f"Saved: {png}\nSaved: {page}")


if __name__ == "__main__":
    main()
