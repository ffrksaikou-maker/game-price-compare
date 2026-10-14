"""Scraper for 買取ホムラ (kaitori-homura.com)."""

from __future__ import annotations

import logging
import time

import requests

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# 2026-10 から商品一覧ページは JS 描画になり HTML に商品が載らない。
# 画面が叩いている公開 API を直接読む(20件/ページ・meta.total_pages)。
API_PRODUCTS = "https://api.kaitori-homura.com/api/v1/products"

SUB_CATEGORY_IDS = [
    128,  # シュリンク有り
    130,
    # ワンピース未開封BOX (sub=132)。ポケカ側matcherは exclude_indicators で弾き、
    # ワンピ側matcherが拾う。
    132,
    # ベイブレード (sub=188)。
    188,
    # ドラゴンボール未開封BOX (sub=171)。ポケカ/ワンピ側matcherは弾番号で弾き、DB側が拾う。
    171,
]

MAX_PAGES = 30


class HomuraScraper(BaseScraper):
    shop_id = "homura"
    shop_name = "ホムラ"

    def _get_json(self, params: dict) -> dict:
        for attempt in range(3):
            try:
                resp = self.session.get(
                    API_PRODUCTS, params=params, timeout=30,
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as e:
                logger.warning(
                    "%s: attempt %d failed for %s: %s",
                    self.shop_name, attempt + 1, params, e,
                )
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))
                else:
                    raise

    def _scrape_sub(self, sub_id: int, seen: set) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        page = 1
        while page <= MAX_PAGES:
            try:
                d = self._get_json({"product_sub_category_id": sub_id, "page": page})
            except Exception:
                break
            for it in d.get("data") or []:
                name = (it.get("name") or "").strip()
                price = it.get("price")
                if not name or not isinstance(price, int) or price <= 0:
                    continue
                key = it.get("id") or (name, price)
                if key in seen:
                    continue
                seen.add(key)
                items.append(ScrapedItem(name=name, price=price))
            if page >= ((d.get("meta") or {}).get("total_pages") or 1):
                break
            page += 1
        return items

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen: set = set()
        for sub_id in SUB_CATEGORY_IDS:
            items.extend(self._scrape_sub(sub_id, seen))
        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
