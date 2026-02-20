"""Main entry point: scrape all shops, match products, generate HTML."""

from __future__ import annotations

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


def main() -> None:
    logger.info("Starting price scraper for %d shops", len(ALL_SCRAPERS))

    # Reset all prices before scraping
    for product in MASTER_PRODUCTS:
        product.prices.clear()

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
                success_count += 1
            else:
                logger.warning("%s: no items scraped", shop_name)
        except Exception:
            logger.error(
                "%s: scraping failed:\n%s", shop_name, traceback.format_exc()
            )

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
