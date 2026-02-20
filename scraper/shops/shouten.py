"""Scraper for kaitorishouten (kaitorishouten-co.jp) - EC-CUBE on AWS.

Trading card category (533) via AJAX loaded into #search-content.
Prices use CSS sprite obfuscation: each digit is a <span class="encrypt-num">
with a background-position offset into a 110x16px PNG sprite (11 slots of 10px,
digits 0-9 + comma in random order).  Each AJAX page response embeds a fresh
sprite URL in an inline <style> block.

Digit decoding uses MD5 fingerprinting of each slot's binarised pixels.
The site always uses the same 11 glyph images (pixel-identical across all
sprite instances); only the slot order is shuffled per request.

Strategy:
  1. Navigate to /kaden (full page load, establishes session).
  2. Click the trading-card category link (.do-product-list[data-category="533"])
     so jQuery AJAX fires and injects the response into #search-content.
     The browser then loads the sprite image from the inline CSS.
  3. Intercept the sprite image via page.route to capture its bytes.
  4. For subsequent pages, call goto_page(N) in JS, which triggers the same
     AJAX+inject flow.
  5. Parse product names from the rendered DOM, decode prices via the sprite.
"""

from __future__ import annotations

import hashlib
import io
import logging

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kaitorishouten-co.jp"
KADEN_URL = f"{BASE_URL}/kaden"
CATEGORY_ID = "533"
MAX_PAGES = 5

# Pre-computed MD5 fingerprints (first 12 hex chars) of each glyph's
# binarised pixel data (10px wide x 16px tall, threshold < 128).
# These are pixel-identical across every sprite the site generates.
_GLYPH_FINGERPRINTS: dict[str, str] = {
    "6b8b35f0d463": "0",
    "cea828afad82": "1",
    "335d2856162a": "2",
    "26355e26c6bc": "3",
    "a57ffcae389f": "4",
    "15b99a9bd601": "5",
    "7152030a2a46": "6",
    "f696ce04bf84": "7",
    "8db2d4fac1be": "8",
    "f095d991b39c": "9",
    "b9a513d7d1d9": ",",
}


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
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            page = context.new_page()

            # Intercept sprite images -- capture the latest one
            sprite_holder: dict[str, bytes | None] = {"latest": None}

            def handle_route(route):
                resp = route.fetch()
                body = resp.body()
                sprite_holder["latest"] = body
                route.fulfill(response=resp, body=body)

            page.route("**/encrypt_price/**", handle_route)

            try:
                # Load main page (establishes session + initial sprite)
                page.goto(KADEN_URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(2000)

                # Click the trading-card parent category
                self._click_category(page, CATEGORY_ID)
                page.wait_for_timeout(3000)

                # Scrape page 1 (already loaded by the click)
                page_items = self._scrape_current_page(
                    page, sprite_holder, page_num=1,
                )
                items.extend(page_items)

                # Scrape subsequent pages
                for page_num in range(2, MAX_PAGES + 1):
                    sprite_holder["latest"] = None
                    has_next = self._goto_page(page, page_num)
                    if not has_next:
                        break
                    page.wait_for_timeout(3000)
                    page_items = self._scrape_current_page(
                        page, sprite_holder, page_num=page_num,
                    )
                    if not page_items:
                        break
                    items.extend(page_items)

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items total", self.shop_name, len(items))
        return items

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _click_category(page, category_id: str) -> None:
        """Click a .do-product-list sidebar link by data-category."""
        page.evaluate(
            """(catId) => {
                const links = document.querySelectorAll('.do-product-list');
                for (const link of links) {
                    if (link.dataset.category === catId) {
                        link.click();
                        return;
                    }
                }
            }""",
            category_id,
        )

    @staticmethod
    def _goto_page(page, page_num: int) -> bool:
        """Invoke the site's goto_page(N) for pagination.

        Returns False when there is no next page.
        """
        return bool(
            page.evaluate(
                """(pageNum) => {
                    if (typeof goto_page !== 'function') return false;
                    const links = document.querySelectorAll(
                        '.ec-pager__item a'
                    );
                    let found = false;
                    for (const a of links) {
                        const href = a.getAttribute('href') || '';
                        if (href.includes("goto_page('" + pageNum + "')") ||
                            href.includes('goto_page("' + pageNum + '")')) {
                            found = true;
                            break;
                        }
                    }
                    if (!found) return false;
                    goto_page(String(pageNum));
                    return true;
                }""",
                page_num,
            )
        )

    # ------------------------------------------------------------------
    # Page scraping
    # ------------------------------------------------------------------

    def _scrape_current_page(
        self,
        page,
        sprite_holder: dict[str, bytes | None],
        page_num: int,
    ) -> list[ScrapedItem]:
        """Extract items from the currently rendered #search-content."""
        items: list[ScrapedItem] = []

        # Prefer route-intercepted sprite; fall back to direct download
        sprite_bytes = sprite_holder.get("latest")
        if not sprite_bytes:
            sprite_bytes = self._download_sprite_from_dom(page)
        if not sprite_bytes:
            logger.warning(
                "%s: no sprite captured for page %d",
                self.shop_name, page_num,
            )
            return items

        # Build position -> character map from the sprite
        digit_map = _decode_sprite(sprite_bytes)
        if not digit_map:
            logger.warning(
                "%s: sprite decode failed for page %d",
                self.shop_name, page_num,
            )
            return items

        # Extract product data from the live DOM
        products = page.evaluate(
            r"""() => {
                const results = [];
                const rows = document.querySelectorAll(
                    '#search-content tr.price_list_item'
                );
                for (const row of rows) {
                    const tds = row.querySelectorAll('td.align-middle');
                    let name = '';
                    if (tds.length >= 2) {
                        for (const node of tds[1].childNodes) {
                            if (node.nodeType === 3) {
                                const t = node.textContent.trim();
                                if (t.length > 3) { name = t; break; }
                            }
                        }
                        if (!name) {
                            name = tds[1].firstChild
                                ? tds[1].firstChild.textContent.trim()
                                : '';
                        }
                    }
                    if (!name) continue;

                    const priceDiv = row.querySelector(
                        'div.item-price.encrypt-price'
                    );
                    if (!priceDiv) continue;
                    const spans = priceDiv.querySelectorAll(
                        'span.encrypt-num'
                    );
                    const positions = [];
                    for (const span of spans) {
                        const style = span.getAttribute('style') || '';
                        const m = style.match(
                            /background-position:\s*-?(\d+)px/
                        );
                        if (m) positions.push(parseInt(m[1], 10));
                    }
                    results.push({ name, positions });
                }
                return results;
            }"""
        )

        for prod in products:
            name = prod["name"]
            positions = prod["positions"]
            if not positions:
                continue
            price = _positions_to_price(positions, digit_map)
            if price > 0:
                items.append(ScrapedItem(name=name, price=price))

        logger.info(
            "%s: page %d found %d items",
            self.shop_name, page_num, len(items),
        )
        return items

    # ------------------------------------------------------------------
    # Sprite download fallback
    # ------------------------------------------------------------------

    def _download_sprite_from_dom(self, page) -> bytes | None:
        """Extract the sprite URL from computed style and download it."""
        sprite_url = page.evaluate(
            r"""() => {
                const el = document.querySelector(
                    '#search-content .encrypt-num'
                );
                if (!el) return null;
                const bg = window.getComputedStyle(el).backgroundImage;
                const m = bg.match(/url\("?([^"]+)"?\)/);
                return m ? m[1] : null;
            }"""
        )
        if not sprite_url:
            return None
        if sprite_url.startswith("/"):
            sprite_url = f"{BASE_URL}{sprite_url}"
        try:
            resp = page.context.request.get(sprite_url)
            if resp.ok:
                return resp.body()
        except Exception as e:
            logger.debug("%s: sprite download failed: %s", self.shop_name, e)
        return None


# ======================================================================
# Sprite decoding via fingerprint matching
# ======================================================================

def _slot_fingerprint(img, x0: int, slot_width: int = 10) -> str:
    """Compute an MD5 fingerprint of a single sprite slot's binarised pixels."""
    bits = []
    for y in range(img.size[1]):
        for x in range(x0, x0 + slot_width):
            bits.append(1 if img.getpixel((x, y)) < 128 else 0)
    return hashlib.md5(bytes(bits)).hexdigest()[:12]


def _decode_sprite(sprite_data: bytes) -> dict[int, str] | None:
    """Decode a sprite image to a {position_px: character} mapping.

    Each of the 11 ten-pixel-wide slots is fingerprinted and looked up
    in the pre-computed reference table.  Returns None on failure.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed -- cannot decode sprite")
        return None

    img = Image.open(io.BytesIO(sprite_data)).convert("L")
    w, h = img.size
    if w < 110 or h < 10:
        return None

    digit_map: dict[int, str] = {}
    for slot_idx in range(11):
        x0 = slot_idx * 10
        fp = _slot_fingerprint(img, x0)
        char = _GLYPH_FINGERPRINTS.get(fp)
        if char is None:
            logger.warning(
                "Unknown sprite glyph fingerprint %s at slot %d",
                fp, slot_idx,
            )
            return None
        digit_map[x0] = char

    return digit_map


def _positions_to_price(
    positions: list[int], digit_map: dict[int, str],
) -> int:
    """Convert background-position offsets to an integer price."""
    chars = []
    for pos in positions:
        ch = digit_map.get(pos)
        if ch is None:
            return 0
        chars.append(ch)
    price_str = "".join(chars).replace(",", "")
    try:
        return int(price_str)
    except ValueError:
        return 0
