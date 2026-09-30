# Discovery Guide

This is the question bank for Step 2. **It is not a script.** Pick questions based on what you already know, what's still missing from the sufficiency checklist, and what the last answer revealed.

## Adaptive rules

1. **One goal per round.** Each round closes one gap (for example "how big is the problem" or "where does the data live"). Use at most 4 questions per round.
2. **Skip what you know.** Re-read `discovery-notes.md` before each round. Never re-ask anything stated in `$ARGUMENTS` or earlier answers.
3. **Only ask questions that change something**: the architecture, the tool choice, the cost, or the ROI. If an answer can't change any of those, drop the question.
4. **Follow up on vague answers.** Turn "a lot", "often" and "some people" into numbers or ranges. Offer ranges as options when the user doesn't know exact figures.
5. **Branch on answers:**
   - Documents, PDFs or long text → ask the document-processing and retrieval questions (see *Vector DB signals*).
   - An existing AI workflow → ask what it does, where it fails, its cost per run, and whether to optimize it or rebuild.
   - Regulated industry (health, finance, legal, EU customers) → ask about compliance, data residency and whether a self-hosted option is required.
   - Revenue-facing process (leads, sales, support) → ask about conversion rates, deal size, and response-time sensitivity.
   - Many people affected → ask about the loaded hourly cost per role and whether the time would be redeployed or headcount avoided.
   - The workflow generates or decides anything with AI (drafts, classifications, summaries, extractions) → ask the review questions in *E. Operations*: who reviews, their hourly value, which outputs can go out unreviewed, and how bad an error would be.
   - The user doesn't know a technical answer → move on, record it as an assumption, and note who at the company would know.
   - The user doesn't know a cost input (a rate, maintenance, training hours) → don't guess. Say you'll offer a benchmark range from cost-benchmarks.md at Step 7 for them to confirm or replace, and record it as an open assumption.
6. **Suggested order** (adapt as needed): Pain and impact → Business context → Current environment → Data and integrations → Operations (approvals, errors, security, monitoring, ownership) → Outcomes and success metrics → Future state.
7. Use `AskUserQuestion` for categorical questions and plain chat for numbers and free text. Keep option labels short, and always leave room for "Other".

## Question bank

### A. Pain and impact
- How often does this problem happen (per day, week, or month)?
- Roughly how many hours a week are lost to it, and across how many people?
- Which roles are affected, and what is their approximate loaded hourly cost (or salary band)?
- What does managing this manually cost today (labor, outsourcing, tools, overtime)?
- How often do errors occur, and what does an error cost (rework time, lost deal, refund, compliance risk, customer churn)?
- What's the root cause as they see it: volume, fragmented tools, manual copy-paste, slow handoffs, missing data?

### B. Business context
- Your role? Your department or function where the problem sits?
- Industry, products or services, and primary customers?
- Company size: small business, mid-market or enterprise? Headcount?
- Approximate ARR or annual revenue (optional; only needed for revenue-based ROI)?
- How many employees would use or benefit from the workflow?
- Key stakeholders and decision-makers? Who approves spend?
- Current core systems (CRM, ERP, helpdesk, email, storage, databases)?
- Estimated financial impact of the problem today?
- Budget constraints (monthly software ceiling)? Implementation constraints (timeline, internal skills)?
- Security, compliance or data residency requirements (SOC 2, HIPAA, GDPR, EU hosting, on-premises)?

### C. Current environment
- Are you using any AI tools for this today? Any existing workflows or integrations?
- Which applies: an existing AI workflow to optimize, integrations to improve, manual processes to automate, or starting from scratch?
- Any platforms or tools you want to use, or must avoid? Any automation platform already licensed (n8n, Make, Zapier)?
- Who would build and maintain the workflow: a technical person, a no-code person, or nobody yet?
- **Implementation mode:** self-implement, freelancer, agency, or undecided? If they have a quote or a rate, get it (fixed fee, or rate × hours, and what it includes). If self-implementing: who, roughly how many hours, and what that person's time is worth per hour.

### D. Data and integrations
- Where does the data originate (form, email inbox, CRM, uploads, API, database)?
- What does it look like? Can you share a sample (redacted)?
- Format: structured records, CSV, JSON, PDFs, emails, documents, images, unstructured text?
- Volume: items per day or month, and the typical size of each item (pages, KB/MB)?
- Where is it stored today? Which systems, apps or databases hold it?
- What integrations exist (native connectors, APIs, webhooks)? Any system with no API?
- How often does new data arrive, and how often should the automation run?
- Real time, scheduled, or event-driven (for example "when a form is submitted")?
- What should the workflow output (a CRM update, report, email, Slack message, document, dashboard)? Who needs access?
- How much historical data needs processing (one-time backfill)?
- How often does the data change (static reference docs vs constantly updated records)?
- Does the workflow need document processing, semantic search, or answers grounded in a body of documents (RAG)?

### Vector DB signals (ask only when documents or knowledge are involved)
- How many documents or pages make up the knowledge base, and how fast does it grow?
- Do users need to find information by *meaning* (natural-language questions) or by exact fields and IDs?
- Does each run need the whole document (it fits in context) or a few relevant passages out of many?
- How accurate must retrieval be, and do answers need to cite their source?
- Is the content already searchable in an existing system (CRM search, SQL, a helpdesk knowledge base)?

### E. Operations
- Where must a human approve before the workflow acts (sending externally, updating records, spending money)?
- What should happen when a step fails: retry, alert someone, fall back to a manual queue?
- Access control: who may trigger it, see outputs, or change it?
- Reporting and monitoring: what do you need to see (run counts, failures, AI cost, time saved)?
- Who owns it after launch, and who handles maintenance? Do they want ongoing maintenance support (a retainer, or pay-as-you-go hours), or will they own it themselves? If they own it, who is the owner, and what is their time worth per hour?
- **Review plan:** which outputs can go out without a human look, which need approval, and how bad an error would be for each (a minor fix, an annoyed customer, a lost deal, a compliance issue)? This sets each AI step's review mode: full approval, sampled, or exception-only.
- **Reviewer:** who will review the outputs, and roughly what is that person's time worth per hour? (It may differ from the rate of the person whose work is being automated.)
- Expected growth in volume or users over the next 12-24 months?

### F. Outcomes and success
- Once this is solved, how valuable would that be to the company?
- How many hours a week do you expect it to save?
- What would you do with those hours? (This decides whether the time is avoided labor, redeployed capacity, or revenue.)
- Could the time saved increase revenue, improve customer satisfaction or reduce costs? How, specifically?
- How will you measure success after implementation (the metric, its baseline today, and the target)?
- **Adoption:** how many people need to adopt the workflow, and roughly how many internal hours will training and rollout take (per person or in total)?
- **Timing:** when do you expect to go live? Will any one-time costs be paid over several months (for example a quote paid in milestones)? This sets where the cash-flow schedule starts.

### G. Future state (always ask once)
- Once we solve the immediate problem, what other challenges or processes would you want to address in the future?

## Sufficiency checklist

Move to the scope document only when each item is **answered** or **marked unknown and converted into a labeled assumption**:

- [ ] Pain point, root cause, frequency
- [ ] Hours lost per week, people affected, loaded hourly cost
- [ ] Error rate and cost of an error (or confirmed as not relevant)
- [ ] Role, industry, company size, department, decision-maker
- [ ] Current tools, existing workflows, platform preferences or exclusions
- [ ] Data sources, formats, volumes, storage, available APIs or integrations
- [ ] Trigger type and run frequency; outputs and who receives them
- [ ] Historical backfill needs; how often the data changes
- [ ] Document processing, semantic search or RAG need (and the vector DB signals if yes)
- [ ] Human approval points, error-handling expectations, monitoring needs
- [ ] Security, compliance and data residency requirements
- [ ] Budget ceiling and implementation constraints; who builds and maintains it
- [ ] Implementation mode (self / freelancer / agency / undecided), with the quote, or the rate and hours
- [ ] Reviewer and their hourly value; for each output, whether it's unreviewed, sampled or approved, and the cost of an error
- [ ] Maintenance: retainer, pay-as-you-go, or owned internally (the owner and their hourly value)
- [ ] Adoption: people to onboard and internal training/rollout hours
- [ ] Go-live timing and how the one-time costs are paid (all up front, or spread)
- [ ] Expected outcomes, what the freed time will be used for, success metrics with baselines
- [ ] Future-state processes (recorded as future phases)

## Scope template (`scope.md`)

```markdown
# Workflow Scope: <client> (<date>)

## Summary
<2-3 sentences: the problem, the proposed workflow, the expected outcome>

## Current process
<numbered steps as done today, who does them, the tools touched>

## Pain points and root causes
| Pain point | Root cause | Frequency | Impact (hours / $ / errors) | Source |
|---|---|---|---|---|

## Future-state workflow
<numbered steps of the automated process>

## Triggers and actions
- Trigger: <event / schedule / real time> — <details>
- Actions: ...

## Data
| Source | Format | Volume | Frequency | Destination |
|---|---|---|---|---|
Historical backfill: ... | Change frequency: ...

## Integrations
| System | Direction (read/write) | Method (native / API / webhook) | Notes |

## AI capabilities and decision points
<what the AI decides, classifies, extracts or generates; the accuracy needed; the context size>

## Retrieval / vector DB assessment
<needed / not needed, and the rubric condition(s) that decide it>

## Human approval steps
## Error handling and fallback
## Security, compliance and access
## Reporting and monitoring
## Expected business outcomes
## Success metrics
| Metric | Baseline | Target | How measured |

## Constraints
<budget, timeline, skills, platform preferences or exclusions>

## Scalability
<expected growth; how the architecture accommodates the future phases>

## Implementation mode
<self / freelancer / agency / undecided>; quote or rate × hours; what it includes; source (client-stated or benchmark)

## Review plan per step
| Step | Output | Review mode (full approval / sampled % / exception-only) | Reviewer and $/h | Error impact | Ramp → steady review |
|---|---|---|---|---|---|

## Ownership and maintenance
<owner after launch; maintenance model: retainer / pay-as-you-go hours / internal; cost basis>

## Adoption and go-live
<people to onboard; training/rollout hours; target go-live month; one-time costs up front or spread (which months)>

## In scope (Phase 1)
## Future phases (out of scope)
## Open assumptions
| Assumption | Basis | Impact if wrong | Who can confirm |
```
