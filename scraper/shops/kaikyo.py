"""Scraper for 海峡通信 (mobile-ichiban.com) - ASP.NET MVC.

Products in Bootstrap cards at /Prod/3/.
Name in span.item_title, price as text matching {number}円.
Pagination via /G01_ProdutShow/Index/{page}?kid=3 (needs session cookies).
"""

from __future__ import annotations

import logging
import re

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

URL = "https://www.mobile-ichiban.com/Prod/3/"


class KaikyoScraper(BaseScraper):
    shop_id = "kaikyo"
    shop_name = "海峡"
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
                page.wait_for_timeout(3000)

                # Scrape page 1
                self._extract_from_page(page, items)

                # Find pagination links
                page_links = page.query_selector_all(
                    "ul.pagination .page-item:not(.disabled):not(.active) .page-link"
                )

                # Get unique page URLs
                visited = {URL}
                page_urls = []
                for link in page_links:
                    href = link.get_attribute("href") or ""
                    if href and "javascript" not in href and href not in visited:
                        if not href.startswith("http"):
                            href = f"https://www.mobile-ichiban.com{href}"
                        visited.add(href)
                        page_urls.append(href)

                # Navigate to remaining pages
                for page_url in page_urls:
                    try:
                        page.goto(
                            page_url,
                            wait_until="networkidle",
                            timeout=30000,
                        )
                        page.wait_for_timeout(2000)
                        self._extract_from_page(page, items)
                    except Exception as e:
                        logger.warning(
                            "%s: page navigation error: %s",
                            self.shop_name, e,
                        )

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    def _extract_from_page(self, page, items: list[ScrapedItem]) -> None:
        """Extract products from the currently displayed page."""
        # Product cards with .card-body
        cards = page.query_selector_all(".card-body, .my-card-body")

        for card in cards:
            # Product name from span.item_title
            name_el = card.query_selector("span.item_title")
            if not name_el:
                continue

            name = name_el.inner_text().strip()
            if not name:
                continue

            # Price: find text matching {number}円 pattern in card
            card_text = card.inner_text()
            price_match = re.search(r"([\d,]+)\s*円", card_text)
            if not price_match:
                continue

            price = self.parse_price(price_match.group(1))

            if name and price > 0:
                items.append(ScrapedItem(name=name, price=price))
