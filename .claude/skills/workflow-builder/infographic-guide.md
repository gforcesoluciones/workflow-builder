# Infographic Guide

Both infographics are generated with Nano Banana through `tools/kie_generate_image.py` (nano-banana-pro, 16:9, 2K by default). They share one visual identity, taken from the image in `design-reference/`.

## Style

1. View the reference image (`design-reference/pricing image.jpg`: dark charcoal/navy background, a 3×2 grid of rounded cards each with its own glowing neon accent (blue, purple, green, red, orange, teal), a price-tag line icon, bold white tool name and big price with a smaller "/mo", a muted plan label under it, faint circuit-trace details in the card corners, an optional ribbon badge such as "Best Value", and a bold centered title with a muted subtitle) and write a 4-6 line **style block**: the background, card style (fill, radius, border, shadow), accent colors (as hex values), typography (weight, case), icon style, and the overall density. Reuse the same style block for both prompts.
2. If there is no reference image and the user says to proceed anyway, use a sleek corporate SaaS look: an off-white or deep-navy background, white rounded cards with soft shadows, one accent color, a geometric sans-serif, thin line icons, and generous spacing.
3. Always require: crisp, perfectly spelled text; strict alignment to a grid; consistent spacing; a clear hierarchy (title → big numbers → labels → footnote); minimal clutter; no third-party logos; no stock photos or people; no decorative text.
4. If the G Force logo will be overlaid, keep the top-left corner clear (see `tools/overlay_logo.py`). On a light background, use `--glow 0`.

## Text discipline (the main reason renders fail)

- Put every string in the prompt **inside double quotes, exactly as it must appear**, and add: "Render only the quoted text. Do not add, change, or invent any other words or numbers."
- Keep the text short: 2-6 words per label and ≤ 12 words per footnote line. Numbers are formatted exactly as in `roi-calculations.md` ($21,600, 900%, 1,040).
- At most about 60 words of total text per image (about 75 for the pricing infographic now that it carries a one-time block). If a formula chain is too long, keep the key lines and move the rest to the README.

## Pricing infographic

Layout: two clearly separated zones, recurring on top and one-time below (divided by a thin rule or a distinct panel background).
- Title: "Estimated Cost of Ownership"; subtitle: "<Client> AI Workflow · <implementation mode, e.g. Freelancer build>"
- **Zone 1, monthly subscriptions** (a row, or a 2×N grid when there are more than 4 tools): one card per tool with the tool name, plan name, "$X / month", a small badge reading "Verified" (filled) or "Estimated" (outlined), and an optional one-line basis (for example "~2,000 runs/month"). Then a subtotal bar: "Subscriptions: $X / month".
- **Zone 2, one-time and maintenance** (a visually distinct block, for example an outlined panel with a different accent): three compact cards: "Implementation" "$X one-time" (with a small basis such as "60 h × $90/h" or "Agency quote"), "Adoption & Training" "$X one-time", and "Maintenance" "$X / month". Badge each one "Client-stated", "Benchmark" or "Assumption", matching `roi-calculations.md`.
- **Total bar:** "Monthly Running Cost: $X" (subscriptions + maintenance) and "First-Year Total Cost: $X" (first-year TCO), side by side.
- Footnote: "Prices from official pricing pages as of <Month YYYY>. Estimated = usage-based. Benchmarks: see report."

Only the tools and cost lines in `roi-calculations.md`, in the same order, with the same numbers. If the client truly has no one-time cost (for example they self-implement and chose not to value their own time), say so in Zone 2 ("Self-implemented, time not valued") rather than dropping the zone.

## ROI infographic

- Title: "Projected ROI"; subtitle: "<Client> <workflow name>"
- **Top section (3-4 big cards)**: "Pays Back In X.X Months", "First-Year ROI X%", "Ongoing ROI X%" (steady state, year 2 on), and "Net Hours Saved X / year" (steady-state **net** hours, never gross). Headline ROI figures always include every cost (one-time and recurring) and net savings.
- **Calculation strip** (small text): the calculation lines from `roi-calculations.md`, verbatim, trimmed to the 3-5 most important, for example first-year TCO, first-year benefit, first-year ROI, and "18 h/week gross → 16.5 h/week net after review".
- **Lower section (3-6 small highlight cards)**: the business-value translations supported by discovery, for example "Faster Follow-Ups: minutes, not days", "More Time for Clients: 20 h/week redeployed", "Fewer Errors", "Higher Lead Capacity". Each needs a basis in discovery or a labeled assumption.
- **Footnote** (required): "Savings are net of human review and rework. Some inputs are benchmarks or assumptions." Add, when true, that revenue upside/capacity value is not included in ROI, for example "Revenue upside ($30,000/yr, estimated) not included in ROI."

Distinguish gross savings, net benefit and ROI clearly. Never label capacity value as savings, and never show gross hours as the headline. If gross hours appear at all, label them "gross". If the workflow never breaks even, don't make an ROI infographic that implies it does: show the payback card as "Does not pay back at these numbers" and discuss with the user whether to produce it at all.

## Prompt skeleton

```
Create a clean, professional 16:9 infographic in a sleek, corporate, modern SaaS product design.

STYLE: <style block>

LAYOUT: <grid description with exact positions: header band, card row(s), total bar, footnote>

TEXT (render exactly, perfectly spelled, nothing else):
- Title: "<...>"
- Subtitle: "<...>"
- Card 1: "<Tool>" / "<Plan>" / "$X / month" / badge "Verified"
...
- Footnote: "<...>"

Render only the quoted text. Do not add, change, or invent any other words or numbers.
Crisp, sharp typography; consistent card sizes; equal spacing; aligned baselines; generous whitespace;
no logos, no photos, no people, no watermark.
```

## Verification checklist (view every image)

- [ ] Every quoted string is present and spelled exactly right, with no extra words or numbers
- [ ] Every number matches `roi-calculations.md` character for character (including $, commas, %)
- [ ] The subscriptions subtotal equals the sum of the tool cards; the tool list matches exactly
- [ ] Monthly running cost = subscriptions + maintenance; first-year total cost = one-time total + 12 × monthly running cost; both match `roi-calculations.md`
- [ ] One-time costs (implementation, adoption) sit in their own visually separate zone, not mixed with the monthly cards
- [ ] Verified/Estimated badges are on the correct tool cards; Client-stated/Benchmark/Assumption badges are on the correct cost cards
- [ ] ROI infographic: payback months (one decimal), first-year ROI and ongoing ROI match `roi-calculations.md` and the payback report; the hours card shows **net** hours
- [ ] The "net of human review and rework" footnote is present
- [ ] Assumption labels and the "not included in ROI" footnote are present where required
- [ ] Cards are aligned, evenly spaced and equally sized; nothing is cut off
- [ ] The logo area is clear (if overlaying)

Report any failure to the user with the exact wrong text, and ask before regenerating (about 18 credits each). When regenerating, simplify the text or strengthen the quote-exact instruction rather than repeating the same prompt.
