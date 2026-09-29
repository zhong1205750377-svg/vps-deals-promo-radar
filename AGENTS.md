::ILANG
[TYPE:project-guidance][PROJECT:vps-deals][LANG:zh]

::STATE{@PROJECT, purpose: A static English-language VPS offers directory built from official public provider pages.}
::BOUNDARY{never: fabricate discounts, coupon codes, prices, expiry dates, traffic, or commissions|scope:permanent}
::BOUNDARY{never: bypass robots.txt, logins, rate limits, or anti-bot controls|scope:permanent}
::RULE{source: .ilang/site.ilang is the only provider/configuration source; scraper.py and build.py must read it}
::RULE{data: each published price must retain its official source_url and fetched_at timestamp}
::RULE{privacy: static site only; no tracking pixels, cookie injection, or runtime API keys}
::RULE{allowed: improve accessible templates, parser reliability, documentation, and deterministic build output}
::RULE{allowed: add a provider only by editing .ilang/site.ilang and using its official public page}
::RULE{monetization: affiliate links only after approval and only per the applicable program terms}
