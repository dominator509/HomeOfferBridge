# City data generator

Regenerates every `data/{state}/{city}.json` from a single knowledge base.
Pure stdlib, deterministic (seeded per city slug).

## Run
```
cd acb/site/data/_generator
python3 generate.py      # writes ../{state}/{city}.json for all 36 legal states
cd ../..                 # -> acb/site
python3 build.py --validate
python3 build.py
```

## Files
- `states.py` — the 36 legal states + per-state legal disclosure sentence used in FAQs.
- `cities_*.py` — the city knowledge base, grouped west→east. Each city carries real
  neighborhoods, landmark, dominant housing eras, local hazards, economic drivers, county,
  and realistic current-cycle market figures.
- `generate.py` — turns the knowledge base into unique longform + situations + testimonials + FAQ.

## To add a city
Add a dict to the appropriate `cities_*.py` batch (copy an existing entry as a template),
confirm the state is legal per `../../seo/legal-market-coverage.md`, then re-run generate + build.

## Before publishing any city
Verify median_price / avg_dom / cash_share against a real source for that metro and replace the
placeholder. Testimonials are illustrative examples — replace with real, authorized seller quotes.
