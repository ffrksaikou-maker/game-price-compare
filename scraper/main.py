"""Main entry point: scrape all shops, match products, generate HTML."""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
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
from scraper.products_beyblade import BEYBLADE_PRODUCTS, BEYBLADE_CONFIG
from scraper.generator_beyblade import generate_beyblade_html
from scraper.products_dragonball import DRAGONBALL_PRODUCTS, DRAGONBALL_CONFIG
from scraper.generator_dragonball import generate_dragonball_html
from scraper import mercari
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
HISTORY_BEY_DIR = Path(__file__).resolve().parent.parent / "data" / "history_bey"
HISTORY_DB_DIR = Path(__file__).resolve().parent.parent / "data" / "history_db"

# 取得に失敗した店を全店ループ後にもう一度試すまでの待ち時間（秒）
# 一時的な接続タイムアウト対策。失敗店が無い回はこの待ちは発生しない
RETRY_DELAY_SECONDS = 300

# 1店あたりの上限秒。1店の障害が全体を道連れにしないための保険。
# 未設定(0)なら無制限で、従来どおりの挙動。CI では workflow の env で設定する。
SHOP_TIMEOUT_SECONDS = int(os.environ.get("SHOP_TIMEOUT_SECONDS", "0") or 0)
# ジョブ全体の目安秒。これを超えていたら失敗店の再試行(RETRY_DELAY_SECONDS の
# 待機を含む)を諦めて、取得済みの結果を確定させにいく。未設定(0)なら無制限。
JOB_DEADLINE_SECONDS = int(os.environ.get("JOB_DEADLINE_SECONDS", "0") or 0)
_JOB_STARTED_AT = time.monotonic()


def _job_elapsed() -> float:
    return time.monotonic() - _JOB_STARTED_AT


def _run_with_timeout(fn, timeout: int):
    """fn() を別スレッドで実行し、timeout 秒を超えたら TimeoutError にする。

    Playwright の goto は外から中断できないためスレッドは走り続けるが、
    daemon スレッドなのでプロセス終了時に道連れで落ちる。呼び出し側は
    待たずに次の店へ進めるので、1店の障害でジョブ全体を失わずに済む。
    """
    box: dict = {}

    def _target() -> None:
        try:
            box["items"] = fn()
        except Exception as e:  # 呼び出し側で従来どおり failed 扱いにする
            box["err"] = e

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        raise TimeoutError(f"scrape exceeded {timeout}s")
    if "err" in box:
        raise box["err"]
    return box.get("items")

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


def match_all_games(scraped: list, shop_id: str) -> None:
    """1店の取得結果をポケカ/ワンピ/ベイ/ドラゴンボールの4マスターに通す。

    各 MatchConfig の exclude_indicators が互いに他ジャンルを弾くので、
    同じ入力を4回流しても取り違えは起きない。
    """
    match_products(scraped, shop_id)
    match_products(scraped, shop_id, ONEPIECE_PRODUCTS, ONEPIECE_CONFIG)
    match_products(scraped, shop_id, BEYBLADE_PRODUCTS, BEYBLADE_CONFIG)
    match_products(scraped, shop_id, DRAGONBALL_PRODUCTS, DRAGONBALL_CONFIG)


def selected_shop_ids() -> set[str] | None:
    """SCRAPER_SHOPS で指定された取得対象の店。未指定なら None(=全店)。

    急ぎ1店だけ直したいときに全店ぶんの待ち時間を省くための絞り込み。
    対象外の店はキャッシュから復元するので、サイトの掲載店は減らない。
    """
    raw = os.environ.get("SCRAPER_SHOPS", "").strip()
    if not raw:
        return None
    known = {c.shop_id for c in ALL_SCRAPERS}
    ids = {s.strip() for s in raw.split(",") if s.strip()}
    unknown = ids - known
    if unknown:
        logger.warning("SCRAPER_SHOPS: 未知の店を無視: %s", ", ".join(sorted(unknown)))
    ids &= known
    if not ids:
        logger.warning("SCRAPER_SHOPS: 有効な店がないため全店を取得します")
        return None
    return ids


def try_scrape(scraper) -> tuple[list | None, str]:
    """1店スクレイプし、(items, 結果) を返す。結果は ok / empty / failed。"""
    logger.info("--- Scraping %s (%s) ---", scraper.shop_name, scraper.shop_id)
    try:
        if SHOP_TIMEOUT_SECONDS > 0:
            items = _run_with_timeout(scraper.scrape, SHOP_TIMEOUT_SECONDS)
        else:
            items = scraper.scrape()
    except TimeoutError as e:
        logger.error("%s: %s — この店を打ち切って次に進みます", scraper.shop_name, e)
        return None, "failed"
    except Exception:
        logger.error(
            "%s: scraping failed:\n%s", scraper.shop_name, traceback.format_exc()
        )
        return None, "failed"
    if items:
        return items, "ok"
    logger.warning("%s: no items scraped", scraper.shop_name)
    return None, "empty"


def main() -> None:
    logger.info("Starting price scraper for %d shops", len(ALL_SCRAPERS))

    # Reset all prices before scraping
    for product in MASTER_PRODUCTS:
        product.prices.clear()
    for product in ONEPIECE_PRODUCTS:
        product.prices.clear()
    for product in BEYBLADE_PRODUCTS:
        product.prices.clear()
    for product in DRAGONBALL_PRODUCTS:
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

    def accept(shop_id: str, items: list) -> None:
        nonlocal success_count
        # Convert to (name, price) tuples for matcher
        scraped = [(item.name, item.price) for item in items]
        # 同じ取得結果をワンピ・ベイ側マスターにも通す(相互排除で分離)
        match_all_games(scraped, shop_id)
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

    def fall_back(shop_id: str, shop_name: str, outcome: str) -> None:
        nonlocal success_count
        if outcome == "failed":
            failed_shops.append(shop_name)
        else:
            empty_shops.append(shop_name)
        cache_counts[shop_id] = cache_counts.get(shop_id, 0) + 1
        # Fall back to cached data
        cached = usable_cache(cache, cache_meta, shop_id, shop_name)
        if cached is not None:
            logger.info("%s: using cached data (%d items)", shop_name, len(cached))
            match_all_games(cached, shop_id)
            cache_used_shops.append(shop_name)
            success_count += 1
        elif shop_id in cache:
            expired_shops.append(shop_name)

    def reuse_cache(shop_id: str, shop_name: str) -> None:
        """取得対象外の店をキャッシュから復元する(掲載を維持するため)。"""
        nonlocal success_count
        cached = usable_cache(cache, cache_meta, shop_id, shop_name)
        if cached is not None:
            logger.info("%s: 取得対象外のためキャッシュを流用 (%d件)", shop_name, len(cached))
            match_all_games(cached, shop_id)
            success_count += 1
        elif shop_id in cache:
            expired_shops.append(shop_name)

    selected = selected_shop_ids()
    if selected:
        logger.info("対象店を限定: %s", ", ".join(sorted(selected)))

    # 1周目。失敗した店はここでは確定させず、待ってから再試行する
    pending: list[tuple[type, str]] = []
    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        if selected and scraper.shop_id not in selected:
            reuse_cache(scraper.shop_id, scraper.shop_name)
            continue
        items, outcome = try_scrape(scraper)
        if outcome == "ok":
            accept(scraper.shop_id, items)
        else:
            pending.append((scraper_cls, outcome))

    if pending and JOB_DEADLINE_SECONDS > 0 and (
            _job_elapsed() + RETRY_DELAY_SECONDS > JOB_DEADLINE_SECONDS):
        logger.warning(
            "経過 %.0f s / 目安 %d s のため %d 店の再試行をスキップします: %s",
            _job_elapsed(), JOB_DEADLINE_SECONDS, len(pending),
            ", ".join(cls.shop_name for cls, _ in pending),
        )
        for scraper_cls, outcome in pending:
            scraper = scraper_cls()
            fall_back(scraper.shop_id, scraper.shop_name, outcome)
        pending = []

    if pending:
        logger.info(
            "Retrying %d shop(s) in %d s: %s",
            len(pending), RETRY_DELAY_SECONDS,
            ", ".join(cls.shop_name for cls, _ in pending),
        )
        time.sleep(RETRY_DELAY_SECONDS)
        for scraper_cls, _ in pending:
            scraper = scraper_cls()
            items, outcome = try_scrape(scraper)
            if outcome == "ok":
                logger.info("%s: recovered on retry", scraper.shop_name)
                accept(scraper.shop_id, items)
            else:
                fall_back(scraper.shop_id, scraper.shop_name, outcome)

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
    anomalies += detect_anomalies(BEYBLADE_PRODUCTS, HISTORY_BEY_DIR)
    anomalies += detect_anomalies(DRAGONBALL_PRODUCTS, HISTORY_DB_DIR)
    drop_anomalies(MASTER_PRODUCTS, anomalies)
    drop_anomalies(ONEPIECE_PRODUCTS, anomalies)
    drop_anomalies(BEYBLADE_PRODUCTS, anomalies)
    drop_anomalies(DRAGONBALL_PRODUCTS, anomalies)
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

    # Generate ベイブレード page (beyblade.html)
    bey_with_prices = sum(1 for p in BEYBLADE_PRODUCTS if p.prices)
    logger.info("Beyblade products with prices: %d/%d",
                bey_with_prices, len(BEYBLADE_PRODUCTS))
    # メルカリ相場は取得に数分かかるため、失敗しても前回キャッシュで描画を続ける
    market = mercari.load_cache()
    if os.environ.get("SCRAPER_SKIP_MERCARI") != "1":
        try:
            market = mercari.fetch_with_cache(BEYBLADE_PRODUCTS)
        except Exception:
            logger.error("mercari: fetch failed:\n%s", traceback.format_exc())
    generate_beyblade_html(BEYBLADE_PRODUCTS, market)
    logger.info("Done! beyblade.html has been generated.")

    # Generate ドラゴンボール page (dragonball.html)
    db_with_prices = sum(1 for p in DRAGONBALL_PRODUCTS if p.prices)
    logger.info("Dragon Ball products with prices: %d/%d",
                db_with_prices, len(DRAGONBALL_PRODUCTS))
    generate_dragonball_html(DRAGONBALL_PRODUCTS)
    logger.info("Done! dragonball.html has been generated.")

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
