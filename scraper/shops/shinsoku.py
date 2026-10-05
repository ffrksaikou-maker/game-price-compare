"""Scraper for 買取シンソク (shinsoku-tcg.com).

/yuso-kaitori はNext.jsで、価格は公開APIから読んでいる。
サイト掲載価格は postal_purchase_price_s。
FUTURISTIC BOX・プレミアムデッキセット・ポケセン限定スペシャルBOXは
type=BOX ではなく UNOPENED_OTHER に分類されているため両方取る。
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

API_ITEMS = "https://shinsoku-tcg.com/api/items"
BRANDS = ("ポケモン", "ワンピース", "DB")
TYPES = ("BOX", "UNOPENED_OTHER")
PAGE_LIMIT = 100
MAX_PAGES = 60


class ShinsokuScraper(BaseScraper):
    shop_id = "shinsoku"
    shop_name = "買取シンソク"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        for brand in BRANDS:
            for item_type in TYPES:
                try:
                    got = self._fetch_brand(brand, item_type)
                except Exception as e:
                    logger.warning("Shinsoku: %s/%s の取得に失敗: %s", brand, item_type, e)
                    continue
                logger.info("Shinsoku: %s/%s から %d件", brand, item_type, len(got))
                items.extend(got)
        logger.info("Shinsoku: 合計 %d件", len(items))
        return items

    def _fetch_brand(self, brand: str, item_type: str) -> list[ScrapedItem]:
        out: list[ScrapedItem] = []
        for page in range(MAX_PAGES):
            resp = self.session.get(
                API_ITEMS,
                params={"type": item_type, "brand": brand,
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
