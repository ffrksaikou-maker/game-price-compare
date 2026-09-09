"""Scraper for 買取シンソク (shinsoku-tcg.com).

/yuso-kaitori はNext.jsで、価格は公開APIから読んでいる。
サイト掲載価格は postal_purchase_price_s。
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

API_ITEMS = "https://shinsoku-tcg.com/api/items"
BRANDS = ("ポケモン", "ワンピース", "DB")
PAGE_LIMIT = 100
MAX_PAGES = 60


class ShinsokuScraper(BaseScraper):
    shop_id = "shinsoku"
    shop_name = "買取シンソク"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        for brand in BRANDS:
            try:
                got = self._fetch_brand(brand)
            except Exception as e:
                logger.warning("Shinsoku: %s の取得に失敗: %s", brand, e)
                continue
            logger.info("Shinsoku: %s から %d件", brand, len(got))
            items.extend(got)
        logger.info("Shinsoku: 合計 %d件", len(items))
        return items

    def _fetch_brand(self, brand: str) -> list[ScrapedItem]:
        out: list[ScrapedItem] = []
        for page in range(MAX_PAGES):
            resp = self.session.get(
                API_ITEMS,
                params={"type": "BOX", "brand": brand,
                        "page": page, "limit": PAGE_LIMIT},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json().get("data") or {}
            for it in data.get("items", []):
                name = (it.get("name_processed") or it.get("name") or "").strip()
                price = it.get("postal_purchase_price_s")
                if name and isinstance(price, int) and price > 0:
                    out.append(ScrapedItem(name=name, price=price))
            if not data.get("has_more"):
                break
        return out
