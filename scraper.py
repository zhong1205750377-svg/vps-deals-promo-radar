# ::ILANG [TYPE:module][PROJECT:vps-deals][LANG:zh]
# ::STATE{@FILE, role: fetch configured official pages and retain only identifiable plan prices}
# ::BOUNDARY{never: invent prices, coupons, commissions, validity dates, or treat renewal/list prices as current|scope:permanent}
# ::RULE{config: read provider sources from .ilang/site.ilang; honor robots.txt}
"""Fetch clean monthly VPS plan prices from configured official pages."""
from __future__ import annotations

import json
import re
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
    """Produce readable page text while omitting executable and hidden-content tags."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "template"} and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)


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


# Require a monthly unit. Plain crossed-out prices and unqualified numbers never pass.
PRICE = re.compile(r"(?<![\w])([$€£])\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:/\s*(?:mo|month|monthly)\b|per\s+month\b)", re.I)
PLAN = re.compile(r"\b(KVM\s*\d+|Cloud\s+VPS\s*\d+|Linux\s+VPS|Windows\s+VPS)\b", re.I)
RENEWAL = re.compile(r"renew(?:s|al|ing)?\s+(?:at|for|to)?\s*$", re.I)


def _clean_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return " ".join(parser.parts)


def _monthly_price(segment: str) -> tuple[str, str] | None:
    candidates = []
    for match in PRICE.finditer(segment):
        before = segment[max(0, match.start() - 36):match.start()]
        if RENEWAL.search(before):
            continue
        amount = match.group(2).replace(",", ".")
        currency = {"$": "USD", "€": "EUR", "£": "GBP"}[match.group(1)]
        candidates.append((amount, currency))
    unique = list(dict.fromkeys(candidates))
    return unique[0] if len(unique) == 1 else None


def parse_page(provider: dict[str, str], html: str, final_url: str, fetched_at: str) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    text = _clean_text(html)
    provider_name = provider["name"]
    if provider_name == "Hostinger":
        allowed = {"KVM 1", "KVM 2", "KVM 4", "KVM 8"}
    elif provider_name == "Contabo":
        allowed = {f"Cloud VPS {n}" for n in ("4", "6", "8", "10", "12", "16", "20", "30", "40", "50", "60")}
    else:
        allowed = set()

    candidates: dict[tuple[str, str], set[tuple[str, str]]] = {}
    discarded: list[dict[str, str]] = []
    matches = list(PLAN.finditer(text))
    for i, match in enumerate(matches):
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        normalized = title.upper() if title.upper().startswith("KVM") else title.title()
        if normalized not in allowed:
            if provider_name == "InterServer" and normalized in {"Linux Vps", "Windows Vps"}:
                discarded.append({"provider": provider_name, "plan": normalized, "reason": "product category/starting slice has no exact named plan model; excluded"})
            continue
        # Use a short plan-local window; never associate later plans' or page-wide prices.
        end = min(len(text), match.end() + (190 if provider_name == "Hostinger" else 85))
        next_plan = next((m.start() for m in matches[i + 1:] if m.start() > match.end()), end)
        end = min(end, next_plan)
        segment = text[match.start():end]
        price = _monthly_price(segment)
        key = (normalized, "")
        if not price:
            discarded.append({"provider": provider_name, "plan": normalized, "reason": "no unique non-renewal monthly price in the plan block"})
            continue
        candidates.setdefault(key, set()).add(price)

    offers: list[dict[str, Any]] = []
    slug = re.sub(r"[^a-z0-9]+", "-", provider_name.lower()).strip("-")
    for (title, _), prices in candidates.items():
        if len(prices) != 1:
            discarded.append({"provider": provider_name, "plan": title, "reason": "duplicate plan blocks contain conflicting current prices"})
            continue
        amount, currency = next(iter(prices))
        oid = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        offers.append({
            "id": f"{slug}-{oid}", "provider": provider_name, "title": title,
            "price": amount, "currency": currency, "billing_period": "month",
            "offer_url": final_url, "source_url": provider["source"],
            "fetched_at": fetched_at, "valid_until": None,
            "kind": "public-price", "description": f"{provider_name} {title}: {currency} {amount}/month. Check current terms on the official source.",
            "affiliate_url": provider.get("affiliate", "") or ""
        })
    return offers, discarded


def deduplicate(offers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    discarded = []
    for offer in offers:
        key = (offer["provider"].strip().casefold(), offer["title"].strip().casefold(), offer["currency"].strip().upper())
        old = seen.get(key)
        if old is None:
            seen[key] = offer
        elif old["price"] == offer["price"]:
            discarded.append({"provider": offer["provider"], "plan": offer["title"], "reason": "duplicate official plan block; kept one listing"})
        else:
            del seen[key]
            discarded.append({"provider": offer["provider"], "plan": offer["title"], "reason": "duplicate key has conflicting current prices; dropped the plan"})
    return list(seen.values()), discarded


def main() -> None:
    config = read_config()
    try:
        previous = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    all_offers = []
    errors = []
    discarded = []
    for provider in config["providers"]:
        try:
            html, final_url = fetch(provider["source"], delay=2)
            offers, rejected = parse_page(provider, html, final_url, stamp)
            all_offers.extend(offers)
            discarded.extend(rejected)
        except Exception as exc:
            errors.append({"provider": provider["name"], "source_url": provider["source"], "error": str(exc)[:240], "fetched_at": stamp})
            # Keep only records written by this clean schema; never revive legacy raw evidence.
            for old in previous.get("offers", []):
                if old.get("provider") != provider["name"] or not old.get("description"):
                    continue
                if (old.get("billing_period") == "month" and old.get("currency") in {"USD", "EUR", "GBP"}
                        and re.fullmatch(r"\d+(?:\.\d{1,2})?", str(old.get("price", "")))
                        and re.fullmatch(r"(?:KVM\s+\d+|Cloud VPS \d+)", str(old.get("title", "")), re.I)):
                    all_offers.append(old)
                    discarded.append({"provider": provider["name"], "plan": old["title"], "reason": "source temporarily unavailable; retained last clean verified price"})
    all_offers, duplicates = deduplicate(all_offers)
    discarded.extend(duplicates)
    payload = {"fetched_at": stamp, "providers": config["providers"], "offers": all_offers, "discarded": discarded, "errors": errors}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(all_offers)} unique plan prices; discarded {len(discarded)} candidates; {len(errors)} provider fetch errors.")


if __name__ == "__main__":
    main()
