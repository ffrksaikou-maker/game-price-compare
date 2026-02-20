"""Scraper for 買取一丁目 (1-chome.com) - Vue.js SPA with REST API.

The site has a REST API at /api/goods/listPage that returns JSON.
Pokemon card category code: 6crqPbpiAbaKuH3x
No Playwright needed - simple HTTP GET.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

API_URL = "https://www.1-chome.com/api/goods/listPage"
POKEMON_CATE_CODE = "6crqPbpiAbaKuH3x"


class IcchomeScraper(BaseScraper):
    shop_id = "icchome"
    shop_name = "一丁目"
    use_playwright = False

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        try:
            resp = self.session.get(
                API_URL,
                params={
                    "page": 1,
                    "size": 100,
                    "keyword": "",
                    "isImpo": "false",
                    "isCampaign": "false",
                    "cateCode": POKEMON_CATE_CODE,
                    "kbNames": "",
                    "cateName": "",
                },
                timeout=30,
                headers=self.HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("%s: API request failed: %s", self.shop_name, e)
            return items

        if data.get("code") != 200:
            logger.error(
                "%s: API error: %s", self.shop_name, data.get("msg", "unknown")
            )
            return items

        content = data.get("data", {}).get("content", [])

        for product in content:
            title = product.get("title", "").strip()
            if not title:
                continue

            # Get the highest buyback price from condition tiers
            # goodsKbDetails contains price tiers (新品未使用, 開封済, etc.)
            kb_details = product.get("goodsKbDetails", [])
            best_price = 0
            for detail in kb_details:
                price = detail.get("kbDetailPrice", 0) or 0
                if price > best_price:
                    best_price = price

            if best_price > 0:
                items.append(ScrapedItem(name=title, price=best_price))

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
