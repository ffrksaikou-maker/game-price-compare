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
NON_POKEMON_INDICATORS = [
    "ONE PIECE", "ワンピース", "遊戯王", "デュエル・マスターズ",
    "ドラゴンボール", "ヴァイスシュヴァルツ", "バトルスピリッツ",
    "ヴァンガード", "ウィクロス",
]

# Non-BOX Pokemon products to exclude
NON_BOX_INDICATORS = [
    "プロモカードパック", "カードファイルセット", "カードファイル", "ファイルセット",
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


# Master product list - canonical names and keywords for matching
MASTER_PRODUCTS: list[MasterProduct] = [
    # ===== MEGA (新しい順) =====
    MasterProduct("mega", 'MEGA 拡張パック「ストームエメラルダ」', 6000, "2026-07-31",
                  desc="MEGAシリーズ最新弾。メガレックウザex収録、2026年7月31日発売(定価200円/BOX 6,000円)。伝説三巨頭レックウザのメガ進化が目玉。",
                  keywords=["ストームエメラルダ", "STORMEMERALDA", "STORM EMERALDA", "MEGA 拡張パック ストーム", "ストームエメラルド"],
                  hit_cards=[("メガレックウザex SAR", "パッケージ目玉。伝説三巨頭レックウザのSAR版。初動9万円予想、イラスト次第で10万円超も(メディア予想)"), ("メガレックウザex MUR", "MUR封入率約59BOXに1枚予想。初動8万円超が予想される最高レアリティ(メディア予想)"), ("レックウザex SAR", "メガ進化前のレックウザSAR。三巨頭人気でSARも高額化が見込まれる(メディア予想)")]),
    MasterProduct("mega", 'MEGA 拡張パック「アビスアイ」', 6000, "2026-05-22",
                  desc="MEGAシリーズ第5弾。値上げ後初の拡張パック(定価200円/BOX 6,000円)。メガダークライex収録、2026年5月22日発売。",
                  keywords=["アビスアイ", "ABYSSEYE", "ABYSS EYE", "MEGA 拡張パック アビス"],
                  hit_cards=[("メガダークライex MUR", "MUR封入率約45BOXに1枚予想。ダークライ人気で初動10万円超が予想される最注目カード(メディア予想)"), ("メガダークライex SAR", "パッケージ目玉のSAR版。ワザ『アビスアイ』は特殊状態なら残HP無視できぜつの強力効果"), ("カラマネロ SAR", "マーイーカ進化ポケモン。こんらん付与でメガダークライexと連携する特殊状態デッキの核")]),
    MasterProduct("mega", 'MEGA 拡張パック「ニンジャスピナー」', 5400, "2026-03-13",
                  desc="MEGAシリーズ第4弾。2026年3月発売。",
                  keywords=["ニンジャスピナー", "NINJASPINNER", "NINJA SPINNER"],
                  hit_cards=[("メガゲッコウガex MUR", "封入率約50BOXに1枚の最高レアリティ。ゲッコウガ人気で10万円超"), ("メガゲッコウガex SAR", "ゲッコウガの圧倒的キャラ人気でSARも高額化"), ("チラチーノex SAR", "可愛らしいイラストでコレクター人気が高い")]),
    MasterProduct("mega", 'MEGA 拡張パック「ムニキスゼロ」', 5400, "2026-01-23",
                  desc="MEGAシリーズ第3弾。2026年1月発売。",
                  keywords=["ムニキスゼロ", "ムニキス", "MUNIX"],
                  hit_cards=[("メガジガルデex MUR", "MUR封入率約70BOXに1枚。希少性で3万円超の高額カード"), ("メイのはげまし SAR", "BWの人気女性トレーナー。コレクター需要が非常に高い"), ("ニャースex SAR", "ロケット団のニャース人気とSARイラストの魅力で高騰")]),
    MasterProduct("mega", 'MEGA スタートデッキ100「バトルコレクション」', 891, "2025-12-19",
                  desc="100種類のデッキからランダムで1つ入っている構築済みデッキ。MUR仕様のメガリザードンYexが超高額。",
                  keywords=["バトルコレクション", "BATTLE COLLECTION"],
                  min_price=1500,  # 定価891円の格安デッキ。買取2200〜3200円なので3000円フィルタ対象外にする
                  hit_cards=[("メガリザードンYex MUR仕様", "封入率が極めて低い最高レアリティ(No.001・約1000個に1枚)。2026年5月の約100万円から反落し買取約94万円(6月初旬)"), ("ピカチュウex SAR仕様", "ピカチュウ人気×SAR仕様の希少性で30万円超"), ("リーリエのピッピex SAR仕様", "リーリエ人気キャラのSAR仕様で14万円超")]),
    MasterProduct("mega", 'MEGA ハイクラスパック「MEGAドリームex」', 5500, "2025-11-28",
                  desc="MEGAシリーズ初のハイクラスパック。2025年11月発売。",
                  keywords=["MEGAドリーム", "メガドリーム", "MEGA DREAM"],
                  hit_cards=[("メガゲンガーex SAR", "ゲンガーのキャラ人気が極めて高く、美麗SARイラストで高額化"), ("ピカチュウex SAR", "ポケモンの顔・ピカチュウのSAR。世界的な人気で常に高需要"), ("メガカイリューex MUR", "MUR封入率約50BOXに1枚。初動4万円超の希少カード")]),
    MasterProduct("mega", 'MEGA 拡張パック「インフェルノX」', 5400, "2025-09-26",
                  desc="MEGAシリーズ第2弾。メガリザードンXex SARが目玉カード。2025年9月発売。",
                  keywords=["インフェルノ", "インフェルノX", "INFERNO"],
                  hit_cards=[("メガリザードンXex MUR", "リザードン人気×MUR封入率50BOXに1枚で10万円超"), ("メガリザードンXex SAR", "リザードンの圧倒的人気でSARも8万円超の高額カード"), ("ヒカリ SAR", "DP主人公の初カード化。古澤あつし氏の美麗イラストで注目")]),
    MasterProduct("mega", 'MEGA 拡張パック「メガブレイブ」', 5400, "2025-08-01",
                  desc="MEGAシリーズ最初の拡張パック（2種同時発売）。2025年8月発売。",
                  keywords=["メガブレイブ", "MEGABRAVE"],
                  hit_cards=[("メガルカリオex MUR", "MUR封入率約50BOXに1枚。ルカリオ人気で6万円前後"), ("リーリエの決心 SAR", "歴代No.1人気トレーナー・リーリエのSAR。初動7万円超"), ("メガルカリオex SAR", "格闘ポケモン人気No.1のルカリオ。SARイラストも好評")]),
    MasterProduct("mega", 'MEGA 拡張パック「メガシンフォニア」', 5400, "2025-08-01",
                  desc="MEGAシリーズ最初の拡張パック（2種同時発売）。2025年8月発売。",
                  keywords=["メガシンフォニア", "MEGASYMPHONIA"],
                  hit_cards=[("メガサーナイトex MUR", "MUR封入率約50BOXに1枚。サーナイト人気で7万円超"), ("メガサーナイトex SAR", "サーナイトのキャラ人気とSARの美麗イラストで高額化"), ("アセロラのいたずら SAR", "ゴーストタイプ使いの人気女性トレーナー。コレクター需要大")]),

    # ===== SV (新しい順) =====
    MasterProduct("sv", 'SV 拡張パックDX「ブラックボルト」', 5800, "2025-06-06",
                  desc="ゼクロムexのBWR（ビーダブリューレア）を収録。DX版はカード枚数が多い特別仕様。",
                  keywords=["ブラックボルト", "BLACKVOLT", "拡張パックDXブラック"],
                  hit_cards=[("ゼクロムex BWR", "20BOXに1枚の激レア。BW時代を彷彿させる全体黒色デザイン"), ("ゼクロムex SAR", "伝説ポケモン・ゼクロムの封入率が低いSARで高額化"), ("Nの筋書き SAR", "BWの人気ライバル・Nの新規SAR。コレクター需要が高い")]),
    MasterProduct("sv", 'SV 拡張パックDX「ホワイトフレア」', 5800, "2025-06-06",
                  desc="レシラムexのBWR（ビーダブリューレア）を収録。DX版はカード枚数が多い特別仕様。",
                  keywords=["ホワイトフレア", "WHITEFLARE", "拡張パックDXホワイト"],
                  hit_cards=[("レシラムex BWR", "20BOXに1枚の激レア。白色レリーフ加工で立体感あるデザイン"), ("レシラムex SAR", "7種SARの中でも伝説ポケモンとして群を抜く人気"), ("トウコ SAR", "さいとうなおき氏イラスト。BW女性主人公の人気で高額化")]),
    MasterProduct("sv", 'SV 拡張パック「ブラックボルト」', 5400, "2025-06-06",
                  desc="イッシュ地方のポケモン156種がAR/SARで登場。ゼクロムexのBWRが目玉。",
                  keywords=["ブラックボルト", "BLACK BOLT"],
                  hit_cards=[("ゼクロムex BWR", "20BOXに1枚の激レア。BW時代を彷彿させる全体黒色デザイン"), ("ゼクロムex SAR", "伝説ポケモン・ゼクロムの封入率が低いSARで高額化"), ("Nの筋書き SAR", "BWの人気ライバル・Nの新規SAR。コレクター需要が高い")]),
    MasterProduct("sv", 'SV 拡張パック「ホワイトフレア」', 5400, "2025-06-06",
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
                  hit_cards=[("シロナのガブリアスex SAR", "シロナ×ガブリアスの人気コンビ。環境トップで3万円超"), ("ヒビキのホウオウex SAR", "金銀主人公ヒビキと伝説ポケモンの組み合わせで高額化"), ("ヒビキの冒険 SAR", "金銀主人公の新規サポートSAR。キャラ人気で需要が高い")]),
    MasterProduct("sv", 'SV 拡張パック「バトルパートナーズ」', 5400, "2025-01-24",
                  desc="SVシリーズの拡張パック。2025年1月発売。",
                  keywords=["バトルパートナーズ", "パートナーズ"],
                  hit_cards=[("リーリエのピッピex SAR", "歴代No.1人気トレーナー・リーリエ。封入率約3%で高額化"), ("ナンジャモのハラバリーex SAR", "SV人気No.1トレーナー・ナンジャモとの組み合わせ"), ("Nのゾロアークex SAR", "BWの人気キャラ・Nの相棒ポケモンでコレクター需要大")]),
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
                  hit_cards=[("ルチアのアピール SAR", "ホウエンNo.1コンテストアイドル。キャラ人気で1.7万円超"), ("ラティアスex SAR", "ラティアスARとイラストが繋がる設計。キャラ人気も高い"), ("ルチアのアピール SR", "SAR同様にルチアのキャラ人気でSRも高値で推移")]),
    MasterProduct("sv", 'SV 強化拡張パック「ステラミラクル」', 5400, "2024-07-19",
                  desc="テラパゴスexを収録した強化拡張パック。2024年7月発売。",
                  keywords=["ステラミラクル", "ステラ"],
                  hit_cards=[("タロ SAR", "新キャラクターのSARで最高額。可愛いイラストで人気"), ("テラパゴスex SAR", "SVシリーズの看板伝説ポケモン。ストーリー上の重要キャラ"), ("ブライア SAR", "DLCに登場する新キャラ。女性サポートSARで需要あり")]),
    MasterProduct("sv", 'SV 強化拡張パック「ナイトワンダラー」', 5400, "2024-06-07",
                  desc="キタカミの里がテーマ。モモワロウexが初収録された強化拡張パック。",
                  keywords=["ナイトワンダラー"],
                  hit_cards=[("キチキギスex SAR", "汎用ドロー特性で環境デッキに必須。封入率の低さで高額化"), ("カシオペア SAR", "スター団マジボスの正体。サイバー感あるイラストが好評"), ("力の砂時計 UR", "エネ加速グッズで汎用性が高く、URの封入率の低さで希少")]),
    MasterProduct("sv", 'SV 拡張パック「変幻の仮面」', 5400, "2024-04-26",
                  desc="オーガポンが4つの姿のexとして収録。ゼロの秘宝がテーマの拡張パック。",
                  keywords=["変幻の仮面", "変幻"],
                  hit_cards=[("ゼイユ SAR", "DLCキャラの人気×もりくら氏の美麗イラストで最高額"), ("なかよしポフィン UR", "ほぼ全デッキ4枚採用の必須グッズ。UR封入率が極めて低い"), ("スグリ SAR", "キタカミの里の人気キャラ。お面姿の可愛いイラストが好評")]),
    MasterProduct("sv", 'SV 拡張パック「クリムゾンヘイズ」', 5400, "2024-03-22",
                  desc="キタカミの里のポケモンやトレーナーが初収録された強化拡張パック。",
                  keywords=["クリムゾンヘイズ", "クリムゾン"],
                  hit_cards=[("ゲッコウガex SAR", "超人気ポケモン・ゲッコウガの低封入率SARで4万円超"), ("サザレ SAR", "碧の仮面の美人キャラ。ヒスイガーディとの連動イラストが人気"), ("スイレンのお世話 SAR", "アローラ人気トレーナー。川遊びの可愛いイラストで需要大")]),
    MasterProduct("sv", 'SV 拡張パック「ワイルドフォース」', 5400, "2024-01-26",
                  desc="「古代」のカードを中心に収録。サイバージャッジと同時発売。",
                  keywords=["ワイルドフォース", "ワイルド"],
                  hit_cards=[("タケルライコex SAR", "古代ライコウの高火力ワザが環境で活躍。封入率の低さで高額化"), ("マツバの確信 SAR", "金銀ジムリーダー×ゲンガーの組合せ。水谷恵氏イラストが人気"), ("ウガツホムラex SAR", "古代エンテイの姿。三聖獣SARの野性味あるイラストが好評")]),
    MasterProduct("sv", 'SV 拡張パック「サイバージャッジ」', 5400, "2024-01-26",
                  desc="「未来」のカードを中心に収録。ワイルドフォースと同時発売。",
                  keywords=["サイバージャッジ", "サイバー"],
                  hit_cards=[("ベルのまごころ SAR", "BW初カード化の人気キャラ。ムシャーナと昼寝する可愛いイラスト"), ("テツノカシラex SAR", "未来パラドックスポケモンの高レアリティSARで希少"), ("テツノイサハex SAR", "未来のビリジオン。メカニカルなデザインがコレクターに人気")]),
    MasterProduct("sv", 'SV ハイクラスパック「シャイニートレジャーex」', 5500, "2023-12-01",
                  desc="色違いポケモンを多数収録したハイクラスパック。大会で活躍した強力カードも再録。",
                  keywords=["シャイニートレジャー"],
                  hit_cards=[("ミュウex SAR", "幻ポケモンの圧倒的人気。8種SAR中で最高額の約5万円"), ("ナンジャモ SAR", "SV人気No.1キャラの新規イラスト。コレクター需要が非常に高い"), ("リザードンex SAR", "リザードンの圧倒的人気×環境最強デッキで高額化")]),
    MasterProduct("sv", 'SV 拡張パック「古代の咆哮」', 5400, "2023-10-27",
                  desc="古代のパラドックスポケモンが登場。トドロクツキexが目玉。未来の一閃と同時発売。",
                  keywords=["古代の咆哮", "古代"],
                  hit_cards=[("トドロクツキex SAR", "古代ボーマンダの姿。一撃きぜつワザと高HPで環境上位"), ("メロコ SAR", "炎デッキ必須のサポート。対戦需要とキャラ人気で高額化"), ("オーリム博士の気迫 SAR", "古代デッキのキーカード。環境での採用率が高く実用需要大")]),
    MasterProduct("sv", 'SV 拡張パック「未来の一閃」', 5400, "2023-10-27",
                  desc="未来のパラドックスポケモンが登場。テツノブジンexが目玉。古代の咆哮と同時発売。",
                  keywords=["未来の一閃", "未来"],
                  hit_cards=[("テツノブジンex SAR", "サーナイト×エルレイド融合の人気デザイン。対戦でも汎用性高い"), ("リップ SAR", "パルデアジムリーダー。江川あきら氏の妖艶なイラスト"), ("チルタリスex SAR", "ドラゴンタイプの美しいイラスト。コレクション人気が高い")]),
    MasterProduct("sv", 'SV 強化拡張パック「レイジングサーフ」', 5400, "2023-09-22",
                  desc="SVシリーズの強化拡張パック。2023年9月発売。",
                  keywords=["レイジングサーフ", "レイジング"],
                  hit_cards=[("パラソルおねえさん SAR", "森倉円氏の儚げな虹空イラストが絶賛。モブキャラ高騰の代表格"), ("サーフゴーex SAR", "環境トップデッキの主力カード。対戦需要で価格が安定"), ("チリ SAR", "パルデア四天王の美人キャラ。女性トレーナーSAR人気")]),
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
                  hit_cards=[("グルーシャ SAR", "ミステリアスな氷ジムリーダー。女性ファン中心にキャラ人気が高い"), ("パオジアンex SAR", "対戦環境で強力な氷タイプ。実用需要とSAR希少性で高額化"), ("すごいつりざお UR", "汎用グッズのUR。実用性の高さと低封入率でグッズ1位の高額")]),
    MasterProduct("sv", 'SV 強化拡張パック「トリプレットビート」', 5400, "2023-03-10",
                  desc="パルデア御三家（ニャオハ・ホゲータ・クワッス）のexが初登場した強化拡張パック。",
                  keywords=["トリプレットビート", "トリプレット"],
                  hit_cards=[("キハダ SAR", "SV人気女教師。GIDORA氏イラスト×低封入率で初動12万円の衝撃"), ("マスカーニャex SAR", "パルデア御三家で人気No.1。猫モチーフの可愛さで高額化"), ("ラウドボーンex SAR", "炎御三家の最終進化。歌うワニのユニークなデザインで人気")]),
    MasterProduct("sv", 'SV 拡張パック「スカーレットex」', 5400, "2023-01-20",
                  desc="SVシリーズ最初の拡張パック。コライドンexが目玉。バイオレットexと同時発売。",
                  keywords=["スカーレットex"],
                  hit_cards=[("サーナイトex SAR", "歴代屈指の人気ポケモン。買取約2万円でSV初期最高額"), ("ボタン SAR", "スター団ボスの正体。女性キャラSARの人気で高額化"), ("コライドンex SAR", "スカーレットの看板伝説。パッケージポケモンの威厳で需要大")]),
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
                  hit_cards=[("ギラティナV SA SR", "競技シーンでの高い需要とかっこいいSAイラスト"), ("プテラV SA SR", "塗壁氏の古代風イラストが海外で特に高評価"), ("おじょうさま SR", "可愛いイラストとエネ加速の汎用性で安定人気")]),
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
                  hit_cards=[("ユウリ SR", "剣盾女主人公のポケカ初登場でさいとうなおき氏イラスト"), ("アセロラの予感 SR", "SM屈指の人気キャラでリーリエに次ぐ女性トレーナー人気"), ("ガラルの仲間たち SR", "マリィ含むガラル代表キャラ集結の豪華イラスト")]),
    MasterProduct("ss", 'S&S 拡張パック「25th ANNIVERSARY COLLECTION」', 5500, "2021-10-22",
                  desc="ポケカ25周年記念パック。ミュウの25thプロモカードが付属。限定生産。",
                  keywords=["25thアニバーサリー", "25th ANNIVERSARY", "ANNIVERSARY COLLECTION"],
                  hit_cards=[("リザードン 25th プロモ", "初代リザードンの25周年仕様復刻で圧倒的コレクション価値"), ("お誕生日ピカチュウ 25th プロモ", "1998年旧裏プロモの復刻で名前記入欄付きの特別デザイン"), ("ミュウ UR", "25周年パック本体の最高レアでミュウの根強い人気")]),
    MasterProduct("ss", 'S&S 拡張パック「フュージョンアーツ」', 4950, "2021-09-24",
                  desc="ミュウVMAXが目玉。「フュージョン」スタイルが初登場した拡張パック。",
                  keywords=["フュージョンアーツ", "フュージョン"],
                  hit_cards=[("ミュウVMAX SA HR", "フュージョン技を全て使える強力性能と美麗SAイラスト"), ("ミュウV SA SR", "進化前としてのプレイ需要と初代人気ポケモンの相乗効果"), ("カミツレのきらめき SR", "BW人気ジムリーダーで女性サポートのコレクター需要")]),
    MasterProduct("ss", 'S&S 拡張パック「蒼空ストリーム」', 4950, "2021-07-09",
                  desc="レックウザVMAX SARが超高額カード。流通量が少なく価格が高騰。",
                  keywords=["蒼空ストリーム", "蒼空"],
                  hit_cards=[("レックウザVMAX SA HR", "伝説ドラゴンの圧倒的人気とHR廃止による希少価値"), ("レックウザV SA SR", "ヒガナとの共演SAで12〜20BOXに1枚の超低封入率"), ("サナ SR", "XYの人気キャラで快活な可愛さがファンに支持")]),
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
                  hit_cards=[("バシャーモVMAX SA HR", "パック唯一の1万円超えSAでダイナミックな炎の描写が人気"), ("ガラルファイヤーV SA SR", "ガラル三鳥の中でも特に人気が高くコレクション需要が高い"), ("クララ SR", "鎧の孤島のどくタイプ使い。キャラ人気とイラストが好評")]),
    MasterProduct("ss", 'S&S 拡張パック「連撃マスター」', 4950, "2021-01-22",
                  desc="れんげきウーラオスVMAXが目玉。一撃マスターと同時発売。",
                  keywords=["連撃マスター", "連撃"],
                  hit_cards=[("れんげきウーラオスVMAX SA HR", "水流の中を構えるSAイラストが圧巻でパック最高額カード"), ("モミ SR", "優しい雰囲気の美麗イラストで女性サポーターSRとして高額"), ("エンペルトV SA SR", "ペンギンポケモンの凛々しいSAイラストがファンに人気")]),
    MasterProduct("ss", 'S&S 拡張パック「一撃マスター」', 4950, "2021-01-22",
                  desc="いちげきウーラオスVMAXが目玉。連撃マスターと同時発売。",
                  keywords=["一撃マスター", "一撃"],
                  hit_cards=[("いちげきウーラオスVMAX SA HR", "力強い一撃スタイルのSAイラストで初動から3倍以上に高騰"), ("バンギラスV SA SR", "荒野を歩く迫力のSAイラストで初動から約5倍に高騰した人気カード"), ("いちげきウーラオスV SA SR", "武道の構えを取るSAイラストがいちげきファンに好評")]),
    MasterProduct("ss", 'S&S ハイクラスパック「シャイニースターV」', 5500, "2020-11-20",
                  desc="色違いポケモンを多数収録したハイクラスパック。リザードンVの色違いが高額。",
                  keywords=["シャイニースターV", "シャイニースター"],
                  hit_cards=[("マリィ SR", "さいとうなおき氏イラストで女性サポーターSR屈指の高額カード"), ("リザードンVMAX SSR", "色違いリザードンVMAXの黒い姿がコレクターに大人気"), ("リザードンV SSR", "色違いリザードンVで希少性とリザードン人気により高額")]),
    MasterProduct("ss", 'S&S 拡張パック「仰天のボルテッカー」', 4950, "2020-09-18",
                  desc="ピカチュウVMAXが目玉カード。2020年9月発売の拡張パック。",
                  keywords=["仰天のボルテッカー", "仰天", "ボルテッカー"],
                  hit_cards=[("ピカチュウVMAX HR", "キョダイマックスピカチュウの虹色HRでピカチュウ人気により高額"), ("ルリナ SR", "水タイプジムリーダーの美人キャラでイラスト人気が非常に高い"), ("サイトウ SR", "格闘ジムリーダーの凛々しいSRイラストがファンに好評")]),
    MasterProduct("ss", 'S&S 強化拡張パック「伝説の鼓動」', 4950, "2020-07-10",
                  desc="ザマゼンタの「アメイジングレア」が初登場した強化拡張パック。",
                  keywords=["伝説の鼓動"],
                  hit_cards=[("レックウザ AR", "初のアメイジングレアとして登場し虹色の特別仕様で希少性が高い"), ("オリーヴ SR", "人気女性キャラのSRイラストでコレクター需要が根強い"), ("オリーヴ HR", "オリーヴの虹色HR仕様でSRと並びパック上位の高額カード")]),
    MasterProduct("ss", 'S&S 拡張パック「ムゲンゾーン」', 4950, "2020-06-05",
                  desc="ムゲンダイナVMAXが目玉。S&Sシリーズ初期の拡張パック。",
                  keywords=["ムゲンゾーン"],
                  hit_cards=[("キャプチャーエネルギー UR", "全面ゴールドのUR特殊エネルギーで実用性とコレクション性が高い"), ("ネズ SR", "エール団リーダーのクールなSRイラストがキャラファンに人気"), ("ムゲンダイナV SR", "パックの看板ポケモンで禍々しいイラストがインパクト大")]),
    MasterProduct("ss", 'S&S 強化拡張パック「爆炎ウォーカー」', 4950, "2020-04-24",
                  desc="マルヤクデVMAXが目玉。強化拡張パック。2020年4月発売。",
                  keywords=["爆炎ウォーカー", "爆炎"],
                  hit_cards=[("サーナイトVMAX HR", "虹色HR仕様でサーナイトの根強いファン人気によりパック最高額"), ("ビッグパラソル UR", "全面ゴールドのURグッズで対戦での実用性もありコレクション向き"), ("ポケモンブリーダーの育成 SR", "育成をテーマにした温かいSRイラストがコレクターに好評")]),
    MasterProduct("ss", 'S&S 拡張パック「反逆クラッシュ」', 4950, "2020-03-06",
                  desc="ドラパルトVMAXが目玉カード。2020年3月発売の拡張パック。",
                  keywords=["反逆クラッシュ", "反逆"],
                  hit_cards=[("ボスの指令 サカキ SR", "初代ロケット団ボスの威厳あるSRで汎用サポートとして需要が高い"), ("ボスの指令 サカキ HR", "サカキの虹色HR仕様でSRに次ぐ高額カード"), ("オリーヴ SR", "人気女性キャラのSRイラストで複数パック収録でも安定して高額")]),
    MasterProduct("ss", 'S&S 拡張パック「VMAXライジング」', 4950, "2020-02-07",
                  desc="VMAX進化が初登場した拡張パック。2020年2月発売。",
                  keywords=["VMAXライジング", "vmaxライジング", "VMAX ライジング"],
                  hit_cards=[("ソニア SR", "さいとうなおき氏イラストのギャル系キャラでパック唯一の1万円超え"), ("ソニア HR", "ソニアの虹色HR仕様でSRに次ぐ高額カード"), ("モスノウ UR", "全面ゴールドのURポケモンで美しいデザインがコレクターに人気")]),
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
    # case-insensitive matching用に小文字化
    return text.strip().lower()


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

    # 既知のBOX製品名(VSTARユニバース等)は救済。ただしカートン/バラ等の
    # 明確な非BOX語が付く出品は従来どおり単品扱いで除外する。
    if any(bn in name for bn in BOX_NAME_WHITELIST):
        if not any(s in name for s in STRONG_SINGLE_INDICATORS):
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

        # Skip obviously-junk prices before matching. The real per-product floor
        # (MIN_BOX_PRICE or product.min_price) is enforced after a match is found,
        # so cheap products like スタートデッキ100 aren't pre-filtered here.
        if price < ABS_MIN_PRICE:
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
            # Enforce the per-product low-price floor (defaults to MIN_BOX_PRICE).
            floor = best_product.min_price or MIN_BOX_PRICE
            if price < floor:
                logger.debug(
                    "  SKIP (below floor %d): %s = %d", floor, name, price,
                )
                continue

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
