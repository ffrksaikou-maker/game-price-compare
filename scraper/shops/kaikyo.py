"""Scraper for 海峡通信 (mobile-ichiban.com) - ASP.NET MVC with AJAX pagination.

Products in Bootstrap cards at /Prod/3/.
Name in label.hideText (title attr), price in label[id^="NewPrice_"].
Pagination via AJAX POST to /G01_ProdutShow/Index/{page}?kid=3.
"""

from __future__ import annotations

import logging

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

                # Get total page count from pagination
                pager = page.query_selector("ul.pagination.my-pagination")
                total_pages = 3  # default
                if pager:
                    count_attr = pager.get_attribute("data-pagecount")
                    if count_attr:
                        total_pages = int(count_attr)

                # Scrape page 1
                self._extract_from_page(page, items)

                # Navigate through remaining pages
                for page_num in range(2, total_pages + 1):
                    # Click next page link
                    next_link = page.query_selector(
                        f'a[data-pageindex="{page_num}"]'
                    )
                    if not next_link:
                        break

                    next_link.click()
                    # Wait for AJAX to update #dateAndPager
                    page.wait_for_timeout(3000)
                    page.wait_for_load_state("networkidle", timeout=15000)

                    self._extract_from_page(page, items)

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    def _extract_from_page(self, page, items: list[ScrapedItem]) -> None:
        """Extract products from the currently displayed page."""
        # Product cards: div.col-6 > div.card
        cards = page.query_selector_all(
            "div.col-6.col-md-4.col-lg-3, div.row.bg-white > div.col-6"
        )

        if not cards:
            # Fallback: try to find cards directly
            cards = page.query_selector_all("div.card")

        for card in cards:
            # Product name from label.hideText title attribute
            name_el = card.query_selector("label.hideText")
            if not name_el:
                continue

            # Prefer title attr (full untruncated name)
            name = name_el.get_attribute("title") or ""
            if not name:
                name = name_el.inner_text().strip()

            # Price from label[id^="NewPrice_"]
            price_el = card.query_selector('label[id^="NewPrice_"]')
            if not price_el:
                continue

            price_text = price_el.inner_text().strip()
            price = self.parse_price(price_text)

            if name and price > 0:
                items.append(ScrapedItem(name=name, price=price))
