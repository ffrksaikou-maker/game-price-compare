"""Scraper for 買取ルデヤ (kaitori-rudeya.com).

Uses card-grid layout: article.pgrid-card.
Name in h3.product-card-name, price in span.product-card-price-value.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# detail/114: ポケカ / detail/224: ONE PIECEカードゲーム / detail/240: ベイブレード
# / detail/225: ドラゴンボールカード(フュージョンワールド+スーパーダイバーズ)。
# ポケカ側matcherはワンピ・ベイ・DBを弾き、それぞれのmatcherが拾う。
URLS = [
    "https://kaitori-rudeya.com/category/detail/114",
    "https://kaitori-rudeya.com/category/detail/224",
    "https://kaitori-rudeya.com/category/detail/240",
    "https://kaitori-rudeya.com/category/detail/225",
]


class RudeyaScraper(BaseScraper):
    shop_id = "rudeya"
    shop_name = "ルデヤ"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        for url in URLS:
            try:
                soup = self._get_soup(url)
            except Exception as e:
                logger.warning("%s: fetch failed %s: %s", self.shop_name, url, e)
                continue

            # Products in card grid: article.pgrid-card
            rows = soup.select("article.pgrid-card")

            for row in rows:
                # Product name
                name_el = row.select_one("h3.product-card-name")
                if not name_el:
                    continue

                # Price in span.product-card-price-value
                price_el = row.select_one("span.product-card-price-value")
                if not price_el:
                    continue

                name = name_el.get_text(strip=True)
                price = self.parse_price(price_el.get_text(strip=True))

                if name and price > 0:
                    items.append(ScrapedItem(name=name, price=price))

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
