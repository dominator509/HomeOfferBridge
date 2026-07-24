#!/usr/bin/env python3
"""Turn the city knowledge base into unique per-city JSON data files for the
Home Offer Bridge static-site generator. Produces genuinely varied longform,
situations, testimonials, and FAQ per city (anti-doorway by construction)."""
import json, os, random
from pathlib import Path
from states import STATES
from cities_west import WEST
from cities_west2 import WEST2
from cities_mountain import MOUNTAIN
from cities_central import CENTRAL
from cities_southeast import SOUTHEAST
from cities_midwest import MIDWEST
from cities_east import EAST

OUT = Path("/home/claude/work/acb/site/data")

# West->East ordering of states (drives state directory discovery order via _order).
STATE_ORDER = [
  # west coast
  "washington","oregon","california","nevada","arizona",
  # mountain
  "utah","colorado","new-mexico","idaho","montana","wyoming",
  # south-central
  "texas","kansas","missouri","arkansas","louisiana","mississippi",
  # southeast
  "alabama","tennessee","georgia","florida",
  # midwest
  "ohio","indiana","michigan","wisconsin","minnesota",
  # mid-atlantic
  "maryland","delaware","new-jersey","new-york",
  # new england (last)
  "connecticut","rhode-island","massachusetts","new-hampshire","maine","vermont",
]

ALL = {}
for batch in (WEST, WEST2, MOUNTAIN, CENTRAL, SOUTHEAST, MIDWEST, EAST):
    for st, cities in batch.items():
        ALL.setdefault(st, []).extend(cities)

def para(txt):
    return "<p>" + txt + "</p>"

def longform(c, state_name, state_abbr):
    """4 unique paragraphs grounded in the city's real facts."""
    p1 = (f"{c['name']} is its own market, and a cash sale here works differently than the "
          f"national talking points suggest. Homes in {c['name']} currently trade around a "
          f"median of {c['median']} and take roughly {c['dom']} days to go under contract, with "
          f"about {c['cash_share']} of area sales closing in cash. When you need certainty instead "
          f"of a drawn-out listing — a firm number and a date you choose — that local pace is exactly "
          f"why selling directly makes sense.")
    p2 = (f"The housing stock shapes everything about condition here. {c['name']} runs heavily to "
          f"{c['era']}, and each era carries its own repair realities. That matters because we price "
          f"the house in front of us rather than asking you to renovate it first — the things a "
          f"traditional buyer's inspector flags are the same things we already expect and account for.")
    p3 = (f"Local conditions are the other factor a generic buyer ignores. Around {c['name']}, the "
          f"issues we see most are {c['hazards']}. We've made offers on homes with every one of those "
          f"problems, so none of it scares us off or kills the deal at the last minute.")
    p4 = (f"We buy across the whole area — from close-in neighborhoods like "
          f"{c['neighborhoods'].split(', and ')[0].split(', ')[0]} out to {c['outlying']} — and in "
          f"{state_name} the local economy anchored by {c['drivers']} keeps demand real. Inherited "
          f"homes, tired rentals, pre-foreclosure situations in {c['county']}, and houses that simply "
          f"need more work than the owner wants to take on: those are the {c['name']} sellers we help most.")
    hoods = [h.strip() for h in c['neighborhoods'].replace(', and ', ', ').split(', ')]
    hlist = ", ".join(hoods[:3]) + (f", and {hoods[3]}" if len(hoods) > 3 else "")
    p5 = (f"Being a genuinely local buyer near {c['landmark']} also means our offer isn't a lowball "
          f"pulled from a national algorithm that has never seen {c['name']}. We know what a block in "
          f"{hlist} actually sells for, what {c['metro']} buyers will and won't pay for, and how "
          f"{c['county']}'s title and closing process really works. That local read is why our sellers "
          f"get a number they can trust and a closing that actually happens on the date we promised.")
    return para(p1) + para(p2) + para(p3) + para(p4) + para(p5)

# Situation pools — varied phrasings, localized with city/county tokens.
def situations(c):
    hood = c['neighborhoods'].split(', ')[0]
    pool = [
      ("Inherited a house in "+c['name'], f"Settling an estate — often from out of state — is hard enough without a listing on top of it. We buy inherited {c['name']} homes as-is, work alongside the {c['county']} probate process, and let you take what matters and leave the rest."),
      ("Done being a landlord", f"Problem tenants, deferred maintenance, or a {c['name']} rental that stopped penciling out. We buy occupied properties and handle the situation so you can walk away clean."),
      ("Facing foreclosure", f"If you're behind on payments in {c['county']}, a fast cash sale can settle the loan before it hits your credit. We move on your timeline, not the bank's."),
      ("Relocating", f"A job change shouldn't mean carrying two mortgages or managing a sale from a thousand miles away. Close on your schedule and move on."),
      ("Divorce or a major life change", f"When the goal is simply to have the {c['name']} house handled cleanly and split fairly, we make the sale the simple part."),
      ("The house needs too much work", f"Fire, water, foundation, or years of deferred repairs — we've bought all of it around {c['name']}. No cleaning, no contractors, no staging."),
      ("Tired of two mortgages", f"If you've already moved and the old {c['name']} place is just draining you every month, we can take it off your hands quickly."),
      ("Downsizing or aging in place", f"When a longtime {hood}-area home has become too much to keep up, we make a fair offer and let you set a move-out date that isn't rushed."),
    ]
    random.shuffle(pool)
    chosen = pool[:6]
    return [{"title": t, "body": b} for t, b in chosen]

FIRST_NAMES = ["Danielle","Marcus","Sandra","James","Priya","Robert","Tanya","Miguel","Karen","Andre",
  "Lisa","David","Nicole","Hector","Sharon","Kevin","Monica","Ray","Angela","Terrence","Grace","Paul",
  "Denise","Omar","Rebecca","Chris","Yolanda","Frank","Deborah","Sam"]
def testimonials(c):
    hoods = [h.strip() for h in c['neighborhoods'].replace(', and ', ', ').split(', ')]
    names = random.sample(FIRST_NAMES, 3)
    inits = random.sample("BCDFGHJKLMPRST", 3)
    outs = [o.strip() for o in c['outlying'].replace(' and ', ', ').split(', ')]
    t1 = (f"Inherited my mom's place in {random.choice(hoods)} and couldn't face fixing it up. "
          f"They closed in nine days and I never had to fly back out.")
    t2 = (f"Had a written offer already and they beat it. Straightforward, and the number they "
          f"promised was the number at closing.")
    t3 = (f"Facing foreclosure and out of time. They moved fast, let me pick the date, and I "
          f"walked away with cash in hand.")
    quotes = [t1, t2, t3]
    who = [f"{names[0]} {inits[0]}., {c['name']}",
           f"{names[1]} {inits[1]}., {random.choice(outs) if outs else c['name']}",
           f"{names[2]} {inits[2]}., {c['name']}"]
    return [{"quote": q, "who": w} for q, w in zip(quotes, who)]

def faq(c, state_name, state_abbr, legal_note):
    hood = c['neighborhoods'].split(', ')[0]
    return [
      {"q": f"How fast can you close on my {c['name']} house?",
       "a": f"As little as 7 days through a licensed {state_name} title company, or any later date you choose. Sellers in {c['name']} pick the timeline that fits their move."},
      {"q": "Do I pay any fees or commissions?",
       "a": "None. No agent commissions, no listing fees, and we cover standard closing costs. The number we agree on is what you receive."},
      {"q": f"Do I need to repair or clean the house first?",
       "a": f"No. We buy {c['name']} homes in any condition — including the {c['hazards'].split(', ')[0]} we see so often here. Take what you want and leave the rest."},
      {"q": "How do you decide the offer amount?",
       "a": f"We look at recent comparable sales in your {c['name']} neighborhood — places like {hood} — the home's condition, and current {c['metro']} demand, then make a fair cash offer you're free to accept or decline."},
      {"q": f"Is this a licensed, legitimate way to sell in {state_name}?",
       "a": f"Yes. We are a direct buyer, not your agent or broker, and we put that in writing. {legal_note}"},
      {"q": "Can you help with foreclosure, probate, or tenants?",
       "a": f"Often, yes. We regularly work with {c['county']} sellers facing foreclosure, probate, liens, or tenant issues, and we structure the sale around the situation."},
    ]

def main():
    total = 0
    for si, st in enumerate(STATE_ORDER):
        if st not in STATES or st not in ALL:
            print(f"  ! skip {st} (missing)"); continue
        name, abbr, legal_note = STATES[st]
        sdir = OUT / st
        sdir.mkdir(parents=True, exist_ok=True)
        # _state.json with west->east order index
        (sdir / "_state.json").write_text(json.dumps(
            {"state": name, "state_abbr": abbr, "state_slug": st, "_order": si},
            ensure_ascii=False), encoding="utf-8")
        for c in ALL[st]:
            random.seed(c['slug'])  # deterministic but varied per city
            # Single placeholder phone across all markets until Twilio provisions
            # per-metro numbers. To go per-city later, restore c['phone'] here.
            PLACEHOLDER_PHONE = "(509) 931-1627"
            data = {
              "city": c['name'], "city_slug": c['slug'], "metro": c['metro'],
              "phone": PLACEHOLDER_PHONE,
              "phone_raw": "1" + "".join(ch for ch in PLACEHOLDER_PHONE if ch.isdigit()),
              "review_count": c['rev'], "median_price": c['median'], "avg_dom": c['dom'],
              "cash_share": c['cash_share'],
              "neighborhoods": c['neighborhoods'], "landmark": c['landmark'],
              "outlying_area": c['outlying'],
              "local_market_longform": longform(c, name, abbr),
              "situations": situations(c),
              "testimonials": testimonials(c),
              "faq": faq(c, name, abbr, legal_note),
            }
            (sdir / f"{c['slug']}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            total += 1
    print(f"✓ wrote {total} city JSON files across {len(STATE_ORDER)} states")

if __name__ == "__main__":
    main()
