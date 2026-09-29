# ::ILANG [TYPE:module][PROJECT:vps-deals][LANG:zh]
# ::STATE{@FILE, role: fetch configured official public provider pages and extract verifiable prices}
# ::BOUNDARY{never: invent prices, coupons, commissions, or validity dates|scope:permanent}
# ::RULE{config: read provider sources from .ilang/site.ilang; honor robots.txt}
"""Fetch verifiable VPS pricing signals from configured official pages."""
from __future__ import annotations

import json
import re
import urllib.error
import time
import urllib.error
import urllib.robotparser
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent
CONFIG = ROOT / ".ilang" / "site.ilang"
OUT = ROOT / "data" / "offers.json"
UA = "VPSDealsBot/1.0 (+static directory; contact via repository issues)"


def read_config() -> dict[str, Any]:
    providers = []
    settings = {}
    in_providers = False
    for raw in CONFIG.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("::MODULE{PROVIDERS"):
            in_providers = True
            continue
        if line.startswith("::MODULE{") and not line.startswith("::MODULE{PROVIDERS"):
            in_providers = False
        if in_providers and "|" in line:
            name, home, source, affiliate = [part.strip() for part in line.split("|", 3)]
            if name and home and source:
                providers.append({"name": name, "home": home, "source": source, "affiliate": affiliate})
        if line.startswith(("locale:", "base_url:", "update_frequency:")):
            k, v = line.split(":", 1)
            settings[k.strip()] = v.strip()
    return {"providers": providers, "settings": settings}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._anchor = ""
        self._href = ""
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        if tag == "a":
            self._anchor, self._href = "", attrs_d.get("href") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1
        if tag == "a" and self._href:
            self.links.append((" ".join(self._anchor.split()), self._href))
            self._anchor, self._href = "", ""

    def handle_data(self, data: str) -> None:
        if not self._skip:
            s = " ".join(data.split())
            if s:
                self.parts.append(s)
                if self._href:
                    self._anchor += " " + s


def fetch(url: str, delay: float = 0.0) -> tuple[str, str]:
    from urllib.parse import urlparse
    u = urlparse(url)
    robots_url = f"{u.scheme}://{u.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser(robots_url)
    try:
        req = urllib.request.Request(robots_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as response:
            rp.parse(response.read(256_000).decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise RuntimeError(f"robots.txt request failed: HTTP {exc.code}") from exc
        rp.parse([])
    except Exception as exc:
        raise RuntimeError("robots.txt could not be checked; refusing to fetch") from exc
    if not rp.can_fetch(UA, url):
        raise RuntimeError("robots.txt disallows this page")
    if delay:
        time.sleep(delay)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req, timeout=25) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(2_000_000).decode(charset, "replace"), response.geturl()


PRICE = re.compile(r"(?<![\w])([$€£])\s?([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:/\s*(?:mo|month|monthly))?", re.I)


def parse_page(provider: dict[str, str], html: str, final_url: str, fetched_at: str) -> list[dict[str, Any]]:
    parser = TextExtractor()
    parser.feed(html)
    text = " ".join(parser.parts)
    # Associate currency prices with nearby plan names; keep the source page as the canonical evidence.
    matches = list(PRICE.finditer(text))
    offers = []
    for i, match in enumerate(matches):
        amount = match.group(2).replace(",", ".")
        before = text[max(0, match.start() - 180):match.start()]
        after = text[match.end():match.end() + 120]
        plan = re.findall(r"\b(?:KVM\s*\d+|Cloud VPS\s*\w*\d*|Linux VPS|Windows VPS|VPS)\b", before, re.I)
        title = (plan[-1] if plan else f"VPS pricing from {provider['name']}").strip()
        symbol = match.group(1)
        currency = {"$": "USD", "€": "EUR", "£": "GBP"}[symbol]
        snippet = (before[-100:] + " " + match.group(0) + " " + after[:70]).strip()
        # Exclude renewal prices when a nearby explicit introductory price is present only by retaining source text.
        offers.append({
            "id": f"{re.sub('[^a-z0-9]+','-',provider['name'].lower()).strip('-')}-{i+1}",
            "provider": provider["name"], "title": title,
            "price": amount, "currency": currency, "billing_period": "month",
            "offer_url": final_url, "source_url": provider["source"],
            "fetched_at": fetched_at, "valid_until": None,
            "kind": "public-price", "evidence": snippet,
            "affiliate_url": provider.get("affiliate", "") or ""
        })
    return offers


def main() -> None:
    config = read_config()
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    all_offers = []
    errors = []
    for provider in config["providers"]:
        try:
            html, final_url = fetch(provider["source"], delay=2)
            all_offers.extend(parse_page(provider, html, final_url, stamp))
        except Exception as exc:
            errors.append({"provider": provider["name"], "source_url": provider["source"], "error": str(exc)[:240], "fetched_at": stamp})
    payload = {"fetched_at": stamp, "providers": config["providers"], "offers": all_offers, "errors": errors}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(all_offers)} observed price signals; {len(errors)} provider fetch errors.")


if __name__ == "__main__":
    main()
