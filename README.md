# Workflow Builder

A Claude Code skill that acts as your AI Solutions Architect. Describe a business pain point and it will:

1. **Interview you** to understand the problem and agree on a scope (Phase 1 vs. future phases)
2. **Research** n8n, Make and Zapier, plus the right AI model and tools, from their official docs
3. **Recommend** the best platform with no vendor bias
4. **Build the workflow** directly in your n8n or Make account (created inactive, so nothing runs until you turn it on). For Zapier, you get a design plus a prompt for Zapier's AI Copilot.
5. **Show the ROI**: full cost of ownership, hours saved, payback period and break-even, with a pricing infographic, an ROI infographic and a payback report

## What's in this repository

```
.claude/skills/workflow-builder/   # The skill (instructions, guides, examples)
tools/                             # Python scripts the skill runs
```

## Setup

**1. Download**

Click the green **Code** button → **Download ZIP**, or:

```bash
git clone https://github.com/gforcesoluciones/workflow-builder.git
```

**2. Copy into your Claude Code project**

- `.claude/skills/workflow-builder/` → your project's `.claude/skills/` folder
- `tools/` → your project's `tools/` folder

**3. Install the Python packages**

```bash
pip install Pillow requests python-dotenv matplotlib
```

**4. Add your API keys**

Create a `.env` file in your project root:

```
# Infographics (https://kie.ai)
KIE_API_KEY=

# Research (https://firecrawl.dev)
FIRECRAWL_API_KEY=

# n8n (only if you build in n8n)
N8N_BASE_URL=
N8N_API_KEY=

# Make (only if you build in Make)
MAKE_ZONE=
MAKE_API_TOKEN=
MAKE_TEAM_ID=
```

Never commit your `.env` file.

**5. Connect Firecrawl**

The research step uses the Firecrawl MCP server (requires Node.js):

```bash
claude mcp add firecrawl -e FIRECRAWL_API_KEY=your-key -- npx -y firecrawl-mcp
```

**6. Add your logo (optional)**

Infographics get a logo in the corner. Put your own logo in `brand-assets/` and pass it with `--logo`, or update `DEFAULT_LOGO` in `tools/overlay_logo.py`.

## Usage

Open Claude Code in your project and run:

```
/workflow-builder
```

Or just ask something like *"Which AI workflow would give us the best ROI?"* or *"Scope an automation for this problem."*

Output is saved to `output/workflow-builder/<client>/`.

## Costs

- The two infographics use about 36 kie.ai credits per run
- Research uses Firecrawl credits
- The ROI math and payback report are free
