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


# Real Admitad affiliate link for is*hosting VPS (offer 173159), joined to ad space
# "VPS Price Watch" (website 3007089). Verified: 302 -> ishosting.com with admitad attribution.
AD_URL = "https://xcdus.com/g/t7pdcms1vh9f1175b8bbf6378a678b/"
AD_BLOCK = (
    '<section class="ad" aria-label="Advertisement">'
    '<p class="ad-label">Sponsored</p>'
    '<div class="ad-card">'
    '<h2>is*hosting VPS — 40+ countries</h2>'
    '<p>Want a VPS outside the usual big brands? is*hosting runs VPS in 40+ locations with '
    'flexible configurations and hourly billing.</p>'
    f'<a class="button" href="{AD_URL}" rel="nofollow sponsored noopener" target="_blank">'
    'View is*hosting plans</a>'
    '</div></section>'
)
ADDITIONAL_AD_BLOCKS = (
    '<section class="ad" aria-label="Advertisement">'
    '<p class="ad-label">Sponsored</p>'
    '<div class="ad-card">'
    '<h2>HyperHost</h2>'
    '<a class="button" href="https://rcpsj.com/g/4y24lnxl7f9f1175b8bb7f67b8171e/" rel="nofollow sponsored noopener" target="_blank">'
    'View HyperHost plans</a>'
    '</div></section>'
    '<section class="ad" aria-label="Advertisement">'
    '<p class="ad-label">Sponsored</p>'
    '<div class="ad-card">'
    '<h2>Godlike.Host</h2>'
    '<a class="button" href="https://yjfca.com/g/n4h0en61qn9f1175b8bb52f0388f55/" rel="nofollow sponsored noopener" target="_blank">'
    'View Godlike.Host plans</a>'
    '</div></section>'
    '<section class="ad" aria-label="Advertisement">'
    '<p class="ad-label">Sponsored</p>'
    '<div class="ad-card">'
    '<h2>ProHoster</h2>'
    '<a class="button" href="https://ntzgd.com/g/gaetfoqpj79f1175b8bb934d4157fe/" rel="nofollow sponsored noopener" target="_blank">'
    'View ProHoster plans</a>'
    '</div></section>'
)
SPONSORED_BLOCKS = AD_BLOCK + ADDITIONAL_AD_BLOCKS


def page(title, description, canonical, body, jsonld, kind=None):
    if kind is None:
        kind = "index" if canonical.endswith("/") else "compare" if canonical.endswith("compare.html") else "deal" if "/deal-" in canonical else "provider"
    template = (ROOT / "templates" / f"{kind}.html").read_text(encoding="utf-8")
    values = {"TITLE": esc(title), "DESCRIPTION": esc(description), "CANONICAL": esc(canonical), "BRAND": esc(CONFIG["brand"]), "BODY": body, "JSONLD": json.dumps(jsonld, ensure_ascii=False)}
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def item(title, price, currency, url, position):
    return {"@type": "ListItem", "position": position, "url": url, "name": title}


def quote(x):
    """Wrap an official-source string in the same curly quotes the source page uses."""
    return "\u201c" + esc(x) + "\u201d"


def plan_line(o):
    """One observed plan per line. Every string printed here is copied verbatim from the
    official source page; the site adds only the field labels around it."""
    if o.get("official_discount") and o.get("official_renewal"):
        specs = " \u00b7 ".join(quote(s) for s in o.get("official_spec_lines", []))
        return (
            f'<li><strong>{esc(o.get("title"))}</strong> \u2014 first term {esc(o.get("currency"))} {esc(o.get("intro_price"))}/mo;'
            f' discount {quote(o.get("official_discount", ""))}; was {quote(o.get("official_was", ""))} \u2192 now {quote(o.get("official_now", ""))};'
            f' renewal {quote(o.get("official_renewal", ""))};'
            f' specs {specs} \u00b7 observed {esc(o.get("fetched_at", ""))}</li>'
        )
    if o.get("official_price_line"):
        return f'<li>{esc(o.get("title"))}: From {esc(o.get("currency"))} {esc(o.get("price"))}/month \u00b7 observed {esc(o.get("fetched_at"))}</li>'
    return f'<li>{esc(o.get("title"))}: {esc(o.get("currency"))} {esc(o.get("price"))}/month \u00b7 observed {esc(o.get("fetched_at"))}</li>'


def main():
    global CONFIG
    CONFIG = read_config()
    data_path = ROOT / "data/offers.json"
    data = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {"offers": [], "fetched_at": None, "errors": []}
    offers = data.get("offers", [])
    # Providers whose official page was read but yielded no usable plan price are published
    # as "not observed" records with their source URL and observation time (never invented).
    unobserved = [u for u in data.get("unobserved", []) if str(u.get("provider", "")).strip()]
    base = CONFIG["settings"].get("base_url", "").strip().rstrip("/")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(exist_ok=True)
    # Defensively enforce one well-formed monthly offer per provider/plan/currency.
    valid_offers = []
    seen = set()
    for offer in offers:
        provider = str(offer.get("provider", "")).strip()
        title = str(offer.get("title", "")).strip()
        currency = str(offer.get("currency", "")).strip().upper()
        price = str(offer.get("price", "")).strip()
        source_url = str(offer.get("source_url", "")).strip()
        if not (provider and title and len(title) <= 80 and "\n" not in title
                and currency in {"USD", "EUR", "GBP"}
                and re.fullmatch(r"\d+(?:\.\d{1,2})?", price)
                and offer.get("billing_period") == "month" and source_url.startswith("https://")):
            continue
        key = (provider.casefold(), title.casefold(), currency)
        if key in seen:
            continue
        seen.add(key)
        valid_offers.append(offer)
    offers = valid_offers
    cards = []
    for offer in offers:
        currency = offer.get("currency", "")
        price = offer.get("price")
        price_text = f"{currency} {price}/month"
        description = offer.get("description") or f"{offer.get('provider')} {offer.get('title')}: {price_text}. Check current terms on the official source."
        if offer.get("official_discount") and offer.get("official_renewal"):
            # The official page prints a discounted price with a separate renewal rate, so the
            # card states exactly those official strings and nothing the page does not print.
            specs = " \u00b7 ".join(quote(s) for s in offer.get("official_spec_lines", []))
            cards.append(
                f'<article class="card"><p class="eyebrow">{esc(offer.get("provider"))} \u00b7 {esc(offer.get("price_basis_label", "Official public price"))} \u00b7 {esc(offer.get("discount", ""))}</p>'
                f'<h2>{esc(offer.get("title"))}</h2>'
                f'<p class="price">{esc(currency)} {esc(offer.get("intro_price"))}/mo first term</p>'
                f'<ul>'
                f'<li><strong>Discount printed on the official page:</strong> {quote(offer.get("official_discount", ""))}</li>'
                f'<li><strong>Price shown before discount:</strong> {quote(offer.get("official_was", ""))}</li>'
                f'<li><strong>Price shown after discount:</strong> {quote(offer.get("official_now", ""))}</li>'
                f'<li><strong>Renewal:</strong> {quote(offer.get("official_renewal", ""))}</li>'
                f'<li><strong>Specs:</strong> {specs}</li>'
                f'<li><strong>How the monthly rate is calculated:</strong> {quote(offer.get("official_note", ""))}</li>'
                f'</ul>'
                f'<p class="source">Observed {esc(offer.get("fetched_at", ""))} \u00b7 <a href="{esc(offer.get("source_url", ""))}">Official source</a></p>'
                f'<a class="button" href="{esc(offer.get("offer_url", offer.get("source_url", "")))}" rel="nofollow noopener">Check provider</a></article>'
            )
            continue
        basis_label = esc(offer.get("price_basis_label", "Official public price"))
        if offer.get("official_price_line"):
            # Official page prints this as a starting price ("From"), not as a fixed list price.
            price_text = f'From {currency} {price}/month'
        cards.append(f'<article class="card"><p class="eyebrow">{esc(offer.get("provider"))} \u00b7 {basis_label}</p><h2>{esc(offer.get("title"))}</h2><p class="price">{esc(price_text)}</p><p>{esc(description)} <a href="{esc(offer.get("source_url", ""))}">Official source</a></p><p class="source">Observed {esc(offer.get("fetched_at", ""))}</p><a class="button" href="{esc(offer.get("offer_url", offer.get("source_url", "")))}" rel="nofollow noopener">Check provider</a></article>')
    # Providers read but with no usable price are shown in the same card structure, with the
    # official source URL and the exact time the page was read.
    for rec in unobserved:
        provider = str(rec.get("provider", "")).strip()
        if any(o.get("provider") == provider for o in offers):
            continue
        note = rec.get("note") or "No plan price could be read on the official page."
        cards.append(
            f'<article class="card empty"><p class="eyebrow">{esc(provider)} · Official public price</p>'
            f'<h2>Not observed</h2><p class="price">—</p>'
            f'<p>{esc(note)} <a href="{esc(rec.get("source_url", ""))}">Official source</a></p>'
            f'<p class="source">Observed {esc(rec.get("fetched_at", ""))}</p>'
            f'<a class="button" href="{esc(rec.get("source_url", ""))}" rel="nofollow noopener">Check provider</a></article>'
        )
    if not cards:
        cards = ['<article class="card empty"><h2>No prices verified yet</h2><p>The scheduled fetch will publish only prices it can read on the official sources. Check the source pages below in the meantime.</p></article>']
    providers_html = "".join(
        f'<li><a href="/provider-{esc(re.sub(r"[^a-z0-9]+", "-", p["name"].lower()).strip("-"))}">{esc(p["name"])} on {esc(CONFIG["brand"])}</a>'
        f' · official pricing page: <a href="{esc(p["source"])}">{esc(p["source"])}</a></li>'
        for p in CONFIG["providers"]
    )
    desc = f"Current VPS prices observed on official provider pages. Source URLs and observation times are shown for each listing."
    index_body = f'<section class="hero"><p class="eyebrow">Independent VPS price tracker</p><h1>VPS deals, with sources attached.</h1><p>Compare public plan prices observed from provider pages. These are price observations, not guaranteed coupons or discounts. Always confirm the current terms at checkout.</p><p class="updated">Last fetch: {esc(data.get("fetched_at") or "not yet fetched")}</p></section><section><h2>Observed prices</h2><div class="grid">{"".join(cards)}</div></section>{SPONSORED_BLOCKS}<section><h2>Official sources</h2><ul>{providers_html}</ul></section>'
    ld = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [item(o.get("title", "VPS"), o.get("price"), o.get("currency"), o.get("source_url", ""), i + 1) for i, o in enumerate(offers)]}
    (OUT / "index.html").write_text(page(f"{CONFIG['brand']} | VPS Prices", desc, base + "/", index_body, ld), encoding="utf-8")
    compare_body = f"<section class=\"hero\"><p class=\"eyebrow\">Provider index</p><h1>Compare official VPS sources</h1><p>Browse each provider's public VPS page. Prices shown here come from the latest successful fetch.</p></section><ul class=\"provider-list\">{providers_html}</ul>{SPONSORED_BLOCKS}"
    (OUT / "compare.html").write_text(page(f"Compare VPS providers | {CONFIG['brand']}", desc, base + "/compare", compare_body, {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [item(p["name"], None, None, p["source"], i + 1) for i, p in enumerate(CONFIG["providers"])]}), encoding="utf-8")
    for p in CONFIG["providers"]:
        pid = re.sub(r"[^a-z0-9]+", "-", p["name"].lower()).strip("-")
        related = [o for o in offers if o.get("provider") == p["name"]]
        notes = [u for u in unobserved if str(u.get("provider", "")).strip() == p["name"]]
        if not related:
            if notes:
                rec = notes[0]
                lis = (f'<li>Not observed · observed {esc(rec.get("fetched_at", ""))} · '
                       f'{esc(rec.get("note", "No plan price could be read on the official page."))}</li>')
            else:
                lis = "<li>No verifiable price captured yet.</li>"
        else:
            lis = "".join(plan_line(o) for o in related)
        detail = f'<section class="hero"><p class="eyebrow">Provider</p><h1>{esc(p["name"])} VPS</h1><p>Official source: <a href="{esc(p["source"])}">{esc(p["source"])}</a></p></section><h2>Latest observed prices</h2><ul>{lis}</ul><p><a class="button" href="{esc(p["source"])}" rel="nofollow noopener">Visit official page</a></p><p><a href="/compare">Back to provider comparison</a></p>'
        offer_nodes = [{"@type": "Offer", "url": o["source_url"], "price": o["price"], "priceCurrency": o["currency"]} for o in related if o.get("price") and o.get("currency") and o.get("source_url")]
        product = {"@context": "https://schema.org", "@type": "Service", "name": f"{p['name']} VPS", "url": p["source"], "provider": {"@type": "Organization", "name": p["name"], "url": p["home"]}}
        if offer_nodes:
            product["offers"] = offer_nodes
        (OUT / f"provider-{pid}.html").write_text(page(f"{p['name']} VPS prices | {CONFIG['brand']}", desc, f"{base}/provider-{pid}", detail, product), encoding="utf-8")
    stamp_raw = data.get("fetched_at")
    try:
        stamp = datetime.fromisoformat(stamp_raw.replace("Z", "+00:00")).date().isoformat()
    except (AttributeError, ValueError):
        stamp = ""
    urls = ["/", "/compare"] + [f"/provider-{re.sub(r'[^a-z0-9]+','-',p['name'].lower()).strip('-')}" for p in CONFIG["providers"]]
    for offer in []:  # Thin duplicate price-only deal pages are excluded; observations remain on the homepage.
        oid = re.sub(r"[^a-z0-9]+", "-", str(offer.get("id", "offer")).lower()).strip("-")
        offer_url = f"{base}/deal-{oid}.html"
        urls.append(f"/deal-{oid}")
        detail_body = f'<section class="hero"><p class="eyebrow">Official VPS price observation</p><h1>{esc(offer.get("provider"))}: {esc(offer.get("title"))}</h1><p class="price">{esc(offer.get("currency", ""))} {esc(offer.get("price", ""))}/month</p><p>{esc(offer.get("description") or f"{offer.get('provider')} {offer.get('title')}: {offer.get('currency')} {offer.get('price')}/month. Check current terms on the official source.")}</p><p>Observed {esc(offer.get("fetched_at", ""))}. Confirm current terms with the provider.</p><p><a href="{esc(offer.get("source_url", ""))}">Original source page</a></p><a class="button" href="{esc(offer.get("offer_url", ""))}" rel="nofollow noopener">Check provider</a></section>'
        schema_offer = {"@context": "https://schema.org", "@type": "Offer", "url": offer.get("offer_url", ""), "seller": {"@type": "Organization", "name": offer.get("provider", "")}}
        if offer.get("price") and offer.get("currency"):
            schema_offer.update({"price": offer["price"], "priceCurrency": offer["currency"]})
        if offer.get("valid_until"):
            schema_offer["priceValidUntil"] = offer["valid_until"]
        (OUT / f"deal-{oid}.html").write_text(page(f"{offer.get('provider')} VPS price | {CONFIG['brand']}", desc, offer_url, detail_body, schema_offer), encoding="utf-8")
    # Static info pages (About / Privacy / Contact) and a real 404 page.
    info = {
        "about": (
            "About | " + CONFIG["brand"],
            "About vpspricewatch.com — an independently maintained VPS price directory.",
            '<section class="hero"><p class="eyebrow">About this site</p><h1>About vpspricewatch.com</h1><p>vpspricewatch.com is an independent VPS price tracking project. It is independently maintained and does not act as an agent for any hosting provider.</p></section>'
            '<section><h2>What this site does</h2><p>It collects and publishes public VPS plan prices observed directly on official hosting provider pages. Every listing links back to its official source so visitors can confirm the current terms themselves.</p><p>The project does not sell hosting, does not represent any hosting provider, and never changes the prices shown by providers. Listings are price observations, not guaranteed coupons or discounts.</p></section>'
            '<section><h2>Why it exists</h2><p>Provider pricing pages are spread across many sites and change often. This project keeps a single, source-linked view of public plan prices so the comparison is easy to verify.</p></section>'
            '<section><h2>Contact</h2><p>Questions or corrections? See the <a href="/contact">contact page</a>.</p></section>',
        ),
        "privacy": (
            "Privacy Policy | " + CONFIG["brand"],
            "Privacy policy for vpspricewatch.com: affiliate links, sponsored placements, third-party advertising and the visitor data the site uses.",
            '<section class="hero"><p class="eyebrow">Legal</p><h1>Privacy Policy</h1><p>Last updated: 2026-10-09</p></section>'
            '<section><h2>Overview</h2><p>This privacy policy explains what information vpspricewatch.com collects and how it is used. By using the site you agree to the practices described here.</p></section>'
            '<section><h2>Advertising and affiliate links</h2><p>This site participates in affiliate marketing. Some outbound links to hosting providers are affiliate links issued and tracked through the <strong>Admitad</strong> affiliate network (admitad.com). If you follow one of these links and later make a qualifying purchase, this site may earn a commission.</p>'
            '<p><strong>No extra cost to you:</strong> affiliate links do not change the price you pay. Prices shown on this site are observations taken from official provider pages, and the final price and terms must always be confirmed with the provider.</p>'
            '<p><strong>Current sponsored partners:</strong> is*hosting, HyperHost, Godlike.Host and ProHoster. Sponsored placements for these partners appear on the homepage and the provider comparison page. The list of partners may change as partnerships are added or removed; this page reflects the current state.</p>'
            '<p><strong>How sponsored links are marked:</strong> sponsored placements are labelled <em>Sponsored</em> and their links carry <code>rel="nofollow sponsored"</code> so that search engines can identify them as paid placements. Sponsored content is always shown separately from price observations.</p>'
            '<p><strong>Editorial independence:</strong> affiliate commissions do not change how we report prices, rankings, or comparisons. This site does not sell hosting itself and cannot change provider prices, accounts, or billing.</p>'
            '<p>When you follow an affiliate link you leave this site. The affiliate network and the advertiser may then process referral information under their own privacy policies, which we do not control.</p></section>'
            '<section><h2>Data we use</h2><p>When you visit, the following data may be processed:</p><ul>'
            '<li><strong>Server and CDN logs:</strong> the hosting provider (Cloudflare) records request metadata such as IP address, browser type, requested URL, and timestamp for security and performance.</li>'
            '<li><strong>Analytics:</strong> privacy-respecting, aggregated usage statistics may be collected to understand which pages are useful. Cloudflare Web Analytics is enabled by the hosting service and collects performance and usage measurements. No Google Analytics measurement script is currently installed in the site source.</li>'
            '<li><strong>Affiliate attribution:</strong> following a sponsored link sends you to the affiliate network, which may set a cookie or use similar technologies to record the referral (referring page, time, and a network identifier) so that a resulting purchase can be attributed. This site only receives aggregated statistics, never your payment or personal details.</li>'
            '<li><strong>Advertising cookies:</strong> if and when additional ad networks are enabled, those networks may set cookies to measure impressions and serve relevant ads.</li>'
            '<li><strong>Email:</strong> if you contact us by email, we store the message and address only to reply.</li>'
            '</ul></section>'
            '<section><h2>Your choices</h2><p>You can disable or block cookies in your browser, including third-party cookies. Blocking them prevents affiliate referral attribution and ad personalization but will not affect access to any core content on this site. For ad personalization controls, use the opt-out tools provided by the advertising network or by Admitad.</p></section>'
            '<section><h2>Contact</h2><p>See the <a href="/contact">contact page</a> for the current availability of a contact channel.</p></section>',
        ),
        "contact": (
            "Contact | " + CONFIG["brand"],
            "Contact channel availability for vpspricewatch.com.",
            '<section class="hero"><p class="eyebrow">Get in touch</p><h1>Contact</h1><p>Contact the independently maintained VPS Price Watch directory by email.</p></section>'
            '<section><h2>Email</h2><p><a href="mailto:zhong1205750377@gmail.com">zhong1205750377@gmail.com</a></p><p>Use this address for listing corrections, questions about this site, or privacy requests.</p></section>'
            '<section><h2>Before you write</h2><p>Prices shown on the site are observations from official provider pages. For billing, account, or service issues, contact the provider directly — this project cannot change provider accounts.</p></section>',
        ),
    }
    for slug, (ptitle, pdesc, pbody) in info.items():
        pcanon = f"{base}/{slug}"
        pld = {"@context": "https://schema.org", "@type": "WebPage", "name": ptitle, "url": pcanon}
        (OUT / f"{slug}.html").write_text(page(ptitle, pdesc, pcanon, pbody, pld, kind="page"), encoding="utf-8")
        urls.append(f"/{slug}")
    notfound_body = '<section class="hero"><p class="eyebrow">404</p><h1>Page not found</h1><p>The page you requested does not exist or has moved. <a href="/">Return home</a> or browse <a href="/compare">providers</a>.</p></section>'
    notfound_ld = {"@context": "https://schema.org", "@type": "WebPage", "name": "404 — Page not found", "url": f"{base}/404.html"}
    (OUT / "404.html").write_text(page("404 | " + CONFIG["brand"], "The requested page was not found.", f"{base}/404.html", notfound_body, notfound_ld, kind="page"), encoding="utf-8")
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{esc(base + u)}</loc><lastmod>{stamp}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    # Providers that were replaced stay reachable: old URLs redirect instead of 404.
    (OUT / "_redirects").write_text("/provider-interserver /compare 301\n/provider-contabo /compare 301\n", encoding="utf-8")
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    editorial = ROOT / "editorial"
    if editorial.exists():
        shutil.copytree(editorial, OUT / "guides", dirs_exist_ok=True)
        with (OUT / "style.css").open("a", encoding="utf-8") as fh:
            fh.write((editorial / "editorial.css").read_text(encoding="utf-8"))
        for hp in OUT.rglob("*.html"):
            txt = hp.read_text(encoding="utf-8")
            if 'href="/guides/"' not in txt:
                txt = txt.replace('<a href="/compare.html">Compare providers</a>', '<a href="/compare.html">Compare providers</a><a href="/guides/">Guides</a>').replace('<a href="/compare">Compare providers</a>', '<a href="/compare">Compare providers</a><a href="/guides/">Guides</a>')
                hp.write_text(txt, encoding="utf-8")
        sm = (OUT / "sitemap.xml").read_text(encoding="utf-8")
        entries = "".join('<url><loc>' + esc(base + '/guides/' + str(p.parent.relative_to(editorial)).replace('\\','/').replace('.', '').strip('/') + '/') + '</loc></url>\n' for p in editorial.rglob('index.html'))
        entries = entries.replace('/guides//', '/guides/')
        (OUT / "sitemap.xml").write_text(sm.replace('</urlset>', entries + '</urlset>'), encoding="utf-8")
    print(f"Built {len(urls)} pages for {len(CONFIG['providers'])} configured providers in {OUT}.")


CSS = """*{box-sizing:border-box}body{margin:0;background:#f5f7fb;color:#172033;font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}header{display:flex;justify-content:space-between;align-items:center;padding:18px max(5vw,24px);background:#0b1220;color:#fff}a{color:#2362a6}header a{color:#fff;text-decoration:none;margin-left:18px}.brand{font-weight:800;font-size:1.15rem}main{max-width:1080px;margin:auto;padding:32px 24px}.hero{padding:34px;border-radius:20px;background:linear-gradient(125deg,#0e1d38,#185e79);color:white}.hero a{color:#c4ecff}.hero h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.1;margin:.3em 0}.eyebrow,.updated,.source{font-size:.86rem;opacity:.8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}.card{background:#fff;border:1px solid #e1e7ef;border-radius:14px;padding:22px;box-shadow:0 4px 18px #0c20300c}.card h2{margin:.3em 0}.price{font-size:1.5rem;font-weight:750;color:#087b62}.button{display:inline-block;background:#0a775d;color:#fff;padding:9px 15px;border-radius:8px;text-decoration:none}.source{overflow-wrap:anywhere}.provider-list{line-height:2.2}footer{padding:28px max(5vw,24px);background:#e9eef4;color:#45536a;font-size:.9rem}.foot-nav{margin:0 0 10px;padding-bottom:10px;border-bottom:1px solid #d6deea}.foot-nav a{margin-right:18px;color:#2362a6;text-decoration:none}@media(max-width:600px){header{align-items:flex-start;gap:12px;flex-direction:column}header a{margin:0 14px 0 0}.hero{padding:24px}}.ad{margin:32px 0;padding:18px 22px;background:#fff8e6;border:1px dashed #d9a441;border-radius:14px}.ad-label{margin:0 0 8px;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:#8a6d1f}.ad-card h2{margin:.2em 0 .4em;font-size:1.15rem}.ad-card p{margin:0 0 12px}"""

CSS += "\nimg{max-width:100%;height:auto}main,section,.card{min-width:0}main{overflow-wrap:anywhere}nav{display:flex;flex-wrap:wrap;gap:8px}nav a{display:inline-flex;align-items:center;min-height:44px}.grid{grid-template-columns:repeat(auto-fit,minmax(min(260px,100%),1fr))}form{grid-template-columns:repeat(auto-fit,minmax(min(230px,100%),1fr))}input,button{min-width:0;max-width:100%}\n"
CSS += "\n.card ul{margin:10px 0;padding-left:20px}.card ul li{margin:2px 0;overflow-wrap:anywhere}\n"

if __name__ == "__main__":
    main()
