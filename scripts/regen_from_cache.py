"""Regenerate all HTML pages from cached scrape data.

Skips the slow scraping step and re-runs matcher + generator only.
Use this after editing generator.py to apply changes locally without
waiting for the GitHub Actions cron job.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper.matcher import MASTER_PRODUCTS, match_products  # noqa: E402
from scraper.generator import generate_html  # noqa: E402


def main():
    cache_path = ROOT / "data" / "cache.json"
    if not cache_path.exists():
        print(f"ERROR: cache.json not found at {cache_path}")
        sys.exit(1)

    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    print(f"Loaded cache: {list(cache.keys())}")

    total = 0
    for shop_id, items in cache.items():
        # items = list of [name, price] pairs
        tuples = [(item[0], item[1]) for item in items if len(item) >= 2]
        match_products(tuples, shop_id)
        total += len(tuples)

    print(f"Matched {total} scraped items across {len(cache)} shops")

    generate_html(MASTER_PRODUCTS)
    print("Regeneration complete")


if __name__ == "__main__":
    main()
