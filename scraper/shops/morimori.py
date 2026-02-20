"""Scraper for 森森買取 (morimori-kaitori.jp).

Uses the search endpoint /search?sk=ポケモンカード to find all Pokemon
card products. The search page renders products server-side in
div.product-item with name in h4.product-details-name and price in
div.price-normal-number. Pagination via ?page=N query parameter.
Falls back to AJAX /category/{id}/products if search yields nothing.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import quote

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

BASE = "https://www.morimori-kaitori.jp"
SEARCH_KEYWORD = "ポケモンカード"
SEARCH_KEYWORD_ENCODED = quote(SEARCH_KEYWORD)

# Fallback: category-based scraping
PARENT_URL = f"{BASE}/category/0112"
AJAX_URL = f"{BASE}/category/{{cat_id}}/products?page={{page}}&pickup="


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen_names: set[str] = set()

        # Try search-based scraping first
        self._scrape_search(items, seen_names)

        # If search didn't work, fall back to category-based
        if len(items) < 10:
            logger.info(
                "%s: search only found %d items, trying category fallback",
                self.shop_name, len(items),
            )
            self._scrape_category(items, seen_names)

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    def _scrape_search(
        self, items: list[ScrapedItem], seen: set[str],
    ) -> None:
        """Scrape via search endpoint with HTML pagination."""
        for page_num in range(1, 30):
            if page_num > 1:
                time.sleep(1.5)
            url = f"{BASE}/search?sk={SEARCH_KEYWORD_ENCODED}&page={page_num}"
            try:
                soup = self._get_soup(url)
            except Exception as e:
                logger.info(
                    "%s: search page %d failed: %s",
                    self.shop_name, page_num, e,
                )
                break

            count_before = len(items)
            self._extract_products(soup, items, seen)
            new_count = len(items) - count_before

            logger.info(
                "%s: search page %d: %d new items (total %d)",
                self.shop_name, page_num, new_count, len(items),
            )
            if new_count == 0:
                break

    def _scrape_category(
        self, items: list[ScrapedItem], seen: set[str],
    ) -> None:
        """Fallback: scrape via category pages + AJAX."""
        soup = self._get_soup(PARENT_URL)

        csrf_meta = soup.select_one('meta[name="csrf-token"]')
        csrf_token = csrf_meta["content"] if csrf_meta else ""

        containers = soup.select(
            "div.product-scroll-container[data-category-id]"
        )
        cat_ids = [c["data-category-id"] for c in containers]
        if not cat_ids:
            cat_ids = ["0112001"]

        for cat_id in cat_ids:
            # Load subcategory page
            cat_url = f"{BASE}/category/{cat_id}"
            try:
                time.sleep(1)
                cat_soup = self._get_soup(cat_url)
                self._extract_products(cat_soup, items, seen)
                cat_csrf = cat_soup.select_one('meta[name="csrf-token"]')
                token = cat_csrf["content"] if cat_csrf else csrf_token
            except Exception:
                continue

            # AJAX pagination
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
                            "X-CSRF-Token": token,
                            "Referer": cat_url,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception:
                    break

                html = data.get("html", "")
                if not html:
                    break

                from bs4 import BeautifulSoup
                page_soup = BeautifulSoup(html, "html.parser")
                count_before = len(items)
                self._extract_products(page_soup, items, seen)
                if len(items) == count_before:
                    break
                if not data.get("has_more", False):
                    break

    def _extract_products(
        self, soup, items: list[ScrapedItem], seen: set[str],
    ) -> None:
        """Extract products from a soup object."""
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
