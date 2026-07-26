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
from scraper.products_onepiece import ONEPIECE_PRODUCTS, ONEPIECE_CONFIG
from scraper.generator_onepiece import generate_onepiece_html
from scraper.anomaly import detect_anomalies, drop_anomalies, update_state

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
HISTORY_OP_DIR = Path(__file__).resolve().parent.parent / "data" / "history_op"

# キャッシュの有効期限（これを過ぎた古い取得結果はサイトに載せない）
CACHE_MAX_AGE_HOURS = 48
CACHE_META_FILE = Path(__file__).resolve().parent.parent / "data" / "cache_meta.json"

# 全商品が同一価格のまま更新されない連続実行回数の閾値（1日3回実行 = 5日相当）
STALE_CONSECUTIVE_THRESHOLD = 15
STALE_COUNT_FILE = Path(__file__).resolve().parent.parent / "data" / "stale_counts.json"


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


def load_json_dict(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_json_dict(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cache_age_hours(meta: dict, shop_id: str) -> float:
    """キャッシュの取得からの経過時間。記録が無ければ無限大扱い。"""
    stamp = meta.get(shop_id)
    if not stamp:
        return float("inf")
    try:
        return (datetime.now(JST) - datetime.fromisoformat(stamp)).total_seconds() / 3600
    except ValueError:
        return float("inf")


def usable_cache(cache: dict, meta: dict, shop_id: str, shop_name: str) -> list | None:
    """有効期限内のキャッシュを返す。期限切れ・記録なしは None。"""
    if shop_id not in cache:
        return None
    age = cache_age_hours(meta, shop_id)
    if age > CACHE_MAX_AGE_HOURS:
        logger.warning(
            "%s: キャッシュが古いため不採用 (%.1f時間前 / 上限%d時間)",
            shop_name, age, CACHE_MAX_AGE_HOURS,
        )
        return None
    return cache[shop_id]


def main() -> None:
    logger.info("Starting price scraper for %d shops", len(ALL_SCRAPERS))

    # Reset all prices before scraping
    for product in MASTER_PRODUCTS:
        product.prices.clear()
    for product in ONEPIECE_PRODUCTS:
        product.prices.clear()

    cache = load_cache()
    cache_counts = load_cache_counts()
    cache_meta = load_json_dict(CACHE_META_FILE)
    stale_counts = load_json_dict(STALE_COUNT_FILE)
    if cache and not cache_meta:
        stamp = datetime.now(JST).isoformat(timespec="seconds")
        cache_meta = {shop_id: stamp for shop_id in cache}

    # Scrape each shop
    success_count = 0
    failed_shops: list[str] = []      # スクレイプ失敗 (例外)
    empty_shops: list[str] = []       # 0件取得
    cache_used_shops: list[str] = []  # キャッシュフォールバック
    expired_shops: list[str] = []     # キャッシュ期限切れで非掲載

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
                # 同じ取得結果をワンピ側マスターにもマッチ(相互排除で分離)
                match_products(scraped, shop_id, ONEPIECE_PRODUCTS, ONEPIECE_CONFIG)
                # Update cache with successful scrape
                if cache.get(shop_id) == scraped:
                    stale_counts[shop_id] = stale_counts.get(shop_id, 0) + 1
                else:
                    stale_counts[shop_id] = 0
                cache[shop_id] = scraped
                cache_meta[shop_id] = datetime.now(JST).isoformat(timespec="seconds")
                success_count += 1
                # リセット: 正常取得できたらカウント0
                cache_counts[shop_id] = 0
            else:
                logger.warning("%s: no items scraped", shop_name)
                empty_shops.append(shop_name)
                cache_counts[shop_id] = cache_counts.get(shop_id, 0) + 1
                # Fall back to cached data
                cached = usable_cache(cache, cache_meta, shop_id, shop_name)
                if cached is not None:
                    logger.info("%s: using cached data (%d items)", shop_name, len(cached))
                    match_products(cached, shop_id)
                    match_products(cached, shop_id, ONEPIECE_PRODUCTS, ONEPIECE_CONFIG)
                    cache_used_shops.append(shop_name)
                    success_count += 1
                elif shop_id in cache:
                    expired_shops.append(shop_name)
        except Exception:
            logger.error(
                "%s: scraping failed:\n%s", shop_name, traceback.format_exc()
            )
            failed_shops.append(shop_name)
            cache_counts[shop_id] = cache_counts.get(shop_id, 0) + 1
            # Fall back to cached data
            cached = usable_cache(cache, cache_meta, shop_id, shop_name)
            if cached is not None:
                logger.info("%s: using cached data (%d items)", shop_name, len(cached))
                match_products(cached, shop_id)
                match_products(cached, shop_id, ONEPIECE_PRODUCTS, ONEPIECE_CONFIG)
                cache_used_shops.append(shop_name)
                success_count += 1
            elif shop_id in cache:
                expired_shops.append(shop_name)

    # Save cache for next run
    save_cache(cache)
    save_cache_counts(cache_counts)
    save_json_dict(CACHE_META_FILE, cache_meta)
    save_json_dict(STALE_COUNT_FILE, stale_counts)
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

    # 価格異常検知 → 極端な外れ値はサイト掲載前に除外
    anomalies = detect_anomalies(MASTER_PRODUCTS, HISTORY_DIR)
    anomalies += detect_anomalies(ONEPIECE_PRODUCTS, HISTORY_OP_DIR)
    drop_anomalies(MASTER_PRODUCTS, anomalies)
    drop_anomalies(ONEPIECE_PRODUCTS, anomalies)
    new_anomalies, resolved_anomalies = update_state(anomalies)

    # Save daily price history
    save_history(MASTER_PRODUCTS)

    # Generate HTML
    generate_html(MASTER_PRODUCTS)
    logger.info("Done! index.html has been generated.")

    # Generate ONE PIECE page (onepiece.html)
    op_with_prices = sum(1 for p in ONEPIECE_PRODUCTS if p.prices)
    logger.info("ONE PIECE products with prices: %d/%d",
                op_with_prices, len(ONEPIECE_PRODUCTS))
    generate_onepiece_html(ONEPIECE_PRODUCTS)
    logger.info("Done! onepiece.html has been generated.")

    # 異常検知 → Discord通知
    alerts: list[str] = []
    shop_names = {c.shop_id: c.shop_name for c in ALL_SCRAPERS}

    # キャッシュ連続使用が閾値超えのショップ
    for scraper_cls in ALL_SCRAPERS:
        sid = scraper_cls.shop_id
        sname = scraper_cls.shop_name
        count = cache_counts.get(sid, 0)
        if count >= CACHE_CONSECUTIVE_THRESHOLD:
            alerts.append(f"  {sname}: {count}回連続キャッシュ使用中（スクレイプ異常の可能性）")
        stale = stale_counts.get(sid, 0)
        if stale >= STALE_CONSECUTIVE_THRESHOLD:
            alerts.append(f"  {sname}: {stale}回連続で全商品同一価格（更新停止の可能性）")

    for sname in expired_shops:
        alerts.append(f"  {sname}: キャッシュが{CACHE_MAX_AGE_HOURS}時間超のため掲載除外（取得できていません）")

    for anomaly in new_anomalies:
        alerts.append(f"  {anomaly.describe(shop_names.get(anomaly.shop, ''))}")
    for key in resolved_anomalies:
        product, _, shop = key.rpartition("|")
        alerts.append(f"  解消: {shop_names.get(shop, shop)} / {product}")

    if alerts:
        now = datetime.now(JST).strftime("%Y/%m/%d %H:%M")
        msg = f"**⚠ ポケカ買取チェッカー 異常検知** ({now})\n"
        msg += "\n".join(alerts)
        msg += "\n\nサイト構造変更・API変更・価格取得ミスの可能性があります。確認してください。"
        send_discord_alert(msg)


if __name__ == "__main__":
    main()
