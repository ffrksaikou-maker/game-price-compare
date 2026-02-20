"""Scraper for 買取ホムラ (kaitori-homura.com).

Rails app with Tailwind CSS. Products in div[data-controller="dialog"].
Pagination via ?page=N. Need to search for Pokemon cards.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# Trading card category (ID=14) includes Pokemon, One Piece, Yu-Gi-Oh etc.
CATEGORY_URL = "https://kaitori-homura.com/products?q[product_sub_category_product_category_id_eq]=14"


class HomuraScraper(BaseScraper):
    shop_id = "homura"
    shop_name = "ホムラ"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        page = 1

        while True:
            url = f"{CATEGORY_URL}&page={page}" if page > 1 else CATEGORY_URL
            try:
                soup = self._get_soup(url)
            except Exception:
                break

            # Each product is in a div[data-controller="dialog"]
            dialogs = soup.select('div[data-controller="dialog"]')
            if not dialogs:
                break

            found = 0
            for dialog in dialogs:
                # Product name in h5 inside a link
                name_el = dialog.select_one('a[href^="/products/"] h5')
                if not name_el:
                    name_el = dialog.select_one("h5")
                if not name_el:
                    continue

                # Price in span.font-semibold inside items-end container
                price_el = dialog.select_one(
                    "div.items-end span.font-semibold"
                )
                if not price_el:
                    # Fallback: any span with text matching price pattern
                    for span in dialog.select("span"):
                        text = span.get_text(strip=True)
                        if "円" in text:
                            price_el = span
                            break

                if not price_el:
                    continue

                name = name_el.get_text(strip=True)
                price = self.parse_price(price_el.get_text(strip=True))

                if name and price > 0:
                    items.append(ScrapedItem(name=name, price=price))
                    found += 1

            if found == 0:
                break

            # Check for next page
            next_link = soup.select_one('a[rel="next"]')
            if not next_link:
                break

            page += 1
            if page > 30:  # safety limit
                break

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
