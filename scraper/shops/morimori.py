"""Scraper for 森森買取 (morimori-kaitori.jp).

Uses Playwright to load the search page /search?sk=ポケモンカード
which renders products via JavaScript. Scrolls/paginates to load all
results. Products in div.product-item with name in
h4.search-product-details-name and price in div[class*=price-normal-number].
"""

from __future__ import annotations

import logging
import os
import re
import time
from urllib.parse import quote

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

BASE = "https://www.morimori-kaitori.jp"
# ポケカ=キーワード検索, ワンピ=専用カテゴリ(検索は取りこぼすため category を直に見る)。
# ワンピは2カテゴリに跨る: 2403=OP-01〜15/EB/PRB-02, 0112003=OP-16以降の新弾/PRB-01。
# 検索sk=ワンピースにも category/2403 にも新弾(OP-16 決戦の刻等)は出ないため両方見る。
# ポケカ側matcherはワンピを弾き、ワンピ側が拾う。(ラベル, URL)
# ベイブレードは 1904001。/category/price-list/1904001 だと div.product-item が
# 描画されずタイムアウトするため price-list を挟まない形を使う。
TARGETS = [
    ("ポケモン", f"{BASE}/search?sk={quote('ポケモンカード')}"),
    ("ワンピ", f"{BASE}/category/2403"),
    ("ワンピ新弾", f"{BASE}/category/0112003"),
    ("ベイブレード", f"{BASE}/category/1904001"),
]
SEARCH_URL = TARGETS[0][1]  # 後方互換(_open_with_retry のデフォルト値)


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen_names: set[str] = set()

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # headless だと morimori-kaitori.jp に BOT 検出され
            # ERR_HTTP2_PROTOCOL_ERROR で全リクエストが弾かれる。
            # headful なら通るため、CI(Linux)では Xvfb 上で実行する
            # (.github/workflows/update.yml で xvfb-run でラップ済み)。
            # ローカルで窓を出したくない時は SCRAPER_HEADLESS=1 でヘッドレス化
            # (ただしBOT検出で失敗しキャッシュにフォールバックする可能性が高い)。
            headless = os.environ.get("SCRAPER_HEADLESS") == "1"
            browser = p.chromium.launch(headless=headless)
            try:
                for label, target_url in TARGETS:
                    try:
                        page = self._open_with_retry(browser, target_url)
                        page.wait_for_timeout(3000)

                        # Extract products from initial load
                        count_before = len(items)
                        self._extract_from_page(page, items, seen_names)
                        logger.info(
                            "%s: %s initial: %d new items",
                            self.shop_name, label, len(items) - count_before,
                        )

                        # Click pagination to load more pages
                        for page_num in range(2, 30):
                            has_next = self._click_next_page(page, page_num)
                            if not has_next:
                                break

                            page.wait_for_timeout(2000)

                            page_before = len(items)
                            self._extract_from_page(page, items, seen_names)
                            new_count = len(items) - page_before

                            logger.info(
                                "%s: %s page %d: %d new items (total %d)",
                                self.shop_name, label, page_num, new_count,
                                len(items),
                            )
                            if new_count == 0:
                                break
                    except Exception as e:
                        logger.error(
                            "%s: %s error: %s", self.shop_name, label, e,
                        )

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    def _extract_from_page(
        self, page, items: list[ScrapedItem], seen: set[str],
    ) -> None:
        """Extract products from the current Playwright page DOM."""
        products = page.evaluate(
            r"""() => {
                const results = [];
                const items = document.querySelectorAll('div.product-item');
                for (const item of items) {
                    // 検索ページは h4.product-details-name、カテゴリページは
                    // h5.product-details-name。タグ非依存で拾う。
                    const nameEl = item.querySelector(
                        '[class*="product-details-name"]'
                    );
                    // Price: 検索ページは price-normal-number クラス。
                    let priceEl = item.querySelector(
                        'div[class*="price-normal-number"]'
                    ) || item.querySelector(
                        'span[class*="price-normal-number"]'
                    ) || item.querySelector(
                        '[class*="price"] [class*="number"]'
                    );
                    // カテゴリページはクラス無し。「通常買取価格:」直後の数値を拾う
                    // (預かり買取価格は採用しない)。
                    if (!priceEl) {
                        const m = item.innerText.match(/通常買取価格[:：]?\s*([\d,]+)\s*円/);
                        if (nameEl && m) {
                            results.push({
                                name: nameEl.textContent.trim(),
                                price: m[1]
                            });
                            continue;
                        }
                    }
                    if (nameEl && priceEl) {
                        results.push({
                            name: nameEl.textContent.trim(),
                            price: priceEl.textContent.trim()
                        });
                    } else if (nameEl) {
                        // Fallback: try to find any price-like text
                        const priceText = item.querySelector(
                            '[class*="price"]'
                        );
                        if (priceText) {
                            results.push({
                                name: nameEl.textContent.trim(),
                                price: priceText.textContent.trim()
                            });
                        }
                    }
                }
                return results;
            }"""
        )

        for prod in products:
            raw_name = prod["name"]
            name = re.sub(r"\s+", " ", raw_name).strip()
            price = self.parse_price(prod["price"])

            if name and price > 0 and name not in seen:
                seen.add(name)
                items.append(ScrapedItem(name=name, price=price))

    def _open_with_retry(self, browser, search_url: str = SEARCH_URL,
                         max_attempts: int = 5):
        """Open the search page with retries.

        morimori-kaitori.jp resets the HTTP/2 connection
        (ERR_HTTP2_PROTOCOL_ERROR) for headless Chromium, so the browser is
        launched headful (see scrape()). headful でも稀に H2 リセットや
        ネットワーク揺らぎで失敗するため多めにリトライする。
        wait_until は domcontentloaded（networkidle は常時接続の EC で
        idle に到達せず timeout する失敗モードがあるため避ける。商品の
        描画は直後の wait_for_selector で担保する）。
        """
        last_err: Exception | None = None
        backoff = [2, 4, 8, 12, 16]
        for attempt in range(max_attempts):
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="ja-JP",
            )
            page = context.new_page()
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector("div.product-item", timeout=30000)
                return page
            except Exception as e:
                last_err = e
                logger.warning(
                    "%s: open attempt %d/%d failed: %s",
                    self.shop_name, attempt + 1, max_attempts, e,
                )
                context.close()
                if attempt < max_attempts - 1:
                    time.sleep(backoff[min(attempt, len(backoff) - 1)])
        raise last_err if last_err else RuntimeError("open failed")

    @staticmethod
    def _click_next_page(page, page_num: int) -> bool:
        """Click the next page button. Returns False if no more pages."""
        # Try clicking numbered pagination link
        result = page.evaluate(
            """(pageNum) => {
                // Look for pagination links
                const links = document.querySelectorAll(
                    '.pagination a, .page-link, a[href*="page="]'
                );
                for (const link of links) {
                    const text = link.textContent.trim();
                    if (text === String(pageNum)) {
                        link.click();
                        return true;
                    }
                }
                // Look for "next" arrow/button
                const nextBtns = document.querySelectorAll(
                    'a.next, a[rel="next"], .pagination .next a, button.next'
                );
                for (const btn of nextBtns) {
                    btn.click();
                    return true;
                }
                // Look for "load more" / "もっと見る" button
                const moreButtons = document.querySelectorAll(
                    'button, a.load-more, .show-more'
                );
                for (const btn of moreButtons) {
                    const text = btn.textContent.trim();
                    if (text.includes('もっと') || text.includes('次') ||
                        text.includes('more') || text.includes('More')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""",
            page_num,
        )
        return bool(result)
