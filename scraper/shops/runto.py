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

from ..matcher import BOX_INDICATORS, NON_BOX_INDICATORS
from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# card/: ポケカ含むトレカ全般 / onepiece/: ONE PIECE専用 / dg/: ドラゴンボール専用。
# ポケカ側matcherはワンピ・DBを弾き、それぞれのmatcherが拾う。
BASE_URLS = [
    "https://runto666.com/product-category/card/",
    "https://runto666.com/product-category/onepiece/",
    "https://runto666.com/product-category/dg/",
]
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

        # Priority: シュリンク有 (ari) > variant labelled as BOX > other BOX-range prices
        for v in variations:
            if not v.get("is_in_stock", True):
                continue
            attrs = v.get("attributes", {})
            shrink = attrs.get("attribute_pa_shrink", "")
            if shrink == "ari":
                return int(v.get("display_price", 0))

        option_labels: dict[str, dict[str, str]] = {}
        for select in form.select("select[name]"):
            option_labels[select["name"]] = {
                opt.get("value", ""): opt.get_text(strip=True)
                for opt in select.select("option")
                if opt.get("value")
            }

        box_prices = []
        candidates = []
        for v in variations:
            if not v.get("is_in_stock", True):
                continue
            p = int(v.get("display_price", 0))
            if p <= 0:
                continue
            labels = [
                option_labels.get(attr, {}).get(val, val)
                for attr, val in v.get("attributes", {}).items()
            ]
            if any(ng in label for label in labels for ng in NON_BOX_INDICATORS):
                continue
            if any(ind in label for label in labels for ind in BOX_INDICATORS):
                box_prices.append(p)
            elif 3000 <= p <= MAX_BOX_PRICE:
                candidates.append(p)

        if box_prices:
            return max(box_prices)
        return max(candidates) if candidates else 0

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        skipped = 0

        for base_url in BASE_URLS:
          for page in range(1, 15):  # up to 14 pages safety limit
            url = f"{base_url}page/{page}/" if page > 1 else base_url
            try:
                soup = self._get_soup(url)
            except Exception:
                break  # no more pages (404)

            # WooCommerce product cards
            products = soup.select("[data-products] .product, li.product, div.product.type-product")
            if not products:
                break

            for product in products:
                # 買取停止(売り切れ)の商品は価格が残ったまま表示されるため除外する。
                # WooCommerce が商品カードに instock / outofstock のクラスを付ける。
                if "outofstock" in product.get("class", []):
                    skipped += 1
                    continue

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

        logger.info("%s: scraped %d items (在庫切れ %d件を除外)",
                    self.shop_name, len(items), skipped)
        return items
