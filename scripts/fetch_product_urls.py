"""Fetch individual product page URLs from each shop.

Runs separately from the main scraper. Saves URL mapping to data/product_urls.json.
Does NOT modify any scraper code or price data.

Usage: python scripts/fetch_product_urls.py
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_PATH = PROJECT_ROOT / "data" / "product_urls.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.9",
}


def _get_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


# ===== Homura =====
def fetch_homura_urls() -> dict[str, str]:
    """Fetch product URLs from kaitori-homura.com."""
    logger.info("Fetching Homura URLs...")
    urls: dict[str, str] = {}
    category_urls = [
        "https://kaitori-homura.com/products?q[product_sub_category_id_eq]=128&q[product_sub_category_product_category_id_eq]=14",
        "https://kaitori-homura.com/products?q[product_sub_category_id_eq]=130&q[product_sub_category_product_category_id_eq]=14",
    ]

    for cat_url in category_urls:
        page = 1
        while True:
            url = f"{cat_url}&page={page}" if page > 1 else cat_url
            try:
                soup = _get_soup(url)
            except Exception:
                break

            dialogs = soup.select('div[data-controller="dialog"]')
            if not dialogs:
                break

            for dialog in dialogs:
                link = dialog.select_one('a[href^="/products/"]')
                name_el = dialog.select_one('a[href^="/products/"] h5')
                if not name_el:
                    name_el = dialog.select_one("h5")
                if link and name_el:
                    name = name_el.get_text(strip=True)
                    href = "https://kaitori-homura.com" + link["href"]
                    urls[name] = href

            page += 1
            if page > 10:
                break
            time.sleep(1)

    logger.info("  Homura: %d URLs", len(urls))
    return urls


# ===== Rudeya =====
def fetch_rudeya_urls() -> dict[str, str]:
    """Fetch product URLs from kaitori-rudeya.com."""
    logger.info("Fetching Rudeya URLs...")
    urls: dict[str, str] = {}

    soup = _get_soup("https://kaitori-rudeya.com/category/detail/114")
    rows = soup.select("div.tbody > div.tr")

    for row in rows:
        link_el = row.select_one(".ttl a")
        if link_el and link_el.get("href"):
            name_el = link_el.select_one("h2")
            if name_el:
                name = name_el.get_text(strip=True)
                href = link_el["href"]
                if not href.startswith("http"):
                    href = "https://kaitori-rudeya.com" + href
                urls[name] = href

    logger.info("  Rudeya: %d URLs", len(urls))
    return urls


# ===== Runto =====
def fetch_runto_urls() -> dict[str, str]:
    """Fetch product URLs from runto666.com (WooCommerce)."""
    logger.info("Fetching Runto URLs...")
    urls: dict[str, str] = {}
    base = "https://runto666.com/product-category/card/"

    page_num = 1
    while True:
        url = base if page_num == 1 else f"{base}page/{page_num}/"
        try:
            soup = _get_soup(url)
        except Exception:
            break

        products = soup.select("li.product")
        if not products:
            break

        for product in products:
            link = product.select_one("a[href]")
            name_el = product.select_one("h2.woocommerce-loop-product__title")
            if link and name_el:
                name = name_el.get_text(strip=True)
                href = link["href"]
                urls[name] = href

        page_num += 1
        if page_num > 15:
            break
        time.sleep(1)

    logger.info("  Runto: %d URLs", len(urls))
    return urls


# ===== Morimori =====
def fetch_morimori_urls() -> dict[str, str]:
    """Fetch product URLs from morimori-kaitori.jp (requires Playwright)."""
    logger.info("Fetching Morimori URLs...")
    urls: dict[str, str] = {}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("  Playwright not available, skipping Morimori")
        return urls

    search_url = f"https://www.morimori-kaitori.jp/search?sk={quote('ポケモンカード')}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1920, "height": 1080},
            locale="ja-JP",
        )
        page = context.new_page()

        try:
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)

            # Extract product links across pages
            for page_num in range(1, 10):
                products = page.evaluate(r"""() => {
                    const results = [];
                    const items = document.querySelectorAll('div.product-item');
                    for (const item of items) {
                        const nameEl = item.querySelector('h4[class*="product-details-name"]');
                        const linkEl = item.querySelector('a[href*="/product/"]');
                        if (nameEl && linkEl) {
                            results.push({
                                name: nameEl.textContent.trim(),
                                url: linkEl.href
                            });
                        }
                    }
                    return results;
                }""")

                for prod in products:
                    name = re.sub(r"\s+", " ", prod["name"]).strip()
                    if name and prod["url"]:
                        urls[name] = prod["url"]

                # Try next page
                has_next = page.evaluate("""(pageNum) => {
                    const links = document.querySelectorAll('.pagination a, .page-link, a[href*="page="]');
                    for (const link of links) {
                        if (link.textContent.trim() === String(pageNum)) {
                            link.click();
                            return true;
                        }
                    }
                    const nextBtns = document.querySelectorAll('a.next, a[rel="next"], .pagination .next a');
                    for (const btn of nextBtns) { btn.click(); return true; }
                    return false;
                }""", page_num + 1)

                if not has_next:
                    break
                page.wait_for_timeout(3000)

        except Exception as e:
            logger.error("  Morimori error: %s", e)
        finally:
            browser.close()

    logger.info("  Morimori: %d URLs", len(urls))
    return urls


# ===== Icchome =====
def fetch_icchome_urls() -> dict[str, str]:
    """Fetch product URLs from 1-chome.com via API."""
    logger.info("Fetching Icchome URLs...")
    urls: dict[str, str] = {}

    try:
        resp = requests.get(
            "https://www.1-chome.com/api/goods/listPage",
            params={
                "page": 1,
                "size": 200,
                "keyword": "",
                "isImpo": "false",
                "isCampaign": "false",
                "cateCode": "IIzyMdayU5wp7T4G",
                "kbNames": "",
                "cateName": "",
            },
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("  Icchome API error: %s", e)
        return urls

    if data.get("code") != 200:
        return urls

    for product in data.get("data", {}).get("content", []):
        title = product.get("title", "").strip()
        goods_id = product.get("goodsId")
        kb_id = product.get("allGoodsKbId")
        if title and goods_id and kb_id:
            url = f"https://www.1-chome.com/wineDetail/{goods_id}/{kb_id}"
            urls[title] = url

    logger.info("  Icchome: %d URLs", len(urls))
    return urls


def main():
    # Load existing URLs (to preserve manually added ones)
    existing: dict[str, dict[str, str]] = {}
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Fetch URLs from each shop
    shop_urls = {
        "homura": fetch_homura_urls(),
        "rudeya": fetch_rudeya_urls(),
        "runto": fetch_runto_urls(),
        "morimori": fetch_morimori_urls(),
        "icchome": fetch_icchome_urls(),
    }

    # Merge with existing (new data overwrites)
    for shop_id, urls in shop_urls.items():
        if shop_id not in existing:
            existing[shop_id] = {}
        existing[shop_id].update(urls)

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved %s", OUTPUT_PATH)

    # Summary
    total = sum(len(v) for v in existing.values())
    logger.info("Total URLs: %d (%s)", total, ", ".join(f"{k}={len(v)}" for k, v in existing.items()))


if __name__ == "__main__":
    main()
