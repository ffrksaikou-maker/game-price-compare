"""Scraper for ラントゥ買取 (runto666.com) - WooCommerce site.

Products in [data-products] .product cards.
Name in h2.woocommerce-loop-product__title.
Price in span.woocommerce-Price-amount bdi.
Pagination at /page/{N}/, 12 items per page, ~10 pages.

Variable products (BOX/carton/pack variants) have range prices on listing.
For those, we fetch the product detail page and read data-product_variations
JSON to get the "シュリンク有" (shrink-wrapped BOX) price.
"""

from __future__ import annotations

import json
import logging
import re
import time

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

BASE_URL = "https://runto666.com/product-category/card/"
MAX_BOX_PRICE = 60000


class RuntoScraper(BaseScraper):
    shop_id = "runto"
    shop_name = "ラントゥ"

    def _get_box_price_from_detail(self, product_url: str) -> int:
        """Fetch product detail page and extract シュリンク有 variant price."""
        try:
            soup = self._get_soup(product_url)
        except Exception:
            return 0

        form = soup.select_one("form.variations_form")
        if not form:
            return 0

        raw = form.get("data-product_variations", "")
        if not raw:
            return 0

        try:
            variations = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return 0

        # Priority: シュリンク有 (ari) > other BOX-range prices
        for v in variations:
            attrs = v.get("attributes", {})
            shrink = attrs.get("attribute_pa_shrink", "")
            if shrink == "ari":
                return int(v.get("display_price", 0))

        # Fallback: pick highest price within BOX range
        candidates = []
        for v in variations:
            p = int(v.get("display_price", 0))
            if 3000 <= p <= MAX_BOX_PRICE:
                candidates.append(p)
        return max(candidates) if candidates else 0

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

                prices = [self.parse_price(el.get_text(strip=True)) for el in price_elements]
                prices = [p for p in prices if p > 0]
                price = max(prices) if prices else 0

                # If max price exceeds BOX range, it's likely a carton price.
                # Fetch the product detail page to get the correct BOX variant price.
                if price > MAX_BOX_PRICE and len(prices) > 1:
                    link_el = product.select_one("a[href]")
                    if link_el:
                        product_url = link_el.get("href", "")
                        if product_url:
                            logger.info(
                                "%s: range price %d for '%s', fetching detail page",
                                self.shop_name, price, name,
                            )
                            box_price = self._get_box_price_from_detail(product_url)
                            if box_price > 0:
                                price = box_price
                            else:
                                price = 0  # can't determine BOX price
                            time.sleep(1)  # polite delay

                if name and price > 0:
                    items.append(ScrapedItem(name=name, price=price))

            # Check for next page
            next_link = soup.select_one("a.next.page-numbers")
            if not next_link:
                break

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
