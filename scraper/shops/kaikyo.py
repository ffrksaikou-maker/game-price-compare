"""Scraper for 海峡通信 (mobile-ichiban.com) - ASP.NET MVC.

Products in Bootstrap cards at /Prod/3/ (category "おもちゃ買取").

The site's JavaScript (nb.js) has a catch block that redirects to the
homepage when it fails to initialise the sidebar navigation, so Playwright
must be launched with ``java_script_enabled=False`` to keep the
server-rendered product HTML intact.

Product name is in the ``title`` attribute of ``label.hideText`` (first
occurrence inside each ``div.card``).  Price is inside
``label[id^='NewPrice_']`` as text matching ``{number}円``.

Pagination uses ASP.NET MvcPager with AJAX POST to
``/G01_ProdutShow/Index/{page}?kid=3``, updating ``#dateAndPager``.
Page 1 is fetched via normal GET; pages 2+ via POST with the form data
from ``#G01_ProdutShow_searchForm``.
"""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

URL = "https://www.mobile-ichiban.com/Prod/3/"
BASE = "https://www.mobile-ichiban.com"


class KaikyoScraper(BaseScraper):
    shop_id = "kaikyo"
    shop_name = "海峡"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # JavaScript MUST be disabled.  The site's nb.js wraps its
            # initialisation in a try/catch and redirects to "/" on any
            # error, which always fires in a headless context.  With JS
            # off the server-rendered HTML (including all product cards)
            # is preserved as-is.
            ctx = browser.new_context(
                java_script_enabled=False,
                user_agent=self.HEADERS["User-Agent"],
            )
            page = ctx.new_page()

            try:
                # --- Page 1 (GET) ---
                page.goto(URL, wait_until="commit", timeout=60000)
                page.wait_for_timeout(2000)

                html = page.content()
                self._extract_from_html(html, items)

                # --- Determine total page count from MvcPager ---
                soup = BeautifulSoup(html, "html.parser")
                pager = soup.select_one("ul.pagination")
                page_count = (
                    int(pager["data-pagecount"])
                    if pager and pager.get("data-pagecount")
                    else 1
                )
                logger.debug(
                    "%s: %d pages detected", self.shop_name, page_count,
                )

                # --- Pages 2+ (AJAX POST) ---
                for pg in range(2, page_count + 1):
                    try:
                        resp = ctx.request.post(
                            f"{BASE}/G01_ProdutShow/Index/{pg}?kid=3",
                            form={
                                "g01Search": "",
                                "g01tagLevel": "",
                                "g01tagCodeLevel1": "",
                                "g01tagCodeLevel2": "",
                                "g01tagCodeLevel3": "",
                                "g01tagNameLevel1": "",
                                "g01tagNameLevel2": "",
                                "g01tagNameLevel3": "",
                                "LeftTagJson": "",
                                "TagJson": "",
                                "g01ListOrImg": "",
                                "idCustom": "",
                            },
                            headers={
                                "X-Requested-With": "XMLHttpRequest",
                            },
                        )
                        self._extract_from_html(resp.text(), items)
                    except Exception as e:
                        logger.warning(
                            "%s: page %d POST error: %s",
                            self.shop_name, pg, e,
                        )

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    # ------------------------------------------------------------------
    def _extract_from_html(self, html: str, items: list[ScrapedItem]) -> None:
        """Parse product cards from an HTML string (full page or AJAX
        fragment) and append results to *items*."""
        soup = BeautifulSoup(html, "html.parser")

        # Each product lives in a ``div.card`` that contains a product
        # image (``img.card-img-top``).  Store-info cards on the
        # homepage also use ``.card`` but never have an image, so the
        # ``:has(.card-img-top)`` filter keeps only real products.
        cards = soup.select("div.card:has(.card-img-top)")

        for card in cards:
            # Product name --------------------------------------------------
            # Stored in the ``title`` attribute of the first
            # ``label.hideText`` inside the card-body.
            name_label = card.select_one("label.hideText")
            name = (name_label.get("title") or "").strip() if name_label else ""
            if not name:
                continue

            # Price ---------------------------------------------------------
            # The "new" (新品) buy-back price sits in a <label> whose id
            # starts with ``NewPrice_`` (e.g. ``NewPrice_S011705``).
            price_label = card.select_one("label[id^='NewPrice_']")
            price_text = price_label.get_text(strip=True) if price_label else ""
            price_match = re.search(r"([\d,]+)\s*円", price_text)
            if not price_match:
                continue

            price = self.parse_price(price_match.group(1))
            if price > 0:
                items.append(ScrapedItem(name=name, price=price))
