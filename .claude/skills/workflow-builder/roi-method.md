# ROI Method

Claude does the cost and ROI math directly from the discovery answers and the research, and shows every headline line in `roi-calculations.md`. `tools/calc_workflow_roi.py` is **required** at Step 7: it produces the month-by-month cash-flow schedule, the payback period, the operating break-even and the sensitivity cases, and it cross-checks the hand math. Its input format is in its docstring, and a full example is in `examples/worked-example-inputs.json`. The two must agree before anything is shown to the user. This file explains how to keep the numbers honest.

## Classify every benefit

| Type | Use when | Counted in gross savings? |
|---|---|---|
| Avoided labor | Labor cost actually goes away: fewer contractor or temp hours, overtime removed, a planned hire not needed, outsourcing cancelled | Yes |
| Cost reduction | A non-labor cost is removed: a replaced tool subscription, error penalties or refunds avoided (use the client's error rate × cost per error) | Yes |
| Capacity | Time is freed but the same people stay on payroll and do other work (the usual case for salaried staff) | No. Report the hours, and optionally a value, separately |
| Revenue | More conversions, faster follow-ups, more clients served | No, unless the user confirms it should count; then label it clearly |

The deciding discovery question is: *"Once this workflow saves you that time, what would you do with those hours?"*
- "We'd stop paying for X / wouldn't need to hire" → avoided labor
- "My team would spend it on clients / selling / strategy" → capacity (plus revenue only if they can quantify a revenue effect)

Salaried time freed is **not** a cash saving. You may still show its value ("≈ $X of team time redeployed") as capacity, but keep it out of net benefit unless the user explicitly asks for a labor-value ROI, in which case label the headline "Value of time saved" rather than "Savings".

## Sources and assumptions

- **Client-stated** means the user gave the figure in discovery (or confirmed it at Step 7).
- **Assumption** means you derived it. Write down the reasoning, for example "industry-typical loaded cost of $35/h for an SDR; user did not know", and have the user confirm it.
- **Benchmark** means a range from [cost-benchmarks.md](cost-benchmarks.md), offered only when the client has no figure. State the range, the value picked and why, its label (Published benchmark or Practitioner estimate (unsourced)) and the source URL. The user confirms or replaces it.
- Revenue estimates need an explicit chain: volume × current conversion → expected conversion × average deal value, with every link sourced or labeled.
- Don't double count: hours counted as avoided labor must not also appear as capacity, and review and rework are deducted from hours saved, never also added as a cost line.

## Costs

Every cost belongs to one of five components. The implementation mode from discovery decides how the first one is priced.

### 1. Implementation (one-time)

| Mode | Formula |
|---|---|
| Self-implement | internal hours × the implementer's loaded hourly value |
| Freelancer | hours × rate, or their fixed quote |
| Agency | their fixed quote |
| Undecided | price the mode the user considers most likely, and give the other modes as a range in the README |

With no quote, estimate hours with the **phase model** in cost-benchmarks.md (discovery + build per workflow + testing at 0.7–1.0 × build + handoff + hypercare), labeled as a practitioner estimate. An optional contingency buffer (for example the 15–20% that agencies add) applies to *estimates* only, never on top of a real quote.

**Cost-to-serve vs. price.** Builder effort (hours, judgment, testing) informs the implementation *estimate*. What the client *pays* is the quote or the rate. When there's a fixed quote, the quote is the implementation cost. Don't add a separate builder-effort line on top of it.

### 2. Adoption and training (one-time)

Client-stated internal hours × loaded rate (for example "4 people × 5 h × $50/h"), or a labeled percentage of implementation cost (15–20% change-management benchmark) when they can't estimate hours.

### 3. Maintenance (recurring)

In order of preference: their retainer if they have one; otherwise hours per month × rate; otherwise a labeled percentage of build cost per year ÷ 12. Always check the result against the benchmark range (15–25% of build cost per year) and show the implied hours per month. The benchmarks disagree (see cost-benchmarks.md), so say which one you used. If the client owns maintenance internally, price the owner's hours at their loaded rate.

### 4. Human review and rework (recurring, as a reduction in hours saved)

Review and rework are **not** a separate cost line. They reduce the hours saved, so nothing is counted twice.

For each automated task type, and separately for the **ramp** (the first 3 months after go-live, unless the client says otherwise) and **steady state**:

- Review hours/week = units per week × review share × minutes per review ÷ 60 (or client-stated review hours)
- Rework hours/week = rework % × gross hours automated (or client-stated rework hours)
- **Net hours saved = gross hours automated − review hours − rework hours**

Value only avoided-labor tasks, and value them net of the review time at the **reviewer's** rate, which may differ from the rate of the person whose work was automated:

- **Weekly labor benefit = gross hours × automated person's rate − (review + rework hours) × reviewer's rate**

When the two rates are the same, this equals net hours × rate. Deducting review time at the reviewer's rate is deliberately conservative, even when the reviewer is salaried: added review work isn't free. Take review shares from discovery, or from the task-type table in cost-benchmarks.md as a labeled assumption, and state the review plan for each AI step (full approval, sampled, or exception-only). Capacity tasks get the same net-hours treatment, but their value stays out of ROI.

### 5. Subscriptions and LLM usage (recurring)

- Include only tools the client must newly pay for. Tools they already own go in the README ("already licensed, no added cost"), not on the infographic.
- **Verified** = the price was read on the official pricing page during research (cite the URL). **Estimated** = usage-based or derived.
- LLM cost per month = runs per month × (input tokens × input price per 1M + output tokens × output price per 1M) ÷ 1,000,000. Use realistic tokens per run: count the prompt, the input document, tool results and output. Agents often make 2-5 model calls per run, so multiply accordingly. LLM usage costs are always labeled Estimated, and they scale with volume, which matters for the operating break-even.
- Platform consumption: check the monthly volume against the plan limits and upgrade the plan if it's exceeded (Make operations = modules executed per run × items; Zapier tasks = action steps per run; n8n Cloud executions = runs).
- Monthly prices assume the billing term you state (monthly vs annual billing). Be consistent.

## Timing and the monthly cash-flow schedule

- **Month 0** is setup: the one-time costs (implementation + adoption) land there, unless the client says they're spread over several months.
- **Go-live** defaults to month 1. Recurring costs (subscriptions + maintenance) and benefits start at go-live, unless the client says subscriptions start earlier.
- **Ramp** = the first 3 months after go-live (review and rework at ramp levels). Steady-state values apply after that.

For each month from 0 to 24, list: one-time costs, recurring costs, net benefit (the monthly labor benefit plus any other counted benefits), net cash flow (net benefit − one-time − recurring), and the cumulative net position. Monthly value = weekly value × weeks per year ÷ 12. Round each monthly figure to whole dollars **before** it enters the schedule, so the schedule, the chat and every deliverable use the same numbers.

- **Payback period** = the first month in which the cumulative net position reaches zero or above, interpolated within that month to one decimal: (m − 1) + (−cumulative at month m − 1 ÷ net cash flow in month m). Always say that it's interpolated. With no one-time costs, payback is "Immediate (no one-time costs)".
- **Operating break-even** = the monthly net hours saved (and the task volume, where the workflow has a countable unit such as emails, leads or meetings) at which the monthly benefit equals the monthly recurring cost. It assumes every task scales with volume in proportion, and that LLM usage cost scales with it:
  - share of expected volume = (fixed recurring cost − other counted monthly benefits) ÷ (steady monthly labor benefit − monthly usage-based cost)
  - break-even net hours/month = share × expected steady net hours/month (avoided-labor tasks)
  - break-even units/month = share × expected units/month, **rounded up**

  This is the minimum use for the workflow to pay its own running costs, which is separate from recovering the setup cost. If the steady labor benefit is at or below the usage-based cost, no volume covers the running costs; say so.

**Edge cases:**
- If steady-state monthly benefit ≤ monthly recurring cost, the workflow **never breaks even**. Say so plainly, report no payback period, and give the operating break-even as the volume it would need.
- If payback falls after month 24, extend the schedule to 36 months. If it's still not reached, report "Not reached within 36 months".

## Outputs and math rules

Show every calculation as a written-out line (inputs → operation → result), the way the worked example does, so the user can check it. Report all of these, each labeled with its assumptions:

- **One-time total** = implementation + adoption
- **Monthly recurring cost** = subscriptions + maintenance
- **First-year TCO** = one-time total + 12 × monthly recurring cost
- **Steady-state annual cost** = 12 × monthly recurring cost
- **First-year benefit** = 3 × ramp monthly benefit + 9 × steady monthly benefit (adjust if the ramp length differs)
- **First-year ROI** = (first-year benefit − first-year TCO) ÷ first-year TCO × 100
- **Steady-state (year 2) ROI** = (12 × steady monthly benefit − steady-state annual cost) ÷ steady-state annual cost × 100
- **Payback period** and **operating break-even** (see above)
- **Hours:** weekly gross (labeled gross), weekly net at ramp and at steady state, annual gross, annual net at steady state, and first-year net hours
- **Annual gross savings** (gross hours × rate × weeks, before review, rework and costs), clearly labeled so it's never mistaken for the net benefit
- **Sensitivity** (computed by the tool, never estimated): payback if net hours saved come in 25% lower, and if review stays at ramp levels
- Any revenue upside or capacity value, kept outside ROI unless the user confirms otherwise

Keep **gross savings**, **net benefit** and **ROI** as separate, clearly named figures. Recompute every line once before showing it. Round money to whole dollars, percentages to whole numbers, hours to one decimal, and payback to one decimal, and use the same rounded figures everywhere (the chat, `roi-calculations.md`, both infographics and the payback report).

## Worked example (the reference case)

Inputs are in `examples/worked-example-inputs.json`. A small B2B company automates two tasks in n8n, built by a freelancer. The ops manager ($40/h loaded) reviews the output. Contractor hours at $30/h are cut, so the benefit is avoided labor (client-stated).

**Recurring subscriptions**
- n8n Cloud Starter: $50/month (Verified; illustrative)
- LLM usage: 350 runs × (4,000 in × $2.50/M + 1,000 out × $10/M) = 350 × $0.02 = $7/month (Estimated)
- Monthly subscriptions: $50 + $7 = $57

**One-time costs**
- Implementation (freelancer, no quote; phase model = practitioner estimate; $90/h within the $40–100/h published Upwork range): (10 discovery + 16 build [2 workflows × 8 h] + 16 testing [1.0 × build] + 6 handoff + 12 hypercare) = 60 h × $90/h = $5,400
- Adoption and training (client-stated): 4 people × 5 h = 20 h × $50/h = $1,000
- One-time total: $5,400 + $1,000 = $6,400

**Maintenance**
- 20% of build per year (published benchmark, middle of 15–25%): 20% × $5,400 ÷ 12 = $90/month. That implies 1 h/month at $90/h, below the 5–12 h/month practitioner estimate. The benchmarks disagree, so flag it to the user.
- Monthly recurring cost: $57 subscriptions + $90 maintenance = $147

**Net hours saved (review shares are labeled assumptions from the cost-benchmarks.md task-type table; 3 min per review)**

| Task | Phase | Gross h/wk | Review h/wk | Rework h/wk | Net h/wk | Weekly value |
|---|---|---|---|---|---|---|
| CRM record sync (200 records/wk) | Ramp | 10 | 200 × 10% × 3 ÷ 60 = 1.0 | 5% × 10 = 0.5 | 8.5 | 10 × $30 − 1.5 × $40 = $240 |
| | Steady | 10 | 200 × 5% × 3 ÷ 60 = 0.5 | 0% = 0 | 9.5 | 10 × $30 − 0.5 × $40 = $280 |
| AI-drafted follow-up emails (80/wk) | Ramp | 8 | 80 × 100% × 3 ÷ 60 = 4.0 | 10% × 8 = 0.8 | 3.2 | 8 × $30 − 4.8 × $40 = $48 |
| | Steady | 8 | 80 × 15% × 3 ÷ 60 = 0.6 | 5% × 8 = 0.4 | 7.0 | 8 × $30 − 1.0 × $40 = $200 |

- Weekly hours: 18 gross; net 11.7 (ramp), 16.5 (steady state)
- Monthly labor benefit, ramp: ($240 + $48) = $288/week × 52 ÷ 12 = $1,248
- Monthly labor benefit, steady: ($280 + $200) = $480/week × 52 ÷ 12 = $2,080
- Monthly net cash flow once running: ramp $1,248 − $147 = $1,101; steady $2,080 − $147 = $1,933

**Headline figures**
- First-year TCO: $6,400 + 12 × $147 = $8,164
- First-year benefit: 3 × $1,248 + 9 × $2,080 = $3,744 + $18,720 = $22,464
- First-year net benefit: $22,464 − $8,164 = $14,300
- First-year ROI: $14,300 ÷ $8,164 × 100 = 175%
- Steady-state annual cost: 12 × $147 = $1,764
- Steady-state annual benefit: 12 × $2,080 = $24,960
- Steady-state net annual benefit: $24,960 − $1,764 = $23,196
- Steady-state (year 2) ROI: $23,196 ÷ $1,764 × 100 = 1,315%
- Annual hours: 18 × 52 = 936 gross; 16.5 × 52 = 858 net at steady state
- First-year net hours: (3 × 11.7 + 9 × 16.5) × 52 ÷ 12 = 796
- Annual gross savings (before review, rework and costs): 18 × $30 × 52 = $28,080

**Cash-flow schedule (months 0–6; the tool writes all 24)**

| Month | Phase | One-time | Recurring | Net benefit | Net cash flow | Cumulative |
|---|---|---|---|---|---|---|
| 0 | Setup | $6,400 | $0 | $0 | −$6,400 | −$6,400 |
| 1 | Ramp | $0 | $147 | $1,248 | $1,101 | −$5,299 |
| 2 | Ramp | $0 | $147 | $1,248 | $1,101 | −$4,198 |
| 3 | Ramp | $0 | $147 | $1,248 | $1,101 | −$3,097 |
| 4 | Steady | $0 | $147 | $2,080 | $1,933 | −$1,164 |
| 5 | Steady | $0 | $147 | $2,080 | $1,933 | $769 |
| 6 | Steady | $0 | $147 | $2,080 | $1,933 | $2,702 |

Month 12 cumulative = $14,300, which reconciles with the first-year net benefit. Month 24 cumulative = $14,300 + 12 × $1,933 = $37,496, which reconciles with the first-year net plus the steady-state net annual benefit ($23,196).

- **Payback period:** cumulative first reaches ≥ 0 in month 5. Interpolated: 4 + $1,164 ÷ $1,933 = 4.6 months.
- **Operating break-even:** fixed recurring = $147 − $7 usage-based LLM = $140. Share = ($140 − $0 other benefits) ÷ ($2,080 − $7) = 6.75%, about 7% of expected volume. Net hours: 16.5 × 52 ÷ 12 = 71.5 expected net h/month × 6.75% = 4.8 net hours/month. Units (rounded up): 866.7 records × 6.75% = 59 records/month, and 346.7 emails × 6.75% = 24 emails/month.
- **Sensitivity (tool):** net hours saved 25% lower → payback 5.9 months. Review stays at ramp levels → payback 5.8 months.

`tools/calc_workflow_roi.py --in examples/worked-example-inputs.json` reproduces every line above.
