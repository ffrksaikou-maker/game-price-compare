"""Main entry point: scrape all shops, match products, generate HTML."""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.shops import ALL_SCRAPERS
from scraper.matcher import MASTER_PRODUCTS, match_products
from scraper.generator import generate_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "cache.json"
HISTORY_DIR = Path(__file__).resolve().parent.parent / "data" / "history"
JST = timezone(timedelta(hours=9))
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# キャッシュ連続使用の閾値（この回数連続でキャッシュ使用したら通知）
CACHE_CONSECUTIVE_THRESHOLD = 2
CACHE_COUNT_FILE = Path(__file__).resolve().parent.parent / "data" / "cache_fallback_counts.json"


def load_cache() -> dict:
    """Load cached scrape results from previous successful runs."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(cache: dict) -> None:
    """Save scrape results to cache file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def save_history(products: list) -> None:
    """Save daily price snapshot for future graph/analysis."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(JST).strftime("%Y-%m-%d")
    filepath = HISTORY_DIR / f"{today}.json"

    snapshot = []
    for p in products:
        if not p.prices:
            continue
        max_price = max(p.prices.values()) if p.prices else 0
        snapshot.append({
            "name": p.name,
            "category": p.category,
            "retail_price": p.retail_price,
            "max_price": max_price,
            "prices": dict(p.prices),
        })

    filepath.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Price history saved: %s (%d products)", filepath, len(snapshot))


def send_discord_alert(message: str) -> None:
    """Discord webhookで警告を送信する。"""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set, skipping alert")
        return
    try:
        payload = json.dumps({"content": message}).encode("utf-8")
        req = Request(
            DISCORD_WEBHOOK_URL,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "PriceChecker/1.0"},
        )
        urlopen(req, timeout=10)
        logger.info("Discord alert sent")
    except Exception as e:
        logger.error("Failed to send Discord alert: %s", e)


def load_cache_counts() -> dict[str, int]:
    """各ショップのキャッシュ連続使用回数を読み込む。"""
    if CACHE_COUNT_FILE.exists():
        try:
            return json.loads(CACHE_COUNT_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache_counts(counts: dict[str, int]) -> None:
    """各ショップのキャッシュ連続使用回数を保存する。"""
    CACHE_COUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_COUNT_FILE.write_text(
        json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    logger.info("Starting price scraper for %d shops", len(ALL_SCRAPERS))

    # Reset all prices before scraping
    for product in MASTER_PRODUCTS:
        product.prices.clear()

    cache = load_cache()
    cache_counts = load_cache_counts()

    # Scrape each shop
    success_count = 0
    failed_shops: list[str] = []      # スクレイプ失敗 (例外)
    empty_shops: list[str] = []       # 0件取得
    cache_used_shops: list[str] = []  # キャッシュフォールバック

    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        shop_id = scraper.shop_id
        shop_name = scraper.shop_name

        logger.info("--- Scraping %s (%s) ---", shop_name, shop_id)
        try:
            items = scraper.scrape()
            if items:
                # Convert to (name, price) tuples for matcher
                scraped = [(item.name, item.price) for item in items]
                match_products(scraped, shop_id)
                # Update cache with successful scrape
                cache[shop_id] = scraped
                success_count += 1
                # リセット: 正常取得できたらカウント0
                cache_counts[shop_id] = 0
            else:
                logger.warning("%s: no items scraped", shop_name)
                empty_shops.append(shop_name)
                cache_counts[shop_id] = cache_counts.get(shop_id, 0) + 1
                # Fall back to cached data
                if shop_id in cache:
                    logger.info("%s: using cached data (%d items)", shop_name, len(cache[shop_id]))
                    match_products(cache[shop_id], shop_id)
                    cache_used_shops.append(shop_name)
                    success_count += 1
        except Exception:
            logger.error(
                "%s: scraping failed:\n%s", shop_name, traceback.format_exc()
            )
            failed_shops.append(shop_name)
            cache_counts[shop_id] = cache_counts.get(shop_id, 0) + 1
            # Fall back to cached data
            if shop_id in cache:
                logger.info("%s: using cached data (%d items)", shop_name, len(cache[shop_id]))
                match_products(cache[shop_id], shop_id)
                cache_used_shops.append(shop_name)
                success_count += 1

    # Save cache for next run
    save_cache(cache)
    save_cache_counts(cache_counts)
    logger.info("Cache saved to %s", CACHE_FILE)

    logger.info(
        "Scraping complete: %d/%d shops succeeded",
        success_count, len(ALL_SCRAPERS),
    )

    # Log summary of matched products
    total_with_prices = 0
    for product in MASTER_PRODUCTS:
        if product.prices:
            total_with_prices += 1
            price_summary = ", ".join(
                f"{k}={v}" for k, v in sorted(product.prices.items())
            )
            logger.info("  %s: %s", product.name, price_summary)

    logger.info(
        "Products with prices: %d/%d",
        total_with_prices, len(MASTER_PRODUCTS),
    )

    # Save daily price history
    save_history(MASTER_PRODUCTS)

    # Generate HTML
    generate_html(MASTER_PRODUCTS)
    logger.info("Done! index.html has been generated.")

    # 異常検知 → Discord通知
    alerts: list[str] = []

    # キャッシュ連続使用が閾値超えのショップ
    for scraper_cls in ALL_SCRAPERS:
        sid = scraper_cls.shop_id
        sname = scraper_cls.shop_name
        count = cache_counts.get(sid, 0)
        if count >= CACHE_CONSECUTIVE_THRESHOLD:
            alerts.append(f"  {sname}: {count}回連続キャッシュ使用中（スクレイプ異常の可能性）")

    if alerts:
        now = datetime.now(JST).strftime("%Y/%m/%d %H:%M")
        msg = f"**⚠ ポケカ買取チェッカー スクレイプ異常検知** ({now})\n"
        msg += "\n".join(alerts)
        msg += "\n\nサイト構造変更・API変更の可能性があります。確認してください。"
        send_discord_alert(msg)


if __name__ == "__main__":
    main()
