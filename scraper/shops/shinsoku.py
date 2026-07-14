"""Scraper for 買取シンソク (shinsoku-tcg.com).

ポケカBOXは /yuso-kaitori ページにあり、JSで動的ロード+lazy scroll。
1. BOXフィルタを選択
2. 最下部まで繰り返しスクロール
3. .product-card のうち .badge-box を持つものから商品名+価格を抽出
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

URL = "https://shinsoku-tcg.com/yuso-kaitori"
# ワンピBOXは既定のBOXフィルタ一覧に含まれないため、title検索で別取得する。
# ポケカ側matcherはワンピを弾き、ワンピ側matcherが拾う。
ONEPIECE_URL = "https://shinsoku-tcg.com/yuso-kaitori?title=%E3%83%AF%E3%83%B3%E3%83%94%E3%83%BC%E3%82%B9"


class ShinsokuScraper(BaseScraper):
    shop_id = "shinsoku"
    shop_name = "買取シンソク"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        from playwright.sync_api import sync_playwright

        items: list[ScrapedItem] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=self.HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 1800},
                locale="ja-JP",
            )
            page = ctx.new_page()
            try:
                # --- ポケカ等: 既定一覧をBOXフィルタで取得 ---
                page.goto(URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                try:
                    page.select_option("select", label="BOX")
                    page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning("Shinsoku: BOX filter select failed: %s", e)
                self._scroll_and_extract(page, items, "BOX filter")

                # --- ワンピ: title検索でワンピBOXを取得 ---
                try:
                    page.goto(ONEPIECE_URL, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)
                    self._scroll_and_extract(page, items, "ONE PIECE title")
                except Exception as e:
                    logger.warning("Shinsoku: ONE PIECE pass failed: %s", e)
            finally:
                browser.close()

        return items

    def _scroll_and_extract(self, page, items: list[ScrapedItem], label: str) -> None:
        """最下部までスクロールして .badge-box 付き商品を抽出し items に追加。"""
        last_h = 0
        for i in range(80):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(700)
            h = page.evaluate("() => document.body.scrollHeight")
            if h == last_h:
                break
            last_h = h

        raw = page.evaluate(
            """() => {
                const cards = Array.from(document.querySelectorAll('.product-card'));
                const boxes = cards.filter(c => c.querySelector('.badge-box'));
                return boxes.map(c => {
                    const h3 = c.querySelector('h3');
                    const m = c.innerText.match(/¥[\\d,]+/);
                    return {
                        name: h3 ? h3.innerText.trim() : '',
                        price: m ? m[0] : '',
                    };
                });
            }"""
        )
        before = len(items)
        for r in raw:
            name = r.get("name", "").strip()
            price = self.parse_price(r.get("price", ""))
            if name and price > 0:
                items.append(ScrapedItem(name=name, price=price))
        logger.info("Shinsoku[%s]: %d BOX cards -> %d items",
                    label, len(raw), len(items) - before)
