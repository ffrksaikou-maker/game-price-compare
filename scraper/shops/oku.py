"""Scraper for 買取オク (kaitori-oku.jp).

Plain-text HTML listing. Products rendered as cards with `h4.tit` for name
and `.price` for price (plain yen like "¥13,300"). Items without price show
"問い合わせ" instead — those are skipped. Pagination via ?page=N.
"""

from __future__ import annotations

import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

# cat2=363: ポケカ / cat2=364: ONE PIECE。ポケカ側matcherはワンピを弾き、
# ワンピ側matcherが拾う。
CATEGORY_URLS = [
    "https://kaitori-oku.jp/category.html?cat1=340&cat2=363",
    "https://kaitori-oku.jp/category.html?cat1=340&cat2=364",
]
MAX_PAGES = 20


class OkuScraper(BaseScraper):
    shop_id = "oku"
    shop_name = "オク"

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        for base_url in CATEGORY_URLS:
            for pg in range(1, MAX_PAGES + 1):
                url = base_url if pg == 1 else f"{base_url}&page={pg}"
                try:
                    soup = self._get_soup(url)
                except Exception as e:
                    logger.warning(
                        "%s: page %d fetch failed: %s", self.shop_name, pg, e,
                    )
                    break

                tits = soup.select("h4.tit")
                page_items = 0
                for t in tits:
                    card = t.find_parent(["a", "div", "li"])
                    if not card:
                        continue
                    price_el = card.select_one(".price")
                    if not price_el:
                        continue
                    price_text = price_el.get_text(strip=True)
                    # Skip news items (no price) and 問い合わせ (inquire only)
                    if "¥" not in price_text:
                        continue
                    name = t.get_text(strip=True)
                    price = self.parse_price(price_text)
                    if name and price > 0:
                        items.append(ScrapedItem(name=name, price=price))
                        page_items += 1

                logger.info(
                    "%s: page %d -> %d items", self.shop_name, pg, page_items,
                )
                # Stop when a page returns nothing after the first few pages
                if page_items == 0 and pg >= 3:
                    break

        logger.info(
            "%s: scraped %d items total", self.shop_name, len(items),
        )
        return items
