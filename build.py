# ::ILANG [TYPE:module][PROJECT:vps-deals][LANG:zh]
# ::STATE{@FILE, role: render the configured provider directory as static HTML and search metadata}
# ::BOUNDARY{never: invent prices, expiry dates, or structured data values|scope:permanent}
# ::RULE{config: brand, providers, locale, and base URL come from .ilang/site.ilang}
"""Build a dependency-free static VPS offers directory."""
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
OUT = ROOT / "site"


def read_config():
    providers, settings = [], {}
    in_providers = False
    for raw in (ROOT / ".ilang/site.ilang").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("::MODULE{PROVIDERS"):
            in_providers = True
            continue
        if line.startswith("::MODULE{") and not line.startswith("::MODULE{PROVIDERS"):
            in_providers = False
        if in_providers and "|" in line:
            parts = [p.strip() for p in line.split("|", 3)]
            if len(parts) == 4 and all(parts[:3]):
                providers.append({"name": parts[0], "home": parts[1], "source": parts[2], "affiliate": parts[3]})
        if line.startswith(("locale:", "base_url:")):
            k, v = line.split(":", 1)
            settings[k.strip()] = v.strip()
    first = next((x.strip() for x in (ROOT / ".ilang/site.ilang").read_text(encoding="utf-8").splitlines() if x.startswith("::STATE{@SITE")), "")
    brand = re.search(r"brand:([^,}]+)", first)
    niche = re.search(r"niche:([^,}]+)", first)
    return {"brand": brand.group(1).strip() if brand else "VPS deals", "niche": niche.group(1).strip() if niche else "VPS hosting", "providers": providers, "settings": settings}


def esc(x):
    return html.escape(str(x), quote=True)


def page(title, description, canonical, body, jsonld):
    kind = "index" if canonical.endswith("/") else "compare" if canonical.endswith("compare.html") else "deal" if "/deal-" in canonical else "provider"
    template = (ROOT / "templates" / f"{kind}.html").read_text(encoding="utf-8")
    values = {"TITLE": esc(title), "DESCRIPTION": esc(description), "CANONICAL": esc(canonical), "BRAND": esc(CONFIG["brand"]), "BODY": body, "JSONLD": json.dumps(jsonld, ensure_ascii=False)}
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def item(title, price, currency, url, position):
    return {"@type": "ListItem", "position": position, "url": url, "name": title}


def main():
    global CONFIG
    CONFIG = read_config()
    data_path = ROOT / "data/offers.json"
    data = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {"offers": [], "fetched_at": None, "errors": []}
    offers = data.get("offers", [])
    base = CONFIG["settings"].get("base_url", "https://vps-deals.pages.dev").rstrip("/")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(exist_ok=True)
    cards = []
    for offer in offers:
        currency = offer.get("currency", "")
        price = offer.get("price")
        price_text = f"{currency} {price}/month" if price else "Price unavailable"
        cards.append(f'<article class="card"><p class="eyebrow">{esc(offer.get("provider"))} · Official public price</p><h2>{esc(offer.get("title"))}</h2><p class="price">{esc(price_text)}</p><p>{esc(offer.get("evidence", ""))}</p><p class="source">Observed {esc(offer.get("fetched_at", ""))}</p><a class="button" href="{esc(offer.get("offer_url", offer.get("source_url", "")))}" rel="nofollow noopener">Check provider</a> <a href="{esc(offer.get("source_url", ""))}">Source</a></article>')
    if not cards:
        cards = ['<article class="card empty"><h2>No prices verified yet</h2><p>The scheduled fetch will publish only prices it can read on the official sources. Check the source pages below in the meantime.</p></article>']
    providers_html = "".join(f'<li><a href="{esc(p["source"])}">{esc(p["name"])} official pricing page</a></li>' for p in CONFIG["providers"])
    desc = f"Current VPS prices observed on official provider pages. Source URLs and observation times are shown for each listing."
    index_body = f'<section class="hero"><p class="eyebrow">Independent VPS price tracker</p><h1>VPS deals, with sources attached.</h1><p>Compare public plan prices observed from provider pages. These are price observations, not guaranteed coupons or discounts. Always confirm the current terms at checkout.</p><p class="updated">Last fetch: {esc(data.get("fetched_at") or "not yet fetched")}</p></section><section><h2>Observed prices</h2><div class="grid">{"".join(cards)}</div></section><section><h2>Official sources</h2><ul>{providers_html}</ul></section>'
    ld = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [item(o.get("title", "VPS"), o.get("price"), o.get("currency"), o.get("source_url", ""), i + 1) for i, o in enumerate(offers)]}
    (OUT / "index.html").write_text(page(f"{CONFIG['brand']} | VPS Prices", desc, base + "/", index_body, ld), encoding="utf-8")
    compare_body = f"<section class=\"hero\"><p class=\"eyebrow\">Provider index</p><h1>Compare official VPS sources</h1><p>Browse each provider's public VPS page. Prices shown here come from the latest successful fetch.</p></section><ul class=\"provider-list\">{providers_html}</ul>"
    (OUT / "compare.html").write_text(page(f"Compare VPS providers | {CONFIG['brand']}", desc, base + "/compare.html", compare_body, {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [item(p["name"], None, None, p["source"], i + 1) for i, p in enumerate(CONFIG["providers"])]}), encoding="utf-8")
    for p in CONFIG["providers"]:
        pid = re.sub(r"[^a-z0-9]+", "-", p["name"].lower()).strip("-")
        related = [o for o in offers if o.get("provider") == p["name"]]
        lis = "".join(f'<li>{esc(o.get("title"))}: {esc(o.get("currency"))} {esc(o.get("price"))}/month · observed {esc(o.get("fetched_at"))}</li>' for o in related) or "<li>No verifiable price captured yet.</li>"
        detail = f'<section class="hero"><p class="eyebrow">Provider</p><h1>{esc(p["name"])} VPS</h1><p>Official source: <a href="{esc(p["source"])}">{esc(p["source"])}</a></p></section><h2>Latest observed prices</h2><ul>{lis}</ul><p><a class="button" href="{esc(p["source"])}" rel="nofollow noopener">Visit official page</a></p>'
        offer_nodes = [{"@type": "Offer", "url": o["source_url"], "price": o["price"], "priceCurrency": o["currency"]} for o in related if o.get("price") and o.get("currency") and o.get("source_url")]
        product = {"@context": "https://schema.org", "@type": "Service", "name": f"{p['name']} VPS", "url": p["source"], "provider": {"@type": "Organization", "name": p["name"], "url": p["home"]}}
        if offer_nodes:
            product["offers"] = offer_nodes
        (OUT / f"provider-{pid}.html").write_text(page(f"{p['name']} VPS prices | {CONFIG['brand']}", desc, f"{base}/provider-{pid}.html", detail, product), encoding="utf-8")
    stamp_raw = data.get("fetched_at")
    try:
        stamp = datetime.fromisoformat(stamp_raw.replace("Z", "+00:00")).date().isoformat()
    except (AttributeError, ValueError):
        stamp = ""
    urls = ["/", "/compare.html"] + [f"/provider-{re.sub(r'[^a-z0-9]+','-',p['name'].lower()).strip('-')}.html" for p in CONFIG["providers"]]
    for offer in offers:
        oid = re.sub(r"[^a-z0-9]+", "-", str(offer.get("id", "offer")).lower()).strip("-")
        offer_url = f"{base}/deal-{oid}.html"
        urls.append(f"/deal-{oid}.html")
        detail_body = f'<section class="hero"><p class="eyebrow">Official VPS price observation</p><h1>{esc(offer.get("provider"))}: {esc(offer.get("title"))}</h1><p class="price">{esc(offer.get("currency", ""))} {esc(offer.get("price", "Price unavailable"))}/month</p><p>Observed {esc(offer.get("fetched_at", ""))}. This is a public price listing, not a guaranteed discount. Confirm current price and terms with the provider.</p><p><a href="{esc(offer.get("source_url", ""))}">Original source page</a></p><a class="button" href="{esc(offer.get("offer_url", ""))}" rel="nofollow noopener">Check provider</a></section><p>{esc(offer.get("evidence", ""))}</p>'
        schema_offer = {"@context": "https://schema.org", "@type": "Offer", "url": offer.get("offer_url", ""), "seller": {"@type": "Organization", "name": offer.get("provider", "")}}
        if offer.get("price") and offer.get("currency"):
            schema_offer.update({"price": offer["price"], "priceCurrency": offer["currency"]})
        if offer.get("valid_until"):
            schema_offer["priceValidUntil"] = offer["valid_until"]
        (OUT / f"deal-{oid}.html").write_text(page(f"{offer.get('provider')} VPS price | {CONFIG['brand']}", desc, offer_url, detail_body, schema_offer), encoding="utf-8")
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{esc(base + u)}</loc><lastmod>{stamp}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    print(f"Built {len(urls)} pages for {len(CONFIG['providers'])} configured providers in {OUT}.")


CSS = """*{box-sizing:border-box}body{margin:0;background:#f5f7fb;color:#172033;font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}header{display:flex;justify-content:space-between;align-items:center;padding:18px max(5vw,24px);background:#0b1220;color:#fff}a{color:#2362a6}header a{color:#fff;text-decoration:none;margin-left:18px}.brand{font-weight:800;font-size:1.15rem}main{max-width:1080px;margin:auto;padding:32px 24px}.hero{padding:34px;border-radius:20px;background:linear-gradient(125deg,#0e1d38,#185e79);color:white}.hero a{color:#c4ecff}.hero h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.1;margin:.3em 0}.eyebrow,.updated,.source{font-size:.86rem;opacity:.8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}.card{background:#fff;border:1px solid #e1e7ef;border-radius:14px;padding:22px;box-shadow:0 4px 18px #0c20300c}.card h2{margin:.3em 0}.price{font-size:1.5rem;font-weight:750;color:#087b62}.button{display:inline-block;background:#0a775d;color:#fff;padding:9px 15px;border-radius:8px;text-decoration:none}.source{overflow-wrap:anywhere}.provider-list{line-height:2.2}footer{padding:28px max(5vw,24px);background:#e9eef4;color:#45536a;font-size:.9rem}@media(max-width:600px){header{align-items:flex-start;gap:12px;flex-direction:column}header a{margin:0 14px 0 0}.hero{padding:24px}}"""

if __name__ == "__main__":
    main()
