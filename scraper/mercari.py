"""メルカリの売却済み(sold_out)相場を取得する。

買取価格より実売(フリマ)の方が高いことが多いため、比較表に「フリマ相場」列を
出すためのデータ源。検索ページを Playwright で開き、内部APIの応答
(api.mercari.jp/v2/entities:search)をそのまま傍受する。DOMのクラス名は変わり
やすいがAPIのフィールド名(name/price/status)は安定しているため。

出品名のノイズ(パーツ単体・バラ売り・複数商品のまとめ売り・箱なし)は相場を大きく
歪めるので、型番が1つだけ載っている出品に絞り、さらに除外語で落とす。

採用するのは「直近30日の最高売却額」と「高値上位の平均」。買取価格と並べる目的は
"フリマならいくらまで狙えるか"を示すことなので、中央値だと本体が高く売れた実績が
バラ売りの山に埋もれてしまう。最高値1点だけでは外れ値に見えるため上位平均を併記する。
"""

from __future__ import annotations

import json
import logging
import math
import re
import statistics
import time
import unicodedata
import urllib.parse as up
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .matcher import MasterProduct

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "data" / "mercari_beyblade.json"

SEARCH_URL = (
    "https://jp.mercari.com/search?keyword={kw}&status=sold_out"
    "&sort=created_time&order=desc"
)
MODEL_RE = re.compile(r"(BX|UX|CX)[\s\-‐－]?(\d{2})", re.I)

# 商品本体ではない出品を落とす語。パーツ取り・箱なし・まとめ売りが対象。
# 「のみ」はセット商品のバラ売り(「バトルエントリーセットU スタジアムのみ」等)を
# 落とすために必須。これが無いと本体の半額以下の出品が中央値を大きく引き下げる。
EXCLUDE_WORDS = [
    "のみ", "ビット", "ラチェット", "パーツ", "部品", "抜粋", "取り",
    "箱無", "箱なし", "空箱", "説明書", "ステッカー", "シール",
    "ジャンク", "欠品", "訳あり", "破損", "傷", "使用済", "開封済", "中古",
    "まとめ", "セット売り", "詰め合わせ", "福袋", "同梱",
    "コンプリート", "セミコンプ", "コンプ", "全種",
]
# 複数個の同梱を示す表記。単品相場を歪めるので落とす。
# 判定は NFKC 正規化後の名前に対して行うので全角数字(「８個」)も拾える。
EXCLUDE_PATTERNS = [
    re.compile(r"他\s*\d+\s*[つ点個種箱]"),         # 「他2つ」「他4種」
    re.compile(r"\d+\s*[点個箱種]\s*(セット|まとめ)"),  # 「5点セット」「2箱セット」
    re.compile(r"[×x]\s*\d+\s*(個|点|箱)\s*$"),     # 末尾の「×3個」
    re.compile(r"\d+\s*個"),                       # 「2個」「6個セット」
    re.compile(r"\d+\s*箱"),                       # 「2箱」
    re.compile(r"\d+\s*セット"),                    # 「2セット」(先頭にも来る)
    re.compile(r"\d+\s*点"),                       # 「3点」
]
# 1商品として成立している最低件数。これ未満は相場と呼べないので出さない。
MIN_SAMPLES = 3
# 中央値のこの倍率を超える価格は、フィルタを抜けたまとめ売り等とみなして除外する。
# 採用値は「残った中の最高値」なので、この上限が異常値に対する防波堤になる。
MAX_VS_MEDIAN = 2.5
# 高値の平均を取る範囲。最高値1点だけだと外れ値に見えるため併記する。
# 件数固定にすると、出品の少ない商品(古い型番など)で下位の安値まで平均に入り、
# 実質中央値になってしまう。母数に対する割合で決めることで高値帯だけを見る。
TOP_RATIO = 0.2
# ただし割合だけだと母数が小さいとき1件になり最高値と同値になるので下限を置く。
MIN_TOP = 3
# 売却からの経過日数の上限。古い取引は現在の相場を表さないため直近1か月に限る。
# APIの updated は取引成立で更新されるため、売却日時として扱う
# (created は出品日時なので、長く売れ残った商品では実態とずれる)。
MAX_AGE_DAYS = 30
# 同時に走らせるブラウザ数。上げすぎるとメルカリ側が応答を返さなくなるため、
# 1ワーカーあたりのアクセス間隔(pause_sec)は据え置いたまま台数だけ増やす。
DEFAULT_WORKERS = 3


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def _codes(text: str) -> set[str]:
    return {f"{m.group(1).upper()}-{m.group(2)}" for m in MODEL_RE.finditer(_norm(text))}


def search_keyword(product: MasterProduct) -> str:
    """商品ごとのメルカリ検索キーワード。

    通常品は型番が最も効く。限定品(00番台)は型番が共通で絞れないため、
    表示名から型番と装飾を落とした主要語で引く。
    """
    if product.category == "limited":
        name = re.sub(r"^(BX|UX|CX)-\d{2}\s*", "", product.name)
        name = re.sub(r"メタルコート[:：].*$", "", name).strip()
        return f"ベイブレードX {name}"
    code = product.name.split()[0]
    return f"ベイブレードX {code}"


def _is_recent(item: dict, now: float) -> bool:
    """売却が直近 MAX_AGE_DAYS 以内か。判定できない出品は採用しない。"""
    ts = item.get("updated") or item.get("created")
    try:
        return (now - int(ts)) <= MAX_AGE_DAYS * 86400
    except (TypeError, ValueError):
        return False


def main_token(product: MasterProduct) -> str | None:
    """商品名の主要語(型番と英数サフィックスを除いた日本語部分)。

    「UX-04 バトルエントリーセットU」→「バトルエントリーセット」。
    型番が一致していても別商品(「UX-04 スターター」等)を掴まないための照合用。
    """
    name = re.sub(r"^(BX|UX|CX)-\d{2}\s*", "", product.name)
    name = re.sub(r"メタルコート[:：].*$", "", name).strip()
    m = re.match(r"^([ァ-ヶー一-龠ぁ-ん]{3,})", name)
    return m.group(1) if m else None


def build_token_index(products: list[MasterProduct]) -> set[str]:
    """他商品の混在を検出するための、商品を一意に指す主要語の集合。

    「ランダムブースター」のように複数商品が共有する語は判定に使えないため除く。
    """
    counts: dict[str, int] = {}
    for p in products:
        t = main_token(p)
        if t:
            counts[t] = counts.get(t, 0) + 1
    return {t for t, c in counts.items() if c == 1}


def _is_relevant(item_name: str, product: MasterProduct,
                 other_tokens: frozenset[str] | set[str] = frozenset()) -> bool:
    """出品が対象商品そのものか判定する。"""
    name = _norm(item_name)
    if any(w in name for w in EXCLUDE_WORDS):
        return False
    if any(p.search(name) for p in EXCLUDE_PATTERNS):
        return False
    # 「ベイブレードx2サムライセイバー」のような密着表記の個数指定。
    # 型番を先に除いてから見ないと「UX03」の "X0" を個数と誤認する。
    # スペース付き(「ベイブレードX 5-60K」)は商品名の一部なので密着のみ対象。
    if re.search(r"[×x]\d", MODEL_RE.sub("", name)):
        return False

    # 別商品の名前が併記されている出品は抱き合わせ売り。型番が1つでも本体価格では
    # ないため除外する(例:「バレットグリフォン・ドランストライクBX-49」)。
    own = main_token(product)
    if any(t in name for t in other_tokens if t != own):
        return False

    codes = _codes(name)
    if product.category == "limited":
        # 限定品は型番で特定できないので、名前のキーワードが入っていることを要求
        if not any(_norm(kw) in name for kw in product.keywords):
            return False
        # 他の型番が混ざる出品(まとめ売り)は除外
        if len(codes) > 1:
            return False
        return True

    want = _codes(product.name)
    if not want:
        return False
    # 型番がちょうど1つで、それが対象商品であること(複数型番=まとめ売り)
    if len(codes) != 1 or codes != want:
        return False
    # 型番が同じでも中身が違う出品があるため、商品名の主要語も要求する
    token = main_token(product)
    return token is None or token in name


def _summarize(prices: list[int]) -> dict | None:
    """高値(最高売却額)と高値上位の平均をまとめて返す。

    中央値ではなく高値側を見るのは、「フリマならいくらまで狙えるか」を買取価格と
    並べたいため。最高値1点だけだと外れ値に振り回されるので、上位 TOP_RATIO の
    平均を併記して相場感を担保する。素の最大値がフィルタを抜けたまとめ売りに
    ならないよう、中央値の MAX_VS_MEDIAN 倍を超える価格は先に捨てる。
    """
    if len(prices) < MIN_SAMPLES:
        return None
    med = statistics.median(prices)
    kept = sorted((p for p in prices if p <= med * MAX_VS_MEDIAN), reverse=True)
    if not kept:
        return None
    n = max(MIN_TOP, math.ceil(len(kept) * TOP_RATIO))
    top = kept[:n]
    return {
        "price": kept[0],
        "top_avg": int(round(statistics.mean(top))),
        "top_n": len(top),
        "samples": len(prices),
        "median": int(med),
    }


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("mercari: cache load failed: %s", e)
    return {}


def save_cache(data: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8",
    )


def _search_once(ctx, keyword: str, wait_ms: int) -> list[dict] | None:
    """検索を1回実行し、傍受した商品リストを返す。取得できなければ None。"""
    captured: list[dict] = []
    page = ctx.new_page()

    def on_response(resp):
        if "entities:search" not in resp.url:
            return
        try:
            captured.append(resp.json())
        except Exception:
            pass

    page.on("response", on_response)
    try:
        # 固定待ちだと応答が遅いときに取りこぼすため、検索APIの応答自体を待つ。
        with page.expect_response(
            lambda r: "entities:search" in r.url, timeout=wait_ms + 20000,
        ):
            page.goto(SEARCH_URL.format(kw=up.quote(keyword)),
                      wait_until="domcontentloaded", timeout=60000)
        # 応答本文の読み取り(on_response)が終わるまで少しだけ待つ
        page.wait_for_timeout(1500)
    except Exception as e:
        logger.warning("mercari: %s search failed: %s", keyword, e)
        page.close()
        return None
    page.close()

    items: list[dict] = []
    for payload in captured:
        items.extend(payload.get("items") or [])
    return items or None


def _fetch_chunk(products: list[MasterProduct], other_tokens: set[str],
                 headless: bool, wait_ms: int, pause_sec: float) -> dict:
    """担当分の商品を1ブラウザで順に処理する。

    other_tokens は「他商品の名前が混ざった出品」を弾く判定に使うため、
    分割前の全商品から作ったものを受け取る(担当分だけでは判定が緩む)。
    """
    from playwright.sync_api import sync_playwright

    result: dict[str, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            ctx = browser.new_context(
                viewport={"width": 1400, "height": 1000}, locale="ja-JP",
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36"),
            )
            for idx, product in enumerate(products):
                kw = search_keyword(product)
                # 連続アクセスで応答が返らなくなるため、成否に関わらず間隔を空ける
                if idx:
                    time.sleep(pause_sec)
                # 商品ごとにページを作り直す。1枚を使い回すと前の検索の応答が
                # 次のループに紛れ込み(遅延到着)、別商品の価格を拾ってしまう。
                items = _search_once(ctx, kw, wait_ms)
                if items is None:
                    items = _search_once(ctx, kw, wait_ms + 4000)
                if not items:
                    logger.warning("mercari: %s -> API応答なし", kw)
                    continue

                now = time.time()
                prices = [
                    int(it["price"]) for it in items
                    if it.get("price") and it.get("name")
                    and _is_recent(it, now)
                    and _is_relevant(it["name"], product, other_tokens)
                ]
                summary = _summarize(prices)
                if summary is None:
                    logger.info(
                        "mercari: %s -> 有効%d件(不足) / 全%d件",
                        kw, len(prices), len(items),
                    )
                    continue

                summary["keyword"] = kw
                summary["period_days"] = MAX_AGE_DAYS
                result[product.name] = summary
                logger.info(
                    "mercari: %s -> 高値 %d円 (上位%d件平均 %d / 中央値%d / %d件中)",
                    kw, summary["price"], summary["top_n"], summary["top_avg"],
                    summary["median"], len(items),
                )

            ctx.close()
        finally:
            browser.close()

    return result


def fetch(products: list[MasterProduct], headless: bool = True,
          wait_ms: int = 6000, pause_sec: float = 2.5,
          workers: int = DEFAULT_WORKERS) -> dict:
    """各商品のフリマ相場を取得して {商品名: {...}} を返す。

    取得に失敗した商品は結果に含めない(呼び出し側が前回キャッシュで補完する)。
    1商品あたり十数秒かかるため、商品を workers 本のブラウザに振り分けて並行に
    処理する。同一ブラウザ内での連続アクセス間隔(pause_sec)は各ワーカーが維持する。
    """
    other_tokens = build_token_index(products)
    workers = max(1, min(workers, len(products)))
    if workers == 1:
        return _fetch_chunk(products, other_tokens, headless, wait_ms, pause_sec)

    # ストライド分割。前半/後半で分けると型番の新旧が偏り、負荷も偏るため
    chunks = [products[i::workers] for i in range(workers)]
    logger.info(
        "mercari: %d商品を%d並列で取得 (各%d件前後)",
        len(products), workers, len(chunks[0]),
    )
    merged: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_fetch_chunk, c, other_tokens, headless, wait_ms, pause_sec)
            for c in chunks if c
        ]
        for f in as_completed(futures):
            try:
                merged.update(f.result())
            except Exception as e:
                # 1ワーカーが落ちても残りの取得結果は使う
                logger.error("mercari: worker failed: %s", e)
    return merged


def fetch_with_cache(products: list[MasterProduct], **kwargs) -> dict:
    """取得を試み、失敗した商品は前回キャッシュの値で補完する。"""
    cache = load_cache()
    fresh = fetch(products, **kwargs)
    merged = dict(cache)
    merged.update(fresh)
    if fresh:
        save_cache(merged)
    logger.info(
        "mercari: %d件取得 / キャッシュ込み %d件", len(fresh), len(merged),
    )
    return merged
