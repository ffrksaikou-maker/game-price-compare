"""Main entry point: scrape all shops, match products, generate HTML."""

from __future__ import annotations

import json
import logging
import sys
import traceback
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.shops import ALL_SCRAPERS
from scraper.matcher import MASTER_PRODUCTS, match_products
from scraper.generator import generate_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "cache.json"


def load_cache() -> dict:
    """Load cached scrape results from previous successful runs."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(cache: dict) -> None:
    """Save scrape results to cache file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    logger.info("Starting price scraper for %d shops", len(ALL_SCRAPERS))

    # Reset all prices before scraping
    for product in MASTER_PRODUCTS:
        product.prices.clear()

    cache = load_cache()

    # Scrape each shop
    success_count = 0
    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        shop_id = scraper.shop_id
        shop_name = scraper.shop_name

        logger.info("--- Scraping %s (%s) ---", shop_name, shop_id)
        try:
            items = scraper.scrape()
            if items:
                # Convert to (name, price) tuples for matcher
                scraped = [(item.name, item.price) for item in items]
                match_products(scraped, shop_id)
                # Update cache with successful scrape
                cache[shop_id] = scraped
                success_count += 1
            else:
                logger.warning("%s: no items scraped", shop_name)
                # Fall back to cached data
                if shop_id in cache:
                    logger.info("%s: using cached data (%d items)", shop_name, len(cache[shop_id]))
                    match_products(cache[shop_id], shop_id)
                    success_count += 1
        except Exception:
            logger.error(
                "%s: scraping failed:\n%s", shop_name, traceback.format_exc()
            )
            # Fall back to cached data
            if shop_id in cache:
                logger.info("%s: using cached data (%d items)", shop_name, len(cache[shop_id]))
                match_products(cache[shop_id], shop_id)
                success_count += 1

    # Save cache for next run
    save_cache(cache)
    logger.info("Cache saved to %s", CACHE_FILE)

    logger.info(
        "Scraping complete: %d/%d shops succeeded",
        success_count, len(ALL_SCRAPERS),
    )

    # Log summary of matched products
    total_with_prices = 0
    for product in MASTER_PRODUCTS:
        if product.prices:
            total_with_prices += 1
            price_summary = ", ".join(
                f"{k}={v}" for k, v in sorted(product.prices.items())
            )
            logger.info("  %s: %s", product.name, price_summary)

    logger.info(
        "Products with prices: %d/%d",
        total_with_prices, len(MASTER_PRODUCTS),
    )

    # Generate HTML
    generate_html(MASTER_PRODUCTS)
    logger.info("Done! index.html has been generated.")


if __name__ == "__main__":
    main()
