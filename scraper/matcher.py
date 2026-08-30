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

# Absolute floor used for the pre-match skip. Cheap products (e.g. スタートデッキ100,
# 定価891円) can legitimately sell below MIN_BOX_PRICE, so the pre-filter only drops
# obvious junk. The real per-product floor (MIN_BOX_PRICE or product.min_price) is
# applied AFTER a product match is found.
ABS_MIN_PRICE = 1500

# Maximum reasonable BOX buyback price (single BOX, yen)
MAX_BOX_PRICE = 500000

# Maximum buyback-to-retail ratio (skip if price > retail * this)
MAX_RETAIL_RATIO = 80.0

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

# BOX 製品名に "VSTAR"/"VMAX" が含まれるため SINGLE_CARD_INDICATORS で
# 誤って単品除外されてしまう製品（"BOX"等の表記が無い出品名で発生）。
# これらの名前を含む出品は単品扱いから救済する。
BOX_NAME_WHITELIST = [
    "VSTARユニバース", "VMAXクライマックス", "VMAXライジング",
]

# 救済対象でも、これらの語があれば単品/非BOX(カートン等)として除外する
STRONG_SINGLE_INDICATORS = [
    "カートン", "バラ", "1枚", "シングル", "プロモ",
]

# Keywords that indicate no-shrink-wrap (lower grade, skip in favor of shrink)
NO_SHRINK_INDICATORS = [
    "シュリンクなし", "シュリンク無し", "シュリンク無",
    "シュリンクナシ", "シュリンク未",
]

# Non-Pokemon products to exclude (e.g., One Piece, other TCGs)
# ワンピは商品名に「ONE PIECE/ワンピース」が無く弾番号だけの出品もある
# (例「OP-07 500年後の未来」がポケカ「未来の一閃」に誤マッチ)。弾番号接頭辞も除外する。
# 店により「OP-07」「OP07」両表記があるためハイフン有無の両形式を生成。
_OP_SET_CODES = (
    [f"OP-{i:02d}" for i in range(1, 19)] + [f"OP{i:02d}" for i in range(1, 19)]
    + [f"EB-{i:02d}" for i in range(1, 6)] + [f"EB{i:02d}" for i in range(1, 6)]
    + [f"PRB-{i:02d}" for i in range(1, 4)] + [f"PRB{i:02d}" for i in range(1, 4)]
)
# ベイブレードXの型番。店により「UX-19」だけ、あるいはJANコードだけの出品名があり
# 「ベイブレード」語が入らないため、型番接頭辞もポケカ/ワンピの除外語に加える。
# 店により「UX-19」「UX19」両表記があるためハイフン有無の両形式を生成。
_BEY_SET_CODES = (
    [f"BX-{i:02d}" for i in range(0, 61)] + [f"BX{i:02d}" for i in range(0, 61)]
    + [f"UX-{i:02d}" for i in range(0, 31)] + [f"UX{i:02d}" for i in range(0, 31)]
    + [f"CX-{i:02d}" for i in range(0, 31)] + [f"CX{i:02d}" for i in range(0, 31)]
)
# ドラゴンボール(フュージョンワールド)の弾番号。店により「FB-07」「FB07」両表記。
# ST(STORY BOOSTER)は ONE PIECE のスタートデッキ(ST-01〜)と番号体系が完全に
# 衝突するため型番では引かず、商品名(STORY BOOSTER)で判別する。
_DB_SET_CODES = (
    [f"FB-{i:02d}" for i in range(1, 21)] + [f"FB{i:02d}" for i in range(1, 21)]
    + [f"SB-{i:02d}" for i in range(1, 11)] + [f"SB{i:02d}" for i in range(1, 11)]
)
# ドラゴンボール固有の商品名。弾番号を持たない出品(ダイバーズ等)を弾くのに使う。
_DB_NAME_INDICATORS = [
    "ドラゴンボール", "フュージョンワールド", "スーパーダイバーズ",
    "MANGA BOOSTER", "STORY BOOSTER", "アドバンスパック",
]
NON_POKEMON_INDICATORS = [
    "ONE PIECE", "ワンピース", "遊戯王", "デュエル・マスターズ",
    "ヴァイスシュヴァルツ", "バトルスピリッツ",
    "ヴァンガード", "ウィクロス",
    "ベイブレード", "BEYBLADE",
] + _OP_SET_CODES + _BEY_SET_CODES + _DB_SET_CODES + _DB_NAME_INDICATORS

# Non-BOX Pokemon products to exclude
NON_BOX_INDICATORS = [
    "プロモカードパック", "プロモパック", "カードファイルセット", "カードファイル", "ファイルセット",
    "GOLDEN BOX", "ゴールデンボックス",
    "スペシャルセット", "ジムセット",
    "ハッピーセット", "記念デッキ", "プレシャスコレクター",
    "イーブイズセット",
    "アタッシュケース",
    "デッキビルドBOX", "ポケセンセット", "白箱", "カートン",
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
    hit_cards: list[tuple[str, str]] = field(default_factory=list)  # 当たりカード（トップレア）[(カード名, コメント), ...]
    prices: dict[str, int] = field(default_factory=dict)  # shop_id -> price
    min_price: int = 0  # 価格下限の上書き（0=MIN_BOX_PRICEを使用）。格安デッキ用
    jan: str = ""  # JANコード（ベイブレードで商品同定用に表示。他ゲームは未使用）


@dataclass
class MatchConfig:
    """ゲーム別のマッチ設定。ポケカ/ワンピで別インスタンスを使う。

    デフォルト値はポケカの現行挙動と一致（POKEMON_CONFIG）。match_products に
    config を渡さなければ従来どおり POKEMON_CONFIG が使われ、挙動は不変。
    """
    exclude_indicators: list[str] = field(default_factory=list)      # 他ゲーム除外
    non_box_indicators: list[str] = field(default_factory=list)      # 非BOX除外
    box_indicators: list[str] = field(default_factory=list)
    single_card_indicators: list[str] = field(default_factory=list)
    box_name_whitelist: list[str] = field(default_factory=list)
    strong_single_indicators: list[str] = field(default_factory=list)
    no_shrink_indicators: list[str] = field(default_factory=list)
    noise_words: list[str] = field(default_factory=list)             # normalize用
    min_box_price: int = MIN_BOX_PRICE
    abs_min_price: int = ABS_MIN_PRICE
    max_box_price: int = MAX_BOX_PRICE
    max_retail_ratio: float = MAX_RETAIL_RATIO
    match_threshold: int = MATCH_THRESHOLD
    enable_dx_disambiguation: bool = True
    # 型番優先マッチ。指定すると「型番が出品名とマスター両方にあるのに食い違う」
    # 組み合わせを別商品として確定除外し、一致した場合はキーワード扱いにする。
    # ベイブレード用(BX/UX/CX-NN)。空文字ならこの判定自体を行わない=従来挙動。
    model_code_pattern: str = ""
    # 型番が一致してもキーワード一致を追加で要求する番号。ベイブレードの
    # UX-00/BX-00/CX-00 は限定品の共通枠で中身が全く別物のため。
    model_code_ambiguous_numbers: list[str] = field(default_factory=list)


# Master product list - canonical names and keywords for matching
MASTER_PRODUCTS: list[MasterProduct] = [
    # ===== MEGA (新しい順) =====
    # 30周年記念商品(2026-09-16発売)。同じ「30th CELEBRATION」を名前に含む
    # 商品が3つあるため、より限定的なキーワードを持つ FUTURISTIC BOX と
    # プレミアムデッキセットを先に置く(マッチはリスト順で先勝ち)。
    MasterProduct("mega", '30th CELEBRATION FUTURISTIC BOX', 27500, "2026-09-16",
                  desc="ポケモンカード30周年記念のプレミアム商品。FUR仕様のピカチュウex2種に加え、プレイマット・デッキケース・ディスプレイフレーム等のサプライ一式が同梱される。2026年9月16日世界同時発売、定価27,500円。",
                  keywords=["FUTURISTIC", "フューチャリスティック", "フューチャリスティックBOX"]),
    MasterProduct("mega", '30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー', 6200, "2026-09-16",
                  desc="ポケモンカード30周年記念のデッキセット。エーフィとブラッキーがテーマ。2026年9月16日発売、定価6,200円。",
                  keywords=["プレミアムデッキセット", "エーフィ・ブラッキー", "エーフィ&ブラッキー",
                            "エーフィブラッキー", "エーフィ ブラッキー"]),
    MasterProduct("mega", 'MEGA 拡張パック「30th CELEBRATION」', 7200, "2026-09-16",
                  desc="ポケモンカード30周年記念の拡張パック。1パック360円でカード6枚すべてがキラ仕様、BOXは20パック入りで定価7,200円と通常弾と仕様が異なる。新レアリティ「FUR」のミュウツーex・ミュウex、30人のイラストレーターが描くピカチュウ30種を収録。2026年9月16日世界同時発売。",
                  keywords=["30th CELEBRATION", "30thCELEBRATION", "30th セレブレーション",
                            "30thセレブレーション", "セレブレーション"]),
    MasterProduct("mega", 'MEGA 拡張パック「ストームエメラルダ」', 6000, "2026-07-31",
                  desc="MEGAシリーズ最新弾。メガレックウザex収録、2026年7月31日発売(定価200円/BOX 6,000円)。伝説三巨頭レックウザのメガ進化が目玉。",
                  keywords=["ストームエメラルダ", "STORMEMERALDA", "STORM EMERALDA", "MEGA 拡張パック ストーム", "ストームエメラルド"],
                  hit_cards=[("メガレックウザex MUR", "本弾の最高額で買取約15.8万円。MUR封入率は約51BOXに1枚と推定され、この射幸性がBOX相場を単体で押し上げている"), ("メガレックウザex SAR", "パッケージ目玉のSAR版で買取約5.6万円。MURに次ぐ2番手で、SAR6種の中では突出"), ("ライコウex SAR", "メガレックウザex以外では最高額の約4,550円。次点はメガレックウザex SR約3,120円、ヒガナの信頼SAR約2,327円")]),
    MasterProduct("mega", 'MEGA 拡張パック「アビスアイ」', 6000, "2026-05-22",
                  desc="MEGAシリーズ第5弾。値上げ後初の拡張パック(定価200円/BOX 6,000円)。メガダークライex収録、2026年5月22日発売。",
                  keywords=["アビスアイ", "ABYSSEYE", "ABYSS EYE", "MEGA 拡張パック アビス"],
                  hit_cards=[("メガダークライex MUR", "MUR封入率は実測で約100BOXに1枚。買取は約4万円で本弾の最高額"), ("メガダークライex SAR", "パッケージ目玉のSAR版で買取約3.3万円。ワザ『アビスアイ』は特殊状態なら残HP無視できぜつの強力効果"), ("ムク SAR", "SAR6種のうちAR/SAR枠で最も高い約4,300円。メガダークライex以外では本弾の上位")]),
    MasterProduct("mega", 'MEGA 拡張パック「ニンジャスピナー」', 5400, "2026-03-13",
                  desc="MEGAシリーズ第4弾。2026年3月発売。",
                  keywords=["ニンジャスピナー", "NINJASPINNER", "NINJA SPINNER"],
                  hit_cards=[("メガゲッコウガex MUR", "封入率約50BOXに1枚の最高レアリティ。買取は約6万円(6月の約11万円から調整)"), ("メガゲッコウガex SAR", "ゲッコウガの圧倒的キャラ人気でSARも高額化"), ("チラチーノex SAR", "可愛らしいイラストでコレクター人気が高い")]),
    MasterProduct("mega", 'MEGA 拡張パック「ムニキスゼロ」', 5400, "2026-01-23",
                  desc="MEGAシリーズ第3弾。2026年1月発売。",
                  keywords=["ムニキスゼロ", "ムニキス", "MUNIX"],
                  hit_cards=[("メガジガルデex MUR", "MUR封入率約70BOXに1枚。買取は約2.7万円(発売時の5万円超から調整)"), ("メイのはげまし SAR", "BWの人気女性トレーナー。コレクター需要が非常に高い"), ("ニャースex SAR", "ロケット団のニャース人気とSARイラストの魅力で高騰")]),
    MasterProduct("mega", 'MEGA スタートデッキ100「バトルコレクション」', 891, "2025-12-19",
                  desc="100種類のデッキからランダムで1つ入っている構築済みデッキ。MUR仕様のメガリザードンYexが超高額。",
                  keywords=["バトルコレクション", "BATTLE COLLECTION"],
                  min_price=1500,  # 定価891円の格安デッキ。買取2200〜3200円なので3000円フィルタ対象外にする
                  hit_cards=[("メガリザードンYex MUR仕様", "封入率が極めて低い最高レアリティ(No.001・約1000個に1枚)。2026年5月の約100万円から続落し買取約80万円"), ("ピカチュウex SAR仕様", "ピカチュウ人気×SAR仕様の希少性で買取約15万円(6月の約30万円から半減)"), ("リーリエのピッピex SAR仕様", "リーリエ人気キャラのSAR仕様。買取約4万円(6月の12〜14万円から大きく調整)")]),
    MasterProduct("mega", 'MEGA ハイクラスパック「MEGAドリームex」', 5500, "2025-11-28",
                  desc="MEGAシリーズ初のハイクラスパック。2025年11月発売。",
                  keywords=["MEGAドリーム", "メガドリーム", "MEGA DREAM"],
                  hit_cards=[("メガゲンガーex SAR", "ゲンガーのキャラ人気が極めて高く、買取約4万円で本弾の最高額"), ("ピカチュウex SAR", "ポケモンの顔・ピカチュウのSAR。買取約3万円で世界的に高需要"), ("メガカイリューex MUR", "MUR封入率約50BOXに1枚。買取約2.8万円の希少カード")]),
    MasterProduct("mega", 'MEGA 拡張パック「インフェルノX」', 5400, "2025-09-26",
                  desc="MEGAシリーズ第2弾。メガリザードンXex SARが目玉カード。2025年9月発売。",
                  keywords=["インフェルノ", "インフェルノX", "INFERNO"],
                  hit_cards=[("メガリザードンXex MUR", "リザードン人気×MUR封入率50BOXに1枚。買取は約15万円で全MEGA弾の最高額級"), ("メガリザードンXex SAR", "リザードンの圧倒的人気でSARも買取約9万円の高額カード"), ("ヒカリ SAR", "DP主人公の初カード化。古澤あつし氏の美麗イラストで注目")]),
    MasterProduct("mega", 'MEGA 拡張パック「メガブレイブ」', 5400, "2025-08-01",
                  desc="MEGAシリーズ最初の拡張パック（2種同時発売）。2025年8月発売。",
                  keywords=["メガブレイブ", "MEGABRAVE"],
                  hit_cards=[("メガルカリオex MUR", "MUR封入率約50BOXに1枚。買取は約4万円"), ("リーリエの決心 SAR", "歴代No.1人気トレーナー・リーリエのSAR。買取約2万円(初動7万円超から調整)"), ("メガルカリオex SAR", "格闘ポケモン人気No.1のルカリオ。SARイラストも好評")]),
    MasterProduct("mega", 'MEGA 拡張パック「メガシンフォニア」', 5400, "2025-08-01",
                  desc="MEGAシリーズ最初の拡張パック（2種同時発売）。2025年8月発売。",
                  keywords=["メガシンフォニア", "MEGASYMPHONIA"],
                  hit_cards=[("メガサーナイトex MUR", "MUR封入率約50BOXに1枚。買取は約4万円(発売時の7万円超から調整)"), ("メガサーナイトex SAR", "サーナイトのキャラ人気とSARの美麗イラストで高額化"), ("アセロラのいたずら SAR", "ゴーストタイプ使いの人気女性トレーナー。コレクター需要大")]),

    # ===== SV (新しい順) =====
    MasterProduct("sv", 'SV 拡張パックDX「ブラックボルト」', 5800, "2025-06-06",
                  desc="ゼクロムexのBWR（ビーダブリューレア）を収録。DX版は1パック35枚入り（通常版の5倍）でARが1枚確定。1BOX4パックのため総枚数140枚は通常版と同じ。",
                  keywords=["ブラックボルト", "BLACKVOLT", "拡張パックDXブラック"],
                  hit_cards=[("ゼクロムex BWR", "20BOXに1枚の激レア。BW時代を彷彿させる全体黒色デザイン"), ("ゼクロムex SAR", "伝説ポケモン・ゼクロムの封入率が低いSARで高額化"), ("Nの筋書き SAR", "BWの人気ライバル・Nの新規SAR。コレクター需要が高い")]),
    MasterProduct("sv", 'SV 拡張パックDX「ホワイトフレア」', 5800, "2025-06-06",
                  desc="レシラムexのBWR（ビーダブリューレア）を収録。DX版は1パック35枚入り（通常版の5倍）でARが1枚確定。1BOX4パックのため総枚数140枚は通常版と同じ。",
                  keywords=["ホワイトフレア", "WHITEFLARE", "拡張パックDXホワイト"],
                  hit_cards=[("レシラムex BWR", "20BOXに1枚の激レア。白色レリーフ加工で立体感あるデザイン"), ("レシラムex SAR", "7種SARの中でも伝説ポケモンとして群を抜く人気"), ("トウコ SAR", "さいとうなおき氏イラスト。BW女性主人公の人気で高額化")]),
    MasterProduct("sv", 'SV 拡張パック「ブラックボルト」', 5800, "2025-06-06",
                  desc="イッシュ地方のポケモン156種がAR/SARで登場。ゼクロムexのBWRが目玉。",
                  keywords=["ブラックボルト", "BLACK BOLT"],
                  hit_cards=[("ゼクロムex BWR", "20BOXに1枚の激レア。BW時代を彷彿させる全体黒色デザイン"), ("ゼクロムex SAR", "伝説ポケモン・ゼクロムの封入率が低いSARで高額化"), ("Nの筋書き SAR", "BWの人気ライバル・Nの新規SAR。コレクター需要が高い")]),
    MasterProduct("sv", 'SV 拡張パック「ホワイトフレア」', 5800, "2025-06-06",
                  desc="イッシュ地方のポケモン156種がAR/SARで登場。レシラムexのBWRが目玉。",
                  keywords=["ホワイトフレア", "WHITE FLARE"],
                  hit_cards=[("レシラムex BWR", "20BOXに1枚の激レア。白色レリーフ加工で立体感あるデザイン"), ("レシラムex SAR", "7種SARの中でも伝説ポケモンとして群を抜く人気"), ("トウコ SAR", "さいとうなおき氏イラスト。BW女性主人公の人気で高額化")]),
    MasterProduct("sv", 'SV 拡張パック「ロケット団の栄光」', 5400, "2025-04-18",
                  desc="ロケット団がテーマの拡張パック。2025年4月発売。",
                  keywords=["ロケット団の栄光", "ロケット団", "ロケット"],
                  hit_cards=[("ロケット団のミュウツーex SAR", "伝説ポケモン・ミュウツーの約3年ぶりハイレア。5万円超"), ("ロケット団のファイヤーex SAR", "江川あきら氏の美麗イラストで初代伝説鳥ポケモン人気"), ("ロケット団のニドキングex SAR", "サカキの相棒ポケモンとして根強いファン人気")]),
    MasterProduct("sv", 'SV 強化拡張パック「熱風のアリーナ」', 5400, "2025-03-14",
                  desc="強化拡張パック。2025年3月発売。",
                  keywords=["熱風のアリーナ", "熱風", "アリーナ"],
                  hit_cards=[("シロナのガブリアスex SAR", "本弾の最高額で買取約3.3万円。歴代屈指の人気チャンピオン×対戦人気ポケモンの組み合わせ"), ("ヒビキのホウオウex SAR", "2位の約2.9万円で1位との差はわずか約12%。金銀主人公×パッケージ伝説の王道"), ("カスミのコダック AR", "AR枠ながら約4,500円。ARは1BOXに3枚確定のため開封の下支えになる")]),
    MasterProduct("sv", 'SV 拡張パック「バトルパートナーズ」', 5400, "2025-01-24",
                  desc="SVシリーズの拡張パック。2025年1月発売。",
                  keywords=["バトルパートナーズ", "パートナーズ"],
                  hit_cards=[("リーリエのピッピex SAR", "本弾の最高額で買取約1.7万円。歴代屈指の人気トレーナー・リーリエと相棒ピッピの組み合わせ"), ("ナンジャモのハラバリーex SAR", "2位の約9,000円。SVを代表する人気トレーナーとの組み合わせ"), ("Nのゾロアークex SAR", "3位の約5,500円。BWの人気キャラNの相棒ポケモン")]),
    MasterProduct("sv", 'SV ハイクラスパック テラスタルフェスex', 5500, "2024-12-06",
                  desc="SVシリーズのハイクラスパック。大会で活躍した強力カードを多数再録。",
                  keywords=["テラスタルフェス", "テラスタル"],
                  hit_cards=[("ブラッキーex SAR", "ポケモン・オブ・ザ・イヤー上位の大人気イーブイ進化形"), ("ニンフィアex SAR", "フェアリータイプの可愛さでコレクション需要が高い"), ("ピカチュウex UR", "ポケモンの顔ピカチュウのUR。封入率10BOXに1枚で希少")]),
    MasterProduct("sv", 'SV 拡張パック「超電ブレイカー」', 5400, "2024-10-18",
                  desc="SVシリーズの拡張パック。2024年10月発売。",
                  keywords=["超電ブレイカー", "超電"],
                  hit_cards=[("ピカチュウex SAR", "ピカチュウ人気×低封入率SARで6万円超の最高額カード"), ("ピカチュウex UR", "ピカチュウのUR。封入率の低さとキャラ人気で2万円超"), ("ミカンのまなざし SAR", "女性ジムリーダーの美麗SARイラストでコレクター人気")]),
    MasterProduct("sv", 'SV 強化拡張パック「楽園ドラゴーナ」', 5400, "2024-09-13",
                  desc="ドラゴンタイプのポケモンが多数登場する強化拡張パック。アローラナッシーexが目玉。",
                  keywords=["楽園ドラゴーナ", "ドラゴーナ"],
                  hit_cards=[("ラティアスex SAR", "本弾の最高額で買取約2.2万円。ドラゴンテーマの看板でAR枠のラティオスと対になる"), ("ルチアのアピール SAR", "2番手の約1.9万円で1位との差はわずか約14%。トレーナーSARとしては破格の水準"), ("アローラナッシーex SAR", "3位の約2,500円。上位2枚とは8倍前後の開きがある")]),
    MasterProduct("sv", 'SV 強化拡張パック「ステラミラクル」', 5400, "2024-07-19",
                  desc="テラパゴスexを収録した強化拡張パック。2024年7月発売。",
                  keywords=["ステラミラクル", "ステラ"],
                  hit_cards=[("タロ SAR", "本弾の最高額だが買取約4,000円と天井は低め。イラスト人気で評価されている"), ("バウッツェルex SAR", "2位の約3,700円。1位との差はわずか約8%で上位が密集している"), ("テラパゴスex SAR", "3位の約3,000円。『ゼロの秘宝』の主役だが相場では1位に届かない")]),
    MasterProduct("sv", 'SV 強化拡張パック「ナイトワンダラー」', 5400, "2024-06-07",
                  desc="キタカミの里がテーマ。モモワロウexが初収録された強化拡張パック。",
                  keywords=["ナイトワンダラー"],
                  hit_cards=[("キチキギスex SAR", "本弾の最高額だが買取約2,500円と控えめ。汎用ドロー特性を持ち対戦実需がBOX相場を支える"), ("モモワロウex SAR", "2位の約1,900円。DLC『碧の仮面』の幻のポケモン"), ("カシオペア SAR", "3位の約1,800円。スター団マジボスの正体でサイバー感あるイラストが好評")]),
    MasterProduct("sv", 'SV 拡張パック「変幻の仮面」', 5400, "2024-04-26",
                  desc="オーガポンが4つの姿のexとして収録。ゼロの秘宝がテーマの拡張パック。",
                  keywords=["変幻の仮面", "変幻"],
                  hit_cards=[("ゼイユ SAR", "本弾の最高額で買取約1.4万円。2位に4倍以上の差をつける一強で、SAR封入率は約6BOXに1枚"), ("スグリ SAR", "2位の約3,000円。ゼイユの弟にあたるキタカミの里の人気キャラ"), ("オーガポンみどりのめんex SAR", "4姿あるオーガポンexのうち最高額の約2,200円。姿ごとに分散収録された分、1枚あたりの希少性は控えめ")]),
    MasterProduct("sv", 'SV 拡張パック「クリムゾンヘイズ」', 5400, "2024-03-22",
                  desc="キタカミの里のポケモンやトレーナーが初収録された強化拡張パック。",
                  keywords=["クリムゾンヘイズ", "クリムゾン"],
                  hit_cards=[("ゲッコウガex SAR", "本弾の最高額で買取約4.4万円。2位に4倍以上の差をつける一強で、SAR封入率は約6BOXに1枚かつ全5種のため狙い撃ちは困難"), ("サザレ SAR", "2位の約9,500円。『碧の仮面』の人気トレーナーで、ヒスイガーディとの連動イラストが評価されている"), ("イーブイ AR", "AR枠ながら約4,000円でSAR3種を上回る。ARは1BOXに3枚が確定封入で、狙いの1種は約4BOXに1枚")]),
    MasterProduct("sv", 'SV 拡張パック「ワイルドフォース」', 5400, "2024-01-26",
                  desc="「古代」のカードを中心に収録。サイバージャッジと同時発売。",
                  keywords=["ワイルドフォース", "ワイルド"],
                  hit_cards=[("マツバの確信 SAR", "本弾の最高額で買取約6,000円。金銀ジムリーダー×ゲンガーの組合せが評価されている"), ("ゲンガーex SR", "2位の約5,500円。SR枠ながらSARのタケルライコex(約4,000円)を上回るゲンガー人気"), ("タケルライコex SAR", "3位の約4,000円。古代ライコウの高火力ワザが環境で活躍した")]),
    MasterProduct("sv", 'SV 拡張パック「サイバージャッジ」', 5400, "2024-01-26",
                  desc="「未来」のカードを中心に収録。ワイルドフォースと同時発売。",
                  keywords=["サイバージャッジ", "サイバー"],
                  hit_cards=[("ベルのまごころ SAR", "本弾の最高額で買取約5,000円。BW世代の人気キャラで、ムシャーナと昼寝する構図が評価されている"), ("テツノカシラex SAR", "2位の約3,000円。未来パラドックスのSARだがテーマの主役ながら1位には届かない"), ("シキジカ AR", "4位の約1,600円。AR枠ながらテツノイワオexSAR・セイジSARという2枚のSARを上回る")]),
    MasterProduct("sv", 'SV ハイクラスパック「シャイニートレジャーex」', 5500, "2023-12-01",
                  desc="色違いポケモンを多数収録したハイクラスパック。大会で活躍した強力カードも再録。",
                  keywords=["シャイニートレジャー"],
                  hit_cards=[("ミュウex SAR", "幻ポケモンの圧倒的人気。8種SAR中で最高額の約5万円"), ("ナンジャモ SAR", "SV人気No.1キャラの新規イラスト。コレクター需要が非常に高い"), ("リザードンex SAR", "リザードンの圧倒的人気×環境最強デッキで高額化")]),
    MasterProduct("sv", 'SV 拡張パック「古代の咆哮」', 5400, "2023-10-27",
                  desc="古代のパラドックスポケモンが登場。トドロクツキexが目玉。未来の一閃と同時発売。",
                  keywords=["古代の咆哮", "古代"],
                  hit_cards=[("トドロクツキex SAR", "買取約5,500円で1位タイ。古代ボーマンダの姿で一撃きぜつワザと高HPにより環境上位"), ("基本悪エネルギー UR", "同じく約5,500円で1位タイ。他弾の基本闘・基本鋼UR(各約2,200円)の2.5倍で、悪タイプの需要の高さが表れている"), ("グソクムシャex SAR", "3位の約2,300円。上位2枚とは2倍以上の開きがある")]),
    MasterProduct("sv", 'SV 拡張パック「未来の一閃」', 5400, "2023-10-27",
                  desc="未来のパラドックスポケモンが登場。テツノブジンexが目玉。古代の咆哮と同時発売。",
                  keywords=["未来の一閃", "未来"],
                  hit_cards=[("チルタリスex SAR", "本弾の最高額で買取約8,000円。テーマの主役であるパラドックスポケモンを相場で上回っている"), ("テツノブジンex SAR", "2位の約3,300円。サーナイト×エルレイド融合の人気デザインで対戦でも汎用性が高い"), ("基本鋼エネルギー UR", "3位に約2,200円。スカーレットexの基本闘エネルギーURと同価格帯で、SV期を通じ弾をまたいで安定している枠")]),
    MasterProduct("sv", 'SV 強化拡張パック「レイジングサーフ」', 5400, "2023-09-22",
                  desc="SVシリーズの強化拡張パック。2023年9月発売。",
                  keywords=["レイジングサーフ", "レイジング"],
                  hit_cards=[("パラソルおねえさん SAR", "本弾の最高額で買取約6,000円。モブキャラながら虹空の儚げなイラストで看板ポケモンを上回った代表例"), ("ガブリアスex SAR", "2位の約5,000円。UR版も約2,800円と同一カードが2枠で上位に入る"), ("サーフゴーex SAR", "3位の約3,800円。パック名に通じる看板ポケモンで対戦でも活躍")]),
    MasterProduct("sv", 'SV 強化拡張パック「黒炎の支配者」', 5400, "2023-07-28",
                  desc="リザードンex SARが高額カードとして人気の強化拡張パック。",
                  keywords=["黒炎の支配者", "黒炎"],
                  hit_cards=[("リザードンex SAR", "リザードン人気×環境最強デッキで3万円超の最高額カード"), ("ピジョットex SAR", "特性マッハサーチが環境必須。実用性とSAR希少性で高額"), ("ポピー SAR", "四天王の女性キャラ。可愛いイラストでコレクター需要あり")]),
    MasterProduct("sv", 'SV 強化拡張パック「151」', 5400, "2023-06-16",
                  desc="初代151匹のポケモンを収録した強化拡張パック。コレクション人気が非常に高い。",
                  keywords=["151", "ポケモンカード151"],
                  hit_cards=[("エリカの招待 SAR", "初代人気ジムリーダー。絵画のような美麗イラストで高額化"), ("リザードンex SAR", "初代御三家の王。圧倒的キャラ人気でSARも2万円超"), ("ミュウex SAR", "幻のポケモンの可愛さとSAR封入率の低さで高額化")]),
    MasterProduct("sv", 'SV 拡張パック「クレイバースト」', 5400, "2023-04-14",
                  desc="ナンジャモSARが高額カードとして人気。2023年4月発売。",
                  keywords=["クレイバースト", "クレイ"],
                  hit_cards=[("ナンジャモ SAR", "SV最人気キャラ×きりさき氏イラスト。買取5万円超の看板カード"), ("ナンジャモ SR", "SAR同様にキャラ人気が絶大。SRでも高値で取引される"), ("イーユイex SAR", "災厄ポケモンの美しいデザイン。コレクション需要で人気")]),
    MasterProduct("sv", 'SV 強化拡張パック「スノーハザード」', 5400, "2023-04-14",
                  desc="パルデア地方の雪山がテーマの強化拡張パック。クレイバーストと同時発売。",
                  keywords=["スノーハザード", "スノー"],
                  hit_cards=[("パオジアンex SAR", "本弾の最高額で買取約3,500円。災いの四災の一体で対戦環境でも活躍した"), ("グルーシャ SAR", "2位の約3,000円。ナッペ山のジムリーダーで女性トレーナーSARの人気枠"), ("基本水エネルギー UR", "3位の約2,800円。実用カードのUR仕様で、デッキを組む層の需要が下支えしている")]),
    MasterProduct("sv", 'SV 強化拡張パック「トリプレットビート」', 5400, "2023-03-10",
                  desc="パルデア御三家（ニャオハ・ホゲータ・クワッス）のexが初登場した強化拡張パック。",
                  keywords=["トリプレットビート", "トリプレット"],
                  hit_cards=[("コイキング AR", "本弾の最高額で買取約1.9万円。ARながらSARを2.5倍上回る異例の1枚で、カンダシンジ氏のイラスト人気とAR30種の希少性が理由"), ("マスカーニャex SAR", "2位の約7,500円。パルデア御三家で人気No.1"), ("キハダ SAR", "3位の約6,000円。SVの人気女教師でトレーナーSAR枠の最高額")]),
    MasterProduct("sv", 'SV 拡張パック「スカーレットex」', 5400, "2023-01-20",
                  desc="SVシリーズ最初の拡張パック。コライドンexが目玉。バイオレットexと同時発売。",
                  keywords=["スカーレットex"],
                  hit_cards=[("サーナイトex SAR", "本弾の最高額で買取約2.2万円。2位に4.4倍差をつける一強でSV初期の最高額枠"), ("コライドンex SAR", "2位の約5,000円。スカーレットの看板伝説でパッケージを飾る"), ("基本闘エネルギー UR", "3位に約2,200円。SV期のUR仕様が初登場した弾ゆえ、汎用カードのURが当たり枠として機能している")]),
    MasterProduct("sv", 'SV 拡張パック「バイオレットex」', 5400, "2023-01-20",
                  desc="SVシリーズ最初の拡張パック。ミライドンexが目玉。スカーレットexと同時発売。",
                  keywords=["バイオレットex"],
                  hit_cards=[("ミモザ SAR", "SV保健室の先生。アニメ調の斬新なイラストで買取3万円超"), ("ミライドンex SAR", "バイオレットの看板伝説。電気ドラゴンのかっこいいデザイン"), ("ペパー SAR", "SV主要キャラ。ストーリーでの活躍とキャラ人気で需要あり")]),

    # ===== S&S ソード&シールド (新しい順) =====
    MasterProduct("ss", 'S&S ハイクラスパック「VSTARユニバース」', 5500, "2022-12-02",
                  desc="S&Sシリーズ総決算のハイクラスパック。SAR・ARが初登場。カイSARが最高額。",
                  keywords=["VSTARユニバース", "VSTAR ユニバース"],
                  hit_cards=[("ピカチュウ AR", "200BOXに1枚の超低封入率で希少性が極めて高い"), ("カイ SAR", "さいとうなおき氏のイラストとキャラ人気で高額化"), ("ギラティナVSTAR UR", "環境トップの性能とイラスト繋がりのコンプ需要")]),
    MasterProduct("ss", 'S&S 拡張パック「パラダイムトリガー」', 4950, "2022-10-21",
                  desc="ルギアVSTARが目玉カード。S&Sシリーズ最後の拡張パック。",
                  keywords=["パラダイムトリガー", "パラダイム"],
                  hit_cards=[("ルギアV SA SR", "環境トップのルギアVSTARデッキで採用率が高い"), ("スズナ SR", "さいとうなおき氏イラストでDP人気ジムリーダー"), ("ルギアVSTAR UR", "ルギアデッキの核で競技・コレクション両需要")]),
    MasterProduct("ss", 'S&S 強化拡張パック「白熱のアルカナ」', 4950, "2022-09-02",
                  desc="セレナSRが高額カードとして人気の強化拡張パック。",
                  keywords=["白熱のアルカナ", "白熱", "アルカナ"],
                  hit_cards=[("セレナ SR", "XYの人気キャラでイラスト・カード性能ともに高評価"), ("ジャローダV CSR", "BW2女主人公メイとの共演で10BOXに1枚の低封入率"), ("ふりそで SR", "和風デザインが海外コレクターから高い評価")]),
    MasterProduct("ss", 'S&S 拡張パック「ロストアビス」', 4950, "2022-07-15",
                  desc="ロストゾーンをテーマにした拡張パック。ギラティナVSTARが目玉。",
                  keywords=["ロストアビス", "ロスト"],
                  hit_cards=[("ギラティナV SA", "買取約22万円でBOX買取の約4.5倍。当サイト追跡でカード/BOX比の最高記録"), ("プテラV SA", "買取約1.2万円。1位とは約18倍差で断層も当サイト最大"), ("ギラティナVSTAR UR", "買取約7,000円。イラスト人気と対戦環境での長期活躍が重なった弾")]),
    MasterProduct("ss", 'S&S 強化拡張パック「ポケモンGO」', 4950, "2022-06-17",
                  desc="ポケモンGOとのコラボ強化拡張パック。ミュウツーVSTARが目玉。",
                  keywords=["ポケモンGO", "ポケモン GO", "POKEMON GO"],
                  hit_cards=[("ミュウツーV SA SR", "初代伝説ポケモンの圧倒的人気と高層ビル群の神秘的SA"), ("ミュウツーVSTAR UR", "ミュウツー人気とURの希少性でコレクター需要大"), ("カイリューV SA SR", "温かみのあるSAイラストとドラゴンタイプの根強い人気")]),
    MasterProduct("ss", 'S&S 強化拡張パック「ダークファンタズマ」', 4950, "2022-05-13",
                  desc="ヒスイ地方がテーマの強化拡張パック。2022年5月発売。",
                  keywords=["ダークファンタズマ", "ファンタズマ"],
                  hit_cards=[("ヒナツ SR", "LEGENDSアルセウスの人気キャラで伊里日葉氏の美麗イラスト"), ("ピカチュウ CHR", "ピカチュウのCHRで安定したコレクター人気"), ("ラブトロスV CSR", "コギトの妖艶な表情と絵画のようなデザインが魅力")]),
    MasterProduct("ss", 'S&S 拡張パック「タイムゲイザー」', 4950, "2022-04-08",
                  desc="オリジンディアルガVSTARが目玉。スペースジャグラーと同時発売。",
                  keywords=["タイムゲイザー"],
                  hit_cards=[("ナタネの活気 SR", "DP人気ジムリーダーで草デッキ必須のサポートカード"), ("オリジンディアルガV SA SR", "美麗SAイラストと4BOXに1枚の低封入率で希少"), ("頂への雪道 UR", "環境必須のスタジアムでプレイヤー需要が非常に高い")]),
    MasterProduct("ss", 'S&S 拡張パック「スペースジャグラー」', 4950, "2022-04-08",
                  desc="オリジンパルキアVSTARが目玉。タイムゲイザーと同時発売。",
                  keywords=["スペースジャグラー"],
                  hit_cards=[("カイ SR", "女性サポート人気トップクラスで初動2万円超の高額カード"), ("オリジンパルキアV SA SR", "VSTARデッキが大会優勝の実績で競技需要が高い"), ("スピアーV SA SR", "花畑を舞う色彩豊かなSAイラストがコレクターに好評")]),
    MasterProduct("ss", 'S&S 強化拡張パック「バトルリージョン」', 4950, "2022-02-25",
                  desc="ヒスイ地方のポケモンが初登場した強化拡張パック。",
                  keywords=["バトルリージョン"],
                  hit_cards=[("スターミーV CSR", "人気キャラ・カスミとの共演フルイラストで高騰"), ("ガブリアスV CSR", "シロナとの共演CSRでシロナ人気に支えられ高額"), ("ツツジ SR", "可愛いイラストと終盤に相手を崩す優秀な性能")]),
    MasterProduct("ss", 'S&S 拡張パック「スターバース」', 4950, "2022-01-14",
                  desc="アルセウスVSTARが目玉。VSTARシステムが初登場した拡張パック。",
                  keywords=["スターバース"],
                  hit_cards=[("リザードンV SA SR", "初代御三家の絶大な人気と4BOXに1枚の低封入率"), ("ハイパーボール UR", "ほぼ全デッキ採用の汎用カードでプレイヤー需要大"), ("シロナの覇気 SR", "歴代屈指の人気キャラでカード性能も強力")]),
    MasterProduct("ss", 'S&S ハイクラスパック「VMAXクライマックス」', 5500, "2021-12-03",
                  desc="CSR（キャラクタースーパーレア）が初登場したハイクラスパック。",
                  keywords=["VMAXクライマックス", "vmaxクライマックス", "VMAX クライマックス"],
                  hit_cards=[("レックウザVMAX UR", "買取約2.9万円。上位8枚すべてが7,000円超という当サイト追跡でもっとも層の厚い弾"), ("ピカチュウVMAX UR", "買取約2万円。1位と8位の差はわずか約4.1倍"), ("レックウザVMAX CSR", "買取約1.9万円。同じレックウザVMAXでも蒼空ストリームのSA(約80万円)とは約27倍差")]),
    MasterProduct("ss", 'S&S 拡張パック「25th ANNIVERSARY COLLECTION」', 5500, "2021-10-22",
                  desc="ポケカ25周年記念パック。ミュウの25thプロモカードが付属。限定生産。",
                  keywords=["25thアニバーサリー", "25th ANNIVERSARY", "ANNIVERSARY COLLECTION"],
                  hit_cards=[("リザードン 25th プロモ", "初代リザードンの25周年仕様復刻で圧倒的コレクション価値"), ("お誕生日ピカチュウ 25th プロモ", "1998年旧裏プロモの復刻で名前記入欄付きの特別デザイン"), ("ミュウ UR", "25周年パック本体の最高レアでミュウの根強い人気")]),
    MasterProduct("ss", 'S&S 拡張パック「フュージョンアーツ」', 4950, "2021-09-24",
                  desc="ミュウVMAXが目玉。「フュージョン」スタイルが初登場した拡張パック。",
                  keywords=["フュージョンアーツ", "フュージョン"],
                  hit_cards=[("ミュウVMAX SA", "買取約14万円で本弾の最高額。BOX買取の約2.5倍に相当する"), ("ミュウV SA", "買取約2万円。上位4枚をミュウ関連が独占する集中構造"), ("ミュウVMAX HR", "買取約1.9万円。同じSAでもゲノセクトV(約2,000円)とは70倍差で、人気が価格を決める")]),
    MasterProduct("ss", 'S&S 拡張パック「蒼空ストリーム」', 4950, "2021-07-09",
                  desc="レックウザVMAX SARが超高額カード。流通量が少なく価格が高騰。",
                  keywords=["蒼空ストリーム", "蒼空"],
                  hit_cards=[("レックウザVMAX SA", "買取約80万円で当サイト調査の最高額カード。伝説ドラゴンの圧倒的人気に加え、SA封入率は約4BOXに1枚(全4種)と極めて低い"), ("レックウザV SA", "買取約15万円。1枚で他弾の最高額を上回る水準で、レックウザ人気の厚みを示す"), ("カイリューV SA", "買取約6.5万円。レックウザ以外で唯一の高額SAで、初代からの人気ドラゴン")]),
    MasterProduct("ss", 'S&S 拡張パック「摩天パーフェクト」', 4950, "2021-07-09",
                  desc="ジュラルドンVMAXが目玉。蒼空ストリームと同時発売の拡張パック。",
                  keywords=["摩天パーフェクト", "摩天"],
                  hit_cards=[("ジュラルドンVMAX SA HR", "特性まてんろうが環境で強力かつ100BOX開封でも出ない希少性"), ("ジュラルドンV SA SR", "キバナとの共演イラストで人気が高い"), ("オンバーンV SA SR", "独特の魅力あるSAイラストで将来的な高騰期待")]),
    MasterProduct("ss", 'S&S 強化拡張パック「イーブイヒーローズ」', 4950, "2021-05-28",
                  desc="イーブイの進化形8種がVで登場。ブラッキーVMAX SARが超高額。",
                  keywords=["イーブイヒーローズ"],
                  hit_cards=[("ブラッキーVMAX SA HR", "イーブイ進化系で最も人気が高く48BOXに1枚の超希少SA"), ("ニンフィアVMAX SA HR", "フェアリータイプの可愛さで女性ファンにも絶大な人気"), ("グレイシアVMAX SA HR", "きりさき氏の美麗イラストとグレイシアの根強い人気")]),
    MasterProduct("ss", 'S&S 拡張パック「白銀のランス」', 4950, "2021-04-23",
                  desc="はくばバドレックスVMAXが目玉。漆黒のガイストと同時発売。",
                  keywords=["白銀のランス", "白銀"],
                  hit_cards=[("はくばバドレックスVMAX SA HR", "ブリザポス騎乗の迫力SAイラストでコレクター人気が極めて高い"), ("はくばバドレックスV SA SR", "氷原を駆けるSAイラストが美しくVMAXに次ぐ高額カード"), ("基本水エネルギー UR", "全面ゴールド仕様のURエネルギーで汎用性とコレクション性を兼備")]),
    MasterProduct("ss", 'S&S 拡張パック「漆黒のガイスト」', 4950, "2021-04-23",
                  desc="こくばバドレックスVMAXが目玉。白銀のランスと同時発売。",
                  keywords=["漆黒のガイスト", "漆黒"],
                  hit_cards=[("こくばバドレックスVMAX SA HR", "スペクタクルVMAXのSAイラストが幻想的でパック最高額カード"), ("カトレア SR", "人気女性サポーターで美麗イラストによりコレクター需要が非常に高い"), ("ゼラオラV SA SR", "躍動感あるSAイラストが評価されファンから根強い人気")]),
    MasterProduct("ss", 'S&S 強化拡張パック「双璧のファイター」', 4950, "2021-03-19",
                  desc="いちげき・れんげき両スタイルのポケモンが収録された強化拡張パック。",
                  keywords=["双璧のファイター"],
                  hit_cards=[("バシャーモVMAX SA", "買取約9万円で本弾の最高額。上位8枚のうち5枚をSAが占める層の厚い弾"), ("ガラルファイヤーV SA", "買取約4.5万円。同じガラル三鳥のサンダー(約6,500円)とは約6.9倍差"), ("カビゴン UR", "買取約2万円。URとしては破格の水準で3位に食い込む")]),
    MasterProduct("ss", 'S&S 拡張パック「連撃マスター」', 4950, "2021-01-22",
                  desc="れんげきウーラオスVMAXが目玉。一撃マスターと同時発売。",
                  keywords=["連撃マスター", "連撃"],
                  hit_cards=[("れんげきウーラオスVMAX SA", "買取約7万円で本弾の最高額。BOX買取の約1.4倍に相当"), ("エンペルトV SA", "買取約1.3万円。1位とは約5.4倍差の一強型"), ("れんげきウーラオスV SA", "買取約3,300円。SAが3枚あっても価格は1位に一極集中する")]),
    MasterProduct("ss", 'S&S 拡張パック「一撃マスター」', 4950, "2021-01-22",
                  desc="いちげきウーラオスVMAXが目玉。連撃マスターと同時発売。",
                  keywords=["一撃マスター", "一撃"],
                  hit_cards=[("いちげきウーラオスVMAX SA", "買取約4.7万円。2位との差はわずか約1.2倍で当サイト追跡中もっとも拮抗した二強型"), ("バンギラスV SA", "買取約4万円。VのSAは通常VMAX SAの5〜19%だが本カードは約85%と例外的"), ("いちげきウーラオスV SA", "買取約4,000円。上位2枚と3位の間に約10倍の断層がある")]),
    MasterProduct("ss", 'S&S ハイクラスパック「シャイニースターV」', 5500, "2020-11-20",
                  desc="色違いポケモンを多数収録したハイクラスパック。リザードンVの色違いが高額。",
                  keywords=["シャイニースターV", "シャイニースター"],
                  hit_cards=[("マリィ SR", "さいとうなおき氏イラストで女性サポーターSR屈指の高額カード"), ("リザードンVMAX SSR", "色違いリザードンVMAXの黒い姿がコレクターに大人気"), ("リザードンV SSR", "色違いリザードンVで希少性とリザードン人気により高額")]),
    MasterProduct("ss", 'S&S 拡張パック「仰天のボルテッカー」', 4950, "2020-09-18",
                  desc="ピカチュウVMAXが目玉カード。2020年9月発売の拡張パック。",
                  keywords=["仰天のボルテッカー", "仰天", "ボルテッカー"],
                  hit_cards=[("ピカチュウVMAX HR", "買取約6.5万円。SAが存在しない2020年の弾で唯一BOX買取を上回った看板カード"), ("ピカチュウV SR", "買取約2.1万円。上位2枚をピカチュウが独占する"), ("ルリナ SR", "買取約4,000円。7位にはR(レア)のリザードンが入る珍しい構成")]),
    MasterProduct("ss", 'S&S 強化拡張パック「伝説の鼓動」', 4950, "2020-07-10",
                  desc="ザマゼンタの「アメイジングレア」が初登場した強化拡張パック。",
                  keywords=["伝説の鼓動"],
                  hit_cards=[("レックウザ A", "買取約1.5万円で本弾の最高額。アメイジングレア(A)が初登場した弾"), ("ジラーチ A", "買取約4,500円。上位6枚すべてをアメイジングレアが占める唯一の構成"), ("セレビィ A", "買取約3,500円。同じAでもザマゼンタ(約1,500円)とは10倍差")]),
    MasterProduct("ss", 'S&S 拡張パック「ムゲンゾーン」', 4950, "2020-06-05",
                  desc="ムゲンダイナVMAXが目玉。S&Sシリーズ初期の拡張パック。",
                  keywords=["ムゲンゾーン"],
                  hit_cards=[("キャプチャーエネルギー UR", "買取約1,700円で本弾の最高額。ポケモンでもトレーナーズでもない特殊エネルギーが1位"), ("ボーマンダVMAX HR", "買取約1,600円。上位8枚すべてが2,000円未満という当サイト屈指の天井の低さ"), ("ハッサムVMAX HR", "買取約1,000円。看板のムゲンダイナVMAX HRも同水準の約1,000円にとどまる")]),
    MasterProduct("ss", 'S&S 強化拡張パック「爆炎ウォーカー」', 4950, "2020-04-24",
                  desc="マルヤクデVMAXが目玉。強化拡張パック。2020年4月発売。",
                  keywords=["爆炎ウォーカー", "爆炎"],
                  hit_cards=[("サーナイトVMAX HR", "買取約3,500円で本弾の最高額。BOX買取¥42,000の約8.3%にとどまる"), ("ゴリランダー UR", "買取約1,500円。上位8枚すべてが4,000円未満"), ("バタフリーVMAX HR", "買取約1,400円。同じサーナイトでもスカーレットexのex SAR(約2.2万円)とは約6.3倍差")]),
    MasterProduct("ss", 'S&S 拡張パック「反逆クラッシュ」', 4950, "2020-03-06",
                  desc="ドラパルトVMAXが目玉カード。2020年3月発売の拡張パック。",
                  keywords=["反逆クラッシュ", "反逆"],
                  hit_cards=[("ボスの指令(サカキ) SR", "買取約1.9万円で本弾の最高額。ポケモンではなくトレーナーズが1位という珍しい弾"), ("ボスの指令(サカキ) HR", "買取約1.4万円。相手のベンチを呼び出す汎用サポートで実用需要が相場を支える"), ("ツールスクラッパー UR", "買取約2,500円。上位2枚との間に約7.6倍の断層がある")]),
    MasterProduct("ss", 'S&S 拡張パック「VMAXライジング」', 4950, "2020-02-07",
                  desc="VMAX進化が初登場した拡張パック。2020年2月発売。",
                  keywords=["VMAXライジング", "vmaxライジング", "VMAX ライジング"],
                  hit_cards=[("ソニア SR", "買取約1.6万円で本弾の最高額。2位のソニアHR(約2,300円)とは約7倍差の一強型"), ("ソニア HR", "買取約2,300円。同じソニアの別レアリティで2番手を占める"), ("大きなおまもり UR", "買取約1,400円。SA登場前の弾のため最高レアリティはSR/HR/UR止まり")]),
    MasterProduct("ss", 'S&S 拡張パック「ソード」', 4950, "2019-12-06",
                  desc="S&Sシリーズ最初の拡張パック。ザシアンVが目玉。シールドと同時発売。",
                  keywords=["ソードV", "ソード V"],
                  hit_cards=[("ザシアンV UR", "伝説ポケモンの全面ゴールドURで対戦でも活躍し高い需要"), ("ザシアンV SR", "剣を咥えた勇ましいSRイラストでザシアンファンに人気"), ("博士の研究 マグノリア博士 SR", "S&S初期の必須サポートSRでマグノリア博士の優しいイラストが好評")]),
    MasterProduct("ss", 'S&S 拡張パック「シールド」', 4950, "2019-12-06",
                  desc="S&Sシリーズ最初の拡張パック。ザマゼンタVが目玉。ソードと同時発売。",
                  keywords=["シールドV", "シールド V"],
                  hit_cards=[("マリィ SR", "初収録マリィSRでキャラ人気とイラストにより5万円超えの超高額"), ("マリィ HR", "マリィの虹色HR仕様でSRに次ぐ人気を誇る高額カード"), ("クイックボール UR", "全面ゴールドのUR汎用グッズで実用性とコレクション性を兼備")]),

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


# ポケカ用のマッチ設定（デフォルト）。値は従来のモジュール定数をそのまま束ねたもので、
# config 未指定時の挙動は改修前と完全に一致する。
POKEMON_CONFIG = MatchConfig(
    exclude_indicators=NON_POKEMON_INDICATORS,
    non_box_indicators=NON_BOX_INDICATORS,
    box_indicators=BOX_INDICATORS,
    single_card_indicators=SINGLE_CARD_INDICATORS,
    box_name_whitelist=BOX_NAME_WHITELIST,
    strong_single_indicators=STRONG_SINGLE_INDICATORS,
    no_shrink_indicators=NO_SHRINK_INDICATORS,
    noise_words=["BOX", "box", "Box", "シュリンク付", "シュリンク", "未開封",
                 "新品", "日本語版", "ポケモンカードゲーム", "ポケカ",
                 "1BOX", "1box", "1Box"],
    min_box_price=MIN_BOX_PRICE,
    abs_min_price=ABS_MIN_PRICE,
    max_box_price=MAX_BOX_PRICE,
    max_retail_ratio=MAX_RETAIL_RATIO,
    match_threshold=MATCH_THRESHOLD,
    enable_dx_disambiguation=True,
)


def normalize(text: str, noise_words: list[str] | None = None) -> str:
    """Normalize text for matching: NFKC + lowercase + strip symbols."""
    text = unicodedata.normalize("NFKC", text)
    # Remove common packaging words
    text = re.sub(r"[【】\[\]（）()「」『』\-\s]+", " ", text)
    # Remove common noise words（ゲーム別。未指定時はポケカのデフォルト）
    if noise_words is None:
        noise_words = POKEMON_CONFIG.noise_words
    for word in noise_words:
        text = text.replace(word, "")
    # case-insensitive matching用に小文字化
    return text.strip().lower()


def _keyword_match(scraped_name: str, product: MasterProduct,
                   config: MatchConfig) -> bool:
    """Check if any keyword from the product matches in the scraped name.

    店側の商品名には弾名の途中に空白が紛れることがある
    (例: 森森「ストームエメラル ダ BOX」)。空白を落とした形でも突き合わせる。
    """
    norm_name = normalize(scraped_name, config.noise_words)
    compact_name = norm_name.replace(" ", "")
    for kw in product.keywords:
        norm_kw = normalize(kw, config.noise_words)
        if not norm_kw:
            continue
        if norm_kw in norm_name or norm_kw.replace(" ", "") in compact_name:
            return True
    return False


def _is_single_card(name: str, config: MatchConfig) -> bool:
    """Check if the product name looks like a single card (not a BOX).

    Only returns True if no BOX indicators are present AND single card
    indicators are found.
    """
    # If any BOX indicator is present, it's not a single card
    for indicator in config.box_indicators:
        if indicator in name:
            return False

    # 既知のBOX製品名(VSTARユニバース等)は救済。ただしカートン/バラ等の
    # 明確な非BOX語が付く出品は従来どおり単品扱いで除外する。
    if any(bn in name for bn in config.box_name_whitelist):
        if not any(s in name for s in config.strong_single_indicators):
            return False

    # Check for single card indicators
    for indicator in config.single_card_indicators:
        if indicator in name:
            return True
    return False


def _extract_model_codes(text: str, model_re: re.Pattern) -> set[str]:
    """出品名/マスター名から型番を抽出して正規化した集合を返す。

    店により「UX-19」「UX19」「ＵＸ−１９」と表記が割れるため NFKC で正規化し、
    区切り文字を無視して ("UX", "19") を拾い "UX-19" 形式に揃える。
    """
    norm = unicodedata.normalize("NFKC", text)
    return {
        f"{m.group(1).upper()}-{m.group(2)}"
        for m in model_re.finditer(norm)
    }


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
    config: MatchConfig | None = None,
) -> None:
    """Match scraped items to master product list and set prices.

    Args:
        scraped_items: list of (product_name, price) tuples
        shop_id: the shop identifier (e.g., "morimori")
        products: master product list (uses MASTER_PRODUCTS if None)
        config: ゲーム別マッチ設定 (uses POKEMON_CONFIG if None)
    """
    if products is None:
        products = MASTER_PRODUCTS
    if config is None:
        config = POKEMON_CONFIG

    matched = set()

    # 型番優先マッチ(ベイブレード)。未指定のポケカ/ワンピでは None のままで、
    # 以降の型番判定は全てスキップされるため従来挙動と完全に一致する。
    model_re = (
        re.compile(config.model_code_pattern, re.I)
        if config.model_code_pattern else None
    )
    product_codes_cache: dict[int, set[str]] = {}
    if model_re:
        for product in products:
            product_codes_cache[id(product)] = _extract_model_codes(
                product.name + " " + " ".join(product.keywords), model_re,
            )

    for name, price in scraped_items:
        if price <= 0:
            continue

        # Skip items that are clearly single cards (not BOX)
        if _is_single_card(name, config):
            continue

        # Skip other-game products (ワンピ視点ならポケカ等、ポケカ視点ならワンピ等)
        if any(ind in name for ind in config.exclude_indicators):
            logger.debug("  SKIP (other game): %s = %d", name, price)
            continue

        # Skip non-BOX products (promo packs, file sets, cartons, etc.)
        if any(ind in name for ind in config.non_box_indicators):
            logger.debug("  SKIP (non-box): %s = %d", name, price)
            continue

        # Skip no-shrink-wrap items (prefer shrink-wrapped price)
        if any(ind in name for ind in config.no_shrink_indicators):
            logger.debug("  SKIP (no shrink): %s = %d", name, price)
            continue

        # Skip obviously-junk prices before matching. The real per-product floor
        # (min_box_price or product.min_price) is enforced after a match is found,
        # so cheap products like スタートデッキ100 aren't pre-filtered here.
        if price < config.abs_min_price:
            logger.debug("  SKIP (price too low): %s = %d", name, price)
            continue

        # Skip unreasonably high prices (likely single rare cards or errors)
        if price > config.max_box_price:
            logger.debug("  SKIP (price too high): %s = %d", name, price)
            continue

        best_product = None
        best_score = 0

        scraped_codes = _extract_model_codes(name, model_re) if model_re else set()

        for product in products:
            # Step 0: 型番判定(ベイブレードのみ)。商品名の表記揺れが激しく
            # ("UX-19" だけ、JANコードだけ等) 名前の類似度は当てにならないため、
            # 型番が両方にあるときはそれを正とする。
            if model_re:
                product_codes = product_codes_cache[id(product)]
                if product_codes and scraped_codes:
                    common = product_codes & scraped_codes
                    if not common:
                        # 型番が食い違う = 別商品が確定。fuzzyに落とさず除外する
                        continue
                    # UX-00 等は限定品の共通枠で中身が別物。型番一致だけでは
                    # 足りないので、名前(keywords)の一致を追加で要求する。
                    if all(c.split("-")[1] in config.model_code_ambiguous_numbers
                           for c in common):
                        if not _keyword_match(name, product, config):
                            continue
                    if 100 > best_score:
                        best_score = 100
                        best_product = product
                    continue

            # Step 1: Try keyword matching first (exact substring)
            if _keyword_match(name, product, config):
                # Handle disambiguation for products with same keywords
                # e.g., "ブラックボルト" matches both DX and non-DX
                if config.enable_dx_disambiguation and product.keywords and any(
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
            norm_name = normalize(name, config.noise_words)
            norm_product = normalize(product.name, config.noise_words)
            score = fuzz.token_sort_ratio(norm_name, norm_product)
            if score > best_score:
                best_score = score
                best_product = product

        if best_product and best_score >= config.match_threshold:
            # Enforce the per-product low-price floor (defaults to min_box_price).
            floor = best_product.min_price or config.min_box_price
            if price < floor:
                logger.debug(
                    "  SKIP (below floor %d): %s = %d", floor, name, price,
                )
                continue

            # Skip if price is unreasonably high relative to retail
            if best_product.retail_price > 0:
                ratio = price / best_product.retail_price
                if ratio > config.max_retail_ratio:
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
