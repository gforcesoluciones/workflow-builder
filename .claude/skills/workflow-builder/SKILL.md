---
name: workflow-builder
description: Use when someone describes business pain points and wants an AI workflow or automation recommended, scoped and priced, asks which AI workflow would give the best ROI, wants a solutions architect to design an n8n, Make or Zapier automation, or asks for pricing and ROI infographics, total cost of ownership, or a payback and break-even analysis for a proposed workflow.
argument-hint: [your pain points]
disable-model-invocation: true
---

## What This Skill Does

Acts as an AI Solutions Architect. Starting from the user's pain points, it runs an adaptive discovery interview, scopes the highest-ROI AI workflow, researches n8n, Make and Zapier (plus the LLMs and other tools) from official sources with Firecrawl, picks the best fit without vendor bias, and delivers four parts:

1. **The Workflow**: created directly in the client's n8n or Make account (plus an importable file and a `.env.example`). For Zapier: a design plus a ready-to-paste prompt for Zapier's AI Copilot, which builds the Zap.
2. **The Pricing Infographic**: the full cost of ownership: monthly subscriptions, plus one-time implementation and adoption costs and recurring maintenance, priced for the implementation mode chosen in discovery.
3. **The ROI Infographic**: the business value, with net hours saved (after human review and rework), first-year and ongoing ROI, and payback, all with accurate, clearly labeled math.
4. **The Payback and Break-Even Report**: a plain-language HTML report with an exact chart of when the investment pays for itself, plus the operating break-even.

**Pain points:** $ARGUMENTS (if empty, ask the user to describe their pain points before doing anything else)

## Context

- **Reference files in this skill folder** (read each when its step says so, not all up front):
  - [discovery-guide.md](discovery-guide.md): the question bank, adaptive rules, sufficiency checklist and scope template.
  - [solution-design.md](solution-design.md): platform evaluation criteria, official sources, the research subagent prompt, LLM selection and the vector database decision rubric.
  - [roi-method.md](roi-method.md): how to classify benefits and do the cost, ROI, cash-flow, payback and break-even math (with a worked example).
  - [cost-benchmarks.md](cost-benchmarks.md): default ranges (rates, setup fees, maintenance, review shares, ramp, adoption) to offer as labeled assumptions when the client has no number.
  - [infographic-guide.md](infographic-guide.md): prompt templates and verification for both infographics.
  - [payback-report-guide.md](payback-report-guide.md): the chart spec, report sections, approval and verification for the payback report.
  - `examples/worked-example-inputs.json`: the ROI tool input for the worked example in roi-method.md.
  - `design-reference/`: the user's design reference image for the infographics (`pricing image.jpg`).
- **Tools** (run with `.venv/bin/python` from the project root):
  - `tools/build_workflow.py`: turns a node spec into an n8n workflow JSON or Make blueprint with a clean layout, and with `--push` creates it in the user's account (keys in `.env`: `N8N_BASE_URL`, `N8N_API_KEY`, `MAKE_ZONE`, `MAKE_API_TOKEN`, `MAKE_TEAM_ID`).
  - `tools/calc_workflow_roi.py`: **required** at Step 7. It computes the monthly cash-flow schedule, payback, operating break-even and sensitivity, cross-checks your hand math, and writes the schedule JSON with `--schedule-out`. Free.
  - `tools/build_payback_report.py`: builds the payback chart (matplotlib) and HTML report from the schedule JSON (Step 9). Free, no credits.
  - `tools/kie_generate_image.py`: Nano Banana via kie.ai. **Costs credits** (about 18 credits per image at nano-banana-pro 2K).
  - `tools/overlay_logo.py`: optional G Force logo overlay. Free.
- **Research:** the Firecrawl MCP server (`.mcp.json` → `tools/run_firecrawl_mcp.sh`, key `FIRECRAWL_API_KEY` in `.env`). Its tools appear as `mcp__firecrawl__firecrawl_*`. Firecrawl scrapes use Firecrawl credits.
- **Zapier:** Zaps can't be created programmatically yet (Zapier-MCP has no create-Zap tool; see Learned identifiers in solution-design.md). For a Zapier pick, the skill writes a prompt the user pastes into the Zap editor's AI Copilot. If a later session finds a create-Zap tool on `Zapier-MCP` (`mcp__Zapier-MCP__*`), tell the user it's available and ask whether to use it instead.
- **Output:** `output/workflow-builder/<client-slug>/`. Research cache and scratch files go in `.tmp/workflow-builder/`.

## Steps

### Step 0: Preflight

1. Check that the Firecrawl tools (`mcp__firecrawl__firecrawl_scrape`, `..._search`, `..._map`) are available. If they are not, tell the user to add `FIRECRAWL_API_KEY` to `.env` and restart Claude Code (approving the `firecrawl` server from `.mcp.json` when prompted). Discovery can run meanwhile, but **do not start Step 4 without Firecrawl** and do not silently swap in another web tool. If the user explicitly says to use WebFetch/WebSearch instead, do so and note it in the research file.
2. Check `design-reference/` for an image. If it is empty, ask the user to drop their reference image there before Step 8. It isn't needed until then.
3. Check that the n8n and Make keys are set in `.env` (report only set/missing, never print values). They don't block discovery, but Step 6 needs the one for the chosen platform.
4. Check that `.venv` has matplotlib (`.venv/bin/python -c "import matplotlib"`). If not, install it from `requirements.txt` before Step 9.
5. Pick a short client slug (company name, or ask) and create `output/workflow-builder/<client-slug>/`.

### Step 1: Intake

Restate the pain points in 2-4 bullets in plain language, name the likely workflow categories (for example lead routing, document extraction, support triage, reporting), and say that you'll ask a few rounds of questions to scope it properly. Don't recommend anything yet.

### Step 2: Adaptive discovery

Read [discovery-guide.md](discovery-guide.md) and follow it.

- Ask in **rounds of at most 4 questions**. Use `AskUserQuestion` for categorical questions (company size, trigger type, data format, platform preference) and plain chat questions for numbers and descriptions.
- **Choose every question based on what you already know.** Skip anything already answered (including in `$ARGUMENTS`), never ask a question whose answer wouldn't change the design or the ROI, and follow up whenever an answer is vague ("a lot of time" → "roughly how many hours a week, and across how many people?").
- After each round, append the answers to `output/workflow-builder/<client-slug>/discovery-notes.md` so nothing is lost if the conversation gets long.
- Continue until every item on the guide's **sufficiency checklist** is answered, or explicitly marked unknown and turned into a labeled assumption. Typically that takes 4-7 rounds.
- Always ask the **future-state question** ("Once we solve this, what other challenges or processes would you want to tackle next?"). Record the answers as *future phases* and use them to test scalability, not to grow the current scope.

### Step 3: Scope document and approval

Write `scope.md` using the template in discovery-guide.md: the current process, root causes, future-state workflow, triggers and actions, data sources and destinations, integrations, AI decision points, human approvals, error handling, security, monitoring, outcomes, success metrics, constraints, scalability, implementation mode, review plan per step, ownership and maintenance, adoption and go-live timing, **In scope (Phase 1)** vs **Future phases (out of scope)**, and **Open assumptions**.

Show the user a short summary and ask them to confirm or correct it. **Do not start research until the scope is approved.** A change requested later that falls outside Phase 1 goes into Future phases unless the user explicitly re-scopes.

### Step 4: Research (Firecrawl, official sources)

Read [solution-design.md](solution-design.md).

1. Check `.tmp/workflow-builder/research/` for a platform research file less than 14 days old. If one exists, ask the user whether to reuse it (it saves Firecrawl credits) or refresh it.
2. Otherwise, launch **one general-purpose subagent** with the research prompt from solution-design.md, filled in with this client's requirements. The subagent keeps the scraping out of the main context. Tell the user roughly how many pages it will scrape (usually 25-45 Firecrawl credits).
3. Save the returned report to `.tmp/workflow-builder/research/<YYYY-MM-DD>-platforms.md` (and copy it to the client folder as `research.md`). Every claim must carry its source URL and a **Verified** or **Unverified/Not documented** label.
4. Research the client-specific tools (the LLMs being considered, the chosen integrations, and a vector database if the rubric says one might be needed) the same way. Include these in the same subagent prompt when they are already known.

### Step 5: Solution design and recommendation

Using the scope and the research, decide on:

- **Platform** (n8n, Make or Zapier): score all three against the criteria in solution-design.md, weighted by what matters for *this* client. If the user already chose a platform, use it, but state its relevant limitations, risks and the strongest alternative. Don't favor n8n or Make just because this skill can create workflows there directly; a Zapier pick is delivered as a Copilot prompt, which is equally valid.
- **LLM(s)**: follow the LLM selection method in solution-design.md. The pick must be justified by the use case (accuracy, cost per run, context, latency, privacy, tool calling), never by provider familiarity. That includes not favoring Anthropic because this skill runs on Claude. Name a runner-up.
- **Vector database: yes or no**, using the rubric. Default is **no**. Recommend one only when the rubric's conditions are met, and say which condition justified it.
- **Other tools and integrations**, keeping only what the workflow needs.

Present a recommendation brief of at most one screen: the platform and why (with the top 3 deciding criteria and the runner-up), the LLM and why, vector DB yes/no and why, the tool list, the flow in 5-10 steps, the **human review plan per AI step** (full approval, sampled at X%, or exception-only, and who reviews), the **expected ramp** (for example "100% review of drafts for the first 3 months, dropping to about 15% sampling once the error rate is below about 5%"), and the key risks. Ask the user to approve before building.

### Step 6: Part 1, The Workflow

The user's approval of the recommendation in Step 5 covers creating the workflow in their account. Always create it **inactive/off**, so nothing runs until the user connects credentials and turns it on.

**n8n or Make:**
1. Write a spec to `.tmp/workflow-builder/<client-slug>/workflow-spec.json` in the format documented in the `tools/build_workflow.py` docstring. Include the trigger, every node or module, the AI model and its tools, memory and vector store sub-nodes if applicable, data transformations, IF/Switch branches or Router routes, loops (n8n `Loop Over Items`, Make Iterator + Aggregator), human approval steps (for example Slack/email "send and wait for approval"), error handling (n8n error workflow or `onError` + retries, Make error handler routes) and outputs. Use real node types and module ids for the recommended apps; name every node descriptively.
2. Run `.venv/bin/python tools/build_workflow.py --platform <n8n|make> --spec <spec> --out output/workflow-builder/<client-slug>/<n8n-workflow.json|make-blueprint.json> --push`. This validates the spec, saves the importable file, and creates the workflow in the account. Fix any errors it reports (validation or API rejection) and rerun. If the platform rejects a node type or module version, correct it and record it under "Learned identifiers" in solution-design.md.
3. Give the user the id the tool prints, and tell them where to find the workflow in their account.
4. Parameters and credentials are placeholders. It's a structural build meant to show the architecture, not a production configuration. Say so in the README.

**Zapier (via the Zap editor's AI Copilot):**
1. Write the Zap design to `zapier-design.md` as a table (step #, type = Trigger/Action/Filter/Path/AI/Approval/Formatter/Looping/Delay, app, event, key fields and mappings, notes), covering triggers, actions, paths, filters, AI steps, integrations, data flow, outputs, human approvals and error handling. Add a Mermaid flowchart of the same design (`zapier-diagram.mmd`) so the user sees the whole architecture.
2. Write `zapier-copilot-prompt.md`: the prompt the user pastes into Copilot, following the template below. It must describe exactly the design in `zapier-design.md`, with the same steps, in the same order, with the same apps.
3. Tell the user how to use it: in Zapier, create a new Zap, open **Copilot** in the Zap editor, paste the prompt, review each step Copilot proposes, connect the app accounts, test each step, and leave the Zap **off** until testing passes. Include a short checklist of the steps from `zapier-design.md` so they can confirm Copilot built every one.

Copilot prompt template (fill in every `<...>` from the design; use exact app names and event names as they appear in Zapier's app directory, which the research step verifies):

```
Build a Zap called "<Zap name>". Keep it turned off; I'll test it before turning it on.

Goal: <one sentence: what the Zap does and for whom>

Trigger: <App> — <Event> (<account/folder/form or filter details>).

Steps, in this order:
1. <Filter/Formatter/Action> — <App> — <Event>: <what it does>. Map: <field> = <trigger/step field>, ...
2. AI step — <AI by Zapier / ChatGPT / Claude / other app chosen in the recommendation> using <model>: <the task>.
   Instructions for the AI: "<the prompt text, including the output format, e.g. JSON with fields a, b, c>".
3. Paths — split on <field from step N>:
   - Path A "<name>": when <condition> → <steps>
   - Path B "<name>": when <condition> → <steps>
4. Approval: <e.g. send a Slack message to #channel with Approve/Reject, or use Human in the Loop> before <the action it gates>.
5. <Looping by Zapier over <line items> → <steps per item>, if the design has a loop>
6. Output: <App> — <Event>: <what gets written or sent, and to whom>.

Error handling: <e.g. if step N fails, send an alert to <owner> with the error details>.
Use the field names from the earlier steps when mapping, and ask me to connect any app accounts that aren't connected yet.
```

Keep the prompt in plain language and each step on its own line. If the design has more than about 10 steps or multiple Paths, also write it as 2-3 **staged prompts** (for example "1: trigger and main steps", "2: add the Paths", "3: add approvals and error alerts") in the same file, so the user can paste them one at a time if Copilot stops partway or gets a step wrong. Record any Copilot quirks the user reports in solution-design.md under "Learned identifiers".

**All platforms:** write `output/workflow-builder/<client-slug>/.env.example` with a placeholder for every credential the workflow needs: the LLM API keys, platform credentials, each integration's key or OAuth client, database or vector store credentials, `FIRECRAWL_API_KEY` if the workflow itself scrapes, and anything else. Group them by service, add a one-line comment with where to get each one, and **never put a real key in it**. It must match the steps in the workflow exactly: no missing and no extra services. (For Zapier, most apps connect through Zapier's own account connections, so only list keys the user must supply themselves, such as a bring-your-own LLM key.)

### Step 7: Costs, ROI, payback and break-even numbers

Read [roi-method.md](roi-method.md) and [cost-benchmarks.md](cost-benchmarks.md). **You do the math yourself** from what discovery and research produced, and `tools/calc_workflow_roi.py` must agree with you.

1. **Fill the gaps with labeled benchmarks.** For every cost input the client didn't give (implementation rate or hours, maintenance, adoption hours, review shares, rework), take the matching range from cost-benchmarks.md, pick a value, and say why. Label it (Published benchmark with its URL, or Practitioner estimate (unsourced)). Never silently assume. The user confirms or replaces each one in step 4 below.
2. Write `output/workflow-builder/<client-slug>/roi-calculations.md` with:
   - **Recurring costs:** every recommended tool with its plan, monthly cost, Verified/Estimated label and source URL. Calculate LLM cost from the tokens per run × runs per month × the researched price, and check platform consumption (tasks, operations, executions) against the plan limits, upgrading the plan if it's exceeded. Add maintenance (retainer, hours × rate, or % of build per year, checked against the benchmark range), then the monthly recurring total.
   - **One-time costs:** implementation (formula by implementation mode; phase-model hours when there's no quote) and adoption/training, then the one-time total.
   - **Net hours:** for each automated task, at ramp and at steady state: gross hours − review hours − rework hours = net hours, and the weekly value at the automated person's rate minus review and rework at the reviewer's rate. Show **gross and net hours side by side**.
   - **ROI:** each benefit classified (avoided labor, cost reduction, capacity, revenue) with its source. Then every line written out as in the worked example: first-year TCO, steady-state annual cost, first-year benefit, first-year ROI, steady-state ROI, weekly and annual net hours (and gross, labeled), annual gross savings (labeled as before review and costs), and any revenue upside or capacity value kept outside the ROI.
   - **Cash flow:** the monthly schedule (months 0-24, or 36 if extended), the payback period (interpolated, and say so), the operating break-even (net hours/month and units/month), and the two sensitivity cases.
3. Write the inputs to `output/workflow-builder/<client-slug>/roi-inputs.json` (format in the tool's docstring; see `examples/worked-example-inputs.json`) and run:
   `.venv/bin/python tools/calc_workflow_roi.py --in <dir>/roi-inputs.json --out <dir>/roi-results.json --schedule-out <dir>/payback-schedule.json`
   Paste its schedule table into `roi-calculations.md`. **Every line must match your hand calculation.** If they differ, find out why and fix whichever is wrong before continuing. Round money to whole dollars, percentages to whole numbers, and hours and payback to one decimal, and use the same rounded figures everywhere. Act on the tool's warnings (for example maintenance outside the benchmark range, plan limits exceeded).
4. Show the user the cost list (recurring and one-time), gross vs net hours, the calculation lines, the cash-flow schedule (at least months 0 through payback), the payback period, the operating break-even, and **every assumption and benchmark with its label**. Ask them to confirm or correct each one. If they give ranges for key inputs (for example "somewhere between 8 and 12 hours"), ask whether to show conservative and optimistic scenarios, and add them to `roi-inputs.json` only if they confirm. **The infographics and the payback report use only the confirmed numbers, copied verbatim from `roi-calculations.md`.** If a confirmed number changes, rerun the tool.

### Step 8: Parts 2 and 3, The Infographics

Read [infographic-guide.md](infographic-guide.md) and view the image in `design-reference/`.

1. Draft both infographics' exact text (every card title, number, label and footnote) and the layout, then show them to the user for approval together with the cost (about 36 kie.ai credits for both). Ask whether to overlay the G Force logo.
2. After approval, write each prompt to `.tmp/workflow-builder/<client-slug>/` and generate:
   `.venv/bin/python tools/kie_generate_image.py --prompt-file <prompt> --out output/workflow-builder/<client-slug>/pricing-infographic.png --aspect 16:9`
   and the same for `roi-infographic.png`.
3. If the user asked for the logo, run `tools/overlay_logo.py` on each image.
4. **Verify** each image by viewing it and comparing every word and number character by character against the approved text and `roi-calculations.md` (see the checklist in infographic-guide.md). If anything is wrong, show the user the issue and **ask before regenerating** (it costs credits again).

### Step 9: Part 4, The Payback and Break-Even Report

Read [payback-report-guide.md](payback-report-guide.md). This step is free (matplotlib, no image credits).

1. Run `.venv/bin/python tools/build_payback_report.py --schedule <dir>/payback-schedule.json --preview` and show the user the bottom-line text and key numbers for approval. Save any rewording to `.tmp/workflow-builder/<client-slug>/bottom-line.txt`.
2. Generate with `--check <dir>/roi-calculations.md --out-dir <dir>` (plus `--bottom-line-file` if reworded). If `--check` stops, **resolve the difference with roi-calculations.md before producing the report**.
3. View `payback-chart.png` and read `payback-report.html`, then verify them with the checklist in payback-report-guide.md: the payback month, callout text, axis range, the zero crossing matching the table, and every figure against `roi-calculations.md`. Fix and regenerate as needed.

### Step 10: Deliver

Write `output/workflow-builder/<client-slug>/README.md` and give the user a short summary:
- the recommended platform, LLM and tools
- the costs: monthly recurring cost, one-time total, **first-year TCO** and **steady-state annual cost**
- the returns: **first-year ROI**, **steady-state ROI**, the **payback period** and the **operating break-even**, each labeled with its key assumptions (which inputs are benchmarks or assumptions), plus net vs gross hours saved
- where the workflow lives in their account (or, for Zapier, the Copilot prompt and how to use it)
- the file list, including `payback-report.html` and `payback-chart.png`
- the next steps to connect credentials, test and turn the workflow on, and the review plan to follow during the ramp
- the Future phases

## Output

```
output/workflow-builder/<client-slug>/
  discovery-notes.md        # raw answers, round by round
  scope.md                  # approved scope (Phase 1 vs future phases, assumptions)
  research.md               # platform/LLM/tool research with source URLs + verified labels
  recommendation.md         # platform, LLM, vector DB decision, tool list, rationale, risks
  n8n-workflow.json | make-blueprint.json          # also created (inactive) in the account
  zapier-design.md + zapier-diagram.mmd + zapier-copilot-prompt.md   # Zapier pick
  .env.example              # placeholders only
  roi-calculations.md       # costs, net hours, ROI, cash-flow schedule, payback, break-even (step by step)
  roi-inputs.json           # confirmed inputs for tools/calc_workflow_roi.py
  roi-results.json          # tool output (all figures)
  payback-schedule.json     # schedule JSON for the payback report
  pricing-infographic.png   # subscriptions + one-time + maintenance + first-year TCO
  roi-infographic.png       # net hours, first-year and ongoing ROI, payback
  payback-chart.png         # cumulative net position by month (matplotlib)
  payback-report.html       # plain-language payback and break-even report (prints to PDF)
  README.md                 # how to import, configure, and measure success
```

## Notes

- **No invented client figures.** Every number is either stated by the user in discovery or labeled as an assumption or benchmark, with its basis (and source URL for benchmarks) shown and the user's confirmation. If a key input is missing, ask for it; if the client has no number, offer the cost-benchmarks.md range as a labeled assumption to confirm or replace.
- **Time saved is not automatically money saved.** Only avoided labor and removed costs count as gross savings. Freed capacity and revenue upside are reported separately unless the user confirms they should count (see roi-method.md).
- **Hours saved are net.** Human review and rework reduce hours saved (they're never a separate cost line), with ramp and steady-state values. Headline hours are net; gross hours appear only when labeled "gross".
- **Vendor neutrality.** No default platform, LLM, or vector DB. Every pick needs a use-case reason and a named runner-up.
- **Unverified is never presented as fact.** If the official docs don't answer something (for example an exact rate limit), say "not documented", cite the page you checked, and design around the uncertainty.
- **Scope creep:** anything new after scope approval goes to Future phases unless the user explicitly re-scopes.
- **Paid calls need consent:** Firecrawl research (tell the user the rough credit use first) and kie.ai images (approve the text and cost first; ask before any regeneration). n8n and Make workflows are created in the account after the recommendation is approved, and always inactive/off. The payback report and the ROI tool are free, but the report's text still needs approval.
- **Show the full cost.** The pricing infographic, `roi-calculations.md`, the ROI figures and the payback report include recurring costs (subscriptions, maintenance) **and** one-time costs (implementation, adoption), priced for the implementation mode chosen in discovery (self-implement, freelancer, agency or undecided). A fixed quote is the implementation cost; don't add builder effort on top of it.
- **Payback honesty.** If the workflow never breaks even, or doesn't pay back within 36 months, say so plainly in the chat, the README and the report, and give the operating break-even volume it would need.
- **Secrets:** API keys live only in `.env`. Generated `.env.example` files contain placeholders only. Never print key values.
- If creation fails in n8n or Make because of a node type or module version, or Copilot mis-builds a Zapier step, fix it and record the lesson in solution-design.md under "Learned identifiers".
