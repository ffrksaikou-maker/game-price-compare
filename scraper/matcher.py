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

# Maximum reasonable BOX buyback price (single BOX, yen)
MAX_BOX_PRICE = 60000

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
]


@dataclass
class MasterProduct:
    """A master product entry to match scraped items against."""
    category: str  # "mega" or "sv"
    name: str  # canonical display name
    retail_price: int  # retail price (0 = unknown)
    keywords: list[str] = field(default_factory=list)  # matching keywords
    prices: dict[str, int] = field(default_factory=dict)  # shop_id -> price


# Master product list - canonical names and keywords for matching
MASTER_PRODUCTS: list[MasterProduct] = [
    # ===== MEGA =====
    MasterProduct("mega", 'MEGA 拡張パック「インフェルノX」', 5400,
                  ["インフェルノ", "インフェルノX", "INFERNO"]),
    MasterProduct("mega", 'MEGA 拡張パック「メガブレイブ」', 5400,
                  ["メガブレイブ", "MEGABRAVE"]),
    MasterProduct("mega", 'MEGA ハイクラスパック「MEGAドリームex」', 5500,
                  ["MEGAドリーム", "メガドリーム", "MEGA DREAM"]),
    MasterProduct("mega", 'MEGA 拡張パック「メガシンフォニア」', 5400,
                  ["メガシンフォニア", "MEGASYMPHONIA"]),
    MasterProduct("mega", 'MEGA 拡張パック「ムニキスゼロ」', 5400,
                  ["ムニキスゼロ", "ムニキス", "MUNIX"]),

    # ===== SV =====
    MasterProduct("sv", 'SV 強化拡張パック「151」', 5400,
                  ["151", "ポケモンカード151"]),
    MasterProduct("sv", 'SV 拡張パック「超電ブレイカー」', 5400,
                  ["超電ブレイカー", "超電"]),
    MasterProduct("sv", 'SV 拡張パックDX「ブラックボルト」', 5800,
                  ["ブラックボルト", "BLACKVOLT", "拡張パックDXブラック"]),
    MasterProduct("sv", 'SV 拡張パックDX「ホワイトフレア」', 5800,
                  ["ホワイトフレア", "WHITEFLARE", "拡張パックDXホワイト"]),
    MasterProduct("sv", 'SV 拡張パック「ロケット団の栄光」', 5400,
                  ["ロケット団の栄光", "ロケット団", "ロケット"]),
    MasterProduct("sv", 'SV 拡張パック「ブラックボルト」', 5400,
                  ["ブラックボルト", "BLACK BOLT"]),
    MasterProduct("sv", 'SV 強化拡張パック「熱風のアリーナ」', 5400,
                  ["熱風のアリーナ", "熱風", "アリーナ"]),
    MasterProduct("sv", 'SV ハイクラスパック テラスタルフェスex', 5500,
                  ["テラスタルフェス", "テラスタル"]),
    MasterProduct("sv", 'SV 強化拡張パック「黒炎の支配者」', 5400,
                  ["黒炎の支配者", "黒炎"]),
    MasterProduct("sv", 'SV 拡張パック「ホワイトフレア」', 5400,
                  ["ホワイトフレア", "WHITE FLARE"]),
    MasterProduct("sv", 'SV 強化拡張パック「トリプレットビート」', 5400,
                  ["トリプレットビート", "トリプレット"]),
    MasterProduct("sv", 'SV 強化拡張パック「楽園ドラゴーナ」', 5400,
                  ["楽園ドラゴーナ", "ドラゴーナ"]),
    MasterProduct("sv", 'SV 拡張パック「クリムゾンヘイズ」', 5400,
                  ["クリムゾンヘイズ", "クリムゾン"]),
    MasterProduct("sv", 'SV ハイクラスパック「シャイニートレジャーex」', 5500,
                  ["シャイニートレジャー", "シャイニー"]),
    MasterProduct("sv", 'SV 拡張パック「クレイバースト」', 5400,
                  ["クレイバースト", "クレイ"]),
    MasterProduct("sv", 'SV 強化拡張パック「レイジングサーフ」', 5400,
                  ["レイジングサーフ", "レイジング"]),
    MasterProduct("sv", 'SV 拡張パック「スカーレットex」', 5400,
                  ["スカーレットex", "スカーレット"]),
    MasterProduct("sv", 'SV 拡張パック「変幻の仮面」', 5400,
                  ["変幻の仮面", "変幻"]),
    MasterProduct("sv", 'SV 拡張パック「ワイルドフォース」', 5400,
                  ["ワイルドフォース", "ワイルド"]),
    MasterProduct("sv", 'SV 強化拡張パック「スノーハザード」', 5400,
                  ["スノーハザード", "スノー"]),
    MasterProduct("sv", 'SV 拡張パック「古代の咆哮」', 5400,
                  ["古代の咆哮", "古代"]),
    MasterProduct("sv", 'SV 強化拡張パック「ステラミラクル」', 5400,
                  ["ステラミラクル", "ステラ"]),
    MasterProduct("sv", 'SV 強化拡張パック「ナイトワンダラー」', 5400,
                  ["ナイトワンダラー", "ナイト"]),
    MasterProduct("sv", 'SV 拡張パック「サイバージャッジ」', 5400,
                  ["サイバージャッジ", "サイバー"]),
    MasterProduct("sv", 'SV 拡張パック「未来の一閃」', 5400,
                  ["未来の一閃", "未来"]),
    MasterProduct("sv", 'SV 拡張パック「バイオレットex」', 5400,
                  ["バイオレットex", "バイオレット"]),
    MasterProduct("sv", 'SV 拡張パック「バトルパートナーズ」', 5400,
                  ["バトルパートナーズ", "パートナーズ"]),
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
    """
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
            key = id(best_product)
            # Keep the first matched price (avoid overwriting with wrong higher-priced matches)
            if shop_id not in best_product.prices:
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
