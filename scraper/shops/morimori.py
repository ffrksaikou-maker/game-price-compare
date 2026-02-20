"""Scraper for 森森買取 (morimori-kaitori.jp).

Uses Playwright to load the search page /search?sk=ポケモンカード
which renders products via JavaScript. Scrolls/paginates to load all
results. Products in div.product-item with name in h4.product-details-name
and price in div.price-normal-number.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

BASE = "https://www.morimori-kaitori.jp"
SEARCH_KEYWORD = "ポケモンカード"
SEARCH_URL = f"{BASE}/search?sk={quote(SEARCH_KEYWORD)}"


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen_names: set[str] = set()

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=self.HEADERS["User-Agent"],
                viewport={"width": 1920, "height": 1080},
                locale="ja-JP",
            )
            page = context.new_page()

            try:
                # Load search page and wait for products to render
                page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)

                # Extract products from initial load
                self._extract_from_page(page, items, seen_names)
                logger.info(
                    "%s: initial search: %d items",
                    self.shop_name, len(items),
                )

                # Click pagination to load more pages
                for page_num in range(2, 30):
                    # Look for a "next page" or numbered page button
                    has_next = self._click_next_page(page, page_num)
                    if not has_next:
                        break

                    page.wait_for_timeout(2000)

                    count_before = len(items)
                    self._extract_from_page(page, items, seen_names)
                    new_count = len(items) - count_before

                    logger.info(
                        "%s: search page %d: %d new items (total %d)",
                        self.shop_name, page_num, new_count, len(items),
                    )
                    if new_count == 0:
                        break

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
                    const nameEl = item.querySelector('h4.product-details-name');
                    const priceEl = item.querySelector('div.price-normal-number');
                    if (nameEl && priceEl) {
                        results.push({
                            name: nameEl.textContent.trim(),
                            price: priceEl.textContent.trim()
                        });
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
