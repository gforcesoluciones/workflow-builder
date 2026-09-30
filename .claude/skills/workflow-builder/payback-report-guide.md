# Payback and Break-Even Report Guide

A separate deliverable from the workflow and the two infographics: a plain-language report that a business owner or executive with no finance background can understand in a couple of minutes. Built by `tools/build_payback_report.py` from the schedule JSON that `tools/calc_workflow_roi.py --schedule-out` writes at Step 7. **It is free: no image-generation credits.**

## Outputs

- `payback-chart.png`: the chart on its own (2400×1320 px)
- `payback-report.html`: self-contained (inline CSS, chart embedded as base64), and prints cleanly to PDF from a browser

## The chart (the centerpiece)

Drawn deterministically with matplotlib from the cash-flow schedule, so every plotted value is exact. The tool draws:

- The cumulative net position by month (x-axis: months 0–24, or 0–36 when the schedule was extended; y-axis: dollars, dollar-formatted ticks)
- A horizontal zero line labeled "Break-even"
- The payback month as a dashed vertical line with the callout "Pays back in month X.X". If there is no payback: "Does not pay back at these numbers" (never breaks even) or "Does not pay back within 36 months"
- Shading: hatched red below zero ("Recovering setup cost", or "Net loss (never recovered)" when it never breaks even) and plain green above zero. The hatching keeps the two regions distinguishable in grayscale.
- The ramp period (months 1–3 after go-live) as a gray band labeled "Ramp-up (heavier review)", so the shallower early slope is explained
- An end label: "Net gain: $X after N months" (or the negative position)
- **Scenario lines only when the user confirmed a range at Step 7** (the `scenarios` block in the ROI inputs, each with a `basis`). Conservative is dashed, optimistic is dotted, and each is labeled with its own payback. Never invent a range. With no confirmed range, draw the expected line alone.

## Report sections (in this order, plain language)

1. **The bottom line**: two or three sentences covering when the investment pays for itself, what it costs up front, and what it returns per month once running. If it never breaks even, say so here and say what would need to change (the operating break-even volume).
2. **The chart**, with a one-sentence caption on how to read it.
3. **Key numbers**: total one-time cost, monthly recurring cost, monthly net benefit (ramp and steady state), payback period, operating break-even, first-year ROI and steady-state ROI.
4. **What break-even means here**: the difference between recovering the setup cost (payback) and covering the running costs (operating break-even), using this client's numbers.
5. **What could change the timeline**: payback if net hours saved come in 25% lower, and if review stays at ramp-period levels, plus any confirmed scenarios. All computed by the tool, never estimated.
6. **Assumptions**: every input, labeled Client-stated, Confirmed assumption, Benchmark, verified price or estimated, with the benchmark or pricing source URL.
7. **Month-by-month table**: the full cash-flow schedule, at the end for anyone who wants the detail.

## Procedure (Step 9 in SKILL.md)

1. **Consistency check first.** The report copies numbers from the schedule JSON. Before generating anything, confirm the JSON came from the same confirmed inputs as `roi-calculations.md`. The `--check` flag verifies that the key figures (one-time total, monthly recurring, ramp and steady monthly benefit, first-year TCO, payback, both ROIs) appear verbatim in `roi-calculations.md`. If it stops with exit code 2, **stop and resolve the difference** (fix whichever side is wrong, rerun the ROI tool, and re-confirm with the user if a confirmed number changes) before producing the report.
2. **Approval.** Run with `--preview` to print the bottom-line text and key numbers. Show them to the user for approval, the same way infographic text is approved. If the user rewords the bottom line, save their wording to `.tmp/workflow-builder/<client-slug>/bottom-line.txt` and pass `--bottom-line-file`. Wording changes are fine, but any number in it must still match `roi-calculations.md`.
3. **Generate:**
   `.venv/bin/python tools/build_payback_report.py --schedule output/workflow-builder/<client-slug>/payback-schedule.json --check output/workflow-builder/<client-slug>/roi-calculations.md --out-dir output/workflow-builder/<client-slug> [--bottom-line-file <file>]`
4. **Verify** (view the PNG, then read the HTML):
   - [ ] The callout's payback month equals the payback in `roi-calculations.md` (to one decimal)
   - [ ] The curve crosses zero between the two months where the schedule's cumulative column changes sign
   - [ ] The x-axis runs 0–24, or 0–36 if the schedule was extended; the y-axis range contains every plotted value
   - [ ] The ramp band covers the right months; scenario lines appear only if the user confirmed them, and are labeled
   - [ ] No label overlaps another label, the line, or the callout (the tool places labels away from the crossing; check anyway)
   - [ ] Every figure in the HTML matches `roi-calculations.md` character for character ($, commas, %, one-decimal months)
   - [ ] The Assumptions table labels every input, and benchmark rows carry their source URL
   - [ ] Never-breaks-even case: the bottom line says so, the chart stays below zero with no payback line, and the report gives the operating break-even volume needed

   If anything is wrong, fix the inputs or the tool and regenerate (it's free). If the tool itself was wrong, fix it and note the lesson here.

## Rules

- Every number in the report and chart must be copied from, or computed by the tool from, the confirmed figures in `roi-calculations.md`.
- Use the skill's rounding: whole dollars, whole percentages, hours and payback months to one decimal, break-even units rounded up.
- Plain language: no "NPV", "IRR" or "amortization". Say "pays for itself", "running cost" and "up-front cost". ROI is shown as "First-year return (ROI)" and "Ongoing yearly return (ROI)".
- Savings are always described as net of human review and rework.
