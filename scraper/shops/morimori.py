"""Scraper for 森森買取 (morimori-kaitori.jp).

Search page at /search?sk=ポケモンカード returns Pokemon card products.
The initial page loads a shell; products are loaded via AJAX at
/search/products?page=N&sk=... starting from page 1.
Products in div.product-item with name in h4.product-details-name
and price in div.price-normal-number.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import quote

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.morimori-kaitori.jp/search"
SEARCH_KEYWORD = "ポケモンカード"
SEARCH_KEYWORD_ENCODED = quote(SEARCH_KEYWORD)
AJAX_SEARCH_URL = "https://www.morimori-kaitori.jp/search/products"


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen_names: set[str] = set()

        # Load the search page to establish session + get CSRF token
        page_url = f"{SEARCH_URL}?sk={SEARCH_KEYWORD_ENCODED}"
        soup = self._get_soup(page_url)

        csrf_meta = soup.select_one('meta[name="csrf-token"]')
        csrf_token = csrf_meta["content"] if csrf_meta else ""
        logger.info(
            "%s: CSRF token %s",
            self.shop_name, "found" if csrf_token else "NOT FOUND",
        )

        # Products are loaded via AJAX, starting from page 1
        referer = f"{SEARCH_URL}?sk={SEARCH_KEYWORD_ENCODED}"
        for page_num in range(1, 30):
            if page_num > 1:
                time.sleep(1.5)
            try:
                resp = self.session.get(
                    f"{AJAX_SEARCH_URL}?page={page_num}&sk={SEARCH_KEYWORD_ENCODED}",
                    timeout=30,
                    headers={
                        **self.HEADERS,
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRF-Token": csrf_token,
                        "Referer": referer,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.info(
                    "%s: AJAX search page %d failed: %s",
                    self.shop_name, page_num, e,
                )
                break

            html = data.get("html", "")
            if not html:
                logger.info(
                    "%s: AJAX search page %d returned empty html",
                    self.shop_name, page_num,
                )
                break

            from bs4 import BeautifulSoup
            page_soup = BeautifulSoup(html, "html.parser")
            count_before = len(items)
            self._extract_products(page_soup, items, seen_names)

            new_count = len(items) - count_before
            logger.info(
                "%s: AJAX search page %d: %d new items (total %d)",
                self.shop_name, page_num, new_count, len(items),
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
