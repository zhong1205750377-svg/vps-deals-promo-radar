# vps-deals

An English-language VPS price directory that reads provider sources from `.ilang/site.ilang`, fetches public official pages, and builds a static site with Python's standard library.

**Live site:** https://vps-deals-promo-radar-2r6.pages.dev

## Data and updates

The seed list contains the official VPS pages for Hostinger, InterServer, and Contabo. The scraper records public price observations with the source URL and fetch timestamp. These are not necessarily coupon offers, discounts, or affiliate offers. The initial configuration has no affiliate links. No validity dates are inferred. If a source page cannot be fetched or parsed, the site must not invent replacement data.

Run locally with Python 3.10 or newer:

```sh
python scraper.py
python build.py
```

The generated static site is in `site/`. To change the providers, edit `.ilang/site.ilang`; both programs read that file. The GitHub Actions workflow runs every six hours and commits data/build output when files change.

## Publish with GitHub Pages + Cloudflare Pages

1. Create a public GitHub repository named `vps-deals-promo-radar`, add these files, and push the default branch.
2. In Cloudflare Pages, create a project connected to that repository. Set the production branch to `main`, build command to `python build.py`, and output directory to `site`.
3. The canonical links and sitemap are generated from `base_url` in `.ilang/site.ilang`.
4. Review the live pages before applying to affiliate programs. Add an affiliate URL only to the provider row in `.ilang/site.ilang` after approval and after checking that program's current rules.

GitHub Actions needs the repository setting **Actions → General → Workflow permissions → Read and write permissions** so the scheduled job can commit its generated files. Cron scheduling can be delayed by GitHub during busy periods; six hours is the requested cadence, not a guaranteed publication SLA.

## Scope

No server, third-party Python packages, runtime inference, secrets, analytics, or fabricated figures. The scraper only requests configured public pages, sends a descriptive user agent, and checks robots.txt when available. Provider websites can change markup; review workflow logs and source links when a parser stops finding data.

Site rules are described in I-Lang in `.ilang/site.ilang`; protocol information: ilang.ai.
