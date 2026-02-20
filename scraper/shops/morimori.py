"""Scraper for 森森買取 (morimori-kaitori.jp).

Pokemon card subcategory at /category/0112001 with standard HTML pagination
(?page=N). Products in div.product-item with name in h4.product-details-name
and price in div.price-normal-number.
"""

from __future__ import annotations

import logging
import re

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# Pokemon card subcategory (standard HTML pagination)
POKEMON_URL = "https://www.morimori-kaitori.jp/category/0112001"


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        for page_num in range(1, 10):  # up to 9 pages safety limit
            url = (
                f"{POKEMON_URL}?page={page_num}"
                if page_num > 1
                else POKEMON_URL
            )
            try:
                soup = self._get_soup(url)
            except Exception as e:
                logger.warning(
                    "%s: page %d failed: %s", self.shop_name, page_num, e,
                )
                break

            products = soup.select("div.product-item")
            if not products:
                break

            for product in products:
                name_el = product.select_one("h4.product-details-name")
                price_el = product.select_one("div.price-normal-number")

                if not name_el or not price_el:
                    continue

                # Name may contain brand prefix + product name with whitespace
                raw_name = name_el.get_text(" ", strip=True)
                name = re.sub(r"\s+", " ", raw_name).strip()
                price = self.parse_price(price_el.get_text(strip=True))

                if name and price > 0:
                    items.append(ScrapedItem(name=name, price=price))

            # Check if there's a next page link
            next_link = soup.select_one("a.page-link[rel='next']")
            if not next_link:
                # Also check for numbered page links
                pager = soup.select("ul.pagination a.page-link")
                has_next = any(
                    str(page_num + 1) == a.get_text(strip=True)
                    for a in pager
                )
                if not has_next:
                    break

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
