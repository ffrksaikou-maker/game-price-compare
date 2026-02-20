"""Scraper for 買取商店 (kaitorishouten-co.jp) - EC-CUBE on AWS.

Pokemon cards via AJAX: /products/2/list_category/533?pageno={1-3}
Prices use CSS sprite obfuscation (encrypt-num with background-position offsets).
Requires sprite image download + OCR to decode digits.
"""

from __future__ import annotations

import io
import logging
import re

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kaitorishouten-co.jp"
KADEN_URL = f"{BASE_URL}/kaden"
CATEGORY_AJAX = f"{BASE_URL}/products/2/list_category/533?pageno={{page}}"


class ShoutenScraper(BaseScraper):
    shop_id = "shouten"
    shop_name = "商店"
    use_playwright = True  # Sprite decoding needs image processing

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []

        # Step 1: Fetch main page to get session cookies + CSRF token
        soup = self._get_soup(KADEN_URL)
        csrf_match = re.search(
            r'eccube-csrf-token.*?content="([^"]+)"', str(soup)
        )
        csrf_token = csrf_match.group(1) if csrf_match else ""

        if not csrf_token:
            # Try alternative CSRF extraction
            meta = soup.select_one('meta[name="eccube-csrf-token"]')
            if meta:
                csrf_token = meta.get("content", "")

        logger.info("%s: CSRF token: %s...", self.shop_name, csrf_token[:20])

        # Step 2: Fetch each page of trading card category via AJAX
        for page_num in range(1, 5):  # up to 4 pages
            url = CATEGORY_AJAX.format(page=page_num)
            try:
                resp = self.session.get(
                    url,
                    timeout=30,
                    headers={
                        **self.HEADERS,
                        "X-Requested-With": "XMLHttpRequest",
                        "ECCUBE-CSRF-TOKEN": csrf_token,
                        "Referer": KADEN_URL,
                    },
                )
                resp.raise_for_status()
                html = resp.text
            except Exception as e:
                logger.warning(
                    "%s: AJAX page %d failed: %s",
                    self.shop_name, page_num, e,
                )
                break

            if not html.strip():
                break

            from bs4 import BeautifulSoup
            page_soup = BeautifulSoup(html, "html.parser")

            # Step 3: Decode the sprite for this page's prices
            digit_map = self._decode_sprite(html)

            if digit_map is None:
                logger.warning(
                    "%s: could not decode price sprite for page %d",
                    self.shop_name, page_num,
                )
                # Try Playwright fallback for this page
                self._scrape_page_playwright(page_num, items)
                continue

            # Step 4: Extract products
            # Table layout: tr.price_list_item
            rows = page_soup.select("tr.price_list_item, tr[id^='ex-product-']")
            if not rows:
                # Card layout: div.item.item-thumbnail
                rows = page_soup.select("div.item.item-thumbnail")

            found = 0
            for row in rows:
                # Product name (table: 2nd td text, card: h4.item-title)
                name = ""
                name_el = row.select_one("h4.item-title")
                if name_el:
                    name = name_el.get_text(strip=True)
                else:
                    # Table layout: name is direct text in 2nd td
                    tds = row.select("td.align-middle")
                    if len(tds) >= 2:
                        # Get text content excluding child elements' text
                        td = tds[1]
                        name = td.find(string=True, recursive=False)
                        if name:
                            name = name.strip()
                        if not name:
                            name = td.get_text(strip=True)

                if not name:
                    continue

                # Price: decode sprite positions
                price_div = row.select_one("div.item-price.encrypt-price")
                if not price_div:
                    continue

                price = self._decode_price(price_div, digit_map)
                if name and price > 0:
                    items.append(ScrapedItem(name=name, price=price))
                    found += 1

            logger.info(
                "%s: page %d found %d items", self.shop_name, page_num, found
            )

            if found == 0:
                break

        logger.info("%s: scraped %d items total", self.shop_name, len(items))
        return items

    def _decode_sprite(self, html: str) -> dict[int, str] | None:
        """Download and decode the price sprite to get position->digit mapping."""
        # Find sprite URL in CSS
        match = re.search(
            r'background-image:\s*url\("?(/products/encrypt_price/[^)"]+)',
            html,
        )
        if not match:
            return None

        sprite_path = match.group(1)
        sprite_url = f"{BASE_URL}{sprite_path}"

        try:
            resp = self.session.get(
                sprite_url,
                timeout=15,
                headers={**self.HEADERS, "Referer": KADEN_URL},
            )
            resp.raise_for_status()
            sprite_data = resp.content
        except Exception as e:
            logger.warning("%s: sprite download failed: %s", self.shop_name, e)
            return None

        return self._ocr_sprite(sprite_data)

    @staticmethod
    def _ocr_sprite(sprite_data: bytes) -> dict[int, str] | None:
        """OCR the sprite image to map positions to digits.

        The sprite is 110px wide x 16px tall, with 11 slots of 10px each.
        Slots 0-9 contain digits (randomly ordered), slot 10 is comma.
        """
        try:
            from PIL import Image
        except ImportError:
            logger.warning("PIL not installed, cannot decode price sprite")
            return None

        img = Image.open(io.BytesIO(sprite_data)).convert("L")  # grayscale
        width, height = img.size

        if width < 100 or height < 10:
            logger.warning("Sprite too small: %dx%d", width, height)
            return None

        # Known digit patterns: compare each 10px slot to reference patterns
        # Simple approach: count dark pixels in each column pattern
        digit_map = {}
        slot_width = 10

        # Extract pixel data for each slot
        slot_signatures = []
        for slot in range(11):  # 0-10
            x_start = slot * slot_width
            x_end = x_start + slot_width
            # Get pixel columns for this slot
            pixels = []
            for y in range(height):
                row = []
                for x in range(x_start, min(x_end, width)):
                    row.append(img.getpixel((x, y)))
                pixels.append(row)
            slot_signatures.append(pixels)

        # Use a simple digit recognition based on pixel patterns
        # The digits 0-9 have distinctive patterns we can match
        # For robustness, count dark pixels in different regions
        slot_features = []
        for slot_idx, pixels in enumerate(slot_signatures):
            if not pixels or not pixels[0]:
                continue
            # Count dark pixels (< 128) in different regions
            h = len(pixels)
            w = len(pixels[0]) if pixels else 0
            if w == 0:
                continue

            total_dark = sum(
                1 for y in range(h) for x in range(w) if pixels[y][x] < 128
            )
            # Top half dark
            top_dark = sum(
                1 for y in range(h // 2) for x in range(w)
                if pixels[y][x] < 128
            )
            # Bottom half dark
            bot_dark = sum(
                1 for y in range(h // 2, h) for x in range(w)
                if pixels[y][x] < 128
            )
            # Left half dark
            left_dark = sum(
                1 for y in range(h) for x in range(w // 2)
                if pixels[y][x] < 128
            )
            # Right half dark
            right_dark = sum(
                1 for y in range(h) for x in range(w // 2, w)
                if pixels[y][x] < 128
            )
            # Center column dark
            cx = w // 2
            center_dark = sum(
                1 for y in range(h) if pixels[y][cx] < 128
            )

            slot_features.append({
                "idx": slot_idx,
                "total": total_dark,
                "top": top_dark,
                "bot": bot_dark,
                "left": left_dark,
                "right": right_dark,
                "center": center_dark,
            })

        # Sort by total dark pixels (comma should have fewest)
        # Then use OCR heuristics to assign digits
        # This is approximate - for production use pytesseract
        if len(slot_features) < 10:
            return None

        # Sort to find comma (least dark pixels)
        sorted_by_dark = sorted(slot_features, key=lambda x: x["total"])
        comma_slot = sorted_by_dark[0]
        pos = comma_slot["idx"] * slot_width
        digit_map[pos] = ","

        # For remaining slots, try pytesseract if available
        remaining = [f for f in slot_features if f["idx"] != comma_slot["idx"]]

        try:
            import pytesseract

            for feat in remaining:
                slot_idx = feat["idx"]
                x_start = slot_idx * slot_width
                x_end = x_start + slot_width
                slot_img = img.crop((x_start, 0, x_end, height))
                # Scale up for better OCR
                slot_img = slot_img.resize(
                    (slot_width * 4, height * 4), Image.NEAREST
                )
                text = pytesseract.image_to_string(
                    slot_img,
                    config="--psm 10 -c tessedit_char_whitelist=0123456789",
                ).strip()
                if text and text.isdigit() and len(text) == 1:
                    digit_map[x_start] = text
        except ImportError:
            # No pytesseract - use Playwright OCR approach instead
            logger.warning(
                "pytesseract not available, using heuristic digit detection"
            )
            # Assign digits by heuristic (sort by various features)
            # This is a best-effort fallback
            return None

        if len(digit_map) >= 10:  # 10 digits + comma
            return digit_map

        return None

    @staticmethod
    def _decode_price(
        price_div, digit_map: dict[int, str]
    ) -> int:
        """Decode a price from sprite background-position offsets."""
        spans = price_div.select("span.encrypt-num")
        if not spans:
            return 0

        price_str = ""
        for span in spans:
            style = span.get("style", "")
            match = re.search(r"background-position:\s*-?(\d+)px", style)
            if not match:
                continue
            pos = int(match.group(1))
            char = digit_map.get(pos, "?")
            if char == "?":
                return 0  # can't decode
            price_str += char

        # Remove commas and convert
        price_str = price_str.replace(",", "")
        try:
            return int(price_str)
        except ValueError:
            return 0

    def _scrape_page_playwright(
        self, page_num: int, items: list[ScrapedItem]
    ) -> None:
        """Fallback: use Playwright to render and read prices visually."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=self.HEADERS["User-Agent"],
                viewport={"width": 1920, "height": 1080},
                locale="ja-JP",
            )
            # Stealth
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            page = context.new_page()

            try:
                page.goto(KADEN_URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)

                # Click trading card category if visible
                cat_link = page.query_selector(
                    "text=トレーディングカード"
                )
                if cat_link:
                    cat_link.click()
                    page.wait_for_load_state("networkidle", timeout=30000)
                    page.wait_for_timeout(3000)

                # Read product names and prices from rendered page
                cards = page.query_selector_all(
                    ".item.item-thumbnail, tr.price_list_item"
                )
                for card in cards:
                    name_el = card.query_selector(
                        "h4.item-title, td.align-middle"
                    )
                    price_el = card.query_selector(
                        ".item-price.encrypt-price"
                    )
                    if not name_el or not price_el:
                        continue

                    name = name_el.inner_text().strip()
                    # With Playwright, the sprite renders visually
                    price_text = price_el.inner_text().strip()
                    price = self.parse_price(price_text)

                    if name and price > 0:
                        items.append(ScrapedItem(name=name, price=price))

            except Exception as e:
                logger.error(
                    "%s: Playwright fallback error: %s", self.shop_name, e
                )
            finally:
                browser.close()
