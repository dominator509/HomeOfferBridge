# Working in this repo (guide for Claude Code / Codex / any AI coding agent)

This file tells you how to edit the Home Offer Bridge site safely and fast. Read it
before touching anything. The same content is in AGENTS.md (Codex convention).

## What this repo is
A "we buy houses for cash" business. Two halves:
- **`site/`** — a static site generator in **pure Python (no Node, no npm)**. It turns
  JSON data + HTML templates into `site/dist/` (118 pages today).
- **`backend/`** — n8n workflows + agent prompts + DB schema. Not needed to edit the site.

## The golden rule: edit DATA and TEMPLATES, never edit `dist/`
`site/dist/` is **generated output**. Anything you change there is destroyed on the next
build. To change the site, edit the source and rebuild:

```
cd site
python3 build.py            # regenerates dist/ from data + templates
python3 build.py --validate # checks every city passes the content rules (run before build)
```

No dependencies to install. If `python3 build.py` runs, your change worked.

## Where to make common edits

| You want to… | Edit this | Then |
|---|---|---|
| Change brand name, phone, domain, webhook, mailing address | `site/data/_brand.json` | rebuild |
| Fix copy/wording on ALL city pages | `site/template/city.html` | rebuild |
| Fix the home page | `site/template/home.html` | rebuild |
| Fix a state hub page | `site/template/state.html` | rebuild |
| Change one city's local content, market numbers, FAQ | `site/data/{state}/{city}.json` | rebuild |
| Change colors, fonts, layout, spacing | `site/assets/styles.css` | rebuild (CSS is copied as-is) |
| Add/adjust JSON-LD schema, meta tags, sitemap logic | `site/build.py` | rebuild |
| Add a whole new city | see "Adding a city" below | validate + rebuild |

## Templates are tokenized
Templates use `{{TOKEN}}` placeholders filled by `build.py`. Examples: `{{CITY}}`,
`{{STATE}}`, `{{PHONE}}`, `{{MEDIAN_PRICE}}`, `{{LOCAL_MARKET_LONGFORM}}`,
`{{MAILING_ADDRESS}}`, `{{LEAD_WEBHOOK}}`. If you add a new `{{TOKEN}}` to a template,
you MUST add it to the matching token dict in `build.py` (there are three: city, state,
home) or the build will leave the literal `{{TOKEN}}` in the output. Grep for an existing
token name to see all the places it's defined.

## Adding a city (the safe way)
1. Confirm the state is legal to operate in — check `seo/legal-market-coverage.md`.
   Do NOT add cities in excluded states (SC, NC, OK, PA, KY, NE, IL, VA).
2. Add a city dict to the right batch file in `site/data/_generator/cities_*.py`
   (copy an existing entry as a template — every field matters for uniqueness).
3. Regenerate + build:
   ```
   cd site/data/_generator && python3 generate.py
   cd ../.. && python3 build.py --validate && python3 build.py
   ```
4. Every city page must be genuinely unique (real neighborhoods, hazards, market data) —
   the validator enforces a 300-word local-content floor. Don't stuff duplicate text.

## Content rules the validator enforces (don't fight them)
- Each city needs 300+ words of unique local longform. This is the anti-doorway rule that
  keeps the site rank-safe. Generic "we buy houses in [city]" filler will fail review.
- Market numbers (median price, days on market, cash share) are realistic PLACEHOLDERS.
  Before a city goes live, verify against a real source and update its JSON.
- Testimonials are illustrative examples — the operator replaces them with real ones.

## Deploy (after editing)
Site is static → deploy `site/dist/` to Cloudflare Pages:
```
npx wrangler pages deploy site/dist --project-name home-offer-bridge
```
(That npx call is the ONLY Node touch in the whole project, and only for upload.)

## Things NOT to do
- Don't edit files in `site/dist/` (regenerated).
- Don't add cities in legally-excluded states.
- Don't introduce a Node/npm build step for the site — it's intentionally pure Python.
- Don't hardcode brand/phone/webhook in templates — they come from `_brand.json`.
- Don't remove the "not a real estate agent/broker" disclaimer or the mailing address
  from footers — both are compliance requirements (CAN-SPAM + wholesaling disclosure).

## Quick sanity checks
```
python3 build.py --validate                      # all cities pass content rules
grep -rl '{{' site/dist/ | wc -l                 # 0 = no unfilled tokens
grep -rli sunbelt site/dist/ | wc -l             # 0 = old brand fully gone
```
