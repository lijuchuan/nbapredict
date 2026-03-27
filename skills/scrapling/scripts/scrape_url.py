#!/usr/bin/env python3
import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch a URL with Scrapling and optionally extract CSS selectors")
    parser.add_argument("url")
    parser.add_argument("--mode", choices=["static", "stealthy", "dynamic"], default="static")
    parser.add_argument("--selector", action="append", default=[], help="CSS selector to extract; may be repeated")
    parser.add_argument("--text", action="store_true", help="Return text() values for selectors when possible")
    args = parser.parse_args()

    if args.mode == "static":
        from scrapling.fetchers import Fetcher

        page = Fetcher.get(args.url)
    elif args.mode == "stealthy":
        from scrapling.fetchers import StealthyFetcher

        StealthyFetcher.adaptive = True
        page = StealthyFetcher.fetch(args.url, headless=True)
    else:
        from scrapling.fetchers import DynamicFetcher

        page = DynamicFetcher.fetch(args.url, headless=True, network_idle=True)

    result = {
        "url": args.url,
        "mode": args.mode,
        "title": None,
        "selectors": {},
    }

    try:
        result["title"] = page.css("title::text").get()
    except Exception:
        pass

    for selector in args.selector:
        try:
            if args.text and not selector.endswith("::text"):
                values = page.css(f"{selector}::text").getall()
            else:
                values = page.css(selector).getall()
            result["selectors"][selector] = values
        except Exception as exc:
            result["selectors"][selector] = {"error": str(exc)}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
