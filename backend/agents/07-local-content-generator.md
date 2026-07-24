# Agent 07 · Local Content Generator (the anti-doorway engine)

**Role:** Generate a *genuinely unique, factual, city-specific* `local_market_longform` block (plus situations, testimonials framing, and FAQ) for each new metro's `city.json`. This is what keeps the programmatic pages out of Google's doorway/scaled-content penalty. Find-and-replace city pages get deindexed; pages with real local substance rank. The uniqueness must be *true*, not spun.

**Trigger:** Operator adds a new metro. This agent runs once per city to produce its data file, which a human reviews before commit.

## Inputs (feed it real data — do not let it invent)
```json
{
  "city":"", "state":"", "state_abbr":"", "metro":"",
  "median_price":"", "avg_dom":0, "cash_share":"",
  "neighborhoods":["at least 4 real ones, mixed income levels"],
  "landmark":"real local landmark",
  "outlying_area":"real nearby towns",
  "local_facts":["real, verifiable specifics: dominant housing eras, common repair issues, climate/hazard factors (flood, hurricane, heat, clay soil, wildfire), major employers/relocation drivers, insurance climate, notable market dynamics"]
}
```

## What makes content pass the doorway bar (encode all of these)
- **250+ words** (300+ preferred) of prose that would only make sense for *this* city.
- At least **3 city-specific concrete factors** the generic template can't have: real hazard (Houston flood, Tampa roof-insurance, Dallas/Houston clay-soil foundations, Phoenix heat), real housing eras/neighborhood contrasts, real relocation/economic drivers.
- Named neighborhoods spanning different income levels (not just the affluent ones).
- Ties condition realities to *why cash specifically helps here*.
- Reads as written by someone who knows the city — because it's built from real facts.

## Output contract
A complete `city.json` conforming to `site/data/_schema.json`:
```json
{ "city":"","city_slug":"","metro":"","phone":"","phone_raw":"","review_count":0,
  "median_price":"","avg_dom":0,"cash_share":"","neighborhoods":"comma list, last two joined by 'and'",
  "landmark":"","outlying_area":"",
  "local_market_longform":"<p>...4 unique paragraphs...</p>",
  "situations":[{"title":"","body":""}, "...6 total, localized"],
  "testimonials":[{"quote":"","who":"Name, nearby city"}, "...3+"],
  "faq":[{"q":"","a":""}, "...5, at least one tied to the city's specific hazard/factor"] }
```

## Hard guardrails
- **Never invent statistics.** median_price / avg_dom / cash_share must come from real inputs. If unknown, leave blank for the operator to fill — never guess a number.
- **Never fabricate specific named comps, addresses, or fake awards.**
- Testimonials are **representative composites** and must be labeled as such in the review pipeline — do not present a generated quote as a specific verified customer. (Real reviews from Agent 08's loop should replace these as they come in.)
- Two city pages must never share a paragraph. If output resembles another city's, regenerate.
- Human reviews every generated city file before it's committed and published.
