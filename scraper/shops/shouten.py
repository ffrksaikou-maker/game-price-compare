"""Scraper for 買取商店 (kaitorishouten-co.jp) - EC-CUBE on AWS.

Pokemon cards via AJAX: /products/2/list_category/533?pageno={1-3}
Prices use CSS sprite obfuscation (encrypt-num with background-position offsets).
Uses Playwright to intercept sprite image + PIL to decode digits.
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
            # Stealth: hide webdriver
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            page = context.new_page()

            # Intercept sprite images
            sprite_data_holder = {}

            def handle_route(route):
                """Capture sprite image bytes via route interception."""
                resp = route.fetch()
                body = resp.body()
                sprite_data_holder["latest"] = body
                route.fulfill(response=resp, body=body)

            page.route("**/encrypt_price/**", handle_route)

            try:
                # Load main page to establish session
                page.goto(KADEN_URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)

                # Scrape each page of trading card category
                for page_num in range(1, 4):  # 3 pages
                    url = CATEGORY_AJAX.format(page=page_num)
                    sprite_data_holder["latest"] = None

                    # Navigate to category page via evaluate to trigger AJAX
                    html = page.evaluate("""
                        async (url) => {
                            const resp = await fetch(url, {
                                headers: {'X-Requested-With': 'XMLHttpRequest'}
                            });
                            return await resp.text();
                        }
                    """, url)

                    if not html or not html.strip():
                        break

                    # Wait for sprite to be loaded
                    page.wait_for_timeout(2000)

                    # If sprite was captured via route, use it
                    # Otherwise try to extract it from the page
                    sprite_bytes = sprite_data_holder.get("latest")

                    if not sprite_bytes:
                        # Try to download sprite directly from page context
                        sprite_match = re.search(
                            r'background-image:\s*url\("?(/products/encrypt_price/[^)"]+)',
                            html,
                        )
                        if sprite_match:
                            sprite_path = sprite_match.group(1)
                            sprite_url = f"{BASE_URL}{sprite_path}"
                            try:
                                resp = page.context.request.get(sprite_url)
                                if resp.ok:
                                    sprite_bytes = resp.body()
                            except Exception as e:
                                logger.debug(
                                    "%s: sprite download failed: %s",
                                    self.shop_name, e,
                                )

                    if not sprite_bytes:
                        logger.warning(
                            "%s: no sprite for page %d",
                            self.shop_name, page_num,
                        )
                        continue

                    # Decode sprite to get position->digit mapping
                    digit_map = self._decode_sprite_pixels(sprite_bytes)
                    if not digit_map:
                        logger.warning(
                            "%s: sprite decode failed for page %d",
                            self.shop_name, page_num,
                        )
                        continue

                    # Parse products from HTML
                    from bs4 import BeautifulSoup
                    page_soup = BeautifulSoup(html, "html.parser")

                    rows = page_soup.select(
                        "tr.price_list_item, div.item.item-thumbnail"
                    )

                    found = 0
                    for row in rows:
                        # Product name
                        name = ""
                        name_el = row.select_one("h4.item-title")
                        if name_el:
                            name = name_el.get_text(strip=True)
                        else:
                            tds = row.select("td.align-middle")
                            if len(tds) >= 2:
                                # Table: name is in 2nd td
                                td = tds[1]
                                # Get direct text (not child elements)
                                for content in td.children:
                                    if isinstance(content, str):
                                        text = content.strip()
                                        if text and len(text) > 3:
                                            name = text
                                            break
                                if not name:
                                    name = td.get_text(strip=True)

                        if not name:
                            continue

                        # Price: decode sprite positions
                        price_div = row.select_one(
                            "div.item-price.encrypt-price"
                        )
                        if not price_div:
                            continue

                        price = self._decode_price(price_div, digit_map)
                        if name and price > 0:
                            items.append(ScrapedItem(name=name, price=price))
                            found += 1

                    logger.info(
                        "%s: page %d found %d items",
                        self.shop_name, page_num, found,
                    )

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items total", self.shop_name, len(items))
        return items

    @staticmethod
    def _decode_sprite_pixels(sprite_data: bytes) -> dict[int, str] | None:
        """Decode sprite image using PIL pixel analysis.

        The sprite is 110px wide x 16px tall, with 11 slots of 10px each.
        Slots contain digits 0-9 and a comma in random order.
        Digits are dark (red/black) on white background.
        """
        try:
            from PIL import Image
        except ImportError:
            logger.warning("PIL not installed, cannot decode sprite")
            return None

        img = Image.open(io.BytesIO(sprite_data)).convert("L")  # grayscale
        width, height = img.size

        if width < 100 or height < 10:
            return None

        slot_width = 10
        num_slots = min(width // slot_width, 11)

        # For each slot, compute pixel features
        slot_features = []
        for slot_idx in range(num_slots):
            x_start = slot_idx * slot_width
            x_end = x_start + slot_width

            # Count dark pixels (< 128) in different regions
            h = height
            w = slot_width

            total_dark = 0
            top_dark = 0
            bot_dark = 0
            left_dark = 0
            right_dark = 0
            mid_h_dark = 0  # middle horizontal band
            center_col = 0  # center column

            for y in range(h):
                for x in range(x_start, min(x_end, width)):
                    px = img.getpixel((x, y))
                    if px < 128:
                        total_dark += 1
                        lx = x - x_start  # local x
                        if y < h // 3:
                            top_dark += 1
                        elif y > 2 * h // 3:
                            bot_dark += 1
                        if h // 3 <= y <= 2 * h // 3:
                            mid_h_dark += 1
                        if lx < w // 2:
                            left_dark += 1
                        else:
                            right_dark += 1
                        if lx == w // 2:
                            center_col += 1

            slot_features.append({
                "idx": slot_idx,
                "pos": x_start,
                "total": total_dark,
                "top": top_dark,
                "bot": bot_dark,
                "left": left_dark,
                "right": right_dark,
                "mid_h": mid_h_dark,
                "center": center_col,
            })

        if len(slot_features) < 11:
            return None

        # Sort by total dark pixels to find comma (fewest dark pixels)
        sorted_slots = sorted(slot_features, key=lambda x: x["total"])
        comma_slot = sorted_slots[0]

        # The remaining 10 slots contain digits 0-9
        digit_slots = sorted_slots[1:]

        # Use reference digit templates based on pixel distribution
        # This is approximate but works for the standard font used
        digit_map = {comma_slot["pos"]: ","}

        # Classify digits by their pixel features
        # Sort remaining by various features to distinguish digits
        # Use a scoring approach based on known digit characteristics
        _classify_digits(digit_slots, digit_map)

        if len(digit_map) >= 11:
            return digit_map

        return None

    @staticmethod
    def _decode_price(price_div, digit_map: dict[int, str]) -> int:
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
                return 0
            price_str += char

        price_str = price_str.replace(",", "")
        try:
            return int(price_str)
        except ValueError:
            return 0


def _classify_digits(
    digit_slots: list[dict], digit_map: dict[int, str]
) -> None:
    """Classify digit slots using pixel feature heuristics.

    Uses relative comparisons between slots to assign digits 0-9.
    This works because the font has consistent distinguishing features.
    """
    if len(digit_slots) < 10:
        return

    # Normalize features relative to each other
    max_total = max(s["total"] for s in digit_slots) or 1
    for s in digit_slots:
        s["norm_total"] = s["total"] / max_total
        s["top_ratio"] = s["top"] / max(s["total"], 1)
        s["bot_ratio"] = s["bot"] / max(s["total"], 1)
        s["left_ratio"] = s["left"] / max(s["total"], 1)
        s["right_ratio"] = s["right"] / max(s["total"], 1)
        s["mid_ratio"] = s["mid_h"] / max(s["total"], 1)
        s["center_ratio"] = s["center"] / max(s["total"], 1)

    # Digit identification by distinctive features:
    # 1: fewest total dark pixels among digits (thin vertical line)
    # 0: high center_ratio, balanced top/bot
    # 8: most total dark pixels (two loops = most ink)
    # 7: high top_ratio, low bot_ratio (top bar + diagonal)
    # 4: high mid_ratio (horizontal bar in middle), low bot_ratio
    # 2: high top_ratio + high bot_ratio (curves top and bottom)
    # 6: low top_ratio, high bot_ratio (loop at bottom)
    # 9: high top_ratio, low bot_ratio (loop at top)
    # 3: balanced, moderate right_ratio
    # 5: moderate, similar to 3

    # Sort by total pixels
    by_total = sorted(digit_slots, key=lambda s: s["total"])

    # 1 has the fewest pixels (thin line)
    digit_map[by_total[0]["pos"]] = "1"

    # 8 has the most pixels (two loops)
    digit_map[by_total[-1]["pos"]] = "8"

    # Among remaining, find 7 (highest top_ratio)
    remaining = [s for s in digit_slots
                 if s["pos"] not in digit_map]
    by_top = sorted(remaining, key=lambda s: s["top_ratio"], reverse=True)

    # 7 has highest top ratio with low bottom
    for s in by_top:
        if s["bot_ratio"] < 0.3:
            digit_map[s["pos"]] = "7"
            break

    # Find 4 (high mid_ratio, lower total)
    remaining = [s for s in digit_slots
                 if s["pos"] not in digit_map]
    by_mid = sorted(remaining, key=lambda s: s["mid_ratio"], reverse=True)
    for s in by_mid:
        if s["norm_total"] < 0.85:
            digit_map[s["pos"]] = "4"
            break

    # Find 0 (high center_ratio, balanced)
    remaining = [s for s in digit_slots
                 if s["pos"] not in digit_map]
    by_center = sorted(remaining, key=lambda s: s["center_ratio"],
                       reverse=True)
    for s in by_center:
        balance = abs(s["top_ratio"] - s["bot_ratio"])
        if balance < 0.15:
            digit_map[s["pos"]] = "0"
            break

    # Find 6 (low top, high bot)
    remaining = [s for s in digit_slots
                 if s["pos"] not in digit_map]
    for s in sorted(remaining, key=lambda s: s["bot_ratio"] - s["top_ratio"],
                    reverse=True):
        digit_map[s["pos"]] = "6"
        break

    # Find 9 (high top, low bot) - opposite of 6
    remaining = [s for s in digit_slots
                 if s["pos"] not in digit_map]
    for s in sorted(remaining, key=lambda s: s["top_ratio"] - s["bot_ratio"],
                    reverse=True):
        digit_map[s["pos"]] = "9"
        break

    # Remaining 3 slots: 2, 3, 5
    remaining = sorted(
        [s for s in digit_slots if s["pos"] not in digit_map],
        key=lambda s: s["total"],
    )

    if len(remaining) >= 3:
        # 5 typically has moderate pixels, heavier left
        # 3 is right-heavy
        # 2 has high bot pixels (bottom bar)
        by_left = sorted(remaining, key=lambda s: s["left_ratio"],
                         reverse=True)
        digit_map[by_left[0]["pos"]] = "5"

        rest = [s for s in remaining if s["pos"] != by_left[0]["pos"]]
        by_bot = sorted(rest, key=lambda s: s["bot_ratio"], reverse=True)
        digit_map[by_bot[0]["pos"]] = "2"

        final = [s for s in rest if s["pos"] != by_bot[0]["pos"]]
        if final:
            digit_map[final[0]["pos"]] = "3"
    elif len(remaining) == 2:
        digit_map[remaining[0]["pos"]] = "2"
        digit_map[remaining[1]["pos"]] = "3"
    elif len(remaining) == 1:
        digit_map[remaining[0]["pos"]] = "2"
