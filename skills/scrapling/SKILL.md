---
name: scrapling
description: Adaptive web scraping with the Python Scrapling library. Use when extracting structured data or readable content from websites, crawling multiple related pages, handling JavaScript-heavy pages, or trying stealthier fetch modes than plain HTTP. Good for research, docs extraction, blogs/news/article scraping, and site-specific data collection. Avoid for login-protected, paywalled, or terms-restricted targets unless the user explicitly authorizes and it is appropriate.
---

# Scrapling

Use this skill when normal page fetches are not enough and the task needs site scraping, DOM extraction, multi-page crawling, or fallback fetch strategies.

## Quick workflow

1. Decide the lightest approach that can work:
   - Static page or simple HTML: use `Fetcher`
   - Anti-bot / inconsistent markup: try `StealthyFetcher`
   - JavaScript-rendered page: try `DynamicFetcher`
   - Many related pages: write a small `Spider`
2. Start with a narrow extraction target.
3. Save raw HTML when debugging selectors.
4. Prefer one good script over repeated ad-hoc shell snippets.
5. Respect site limits, robots rules, and the user's intent.

## Minimal patterns

### Static fetch

```python
from scrapling.fetchers import Fetcher

page = Fetcher.get('https://example.com')
title = page.css('h1::text').get()
items = page.css('.item').getall()
```

### Stealthier fetch

```python
from scrapling.fetchers import StealthyFetcher

StealthyFetcher.adaptive = True
page = StealthyFetcher.fetch('https://example.com', headless=True, solve_cloudflare=True)
```

### Dynamic/browser fetch

```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch('https://example.com', headless=True, network_idle=True)
```

## Practical rules

- Prefer CSS selectors first; use XPath only when it is clearly better.
- Extract only the fields needed for the task.
- For brittle sites, keep selector logic in a script file under `scripts/`.
- If selectors fail, inspect saved HTML before escalating fetch complexity.
- If the task becomes recurring for one site, create a site-specific script instead of improvising each time.

## Local environment

This workspace expects Scrapling to be installed in a dedicated virtualenv at:

- `/root/.openclaw/workspace/.venvs/scrapling`

Run scripts with that interpreter when available.

## Bundled resources

- `references/setup.md` — local install and troubleshooting notes
- `scripts/scrape_url.py` — small helper for one-off fetch + selector extraction
