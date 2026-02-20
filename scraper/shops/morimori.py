"""Scraper for 森森買取 (morimori-kaitori.jp).

Parent category at /category/0112 shows initial products.
AJAX pagination at /category/{subcategoryId}/products?page=N&pickup= for more.
Products in div.product-item with name in h4.product-details-name
and price in div.price-normal-number.
"""

from __future__ import annotations

import logging
import re

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# Pokemon card parent category page
URL = "https://www.morimori-kaitori.jp/category/0112"
# Default subcategory for AJAX pagination
DEFAULT_CAT_ID = "0112001"
AJAX_URL = "https://www.morimori-kaitori.jp/category/{cat_id}/products?page={page}&pickup="


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen_names: set[str] = set()

        # Load the parent category page for initial products + CSRF token
        soup = self._get_soup(URL)

        csrf_meta = soup.select_one('meta[name="csrf-token"]')
        csrf_token = csrf_meta["content"] if csrf_meta else ""
        logger.info(
            "%s: CSRF token %s",
            self.shop_name, "found" if csrf_token else "NOT FOUND",
        )

        # Extract initial products from page HTML
        self._extract_products(soup, items, seen_names)
        logger.info(
            "%s: initial page has %d products", self.shop_name, len(items),
        )

        # Find all subcategory IDs
        containers = soup.select(
            "div.product-scroll-container[data-category-id]"
        )
        cat_ids = [c["data-category-id"] for c in containers]
        if not cat_ids:
            cat_ids = [DEFAULT_CAT_ID]
        logger.info(
            "%s: subcategories: %s", self.shop_name, cat_ids,
        )

        # Fetch pages via AJAX for each subcategory
        for cat_id in cat_ids:
            for page_num in range(1, 15):  # up to 14 pages
                url = AJAX_URL.format(cat_id=cat_id, page=page_num)
                try:
                    resp = self.session.get(
                        url,
                        timeout=30,
                        headers={
                            **self.HEADERS,
                            "X-Requested-With": "XMLHttpRequest",
                            "X-CSRF-Token": csrf_token,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.info(
                        "%s: AJAX page %d for %s failed: %s",
                        self.shop_name, page_num, cat_id, e,
                    )
                    break

                html = data.get("html", "")
                if not html:
                    logger.info(
                        "%s: AJAX page %d for %s returned empty html",
                        self.shop_name, page_num, cat_id,
                    )
                    break

                from bs4 import BeautifulSoup
                page_soup = BeautifulSoup(html, "html.parser")
                count_before = len(items)
                self._extract_products(page_soup, items, seen_names)

                new_count = len(items) - count_before
                logger.info(
                    "%s: AJAX page %d for %s: %d new items",
                    self.shop_name, page_num, cat_id, new_count,
                )
                if new_count == 0:
                    break

                has_more = data.get("has_more", False)
                if not has_more:
                    logger.info(
                        "%s: no more pages for %s", self.shop_name, cat_id,
                    )
                    break

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    def _extract_products(
        self, soup, items: list[ScrapedItem], seen: set[str],
    ) -> None:
        """Extract products from a soup object (page or AJAX fragment)."""
        for product in soup.select("div.product-item"):
            name_el = product.select_one("h4.product-details-name")
            price_el = product.select_one("div.price-normal-number")

            if not name_el or not price_el:
                continue

            raw_name = name_el.get_text(" ", strip=True)
            name = re.sub(r"\s+", " ", raw_name).strip()
            price = self.parse_price(price_el.get_text(strip=True))

            if name and price > 0 and name not in seen:
                seen.add(name)
                items.append(ScrapedItem(name=name, price=price))
