# Cost Benchmarks

**As of: September 2026.**

Default ranges to offer as **labeled assumptions** when the client has no figure of their own (Step 7). They come mostly from agency pricing guides and vendor surveys, so they are **directional, not authoritative**. Refresh them periodically (at least every 6 months) and update the date above.

How to use them:
- A client-stated number always beats a benchmark. Offer a benchmark only when the client has none, and ask the user to confirm it or replace it.
- Quote the range, say which value you picked and why (for example "middle of the range", or "high end, because it's multi-system and LLM-heavy"), and carry the label and source URL into `roi-calculations.md` and the payback report's Assumptions table.
- **Published benchmark** = a figure from the cited source. **Practitioner estimate (unsourced)** = a judgment call with no source. Never present a practitioner estimate as a published figure.
- These source URLs were supplied with the skill update and have not been re-verified by scraping. If a figure matters a lot for a client, offer to check the source with Firecrawl first (it costs credits).

## 1. Specialist hourly rates (implementation, maintenance)

| Benchmark | Range | Applies to | Label | Source |
|---|---|---|---|---|
| Freelance n8n experts (Upwork) | $40–100/hr | Freelancer mode, typical | Published benchmark | https://www.upwork.com/hire/n8n-experts/ |
| Senior n8n specialists | $125–250+/hr | Freelancer mode, senior or complex builds | Published benchmark | https://adsnipper.com/blog/hire-n8n-developer/ |
| Solo automation operators (n8n, Make, Zapier) | $95–235/hr | Freelancer mode | Published benchmark | https://betonai.net/ai-automation-rate-card-2026-what-to-charge-for-n8n-make-and-zapier-builds-real-rates-from-54-operators/ |
| Agencies | $100–300/hr | Agency mode, hourly | Published benchmark | https://thecrunch.io/ai-automation-agency-cost/ |

## 2. Setup fees and retainers (agency mode)

| Benchmark | Setup | Monthly retainer | Label | Source |
|---|---|---|---|---|
| Small business | $1,500–5,000 | $500–1,500 | Published benchmark | https://taskip.net/ai-automation-agency-pricing/ |
| Mid-market | $5,000–20,000 | $1,500–4,000 | Published benchmark | https://taskip.net/ai-automation-agency-pricing/ |
| Automated lead follow-up | $2,000–8,000 | $400–1,500 | Published benchmark | https://evolvaiagents.com/blog/how-much-does-an-ai-automation-agency-cost-in-2026-real-pricing-breakdown/ |
| Custom agents | $5,000–25,000+ | $1,000–5,000 | Published benchmark | https://evolvaiagents.com/blog/how-much-does-an-ai-automation-agency-cost-in-2026-real-pricing-breakdown/ |

**Fixed-fee risk buffer:** agencies often add 15–20% to fixed-fee quotes. Published benchmark, https://www.digitalapplied.com/blog/ai-agency-services-pricing-strategies-2026. Use it to explain why a quote sits above an hours × rate estimate, or as the `contingency_pct` on a self-built or freelancer estimate if the user wants a buffer. **Never add it on top of a real quote.**

## 3. Builder hours by phase (implementation estimate when there's no quote)

Practitioner estimate (unsourced).

| Phase | Hours |
|---|---|
| Discovery | 8–15 |
| Build | about 6–10 per workflow |
| Testing and edge cases | 0.7–1.0 × build hours |
| Handoff and training | 5–10 |
| Hypercare (first 2–4 weeks) | 10–20 |
| **Four-workflow stack, total** | **about 70–120** |

## 4. Maintenance

| Benchmark | Range | Label | Source |
|---|---|---|---|
| Share of build cost per year | 15–25%/year, toward the high end for multi-system or LLM-heavy workflows | Published benchmark | https://themona.global/blog/workflow-automation-cost/, https://www.perfectiongeeks.com/pricing/workflow-automation-development-cost |
| No-code maintenance as share of build **time** | 10–15% of build time per month | Published benchmark | https://crmautomates.com/post/workflow-automation-software |
| Ongoing hours, small stack | 5–12 hrs/month | Practitioner estimate (unsourced) | — |

**The sources disagree a lot.** 10–15% of build time per month works out to about 120–180% of build effort per year, versus 15–25% per year. On a small build, 15–25% per year also comes out well below the 5–12 hrs/month practitioner estimate. When you use a benchmark, show both the % of build cost and the implied hours per month, and let the user choose. `calc_workflow_roi.py` warns when maintenance falls outside 15–25% of build per year. Treat that as a prompt to explain the basis, not as an error.

## 5. Human review and rework

| Benchmark | Figure | Label | Source |
|---|---|---|---|
| Rework on AI output | About 37% of time saved by AI is lost to correcting, verifying or rewriting output (Workday, Jan 2026, 3,200 employees) | Published benchmark | https://investor.workday.com/news-and-events/press-releases/news-details/2026/New-Workday-Research-Companies-Are-Leaving-AI-Gains-on-the-Table/default.aspx |
| Targeted review | One production case cut human review from 100% of tasks to 23% after targeting | Published benchmark | https://dev.to/taimoor__z/-human-in-the-loop-hitl-for-ai-agents-patterns-and-best-practices-5ep5 |
| Sampling pattern | 100% of high-risk actions, 5–20% of low-risk ones | Published benchmark | https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation |
| Threshold for reducing review | Error rate below about 5% on that action | Published benchmark | https://pickaxe.co/post/human-in-the-loop-ai-agents |

**Caveat on the Workday figure:** it measures generic AI tools used ad hoc, not purpose-built workflows with targeted review. Use it as a ceiling or a stress test, not as the default rework rate for a designed workflow.

**Review share by task type.** Practitioner estimate (unsourced).

| Task type | Review share | Notes |
|---|---|---|
| Deterministic data moves (imports, CRM syncs) | Exceptions only, plus a 5–10% spot check | Little rework once mappings are right |
| AI-drafted routine messages | 100% at launch, dropping to 10–25% sampling once errors settle | Move to sampling only after the error rate is below about 5% |
| Meeting notes into CRM | Skim every item, about 2–5 min each, indefinitely | Review doesn't drop with time |
| Marketing copy and newsletters | 100% review with real edits | Net time saved about 40–60% of gross |

**Ramp.** Practitioner estimate (unsourced): net savings run at about 50–60% of gross in months 1–3, rising to 65–80% at steady state. Use it as a sanity check on the per-task review and rework figures. If the modeled net share is far outside it, explain why.

## 6. Adoption and training

| Benchmark | Figure | Label | Source |
|---|---|---|---|
| Change-management budget | 15–20% of the project budget | Published benchmark | https://simo-online.com/en/blog/change-management-ki-einfuehrung-mittelstand-2026 |
| BCG finding | Spending at least 10% of AI budget on training and change management made success 1.5x more likely | Published benchmark | https://www.forbes.com/sites/terdawn-deboe/2026/07/28/ai-adoption-fails-95-of-the-time-small-business-leadership-is-why/ |

Prefer client-stated internal hours × loaded rate. Use a percentage of implementation cost only when the client can't estimate hours.
