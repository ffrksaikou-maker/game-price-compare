"""Scraper for ラントゥ買取 (runto666.com) - WooCommerce site.

Products in [data-products] .product cards.
Name in h2.woocommerce-loop-product__title.
Price in span.woocommerce-Price-amount bdi.
Pagination at /page/{N}/, 12 items per page, ~10 pages.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

BASE_URL = "https://runto666.com/product-category/card/"


class RuntoScraper(BaseScraper):
    shop_id = "runto"
    shop_name = "ラントゥ"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        for page in range(1, 15):  # up to 14 pages safety limit
            url = f"{BASE_URL}page/{page}/" if page > 1 else BASE_URL
            try:
                soup = self._get_soup(url)
            except Exception:
                break  # no more pages (404)

            # WooCommerce product cards
            products = soup.select("[data-products] .product, li.product, div.product.type-product")
            if not products:
                break

            for product in products:
                # Product title
                name_el = product.select_one("h2.woocommerce-loop-product__title")
                if not name_el:
                    name_el = product.select_one("h2")
                if not name_el:
                    continue

                # Price - for WooCommerce products
                price_elements = product.select(
                    "span.woocommerce-Price-amount.amount bdi"
                )
                if not price_elements:
                    price_elements = product.select("span.price")
                if not price_elements:
                    continue

                name = name_el.get_text(strip=True)

                # For range prices (¥100 – ¥8,500), skip - these are
                # variable products with single card prices, not BOX prices.
                # BOX buyback prices should be a single fixed price.
                prices = [self.parse_price(el.get_text(strip=True)) for el in price_elements]
                prices = [p for p in prices if p > 0]
                if len(prices) > 1:
                    # Price range = variable product, skip
                    continue
                price = prices[0] if prices else 0

                if name and price > 0:
                    items.append(ScrapedItem(name=name, price=price))

            # Check for next page
            next_link = soup.select_one("a.next.page-numbers")
            if not next_link:
                break

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
