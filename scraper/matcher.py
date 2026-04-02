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
]

# Keywords that indicate no-shrink-wrap (lower grade, skip in favor of shrink)
NO_SHRINK_INDICATORS = [
    "シュリンクなし", "シュリンク無し", "シュリンク無",
    "シュリンクナシ", "シュリンク未",
]

# Non-Pokemon products to exclude (e.g., One Piece, other TCGs)
NON_POKEMON_INDICATORS = [
    "ONE PIECE", "ワンピース", "遊戯王", "デュエル・マスターズ",
    "ドラゴンボール", "ヴァイスシュヴァルツ", "バトルスピリッツ",
    "ヴァンガード", "ウィクロス",
]

# Non-BOX Pokemon products to exclude
NON_BOX_INDICATORS = [
    "プロモカードパック", "カードファイルセット", "カードファイル",
    "GOLDEN BOX", "ゴールデンボックス",
    "スペシャルセット", "ジムセット",
    "ハッピーセット", "記念デッキ", "プレシャスコレクター",
    "イーブイズセット",
]


@dataclass
class MasterProduct:
    """A master product entry to match scraped items against."""
    category: str  # "mega" or "sv"
    name: str  # canonical display name
    retail_price: int  # retail price (0 = unknown)
    release_date: str = ""  # "YYYY-MM-DD"
    desc: str = ""  # 商品説明文（個別ページ用）
    keywords: list[str] = field(default_factory=list)  # matching keywords
    prices: dict[str, int] = field(default_factory=dict)  # shop_id -> price


# Master product list - canonical names and keywords for matching
MASTER_PRODUCTS: list[MasterProduct] = [
    # ===== MEGA (新しい順) =====
    MasterProduct("mega", 'MEGA 拡張パック「ニンジャスピナー」', 5400, "2026-03-13",
                  desc="MEGAシリーズ第4弾。2026年3月発売。",
                  keywords=["ニンジャスピナー", "NINJASPINNER", "NINJA SPINNER"]),
    MasterProduct("mega", 'MEGA 拡張パック「ムニキスゼロ」', 5400, "2026-01-23",
                  desc="MEGAシリーズ第3弾。2026年1月発売。",
                  keywords=["ムニキスゼロ", "ムニキス", "MUNIX"]),
    MasterProduct("mega", 'MEGA ハイクラスパック「MEGAドリームex」', 5500, "2025-11-28",
                  desc="MEGAシリーズ初のハイクラスパック。2025年11月発売。",
                  keywords=["MEGAドリーム", "メガドリーム", "MEGA DREAM"]),
    MasterProduct("mega", 'MEGA 拡張パック「インフェルノX」', 5400, "2025-09-26",
                  desc="MEGAシリーズ第2弾。メガリザードンXex SARが目玉カード。2025年9月発売。",
                  keywords=["インフェルノ", "インフェルノX", "INFERNO"]),
    MasterProduct("mega", 'MEGA 拡張パック「メガブレイブ」', 5400, "2025-08-01",
                  desc="MEGAシリーズ最初の拡張パック（2種同時発売）。2025年8月発売。",
                  keywords=["メガブレイブ", "MEGABRAVE"]),
    MasterProduct("mega", 'MEGA 拡張パック「メガシンフォニア」', 5400, "2025-08-01",
                  desc="MEGAシリーズ最初の拡張パック（2種同時発売）。2025年8月発売。",
                  keywords=["メガシンフォニア", "MEGASYMPHONIA"]),

    # ===== SV (新しい順) =====
    MasterProduct("sv", 'SV 拡張パックDX「ブラックボルト」', 5800, "2025-06-06",
                  desc="ゼクロムexのBWR（ビーダブリューレア）を収録。DX版はカード枚数が多い特別仕様。",
                  keywords=["ブラックボルト", "BLACKVOLT", "拡張パックDXブラック"]),
    MasterProduct("sv", 'SV 拡張パックDX「ホワイトフレア」', 5800, "2025-06-06",
                  desc="レシラムexのBWR（ビーダブリューレア）を収録。DX版はカード枚数が多い特別仕様。",
                  keywords=["ホワイトフレア", "WHITEFLARE", "拡張パックDXホワイト"]),
    MasterProduct("sv", 'SV 拡張パック「ブラックボルト」', 5400, "2025-06-06",
                  desc="イッシュ地方のポケモン156種がAR/SARで登場。ゼクロムexのBWRが目玉。",
                  keywords=["ブラックボルト", "BLACK BOLT"]),
    MasterProduct("sv", 'SV 拡張パック「ホワイトフレア」', 5400, "2025-06-06",
                  desc="イッシュ地方のポケモン156種がAR/SARで登場。レシラムexのBWRが目玉。",
                  keywords=["ホワイトフレア", "WHITE FLARE"]),
    MasterProduct("sv", 'SV 拡張パック「ロケット団の栄光」', 5400, "2025-04-18",
                  desc="ロケット団がテーマの拡張パック。2025年4月発売。",
                  keywords=["ロケット団の栄光", "ロケット団", "ロケット"]),
    MasterProduct("sv", 'SV 強化拡張パック「熱風のアリーナ」', 5400, "2025-03-14",
                  desc="強化拡張パック。2025年3月発売。",
                  keywords=["熱風のアリーナ", "熱風", "アリーナ"]),
    MasterProduct("sv", 'SV 拡張パック「バトルパートナーズ」', 5400, "2025-01-24",
                  desc="SVシリーズの拡張パック。2025年1月発売。",
                  keywords=["バトルパートナーズ", "パートナーズ"]),
    MasterProduct("sv", 'SV ハイクラスパック テラスタルフェスex', 5500, "2024-12-06",
                  desc="SVシリーズのハイクラスパック。大会で活躍した強力カードを多数再録。",
                  keywords=["テラスタルフェス", "テラスタル"]),
    MasterProduct("sv", 'SV 拡張パック「超電ブレイカー」', 5400, "2024-10-18",
                  desc="SVシリーズの拡張パック。2024年10月発売。",
                  keywords=["超電ブレイカー", "超電"]),
    MasterProduct("sv", 'SV 強化拡張パック「楽園ドラゴーナ」', 5400, "2024-09-13",
                  desc="ドラゴンタイプのポケモンが多数登場する強化拡張パック。アローラナッシーexが目玉。",
                  keywords=["楽園ドラゴーナ", "ドラゴーナ"]),
    MasterProduct("sv", 'SV 強化拡張パック「ステラミラクル」', 5400, "2024-07-19",
                  desc="テラパゴスexを収録した強化拡張パック。2024年7月発売。",
                  keywords=["ステラミラクル", "ステラ"]),
    MasterProduct("sv", 'SV 強化拡張パック「ナイトワンダラー」', 5400, "2024-06-07",
                  desc="キタカミの里がテーマ。モモワロウexが初収録された強化拡張パック。",
                  keywords=["ナイトワンダラー", "ナイト"]),
    MasterProduct("sv", 'SV 拡張パック「変幻の仮面」', 5400, "2024-04-26",
                  desc="オーガポンが4つの姿のexとして収録。ゼロの秘宝がテーマの拡張パック。",
                  keywords=["変幻の仮面", "変幻"]),
    MasterProduct("sv", 'SV 拡張パック「クリムゾンヘイズ」', 5400, "2024-03-22",
                  desc="キタカミの里のポケモンやトレーナーが初収録された強化拡張パック。",
                  keywords=["クリムゾンヘイズ", "クリムゾン"]),
    MasterProduct("sv", 'SV 拡張パック「ワイルドフォース」', 5400, "2024-01-26",
                  desc="「古代」のカードを中心に収録。サイバージャッジと同時発売。",
                  keywords=["ワイルドフォース", "ワイルド"]),
    MasterProduct("sv", 'SV 拡張パック「サイバージャッジ」', 5400, "2024-01-26",
                  desc="「未来」のカードを中心に収録。ワイルドフォースと同時発売。",
                  keywords=["サイバージャッジ", "サイバー"]),
    MasterProduct("sv", 'SV ハイクラスパック「シャイニートレジャーex」', 5500, "2023-12-01",
                  desc="色違いポケモンを多数収録したハイクラスパック。大会で活躍した強力カードも再録。",
                  keywords=["シャイニートレジャー"]),
    MasterProduct("sv", 'SV 拡張パック「古代の咆哮」', 5400, "2023-10-27",
                  desc="古代のパラドックスポケモンが登場。トドロクツキexが目玉。未来の一閃と同時発売。",
                  keywords=["古代の咆哮", "古代"]),
    MasterProduct("sv", 'SV 拡張パック「未来の一閃」', 5400, "2023-10-27",
                  desc="未来のパラドックスポケモンが登場。テツノブジンexが目玉。古代の咆哮と同時発売。",
                  keywords=["未来の一閃", "未来"]),
    MasterProduct("sv", 'SV 強化拡張パック「レイジングサーフ」', 5400, "2023-09-22",
                  desc="SVシリーズの強化拡張パック。2023年9月発売。",
                  keywords=["レイジングサーフ", "レイジング"]),
    MasterProduct("sv", 'SV 強化拡張パック「黒炎の支配者」', 5400, "2023-07-28",
                  desc="リザードンex SARが高額カードとして人気の強化拡張パック。",
                  keywords=["黒炎の支配者", "黒炎"]),
    MasterProduct("sv", 'SV 強化拡張パック「151」', 5400, "2023-06-16",
                  desc="初代151匹のポケモンを収録した強化拡張パック。コレクション人気が非常に高い。",
                  keywords=["151", "ポケモンカード151"]),
    MasterProduct("sv", 'SV 拡張パック「クレイバースト」', 5400, "2023-04-14",
                  desc="ナンジャモSARが高額カードとして人気。2023年4月発売。",
                  keywords=["クレイバースト", "クレイ"]),
    MasterProduct("sv", 'SV 強化拡張パック「スノーハザード」', 5400, "2023-04-14",
                  desc="パルデア地方の雪山がテーマの強化拡張パック。クレイバーストと同時発売。",
                  keywords=["スノーハザード", "スノー"]),
    MasterProduct("sv", 'SV 強化拡張パック「トリプレットビート」', 5400, "2023-03-10",
                  desc="パルデア御三家（ニャオハ・ホゲータ・クワッス）のexが初登場した強化拡張パック。",
                  keywords=["トリプレットビート", "トリプレット"]),
    MasterProduct("sv", 'SV 拡張パック「スカーレットex」', 5400, "2023-01-20",
                  desc="SVシリーズ最初の拡張パック。コライドンexが目玉。バイオレットexと同時発売。",
                  keywords=["スカーレットex"]),
    MasterProduct("sv", 'SV 拡張パック「バイオレットex」', 5400, "2023-01-20",
                  desc="SVシリーズ最初の拡張パック。ミライドンexが目玉。スカーレットexと同時発売。",
                  keywords=["バイオレットex"]),

    # ===== S&S ソード&シールド (新しい順) =====
    MasterProduct("ss", 'S&S ハイクラスパック「VSTARユニバース」', 5500, "2022-12-02",
                  desc="S&Sシリーズ総決算のハイクラスパック。SAR・ARが初登場。カイSARが最高額。",
                  keywords=["VSTARユニバース", "VSTAR ユニバース"]),
    MasterProduct("ss", 'S&S 拡張パック「パラダイムトリガー」', 4950, "2022-10-21",
                  desc="ルギアVSTARが目玉カード。S&Sシリーズ最後の拡張パック。",
                  keywords=["パラダイムトリガー", "パラダイム"]),
    MasterProduct("ss", 'S&S 強化拡張パック「白熱のアルカナ」', 4950, "2022-09-02",
                  desc="セレナSRが高額カードとして人気の強化拡張パック。",
                  keywords=["白熱のアルカナ", "白熱", "アルカナ"]),
    MasterProduct("ss", 'S&S 拡張パック「ロストアビス」', 4950, "2022-07-15",
                  desc="ロストゾーンをテーマにした拡張パック。ギラティナVSTARが目玉。",
                  keywords=["ロストアビス", "ロスト"]),
    MasterProduct("ss", 'S&S 強化拡張パック「ポケモンGO」', 4950, "2022-06-17",
                  desc="ポケモンGOとのコラボ強化拡張パック。ミュウツーVSTARが目玉。",
                  keywords=["ポケモンGO", "ポケモン GO", "POKEMON GO"]),
    MasterProduct("ss", 'S&S 強化拡張パック「ダークファンタズマ」', 4950, "2022-05-13",
                  desc="ヒスイ地方がテーマの強化拡張パック。2022年5月発売。",
                  keywords=["ダークファンタズマ", "ファンタズマ"]),
    MasterProduct("ss", 'S&S 拡張パック「タイムゲイザー」', 4950, "2022-04-08",
                  desc="オリジンディアルガVSTARが目玉。スペースジャグラーと同時発売。",
                  keywords=["タイムゲイザー"]),
    MasterProduct("ss", 'S&S 拡張パック「スペースジャグラー」', 4950, "2022-04-08",
                  desc="オリジンパルキアVSTARが目玉。タイムゲイザーと同時発売。",
                  keywords=["スペースジャグラー"]),
    MasterProduct("ss", 'S&S 強化拡張パック「バトルリージョン」', 4950, "2022-02-25",
                  desc="ヒスイ地方のポケモンが初登場した強化拡張パック。",
                  keywords=["バトルリージョン"]),
    MasterProduct("ss", 'S&S 拡張パック「スターバース」', 4950, "2022-01-14",
                  desc="アルセウスVSTARが目玉。VSTARシステムが初登場した拡張パック。",
                  keywords=["スターバース"]),
    MasterProduct("ss", 'S&S ハイクラスパック「VMAXクライマックス」', 5500, "2021-12-03",
                  desc="CSR（キャラクタースーパーレア）が初登場したハイクラスパック。",
                  keywords=["VMAXクライマックス", "vmaxクライマックス", "VMAX クライマックス"]),
    MasterProduct("ss", 'S&S 拡張パック「25th ANNIVERSARY COLLECTION」', 5500, "2021-10-22",
                  desc="ポケカ25周年記念パック。ミュウの25thプロモカードが付属。限定生産。",
                  keywords=["25thアニバーサリー", "25th ANNIVERSARY", "ANNIVERSARY COLLECTION"]),
    MasterProduct("ss", 'S&S 拡張パック「フュージョンアーツ」', 4950, "2021-09-24",
                  desc="ミュウVMAXが目玉。「フュージョン」スタイルが初登場した拡張パック。",
                  keywords=["フュージョンアーツ", "フュージョン"]),
    MasterProduct("ss", 'S&S 拡張パック「蒼空ストリーム」', 4950, "2021-07-09",
                  desc="レックウザVMAX SARが超高額カード。流通量が少なく価格が高騰。",
                  keywords=["蒼空ストリーム", "蒼空"]),
    MasterProduct("ss", 'S&S 拡張パック「摩天パーフェクト」', 4950, "2021-07-09",
                  desc="ジュラルドンVMAXが目玉。蒼空ストリームと同時発売の拡張パック。",
                  keywords=["摩天パーフェクト", "摩天"]),
    MasterProduct("ss", 'S&S 強化拡張パック「イーブイヒーローズ」', 4950, "2021-05-28",
                  desc="イーブイの進化形8種がVで登場。ブラッキーVMAX SARが超高額。",
                  keywords=["イーブイヒーローズ"]),
    MasterProduct("ss", 'S&S 拡張パック「白銀のランス」', 4950, "2021-04-23",
                  desc="はくばバドレックスVMAXが目玉。漆黒のガイストと同時発売。",
                  keywords=["白銀のランス", "白銀"]),
    MasterProduct("ss", 'S&S 拡張パック「漆黒のガイスト」', 4950, "2021-04-23",
                  desc="こくばバドレックスVMAXが目玉。白銀のランスと同時発売。",
                  keywords=["漆黒のガイスト", "漆黒"]),
    MasterProduct("ss", 'S&S 強化拡張パック「双璧のファイター」', 4950, "2021-03-19",
                  desc="いちげき・れんげき両スタイルのポケモンが収録された強化拡張パック。",
                  keywords=["双璧のファイター"]),
    MasterProduct("ss", 'S&S 拡張パック「連撃マスター」', 4950, "2021-01-22",
                  desc="れんげきウーラオスVMAXが目玉。一撃マスターと同時発売。",
                  keywords=["連撃マスター", "連撃"]),
    MasterProduct("ss", 'S&S 拡張パック「一撃マスター」', 4950, "2021-01-22",
                  desc="いちげきウーラオスVMAXが目玉。連撃マスターと同時発売。",
                  keywords=["一撃マスター", "一撃"]),
    MasterProduct("ss", 'S&S ハイクラスパック「シャイニースターV」', 5500, "2020-11-20",
                  desc="色違いポケモンを多数収録したハイクラスパック。リザードンVの色違いが高額。",
                  keywords=["シャイニースターV", "シャイニースター"]),
    MasterProduct("ss", 'S&S 拡張パック「仰天のボルテッカー」', 4950, "2020-09-18",
                  desc="ピカチュウVMAXが目玉カード。2020年9月発売の拡張パック。",
                  keywords=["仰天のボルテッカー", "仰天", "ボルテッカー"]),
    MasterProduct("ss", 'S&S 強化拡張パック「伝説の鼓動」', 4950, "2020-07-10",
                  desc="ザマゼンタの「アメイジングレア」が初登場した強化拡張パック。",
                  keywords=["伝説の鼓動"]),
    MasterProduct("ss", 'S&S 拡張パック「ムゲンゾーン」', 4950, "2020-06-05",
                  desc="ムゲンダイナVMAXが目玉。S&Sシリーズ初期の拡張パック。",
                  keywords=["ムゲンゾーン"]),
    MasterProduct("ss", 'S&S 強化拡張パック「爆炎ウォーカー」', 4950, "2020-04-24",
                  desc="マルヤクデVMAXが目玉。強化拡張パック。2020年4月発売。",
                  keywords=["爆炎ウォーカー", "爆炎"]),
    MasterProduct("ss", 'S&S 拡張パック「反逆クラッシュ」', 4950, "2020-03-06",
                  desc="ドラパルトVMAXが目玉カード。2020年3月発売の拡張パック。",
                  keywords=["反逆クラッシュ", "反逆"]),
    MasterProduct("ss", 'S&S 拡張パック「VMAXライジング」', 4950, "2020-02-07",
                  desc="VMAX進化が初登場した拡張パック。2020年2月発売。",
                  keywords=["VMAXライジング", "vmaxライジング", "VMAX ライジング"]),
    MasterProduct("ss", 'S&S 拡張パック「ソード」', 4950, "2019-12-06",
                  desc="S&Sシリーズ最初の拡張パック。ザシアンVが目玉。シールドと同時発売。",
                  keywords=["ソードV", "ソード V"]),
    MasterProduct("ss", 'S&S 拡張パック「シールド」', 4950, "2019-12-06",
                  desc="S&Sシリーズ最初の拡張パック。ザマゼンタVが目玉。ソードと同時発売。",
                  keywords=["シールドV", "シールド V"]),

    # ===== SPECIAL BOX =====
    MasterProduct("special", 'スペシャルBOX トウホク', 2090, "2025-06-13",
                  desc="ポケモンセンタートウホク限定のスペシャルBOX。",
                  keywords=["トウホク", "TOHOKU", "東北"]),
    MasterProduct("special", 'スペシャルBOX ヒロシマ', 2090, "2025-06-13",
                  desc="ポケモンセンターヒロシマ限定のスペシャルBOX。",
                  keywords=["ヒロシマ", "HIROSHIMA", "広島"]),
    MasterProduct("special", 'スペシャルBOX フクオカ', 2090, "2025-06-13",
                  desc="ポケモンセンターフクオカ限定のスペシャルBOX。",
                  keywords=["フクオカ", "FUKUOKA", "福岡"]),
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

        # Skip non-Pokemon products (One Piece, etc.)
        if any(ind in name for ind in NON_POKEMON_INDICATORS):
            logger.debug("  SKIP (non-pokemon): %s = %d", name, price)
            continue

        # Skip non-BOX Pokemon products (promo packs, file sets, etc.)
        if any(ind in name for ind in NON_BOX_INDICATORS):
            logger.debug("  SKIP (non-box): %s = %d", name, price)
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
