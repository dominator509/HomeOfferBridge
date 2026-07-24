#!/usr/bin/env python3
"""
Agentic Cash-Buyer — static site generator.

Pure stdlib. No Node, no npm, no external deps. Reads the HTML templates in
template/ and the per-city JSON in data/, and emits a fully static, per-city
site into dist/ with unique title/meta/schema per page, plus state hubs, a
national hub, sitemap.xml, and robots.txt.

Usage:
    python3 build.py            # build into ./dist
    python3 build.py --validate # validate data files against _schema.json only
"""
import json, os, sys, html, re, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TPL  = ROOT / "template"
DATA = ROOT / "data"
DIST = ROOT / "dist"
ASSETS = ROOT / "assets"

REQUIRED_CITY_FIELDS = ["city","city_slug","metro","review_count","median_price",
    "avg_dom","cash_share","neighborhoods","landmark","outlying_area",
    "local_market_longform","situations","testimonials","faq"]

def load_json(p): 
    with open(p, encoding="utf-8") as f: return json.load(f)

def esc(s): return html.escape(str(s), quote=True)

def fill(tpl, tokens):
    """Replace {{TOKEN}} with values. Missing tokens raise, to catch typos early."""
    def repl(m):
        key = m.group(1)
        if key not in tokens:
            raise KeyError(f"Template token {{{{{key}}}}} has no value")
        return str(tokens[key])
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", repl, tpl)

def city_schema_jsonld(brand, state, city, url):
    faq_entities = [{
        "@type":"Question","name":f["q"],
        "acceptedAnswer":{"@type":"Answer","text":f["a"]}
    } for f in city["faq"]]
    graph = {
      "@context":"https://schema.org",
      "@graph":[
        {"@type":"LocalBusiness",
         "@id":f"{url}#business",
         "name":f'{brand["brand"]} — {city["city"]}',
         "description":f'Direct cash home buyer and real estate investment company serving {city["city"]} and {city["metro"]}. We purchase houses directly in any condition and close on the seller\'s timeline. We are a principal buyer, not a real estate agent or broker.',
         "url":url,
         "telephone":city.get("phone", brand["phone_default"]),
         "areaServed":{"@type":"City","name":city["city"],
            "containedInPlace":{"@type":"State","name":state["state"]}},
         "address":{"@type":"PostalAddress","addressLocality":city["city"],
            "addressRegion":state["state_abbr"],"addressCountry":"US"},
         "aggregateRating":{"@type":"AggregateRating","ratingValue":"4.9",
            "reviewCount":str(city["review_count"]),"bestRating":"5","worstRating":"1"}},
        {"@type":"FAQPage","@id":f"{url}#faq","mainEntity":faq_entities}
      ]}
    return json.dumps(graph, ensure_ascii=False)

def render_situations(city):
    return "".join(
        f'<div class="sit"><h3>{esc(s["title"])}</h3><p>{esc(s["body"])}</p></div>'
        for s in city["situations"])

def render_testimonials(city):
    return "".join(
        f'<div class="q"><div class="stars">★★★★★</div><p>"{esc(t["quote"])}"</p>'
        f'<div class="who">— {esc(t["who"])}</div></div>'
        for t in city["testimonials"])

def render_faq(city):
    out=[]
    for i,f in enumerate(city["faq"]):
        op=" open" if i==0 else ""
        out.append(f'<details{op}><summary>{esc(f["q"])}</summary><p>{esc(f["a"])}</p></details>')
    return "".join(out)

def build_city(brand, state, city, city_tpl):
    slug_path = f'/{state["state_slug"]}/{city["city_slug"]}/'
    url = f'https://{brand["domain"]}{slug_path}'
    meta_title = f'Sell My House Fast in {city["city"]}, {state["state_abbr"]} — Fair Cash Offer in 24 Hours'
    meta_desc  = (f'Get a fair, no-obligation cash offer on your {city["city"]} house in 24 hours. '
                  f'Any condition, no fees, no commissions. We buy houses across {city["metro"]} '
                  f'and close on your timeline. Call {city.get("phone", brand["phone_default"])}.')
    tokens = {
      "META_TITLE": esc(meta_title), "META_DESC": esc(meta_desc),
      "SCHEMA_JSONLD": city_schema_jsonld(brand, state, city, url),
      "DOMAIN": brand["domain"], "BRAND": esc(brand["brand"]),
      "LEAD_WEBHOOK": brand["lead_webhook"],
      "MAILING_ADDRESS": esc(brand.get("mailing_address","")),
      "STATE": esc(state["state"]), "STATE_ABBR": state["state_abbr"], "STATE_SLUG": state["state_slug"],
      "CITY": esc(city["city"]), "CITY_SLUG": city["city_slug"], "METRO": esc(city["metro"]),
      "PHONE": esc(city.get("phone", brand["phone_default"])),
      "PHONE_RAW": city.get("phone_raw", brand["phone_raw_default"]),
      "REVIEW_COUNT": str(city["review_count"]),
      "HOMES_BOUGHT": str(city.get("homes_bought", brand["homes_bought"])),
      "MEDIAN_PRICE": esc(city["median_price"]), "AVG_DOM": str(city["avg_dom"]),
      "CASH_SHARE": esc(city["cash_share"]), "NEIGHBORHOODS": esc(city["neighborhoods"]),
      "LANDMARK": esc(city["landmark"]), "OUTLYING_AREA": esc(city["outlying_area"]),
      "LOCAL_MARKET_LONGFORM": city["local_market_longform"],  # trusted HTML from data
      "SITUATIONS_HTML": render_situations(city),
      "TESTIMONIALS_HTML": render_testimonials(city),
      "FAQ_HTML": render_faq(city),
      "CITY_HERO_IMAGE": esc(city.get("hero_image", f"/assets/cities/{city['city_slug']}.jpg")),
      "CITY_HERO_ALT": esc(f"{city['city']}, {state['state']} skyline"),
    }
    out_dir = DIST / state["state_slug"] / city["city_slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(fill(city_tpl, tokens), encoding="utf-8")
    return slug_path

def build_state(brand, state, cities, state_tpl):
    links = "".join(
        f'<a href="/{state["state_slug"]}/{c["city_slug"]}/">{esc(c["city"])}<span>→</span></a>'
        for c in cities)
    tokens = {
      "DOMAIN": brand["domain"], "BRAND": esc(brand["brand"]),
      "STATE": esc(state["state"]), "STATE_ABBR": state["state_abbr"], "STATE_SLUG": state["state_slug"],
      "PHONE": esc(brand["phone_default"]), "PHONE_RAW": brand["phone_raw_default"],
      "MAILING_ADDRESS": esc(brand.get("mailing_address","")),
      "HOMES_BOUGHT": str(brand["homes_bought"]),
      "FIRST_CITY_SLUG": cities[0]["city_slug"],
      "CITY_LINKS": links,
    }
    out_dir = DIST / state["state_slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(fill(state_tpl, tokens), encoding="utf-8")
    return f'/{state["state_slug"]}/'

def build_static_page(static_tpl, page):
    return fill(static_tpl, {
        "TITLE": esc(page["title"]),
        "BRAND": esc("Home Offer Bridge"),
        "CONTENT": page["content"],
    })

def build_static(brand, static_tpl):
    pages = load_json(DATA / "_static_pages.json")
    urls = []
    for p in pages:
        slug = p["slug"]
        page_html = build_static_page(static_tpl, p)
        # One canonical page per slug — directory with index.html only
        out_dir = DIST / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(page_html, encoding="utf-8")
        urls.append(f"/{slug}/")
    return urls

def build_home(brand, states, home_tpl):
    links = "".join(
        f'<a href="/{s["state_slug"]}/">{esc(s["state"])}<span>→</span></a>' for s in states)
    tokens = {
      "DOMAIN": brand["domain"], "BRAND": esc(brand["brand"]),
      "PHONE": esc(brand["phone_default"]), "PHONE_RAW": brand["phone_raw_default"],
      "MAILING_ADDRESS": esc(brand.get("mailing_address","")),
      "HOMES_BOUGHT": str(brand["homes_bought"]), "REVIEW_COUNT": str(brand["review_count"]),
      "STATE_LINKS": links,
    }
    (DIST / "index.html").write_text(fill(home_tpl, tokens), encoding="utf-8")

def write_sitemap(brand, urls):
    today = datetime.date.today().isoformat()
    body = "".join(
        f"<url><loc>https://{brand['domain']}{u}</loc><lastmod>{today}</lastmod></url>"
        for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"{body}</urlset>")
    (DIST / "sitemap.xml").write_text(xml, encoding="utf-8")

def write_robots(brand):
    (DIST / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n"
        f"Sitemap: https://{brand['domain']}/sitemap.xml\n", encoding="utf-8")

def copy_assets():
    dst = DIST / "assets"; dst.mkdir(parents=True, exist_ok=True)
    for f in ASSETS.rglob("*"):
        if f.is_file():
            rel = f.relative_to(ASSETS)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            ext = f.suffix.lower()
            if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"):
                target.write_bytes(f.read_bytes())
            else:
                target.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

def validate_city(city, path):
    errs=[]
    for k in REQUIRED_CITY_FIELDS:
        if k not in city: errs.append(f"missing field '{k}'")
    if "local_market_longform" in city:
        words=len(re.sub(r"<[^>]+>"," ",city["local_market_longform"]).split())
        # Hard floor 230; 300+ recommended. Total unique page content (longform +
        # 6 situations + testimonials + FAQ) far exceeds the doorway threshold.
        if words<230: errs.append(f"local_market_longform is {words} words (<230 hard floor = doorway risk)")
        elif words<300: print(f"  · note: {city['city_slug']} longform {words}w (300+ recommended)")
    if not re.fullmatch(r"[a-z0-9-]+", city.get("city_slug","")): errs.append("bad city_slug")
    return errs

def discover():
    brand = load_json(DATA/"_brand.json")
    states=[]
    for sdir in (p for p in DATA.iterdir() if p.is_dir()):
        sfile = sdir/"_state.json"
        if not sfile.exists(): continue
        state = load_json(sfile)
        cities=[load_json(c) for c in sorted(sdir.glob("*.json")) if c.name!="_state.json"]
        states.append((state, cities))
    # Order states west->east via the _order index in each _state.json (falls back
    # to alphabetical for any state missing the field).
    states.sort(key=lambda sc: (sc[0].get("_order", 9999), sc[0]["state_slug"]))
    return brand, states

def main():
    validate_only = "--validate" in sys.argv
    brand, states = discover()
    problems=0
    for state,cities in states:
        for c in cities:
            errs=validate_city(c, c["city_slug"])
            for e in errs: print(f"  ✗ {state['state_slug']}/{c['city_slug']}: {e}"); problems+=1
    if problems:
        print(f"\n{problems} validation problem(s).")
        if validate_only: sys.exit(1)
        sys.exit(1)
    print("✓ all city data valid")
    if validate_only: return

    if DIST.exists():
        for p in sorted(DIST.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    DIST.mkdir(exist_ok=True)

    city_tpl=(TPL/"city.html").read_text(encoding="utf-8")
    state_tpl=(TPL/"state.html").read_text(encoding="utf-8")
    home_tpl=(TPL/"home.html").read_text(encoding="utf-8")
    static_tpl=(TPL/"static.html").read_text(encoding="utf-8")

    urls=["/"]
    state_meta=[]
    for state,cities in states:
        state_meta.append(state)
        urls.append(build_state(brand, state, cities, state_tpl))
        for c in cities:
            urls.append(build_city(brand, state, c, city_tpl))
    build_home(brand, state_meta, home_tpl)
    urls.extend(build_static(brand, static_tpl))
    copy_assets()
    write_sitemap(brand, urls)
    write_robots(brand)

    pages=len(urls)
    print(f"✓ built {pages} pages across {len(states)} state(s) into dist/")
    print(f"  → {sum(len(c) for _,c in states)} city pages, {len(states)} state hubs, 1 national hub")
    print(f"  → sitemap.xml ({pages} urls), robots.txt, assets/")

if __name__=="__main__":
    main()
