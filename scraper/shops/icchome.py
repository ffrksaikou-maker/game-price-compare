"""Scraper for 買取一丁目 (1-chome.com) - Full SPA, requires Playwright.

The site is a JavaScript SPA that renders all content client-side.
We need to navigate and interact with it via Playwright.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

URL = "https://www.1-chome.com/"


class IcchomeScraper(BaseScraper):
    shop_id = "icchome"
    shop_name = "一丁目"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

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
                page.goto(URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(5000)  # Wait for SPA to hydrate

                # Try to navigate to electronics/hobby section
                # URL pattern: /elec/cate/{id}/{name} or /hobby
                for nav_url in [
                    "https://www.1-chome.com/hobby",
                    "https://www.1-chome.com/electricAppliance",
                ]:
                    try:
                        page.goto(nav_url, wait_until="networkidle", timeout=30000)
                        page.wait_for_timeout(3000)
                    except Exception:
                        continue

                # Try searching for Pokemon cards
                search_input = page.query_selector(
                    "input[type='search'], input[type='text'], "
                    "input[placeholder*='検索'], input[placeholder*='商品名'], "
                    ".search-input, #search"
                )
                if search_input:
                    search_input.fill("ポケモンカード BOX")
                    page.keyboard.press("Enter")
                    page.wait_for_load_state("networkidle", timeout=30000)
                    page.wait_for_timeout(5000)
                else:
                    # Try the search page directly
                    page.goto(
                        "https://www.1-chome.com/elec/search",
                        wait_until="networkidle",
                        timeout=30000,
                    )
                    page.wait_for_timeout(3000)
                    search_input = page.query_selector(
                        "input[type='search'], input[type='text'], input"
                    )
                    if search_input:
                        search_input.fill("ポケモンカード BOX")
                        page.keyboard.press("Enter")
                        page.wait_for_load_state("networkidle", timeout=30000)
                        page.wait_for_timeout(5000)

                # Scrape whatever product listings we find
                # Try multiple selector patterns since we can't inspect the SPA directly
                selectors = [
                    ".product-item", ".item-card", ".product",
                    "[class*='product']", "[class*='item']",
                    "table tbody tr", ".card",
                ]

                for selector in selectors:
                    rows = page.query_selector_all(selector)
                    if len(rows) >= 3:  # reasonable amount of results
                        for row in rows:
                            name = self._extract_text(row, [
                                ".product-name", ".item-name", ".name",
                                "h2", "h3", "h4", "a", ".title",
                                "[class*='name']", "[class*='title']",
                            ])
                            price = self._extract_price(row, [
                                ".product-price", ".price",
                                "[class*='price']", "[class*='amount']",
                            ])
                            if name and price > 0:
                                items.append(ScrapedItem(name=name, price=price))
                        break  # found working selectors

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    @staticmethod
    def _extract_text(element, selectors: list[str]) -> str:
        """Try multiple selectors to extract text from an element."""
        for sel in selectors:
            try:
                el = element.query_selector(sel)
                if el:
                    text = el.inner_text().strip()
                    if text and len(text) > 2:
                        return text
            except Exception:
                continue
        return ""

    def _extract_price(self, element, selectors: list[str]) -> int:
        """Try multiple selectors to extract a price from an element."""
        for sel in selectors:
            try:
                el = element.query_selector(sel)
                if el:
                    price = self.parse_price(el.inner_text().strip())
                    if price > 0:
                        return price
            except Exception:
                continue
        return 0
