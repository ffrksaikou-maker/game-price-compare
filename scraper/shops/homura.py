"""Scraper for 買取ホムラ (kaitori-homura.com)."""

from __future__ import annotations

import logging
import re

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

CATEGORY_URLS = [
    "https://kaitori-homura.com/products?q[product_sub_category_id_eq]=128&q[product_sub_category_product_category_id_eq]=14",
    "https://kaitori-homura.com/products?q[product_sub_category_id_eq]=130&q[product_sub_category_product_category_id_eq]=14",
    # ワンピース未開封BOX (sub=132)。ポケカ側matcherは exclude_indicators で弾き、
    # ワンピ側matcherが拾う。
    "https://kaitori-homura.com/products?q[product_sub_category_id_eq]=132&q[product_sub_category_product_category_id_eq]=14",
]

_PID_RE = re.compile(r"/products/(\d+)")


class HomuraScraper(BaseScraper):
    shop_id = "homura"
    shop_name = "ホムラ"

    def _extract(self, soup) -> list[tuple[str | None, str, int]]:
        rows: list[tuple[str | None, str, int]] = []
        for span in soup.select("span"):
            text = span.get_text(strip=True)
            if "\xa5" not in text or not any(ch.isdigit() for ch in text):
                continue

            card = None
            name_el = None
            node = span
            for _ in range(8):
                node = node.parent
                if node is None:
                    break
                found = node.find("h5")
                if found is not None:
                    card = node
                    name_el = found
                    break

            if card is None or name_el is None:
                continue

            name = name_el.get_text(strip=True)
            price = self.parse_price(text)
            if not name or price <= 0:
                continue

            pid = None
            link = card.select_one('a[href*="/products/"]')
            if link is not None:
                m = _PID_RE.search(link.get("href", ""))
                if m:
                    pid = m.group(1)

            rows.append((pid, name, price))
        return rows

    def _scrape_category(self, category_url: str, seen: set) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        page = 1
        prev_sig = None

        while True:
            url = f"{category_url}&page={page}" if page > 1 else category_url
            try:
                soup = self._get_soup(url)
            except Exception:
                break

            rows = self._extract(soup)
            sig = tuple(sorted({pid for pid, _, _ in rows if pid}))
            if not rows or sig == prev_sig:
                break
            prev_sig = sig

            for pid, name, price in rows:
                key = pid if pid else (name, price)
                if key in seen:
                    continue
                seen.add(key)
                items.append(ScrapedItem(name=name, price=price))

            if not soup.select_one('a[rel="next"]'):
                break

            page += 1
            if page > 30:
                break

        return items

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen: set = set()
        for cat_url in CATEGORY_URLS:
            items.extend(self._scrape_category(cat_url, seen))
        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items
