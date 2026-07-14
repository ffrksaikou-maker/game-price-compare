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
POKEMON_CATE_CODE = "IIzyMdayU5wp7T4G"
ONEPIECE_CATE_CODE = "SEbO7gSBevo6KsPE"
# ポケカ側matcherはワンピを弾き、ワンピ側matcherが拾う。cate/list列挙は要ログインだが
# 個別カテゴリのlistPageは匿名で叩ける。
CATE_CODES = [POKEMON_CATE_CODE, ONEPIECE_CATE_CODE]


class IcchomeScraper(BaseScraper):
    shop_id = "icchome"
    shop_name = "一丁目"
    use_playwright = False

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        for cate_code in CATE_CODES:
            try:
                resp = self.session.get(
                    API_URL,
                    params={
                        "page": 1,
                        "size": 100,
                        "keyword": "",
                        "isImpo": "false",
                        "isCampaign": "false",
                        "cateCode": cate_code,
                        "kbNames": "",
                        "cateName": "",
                    },
                    timeout=30,
                    headers=self.HEADERS,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("%s: API request failed (%s): %s",
                             self.shop_name, cate_code, e)
                continue

            if data.get("code") != 200:
                logger.error(
                    "%s: API error: %s", self.shop_name, data.get("msg", "unknown")
                )
                continue

            content = data.get("data", {}).get("content", [])

            for product in content:
                title = product.get("title", "").strip()
                if not title:
                    continue

                # Get the "新品" (new/sealed) buyback price from condition tiers
                kb_details = product.get("goodsKbDetails", [])
                best_price = 0
                for detail in kb_details:
                    price = detail.get("kbDetailPrice", 0) or 0
                    name = detail.get("kbDetailName", "")
                    # Prefer "新品" tier; skip シュリンクなし variants
                    if "新品" in name:
                        best_price = price
                        break
                # Fallback: use first tier if no "新品" found
                if best_price == 0 and kb_details:
                    best_price = kb_details[0].get("kbDetailPrice", 0) or 0

                if best_price > 0:
                    items.append(ScrapedItem(name=title, price=best_price))

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
