"""Scraper for 森森買取 (morimori-kaitori.jp).

Parent category at /category/0112 links to subcategories.
Each subcategory page at /category/{id} shows initial products.
AJAX pagination at /category/{id}/products?page=N&pickup= loads more.
Products in div.product-item with name in h4.product-details-name
and price in div.price-normal-number.
"""

from __future__ import annotations

import logging
import re
import time

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# Pokemon card parent category page
PARENT_URL = "https://www.morimori-kaitori.jp/category/0112"
# Known subcategories (fallback if parent page detection fails)
KNOWN_CAT_IDS = ["0112001", "0112003", "0112004"]
AJAX_URL = "https://www.morimori-kaitori.jp/category/{cat_id}/products?page={page}&pickup="


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen_names: set[str] = set()

        # Load the parent category page to discover subcategories
        soup = self._get_soup(PARENT_URL)

        csrf_meta = soup.select_one('meta[name="csrf-token"]')
        csrf_token = csrf_meta["content"] if csrf_meta else ""
        logger.info(
            "%s: CSRF token %s",
            self.shop_name, "found" if csrf_token else "NOT FOUND",
        )

        # Find all subcategory IDs
        containers = soup.select(
            "div.product-scroll-container[data-category-id]"
        )
        cat_ids = [c["data-category-id"] for c in containers]
        if not cat_ids:
            cat_ids = list(KNOWN_CAT_IDS)
        logger.info("%s: subcategories: %s", self.shop_name, cat_ids)

        # For each subcategory, load its own page + AJAX pagination
        for cat_id in cat_ids:
            cat_url = f"https://www.morimori-kaitori.jp/category/{cat_id}"
            try:
                time.sleep(1)
                cat_soup = self._get_soup(cat_url)
                self._extract_products(cat_soup, items, seen_names)
                logger.info(
                    "%s: subcategory %s initial: %d total items",
                    self.shop_name, cat_id, len(items),
                )

                # Get CSRF from subcategory page (may differ)
                cat_csrf = cat_soup.select_one('meta[name="csrf-token"]')
                cat_token = cat_csrf["content"] if cat_csrf else csrf_token
            except Exception as e:
                logger.info(
                    "%s: subcategory %s page failed: %s",
                    self.shop_name, cat_id, e,
                )
                continue

            # AJAX pagination for this subcategory
            for page_num in range(2, 20):
                time.sleep(1.5)
                url = AJAX_URL.format(cat_id=cat_id, page=page_num)
                try:
                    resp = self.session.get(
                        url,
                        timeout=30,
                        headers={
                            **self.HEADERS,
                            "X-Requested-With": "XMLHttpRequest",
                            "X-CSRF-Token": cat_token,
                            "Referer": cat_url,
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
