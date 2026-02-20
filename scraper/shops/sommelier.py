"""Scraper for 買取ソムリエ (somurie-kaitori.com) - Next.js React SPA.

All products at /products (single page, ~38 items).
Ant Design cards: .ant-card with name in p.text-dark-gray, price in p.text-price-red.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

URL = "https://somurie-kaitori.com/products"


class SommelierScraper(BaseScraper):
    shop_id = "sommelier"
    shop_name = "ソムリエ"
    use_playwright = True

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

                # Ant Design product cards
                cards = page.query_selector_all(".ant-card")

                for card in cards:
                    # Product name
                    name_el = card.query_selector("p.text-dark-gray")
                    if not name_el:
                        # Fallback selectors
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

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
