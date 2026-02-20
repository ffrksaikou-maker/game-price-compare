"""Scraper for 森森買取 (morimori-kaitori.jp).

Uses AJAX pagination: /category/{categoryId}/products?page=N&pickup=
Initial page loads ~10 items, more loaded via JSON API.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# Pokemon card category page
URL = "https://www.morimori-kaitori.jp/category/0112"
# Pokemon card subcategory ID for AJAX pagination
CATEGORY_ID = "0112001"
AJAX_URL = "https://www.morimori-kaitori.jp/category/{cat_id}/products?page={page}&pickup="


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        # First, load the main page to get CSRF token and initial products
        soup = self._get_soup(URL)

        # Extract CSRF token for AJAX requests
        csrf_meta = soup.select_one('meta[name="csrf-token"]')
        csrf_token = csrf_meta["content"] if csrf_meta else ""

        # Scrape initial products from page HTML
        self._extract_products(soup, items)

        # Find all subcategory IDs from product scroll containers
        containers = soup.select("div.product-scroll-container[data-category-id]")
        cat_ids = [c["data-category-id"] for c in containers]
        if not cat_ids:
            cat_ids = [CATEGORY_ID]

        # Fetch all pages via AJAX for each subcategory
        for cat_id in cat_ids:
            page = 1
            while True:
                url = AJAX_URL.format(cat_id=cat_id, page=page)
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
                    logger.warning(
                        "%s: AJAX page %d for %s failed: %s",
                        self.shop_name, page, cat_id, e,
                    )
                    break

                html = data.get("html", "")
                if not html:
                    break

                from bs4 import BeautifulSoup
                page_soup = BeautifulSoup(html, "html.parser")
                count_before = len(items)
                self._extract_products(page_soup, items)

                if len(items) == count_before:
                    break  # no new items found

                has_more = data.get("has_more", False)
                if not has_more:
                    break

                page += 1
                if page > 30:  # safety limit
                    break

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    def _extract_products(self, soup, items: list[ScrapedItem]) -> None:
        """Extract products from a soup object (page or AJAX fragment)."""
        for product in soup.select("div.product-item"):
            name_el = product.select_one("h4.product-details-name")
            price_el = product.select_one("div.price-normal-number")

            if not name_el or not price_el:
                continue

            # Name may contain brand prefix + product name with whitespace
            raw_name = name_el.get_text(" ", strip=True)
            # Collapse whitespace and remove brand prefix
            import re as _re
            name = _re.sub(r"\s+", " ", raw_name).strip()
            price = self.parse_price(price_el.get_text(strip=True))

            if name and price > 0:
                items.append(ScrapedItem(name=name, price=price))
