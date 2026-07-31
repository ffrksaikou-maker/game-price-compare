"""Scraper for 買取ソムリエ (somurie-kaitori.com) - Next.js React SPA.

Products at /products with Ant Design pagination (multiple pages).
Ant Design cards: .ant-card with name in p.text-dark-gray, price in p.text-price-red.

?category=2 はトレーディングカード(サブカテゴリのポケカ/ワンピを含む)。
全商品一覧は iPhone・カメラ・フィギュア等が大半を占め、トレカが後ろのページに
押し出されると取りこぼすため、カテゴリで絞って取得する。
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

URL = "https://somurie-kaitori.com/products?category=2"


class SommelierScraper(BaseScraper):
    shop_id = "sommelier"
    shop_name = "ソムリエ"
    use_playwright = True

    def _scrape_current_page(self, page) -> list[ScrapedItem]:
        """Scrape all product cards on the current page."""
        items: list[ScrapedItem] = []
        cards = page.query_selector_all(".ant-card")

        for card in cards:
            # Product name
            name_el = card.query_selector("p.text-dark-gray")
            if not name_el:
                name_el = card.query_selector(
                    "p.font-bold.text-lg, p.font-bold"
                )
            if not name_el:
                continue

            name = name_el.inner_text().strip()

            # Price (first p.text-price-red is the number)
            price_el = card.query_selector("p.text-price-red")
            if not price_el:
                continue

            price_text = price_el.inner_text().strip()
            price = self.parse_price(price_text)

            if name and price > 0:
                items.append(ScrapedItem(name=name, price=price))

        return items

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({
                "User-Agent": self.HEADERS["User-Agent"],
            })

            try:
                page.goto(URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(5000)  # Wait for React hydration

                # Scroll to load all lazy content
                for _ in range(3):
                    page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    page.wait_for_timeout(1500)

                # Scrape page 1
                items.extend(self._scrape_current_page(page))
                logger.info("%s: page 1 scraped %d items", self.shop_name, len(items))

                # Click through remaining pages
                while True:
                    next_btn = page.query_selector(
                        ".ant-pagination-next:not(.ant-pagination-disabled)"
                    )
                    if not next_btn:
                        break

                    next_btn.click()
                    page.wait_for_timeout(3000)

                    # Scroll to load lazy content on new page
                    for _ in range(3):
                        page.evaluate(
                            "window.scrollTo(0, document.body.scrollHeight)"
                        )
                        page.wait_for_timeout(1000)

                    page_items = self._scrape_current_page(page)
                    items.extend(page_items)
                    logger.info(
                        "%s: next page scraped %d items (total %d)",
                        self.shop_name, len(page_items), len(items),
                    )

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items total", self.shop_name, len(items))
        return items
