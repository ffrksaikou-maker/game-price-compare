"""Product name matching using rapidfuzz for fuzzy string matching."""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Threshold for fuzzy matching (0-100)
MATCH_THRESHOLD = 75

# Minimum reasonable BOX buyback price (yen) - filters accessories/sleeves
MIN_BOX_PRICE = 3000

# Maximum reasonable BOX buyback price (single BOX, yen)
MAX_BOX_PRICE = 250000

# Maximum buyback-to-retail ratio (skip if price > retail * this)
MAX_RETAIL_RATIO = 50.0

# Keywords that indicate a BOX/sealed product (safe to match)
BOX_INDICATORS = [
    "BOX", "box", "Box", "ボックス",
    "パック", "シュリンク", "未開封",
    "セット", "デッキ", "コレクション",
]

# Keywords that indicate a single card (not a BOX)
# Only applied when no BOX_INDICATORS are found in the name
SINGLE_CARD_INDICATORS = [
    "SAR", " SR ", " UR ", " AR ", " RR ", " HR ", " CSR ", " ACE ",
    "VSTAR", "VMAX",
    "プロモ", "プロモカード", "バラ",
    "1枚", "シングル", "カートン",
    "ファイル", "スリーブ", "デッキシールド", "プレイマット",
]

# Keywords that indicate no-shrink-wrap (lower grade, skip in favor of shrink)
NO_SHRINK_INDICATORS = [
    "シュリンクなし", "シュリンク無し", "シュリンク無",
    "シュリンクナシ", "シュリンク未",
]


@dataclass
class MasterProduct:
    """A master product entry to match scraped items against."""
    category: str  # "mega" or "sv"
    name: str  # canonical display name
    retail_price: int  # retail price (0 = unknown)
    release_date: str = ""  # "YYYY-MM-DD"
    keywords: list[str] = field(default_factory=list)  # matching keywords
    prices: dict[str, int] = field(default_factory=dict)  # shop_id -> price


# Master product list - canonical names and keywords for matching
MASTER_PRODUCTS: list[MasterProduct] = [
    # ===== MEGA (新しい順) =====
    MasterProduct("mega", 'MEGA 拡張パック「ニンジャスピナー」', 5400, "2026-03-13",
                  ["ニンジャスピナー", "NINJASPINNER", "NINJA SPINNER"]),
    MasterProduct("mega", 'MEGA 拡張パック「ムニキスゼロ」', 5400, "2026-01-23",
                  ["ムニキスゼロ", "ムニキス", "MUNIX"]),
    MasterProduct("mega", 'MEGA ハイクラスパック「MEGAドリームex」', 5500, "2025-11-28",
                  ["MEGAドリーム", "メガドリーム", "MEGA DREAM"]),
    MasterProduct("mega", 'MEGA 拡張パック「インフェルノX」', 5400, "2025-09-26",
                  ["インフェルノ", "インフェルノX", "INFERNO"]),
    MasterProduct("mega", 'MEGA 拡張パック「メガブレイブ」', 5400, "2025-08-01",
                  ["メガブレイブ", "MEGABRAVE"]),
    MasterProduct("mega", 'MEGA 拡張パック「メガシンフォニア」', 5400, "2025-08-01",
                  ["メガシンフォニア", "MEGASYMPHONIA"]),

    # ===== SV (新しい順) =====
    MasterProduct("sv", 'SV 拡張パックDX「ブラックボルト」', 5800, "2025-06-06",
                  ["ブラックボルト", "BLACKVOLT", "拡張パックDXブラック"]),
    MasterProduct("sv", 'SV 拡張パックDX「ホワイトフレア」', 5800, "2025-06-06",
                  ["ホワイトフレア", "WHITEFLARE", "拡張パックDXホワイト"]),
    MasterProduct("sv", 'SV 拡張パック「ブラックボルト」', 5400, "2025-06-06",
                  ["ブラックボルト", "BLACK BOLT"]),
    MasterProduct("sv", 'SV 拡張パック「ホワイトフレア」', 5400, "2025-06-06",
                  ["ホワイトフレア", "WHITE FLARE"]),
    MasterProduct("sv", 'SV 拡張パック「ロケット団の栄光」', 5400, "2025-04-18",
                  ["ロケット団の栄光", "ロケット団", "ロケット"]),
    MasterProduct("sv", 'SV 強化拡張パック「熱風のアリーナ」', 5400, "2025-03-14",
                  ["熱風のアリーナ", "熱風", "アリーナ"]),
    MasterProduct("sv", 'SV 拡張パック「バトルパートナーズ」', 5400, "2025-01-24",
                  ["バトルパートナーズ", "パートナーズ"]),
    MasterProduct("sv", 'SV ハイクラスパック テラスタルフェスex', 5500, "2024-12-06",
                  ["テラスタルフェス", "テラスタル"]),
    MasterProduct("sv", 'SV 拡張パック「超電ブレイカー」', 5400, "2024-10-18",
                  ["超電ブレイカー", "超電"]),
    MasterProduct("sv", 'SV 強化拡張パック「楽園ドラゴーナ」', 5400, "2024-09-13",
                  ["楽園ドラゴーナ", "ドラゴーナ"]),
    MasterProduct("sv", 'SV 強化拡張パック「ステラミラクル」', 5400, "2024-07-19",
                  ["ステラミラクル", "ステラ"]),
    MasterProduct("sv", 'SV 強化拡張パック「ナイトワンダラー」', 5400, "2024-06-07",
                  ["ナイトワンダラー", "ナイト"]),
    MasterProduct("sv", 'SV 拡張パック「変幻の仮面」', 5400, "2024-04-26",
                  ["変幻の仮面", "変幻"]),
    MasterProduct("sv", 'SV 拡張パック「クリムゾンヘイズ」', 5400, "2024-03-22",
                  ["クリムゾンヘイズ", "クリムゾン"]),
    MasterProduct("sv", 'SV 拡張パック「ワイルドフォース」', 5400, "2024-01-26",
                  ["ワイルドフォース", "ワイルド"]),
    MasterProduct("sv", 'SV 拡張パック「サイバージャッジ」', 5400, "2024-01-26",
                  ["サイバージャッジ", "サイバー"]),
    MasterProduct("sv", 'SV ハイクラスパック「シャイニートレジャーex」', 5500, "2023-12-01",
                  ["シャイニートレジャー"]),
    MasterProduct("sv", 'SV 拡張パック「古代の咆哮」', 5400, "2023-10-27",
                  ["古代の咆哮", "古代"]),
    MasterProduct("sv", 'SV 拡張パック「未来の一閃」', 5400, "2023-10-27",
                  ["未来の一閃", "未来"]),
    MasterProduct("sv", 'SV 強化拡張パック「レイジングサーフ」', 5400, "2023-09-22",
                  ["レイジングサーフ", "レイジング"]),
    MasterProduct("sv", 'SV 強化拡張パック「黒炎の支配者」', 5400, "2023-07-28",
                  ["黒炎の支配者", "黒炎"]),
    MasterProduct("sv", 'SV 強化拡張パック「151」', 5400, "2023-06-16",
                  ["151", "ポケモンカード151"]),
    MasterProduct("sv", 'SV 拡張パック「クレイバースト」', 5400, "2023-04-14",
                  ["クレイバースト", "クレイ"]),
    MasterProduct("sv", 'SV 強化拡張パック「スノーハザード」', 5400, "2023-04-14",
                  ["スノーハザード", "スノー"]),
    MasterProduct("sv", 'SV 強化拡張パック「トリプレットビート」', 5400, "2023-03-10",
                  ["トリプレットビート", "トリプレット"]),
    MasterProduct("sv", 'SV 拡張パック「スカーレットex」', 5400, "2023-01-20",
                  ["スカーレットex"]),
    MasterProduct("sv", 'SV 拡張パック「バイオレットex」', 5400, "2023-01-20",
                  ["バイオレットex"]),

    # ===== S&S ソード&シールド (新しい順) =====
    MasterProduct("ss", 'S&S ハイクラスパック「VSTARユニバース」', 5500, "2022-12-02",
                  ["VSTARユニバース", "VSTAR ユニバース"]),
    MasterProduct("ss", 'S&S 拡張パック「パラダイムトリガー」', 4950, "2022-10-21",
                  ["パラダイムトリガー", "パラダイム"]),
    MasterProduct("ss", 'S&S 強化拡張パック「白熱のアルカナ」', 4950, "2022-09-02",
                  ["白熱のアルカナ", "アルカナ"]),
    MasterProduct("ss", 'S&S 拡張パック「ロストアビス」', 4950, "2022-07-15",
                  ["ロストアビス"]),
    MasterProduct("ss", 'S&S 強化拡張パック「ポケモンGO」', 4950, "2022-06-17",
                  ["ポケモンGO", "ポケモン GO", "POKEMON GO"]),
    MasterProduct("ss", 'S&S 強化拡張パック「ダークファンタズマ」', 4950, "2022-05-13",
                  ["ダークファンタズマ", "ファンタズマ"]),
    MasterProduct("ss", 'S&S 拡張パック「タイムゲイザー」', 4950, "2022-04-08",
                  ["タイムゲイザー"]),
    MasterProduct("ss", 'S&S 拡張パック「スペースジャグラー」', 4950, "2022-04-08",
                  ["スペースジャグラー"]),
    MasterProduct("ss", 'S&S 強化拡張パック「バトルリージョン」', 4950, "2022-02-25",
                  ["バトルリージョン"]),
    MasterProduct("ss", 'S&S 拡張パック「スターバース」', 4950, "2022-01-14",
                  ["スターバース"]),
    MasterProduct("ss", 'S&S ハイクラスパック「VMAXクライマックス」', 5500, "2021-12-03",
                  ["VMAXクライマックス", "vmaxクライマックス", "VMAX クライマックス"]),
    MasterProduct("ss", 'S&S 拡張パック「25th ANNIVERSARY COLLECTION」', 5500, "2021-10-22",
                  ["25thアニバーサリー", "25th ANNIVERSARY", "ANNIVERSARY COLLECTION"]),
    MasterProduct("ss", 'S&S 拡張パック「フュージョンアーツ」', 4950, "2021-09-24",
                  ["フュージョンアーツ", "フュージョン"]),
    MasterProduct("ss", 'S&S 拡張パック「蒼空ストリーム」', 4950, "2021-07-09",
                  ["蒼空ストリーム"]),
    MasterProduct("ss", 'S&S 拡張パック「摩天パーフェクト」', 4950, "2021-07-09",
                  ["摩天パーフェクト"]),
    MasterProduct("ss", 'S&S 強化拡張パック「イーブイヒーローズ」', 4950, "2021-05-28",
                  ["イーブイヒーローズ"]),
    MasterProduct("ss", 'S&S 拡張パック「白銀のランス」', 4950, "2021-04-23",
                  ["白銀のランス"]),
    MasterProduct("ss", 'S&S 拡張パック「漆黒のガイスト」', 4950, "2021-04-23",
                  ["漆黒のガイスト"]),
    MasterProduct("ss", 'S&S 強化拡張パック「双璧のファイター」', 4950, "2021-03-19",
                  ["双璧のファイター"]),
    MasterProduct("ss", 'S&S 拡張パック「連撃マスター」', 4950, "2021-01-22",
                  ["連撃マスター"]),
    MasterProduct("ss", 'S&S 拡張パック「一撃マスター」', 4950, "2021-01-22",
                  ["一撃マスター"]),
    MasterProduct("ss", 'S&S ハイクラスパック「シャイニースターV」', 5500, "2020-11-20",
                  ["シャイニースターV", "シャイニースター"]),
    MasterProduct("ss", 'S&S 拡張パック「仰天のボルテッカー」', 4950, "2020-09-18",
                  ["仰天のボルテッカー", "ボルテッカー"]),
    MasterProduct("ss", 'S&S 強化拡張パック「伝説の鼓動」', 4950, "2020-07-10",
                  ["伝説の鼓動"]),
    MasterProduct("ss", 'S&S 拡張パック「ムゲンゾーン」', 4950, "2020-06-05",
                  ["ムゲンゾーン"]),
    MasterProduct("ss", 'S&S 強化拡張パック「爆炎ウォーカー」', 4950, "2020-04-24",
                  ["爆炎ウォーカー"]),
    MasterProduct("ss", 'S&S 拡張パック「反逆クラッシュ」', 4950, "2020-03-06",
                  ["反逆クラッシュ"]),
    MasterProduct("ss", 'S&S 拡張パック「VMAXライジング」', 4950, "2020-02-07",
                  ["VMAXライジング", "vmaxライジング", "VMAX ライジング"]),
    MasterProduct("ss", 'S&S 拡張パック「ソード」', 4950, "2019-12-06",
                  ["ソードV", "ソード V"]),
    MasterProduct("ss", 'S&S 拡張パック「シールド」', 4950, "2019-12-06",
                  ["シールドV", "シールド V"]),

    # ===== SPECIAL BOX =====
    MasterProduct("special", 'スペシャルBOX トウホク', 2090, "2025-06-13",
                  ["トウホク", "TOHOKU", "東北"]),
    MasterProduct("special", 'スペシャルBOX ヒロシマ', 2090, "2025-06-13",
                  ["ヒロシマ", "HIROSHIMA", "広島"]),
    MasterProduct("special", 'スペシャルBOX フクオカ', 2090, "2025-06-13",
                  ["フクオカ", "FUKUOKA", "福岡"]),
]


def normalize(text: str) -> str:
    """Normalize text for matching: NFKC + lowercase + strip symbols."""
    text = unicodedata.normalize("NFKC", text)
    # Remove common packaging words
    text = re.sub(r"[【】\[\]（）()「」『』\-\s]+", " ", text)
    # Remove common noise words
    noise = ["BOX", "box", "Box", "シュリンク付", "シュリンク", "未開封",
             "新品", "日本語版", "ポケモンカードゲーム", "ポケカ",
             "1BOX", "1box", "1Box"]
    for word in noise:
        text = text.replace(word, "")
    return text.strip()


def _keyword_match(scraped_name: str, product: MasterProduct) -> bool:
    """Check if any keyword from the product matches in the scraped name."""
    norm_name = normalize(scraped_name)
    for kw in product.keywords:
        norm_kw = normalize(kw)
        if norm_kw and norm_kw in norm_name:
            return True
    return False


def _is_single_card(name: str) -> bool:
    """Check if the product name looks like a single card (not a BOX).

    Only returns True if no BOX indicators are present AND single card
    indicators are found.
    Promo items are always considered single cards.
    """
    # Promo/supply items are always single cards, regardless of BOX indicators
    # (e.g., "25thアニバーサリーコレクション プロモ" contains "コレクション"
    #  but is still a promo card, not a BOX)
    # (e.g., "ポケモンGO カードファイルセット" contains "セット"
    #  but is a supply item, not a BOX)
    ALWAYS_SKIP = ["プロモ", "プロモカード", "ファイル", "スリーブ",
                   "デッキシールド", "プレイマット", "ダメカン",
                   "スペシャルセット", "GOLDEN BOX"]
    for indicator in ALWAYS_SKIP:
        if indicator in name:
            return True

    # If any BOX indicator is present, it's not a single card
    for indicator in BOX_INDICATORS:
        if indicator in name:
            return False

    # Check for single card indicators
    for indicator in SINGLE_CARD_INDICATORS:
        if indicator in name:
            return True
    return False


def _disambiguate_dx(scraped_name: str) -> str | None:
    """Distinguish between DX and non-DX versions of same-name packs.

    Returns 'dx' if the item is a DX pack, 'normal' if normal, None if unclear.
    """
    norm = normalize(scraped_name).lower()
    if "dx" in norm or "DX" in scraped_name:
        return "dx"
    if "拡張パックdx" in norm or "拡張パックDX" in scraped_name:
        return "dx"
    # Runto uses "デラックス" instead of "DX"
    if "デラックス" in scraped_name:
        return "dx"
    return "normal"


def match_products(
    scraped_items: list[tuple[str, int]],
    shop_id: str,
    products: list[MasterProduct] | None = None,
) -> None:
    """Match scraped items to master product list and set prices.

    Args:
        scraped_items: list of (product_name, price) tuples
        shop_id: the shop identifier (e.g., "morimori")
        products: master product list (uses MASTER_PRODUCTS if None)
    """
    if products is None:
        products = MASTER_PRODUCTS

    matched = set()

    for name, price in scraped_items:
        if price <= 0:
            continue

        # Skip items that are clearly single cards (not BOX)
        if _is_single_card(name):
            continue

        # Skip no-shrink-wrap items (prefer shrink-wrapped price)
        if any(ind in name for ind in NO_SHRINK_INDICATORS):
            logger.debug("  SKIP (no shrink): %s = %d", name, price)
            continue

        # Skip unreasonably low prices (likely accessories/sleeves)
        if price < MIN_BOX_PRICE:
            logger.debug("  SKIP (price too low): %s = %d", name, price)
            continue

        # Skip unreasonably high prices (likely single rare cards or errors)
        if price > MAX_BOX_PRICE:
            logger.debug("  SKIP (price too high): %s = %d", name, price)
            continue

        best_product = None
        best_score = 0

        for product in products:
            # Step 1: Try keyword matching first (exact substring)
            if _keyword_match(name, product):
                # Handle disambiguation for products with same keywords
                # e.g., "ブラックボルト" matches both DX and non-DX
                if product.keywords and any(
                    kw in ["ブラックボルト", "ホワイトフレア"]
                    for kw in product.keywords
                ):
                    is_dx = _disambiguate_dx(name)
                    product_is_dx = "DX" in product.name
                    if product_is_dx and is_dx != "dx":
                        continue
                    if not product_is_dx and is_dx == "dx":
                        continue

                score = 100
                if score > best_score:
                    best_score = score
                    best_product = product
                continue

            # Step 2: Fuzzy matching as fallback
            norm_name = normalize(name)
            norm_product = normalize(product.name)
            score = fuzz.token_sort_ratio(norm_name, norm_product)
            if score > best_score:
                best_score = score
                best_product = product

        if best_product and best_score >= MATCH_THRESHOLD:
            # Skip if price is unreasonably high relative to retail
            if best_product.retail_price > 0:
                ratio = price / best_product.retail_price
                if ratio > MAX_RETAIL_RATIO:
                    logger.debug(
                        "  SKIP (ratio %.1fx): %s = %d (retail=%d)",
                        ratio, name, price, best_product.retail_price,
                    )
                    continue

            key = id(best_product)
            # Keep the LOWEST valid price per shop+product
            # (single cards tend to be more expensive than BOX)
            existing = best_product.prices.get(shop_id)
            if existing is None or price < existing:
                best_product.prices[shop_id] = price
            if key not in matched:
                matched.add(key)
                logger.debug(
                    "  %s -> %s (score=%d, price=%d)",
                    name, best_product.name, best_score, price,
                )
        else:
            logger.debug(
                "  UNMATCHED: %s (best_score=%d)", name, best_score,
            )

    logger.info(
        "%s: matched %d/%d items",
        shop_id, len(matched), len(scraped_items),
    )
