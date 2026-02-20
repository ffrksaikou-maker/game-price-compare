"""Scraper for 買取ルデヤ (kaitori-rudeya.com).

Uses CSS-table layout with div.tbody > div.tr.
Name in .ttl a h2, price in .td2wrap.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# Pokemon card category
URL = "https://kaitori-rudeya.com/category/detail/114"


class RudeyaScraper(BaseScraper):
    shop_id = "rudeya"
    shop_name = "ルデヤ"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        soup = self._get_soup(URL)

        # Products in CSS-table: div.tbody > div.tr
        rows = soup.select("div.tbody > div.tr")

        for row in rows:
            # Product name
            name_el = row.select_one(".ttl a h2")
            if not name_el:
                name_el = row.select_one(".ttl h2")
            if not name_el:
                continue

            # Price in div.td2wrap
            price_el = row.select_one("div.td2wrap")
            if not price_el:
                continue

            name = name_el.get_text(strip=True)
            price = self.parse_price(price_el.get_text(strip=True))

            if name and price > 0:
                items.append(ScrapedItem(name=name, price=price))

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
