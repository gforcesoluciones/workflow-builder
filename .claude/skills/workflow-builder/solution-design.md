# Solution Design Reference

## 1. Platform evaluation criteria (n8n, Make, Zapier)

Score each platform 1-5 on the criteria that matter for this client, and weight them by the scope (for example, a heavy data-looping workflow weights iteration and per-operation pricing highly). Evidence comes from the research report, never from memory.

| Group | Criteria |
|---|---|
| Limits | Rate limits, payload/file size limits, execution time limits, execution/task/operation quotas |
| Pricing | Pricing unit (task vs operation vs execution), plan tiers, overage, how loops and branches are billed, self-host option |
| Logic | Conditional branching (Zapier Paths vs Make Routers vs n8n IF/Switch), loops and iteration (Make Iterator/Aggregator vs Zapier Looping vs n8n Loop Over Items), data transformation, code steps |
| Reliability | Error handling, retries, error routes/workflows, replay of failed runs |
| Triggers | Webhooks, polling intervals per plan, event-driven, schedules |
| Integrations | Native connector coverage for the client's systems, generic HTTP/API support, auth methods (OAuth, API key, custom) |
| AI | Native AI steps, AI agent capabilities, tool calling, memory/context management, choice of LLM providers (bring your own key vs built-in credits), vector store support, external database support |
| Scale and ops | Scalability, concurrency, queueing, observability and logs, log retention, version control, environments and deployment |
| Governance | Security certifications, data residency/region options, SSO/RBAC, audit logs, self-hosting |
| Lifetime | Maintenance effort for the client's skill level, vendor lock-in and exportability, total cost of ownership, token economics |

**Structural differences to verify in the official docs every time** (don't rely on memory, because pricing and features change):
- How Make bills each module run inside an iterator (operations multiply per item) vs how Zapier bills tasks inside Looping and Paths vs how n8n counts executions (per workflow run, regardless of steps) on Cloud vs self-hosted.
- Make's Iterator + Aggregator pattern vs Zapier's Looping by Zapier (item limits) and Paths (branch limits, nesting) vs n8n's Loop Over Items and item-based processing.
- Zapier's multi-step Paths vs Make's Router with filters vs n8n's IF/Switch plus merge.
- The AI agent features of each platform: which models they support, tool calling, memory, and whether AI usage consumes platform credits or your own API key.
- Each plan's minimum polling interval, max execution time, and max payload/file size.

If a limit is not documented, write "Not documented (checked <URL>)" and don't estimate it as fact.

## 2. Official sources (starting points)

URLs move, so use `firecrawl_map` on the domain to find the current page when a path 404s. Prefer official docs, help centers and pricing pages. Community forums and third-party blogs can be listed only as **Unverified** context.

- **n8n:** n8n.io/pricing, docs.n8n.io (flow logic: splitting, merging, looping; error handling; AI/Advanced AI and the AI Agent node; vector stores; Cloud execution limits and data retention; source control and environments; hosting/queue mode; security), n8n.io/integrations
- **Make:** make.com/en/pricing, help.make.com (routers, filters, iterators, aggregators, error handlers and directives, operations and credits, scenario execution limits, webhooks and queue limits, data stores, AI agents/AI tools), developers.make.com (API), make.com/en/integrations, the Make trust/security page
- **Zapier:** zapier.com/pricing, help.zapier.com (Paths, Filters, Looping by Zapier, Webhooks by Zapier, tasks and task usage, rate/throttle limits, polling intervals by plan, AI actions/AI by Zapier, Zapier Agents, Tables, data retention), zapier.com/apps, the Zapier security/trust page
- **LLMs:** each provider's official model and pricing pages (for example OpenAI, Anthropic, Google Gemini, Mistral, xAI, DeepSeek, and Meta Llama through the hosts the client might use). Include the enterprise/data-privacy pages when privacy matters.
- **Vector DBs (only if the rubric says one might be needed):** the pricing and limits pages of the options that fit (for example Pinecone, Qdrant Cloud, Weaviate Cloud, Supabase pgvector, or the platform's built-in store)
- **Client integrations:** each recommended app's official pricing page and API docs (rate limits, auth, webhook support).

## 3. Research subagent prompt

Launch with the Agent tool (`subagent_type: general-purpose`). Fill in the `<...>` parts from `scope.md`.

```
You are researching workflow automation platforms for a client's AI workflow. Use ONLY the Firecrawl MCP tools
(mcp__firecrawl__firecrawl_search, firecrawl_map, firecrawl_scrape; prefer scrape with formats ["markdown"] and
onlyMainContent true). Do not use other web tools. Keep total scrapes under ~45 pages.

Client workflow (from the approved scope):
<3-8 line summary: trigger, volume per day/month, steps per run, loops (items per run), branches, AI steps,
data formats and sizes, integrations needed, approvals, compliance/residency needs, budget ceiling, who maintains it>

Research, from OFFICIAL docs/pricing pages only:
1. n8n, Make and Zapier, for every criterion below that is relevant to this workflow:
   rate limits; payload/file size limits; execution time limits; pricing unit and plan tiers (price, included
   tasks/operations/executions, polling interval, overage); how loops/iterations and branches are billed; conditional
   branching; loops and iteration; data transformation and code steps; error handling and retries; webhooks and
   event triggers; API/HTTP integrations and auth methods; native connectors for <client systems>; native AI
   features, AI agents, tool calling, memory; which LLM providers can be used and whether AI usage is billed by the
   platform; external database and vector store support; scalability and concurrency; observability/logging and
   log retention; version control and deployment; security certifications, data residency, SSO/RBAC; self-hosting;
   vendor lock-in/export; maintenance effort.
   Specifically verify: Make Iterator/Aggregator + per-operation billing vs Zapier Looping and Paths (limits, task
   billing) vs n8n Loop Over Items and per-execution billing.
2. LLM candidates for this use case: <task type, e.g. extraction from 10-page PDFs / classification of short emails /
   agent with 4 tools>. For <2-4 candidate models across different providers, chosen by fit, not brand>, get
   current input/output price per 1M tokens, context window, structured output and tool-calling support, rate
   limits for the entry tier, data retention/training policy, and regional hosting options.
3. <Only if applicable: vector DB options — pricing, free tier, limits, hosting region>
4. <Client-specific tools/integrations — current plan pricing and API limits>

Return a Markdown report with:
- A comparison table per platform (criterion | finding | source URL | Verified / Not documented).
- Plan recommendation per platform for this volume, with a monthly cost calculation shown step by step.
- An LLM table with prices and a cost-per-run estimate at <tokens in/out per run>.
- A "Not documented / unverified" list.
- The date of research.
Never state a number without a source URL. If pages conflict, report both with URLs.
```

## 4. LLM selection method

1. Define the task profile from the scope: the task type (extraction, classification, generation, agentic tool use, reasoning), the input size per run, the output size, accuracy needs, latency needs, volume, and privacy/residency needs.
2. Choose 2-4 candidates **from different providers** that plausibly fit (include an open-weight/self-hostable option when privacy or cost dominates).
3. Compare them on task fit and accuracy, reasoning, context window, input/output token costs → **cost per run and per month**, latency, reliability, tool calling and structured output, privacy/data retention, integration with the chosen platform (does it have a native node/module, or does it need an HTTP call), rate limits, and scalability.
4. Pick the lowest-TCO model that meets the accuracy bar. Use a larger model only for the steps that need it, and consider routing (a cheap model for triage, a stronger model for the hard cases) when volume is high.
5. State the pick, the runner-up, and the one-line reason the pick won. Never pick by brand, and never favor Anthropic because this skill runs on Claude.

## 5. Vector database decision rubric

**The default is NO vector database.** Recommend one only when **all three** hold:

1. **A retrieval need**: the workflow must find relevant passages by meaning (natural-language questions, similar-case lookup, grounded answers with citations), not by exact fields, IDs or filters.
2. **Scale beyond context**: the relevant corpus doesn't fit in the model's context per run at an acceptable cost (roughly, more than a few hundred pages, or many documents where only a few passages matter per run), or it's reused across many runs such that re-sending it would cost more than retrieval.
3. **No simpler store works**: an existing search (CRM, helpdesk knowledge base, SQL full-text search, file search in the LLM provider) can't meet the accuracy need.

The usual alternatives: pass the whole document in context (a single document per run), structured lookups in the CRM, database or spreadsheet, keyword/full-text search, or the LLM provider's built-in file search.

If one is justified: prefer the lightest option that fits the platform and the client's stack (for example pgvector in an existing Postgres/Supabase, the platform's native vector store node, or a managed service). Also consider the ingestion pipeline (chunking, embeddings model and cost, re-indexing when the data changes), and state which rubric conditions justified it.

## 6. Learned identifiers

Record node types, module ids and Zapier-MCP capabilities confirmed to work (or corrections after a failure).

| Platform | Purpose | Identifier | Version | Confirmed on |
|---|---|---|---|---|
| n8n | AI Agent | `@n8n/n8n-nodes-langchain.agent` | (check) | not yet confirmed |
| n8n | Loop | `n8n-nodes-base.splitInBatches` (Loop Over Items) | (check) | not yet confirmed |
| Make | Webhook trigger | `gateway:CustomWebHook` | 1 | not yet confirmed |
| Make | Iterator / Aggregator / Router | `builtin:BasicFeeder` / `builtin:BasicAggregator` / `builtin:BasicRouter` | 1 | not yet confirmed |
| Zapier | Zap creation | NOT supported by Zapier-MCP: no create-Zap tool; Zapier Manager app only finds/toggles Zaps. MCP can run app actions and save skills (`create_zapier_skill`). Build Zaps via the Zap editor Copilot. | n/a | 2026-09-26 (confirmed limitation) |
| Make | Setup | `MAKE_TEAM_ID` must be the team id (e.g. "My Team"), not the organization id; the org id gives 403 IM002 "Insufficient rights". `MAKE_ZONE` may be `us2` or `us2.make.com`. | n/a | 2026-09-26 |
| Make | Discover real module ids | `GET https://<zone>/api/v2/imt/apps/<app>` (Token auth) returns `groups[].modules` (e.g. hubspotcrm, openai-gpt-3, google-email, builtin); json/gateway list them under `transformers`/`triggers`. Blueprint `version` = app major version | n/a | 2026-09-26 |
| Make | HubSpot CRM (app v2) | `hubspotcrm:upsertAContact`, `updateContact`, `createANote`, `createATask`, `createDeal`, `updateDeal`, `searchDeals`, `CreateAssociation` | 2 | 2026-09-26 (accepted by API, isinvalid=false) |
| Make | OpenAI (Responses API) | `openai-gpt-3:createModelResponse` (also `CreateCompletion`, `transformTextToStructuredData`) | 1 | 2026-09-26 (accepted) |
| Make | Gmail send | `google-email:sendAnEmail` | 4 | 2026-09-26 (accepted) |
| Make | JSON / errors | `json:ParseJSON`, `json:TransformToJSON`; `builtin:Break` (retry, needs `scenario_settings: {"dlq": true}`), `builtin:ThrowError` | 1 | 2026-09-26 (accepted) |
