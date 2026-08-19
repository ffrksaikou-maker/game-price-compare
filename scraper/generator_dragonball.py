"""ドラゴンボール版ページ(dragonball.html)を dragonball-template.html から生成する。

ポケカ側 generator.py / ワンピ側 generator_onepiece.py / ベイ側
generator_beyblade.py は無改修。記事・個別商品ページは作らず、比較表1枚だけを
出力する。価格履歴は data/history_db に保存し、前日比(y)に使う。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .matcher import MasterProduct

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_DB_DIR = PROJECT_ROOT / "data" / "history_db"

# ドラゴンボールを扱っている4店のみ(ポケカ/ワンピの店舗リストとは別)。
# 一丁目・シンソク・海峡・オクはドラゴンボールの買取カテゴリ自体が無い。
SHOP_IDS = ["homura", "rudeya", "runto", "morimori"]
SHOP_NAMES = {
    "homura": "ホムラ", "rudeya": "ルデヤ",
    "runto": "ラントゥ", "morimori": "森森",
}
CATEGORY_LABELS = {
    "fb": "ブースターパック (FB)", "sb": "MANGA BOOSTER (SB)",
    "st": "STORY BOOSTER (ST)", "dv": "スーパーダイバーズ",
}
# 表示順(掲載数の多いブースターを先頭に。テンプレの絞り込みボタンと揃える)
CATEGORY_ORDER = ["fb", "sb", "st", "dv"]

SITE_URL = "https://pokeca-box-hikaku.com/dragonball"

_CODE_RE = re.compile(r"(FB|SB|ST)[\s\-‐－]?(\d{2})")


def _slug(name: str) -> str:
    """弾番号ベースの安定slug(個別ページは作らないがデータキーとして持たせる)。"""
    m = _CODE_RE.search(name)
    if m:
        return f"{m.group(1).lower()}-{int(m.group(2)):02d}"
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "item"


def save_history_db(products: list[MasterProduct]) -> None:
    """当日のドラゴンボール価格スナップショットを保存(前日比用)。"""
    HISTORY_DB_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(JST).strftime("%Y-%m-%d")
    snapshot = []
    for p in products:
        if not p.prices:
            continue
        snapshot.append({
            "name": p.name,
            "category": p.category,
            "retail_price": p.retail_price,
            "max_price": max(p.prices.values()),
            "prices": dict(p.prices),
        })
    (HISTORY_DB_DIR / f"{today}.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    logger.info("DB history saved: %d products", len(snapshot))


def _sorted_products(products: list[MasterProduct]) -> list[MasterProduct]:
    """カテゴリ順に並べ、各カテゴリ内は発売日の新しい順にする。

    表は「FB→SB→ST→ダイバーズ」のグループ見出しを挟んで描画されるので、
    カテゴリを第1キーに保ったまま日付だけ降順にする。同日発売が並んだときに
    順序が定義順で揺れないよう、第2キーに弾番号の降順を入れる。
    """
    order = {c: i for i, c in enumerate(CATEGORY_ORDER)}

    def key(p: MasterProduct):
        # "2026-09-12" -> -20260912。新しいほど小さくなるので昇順で新しい順になる。
        d = -int(p.release_date.replace("-", "")) if p.release_date else 0
        m = _CODE_RE.search(p.name)
        num = -int(m.group(2)) if m else 0
        return (order.get(p.category, 99), d, num)

    return sorted(products, key=key)


def _product_js(products: list[MasterProduct]) -> str:
    """クライアント用 const P 配列を生成。y は前日の最高買取額。"""
    prev_max: dict[str, int] = {}
    if HISTORY_DB_DIR.exists():
        files = sorted(HISTORY_DB_DIR.glob("*.json"))
        # 当日分は save_history_db で書き済みなので直前(files[-2])が前日
        if len(files) >= 2:
            try:
                prev = json.loads(files[-2].read_text(encoding="utf-8"))
                prev_max = {x["name"]: x.get("max_price", 0) for x in prev}
            except (json.JSONDecodeError, OSError):
                pass

    lines = ["const P=["]
    current_cat = None
    for p in products:
        if p.category != current_cat:
            current_cat = p.category
            lines.append(f"// ===== {current_cat.upper()} =====")
        prices = {sid: p.prices.get(sid, 0) for sid in SHOP_IDS}
        name_esc = p.name.replace("\\", "\\\\").replace('"', '\\"')
        price_parts = ",".join(f"{sid}:{prices[sid]}" for sid in SHOP_IDS)
        y = prev_max.get(p.name, 0)
        lines.append(
            f'{{c:"{p.category}",n:"{name_esc}",s:"{_slug(p.name)}",'
            f'r:{p.retail_price},d:"{p.release_date}",y:{y},'
            f'p:{{{price_parts}}}}},'
        )
    lines.append("];")
    return "\n".join(lines)


def _jsonld(products: list[MasterProduct]) -> str:
    priced = [p for p in products if p.prices]
    items = []
    for i, p in enumerate(priced, 1):
        values = [v for v in p.prices.values() if v > 0]
        if not values:
            continue
        items.append({
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "Product",
                "name": p.name,
                "category": "トレーディングカード / ドラゴンボールカード",
                "offers": {
                    "@type": "AggregateOffer",
                    "priceCurrency": "JPY",
                    "highPrice": max(values),
                    "lowPrice": min(values),
                    "offerCount": len(values),
                },
            },
        })
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "ドラゴンボールカード 未開封BOX 買取価格比較",
        "itemListElement": items,
    }
    website = {
        "@context": "https://schema.org", "@type": "WebSite",
        "name": "ドラゴンボール買取チェッカー",
        "url": SITE_URL,
    }
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム",
             "item": "https://pokeca-box-hikaku.com/"},
            {"@type": "ListItem", "position": 2, "name": "ドラゴンボール買取チェッカー",
             "item": SITE_URL},
        ],
    }
    return "\n".join(
        '<script type="application/ld+json">'
        + json.dumps(d, ensure_ascii=False) + "</script>"
        for d in (item_list, website, breadcrumb)
    )


def _append_dragonball_sitemap() -> None:
    """sitemap.xml に /dragonball を追記する(冪等)。

    ポケカ generator が sitemap.xml を毎回全書換えするため、その後に呼ぶ前提。
    """
    path = PROJECT_ROOT / "sitemap.xml"
    if not path.exists():
        logger.warning("sitemap.xml not found; skip dragonball entry")
        return
    xml = path.read_text(encoding="utf-8")
    if "/dragonball" in xml:
        return
    today = datetime.now(JST).strftime("%Y-%m-%d")
    entry = (f"  <url>\n    <loc>{SITE_URL}</loc>\n"
             f"    <lastmod>{today}</lastmod>\n"
             f"    <changefreq>daily</changefreq>\n"
             f"    <priority>0.9</priority>\n  </url>\n")
    xml = xml.replace("</urlset>", entry + "</urlset>")
    path.write_text(xml, encoding="utf-8")
    logger.info("sitemap.xml: added %s", SITE_URL)


def generate_dragonball_html(products: list[MasterProduct]) -> str:
    template_path = PROJECT_ROOT / "dragonball-template.html"
    output_path = PROJECT_ROOT / "dragonball.html"

    products = _sorted_products(products)
    save_history_db(products)

    template = template_path.read_text(encoding="utf-8")
    update_date = datetime.now(JST).strftime("%Y/%m/%d %H:%M")

    html = template.replace("// {{PRODUCT_DATA}}", _product_js(products))
    html = html.replace("<!-- {{JSONLD}} -->", _jsonld(products))
    html = html.replace("<!-- {{AI_SUMMARY}} -->", "")
    html = html.replace("{{UPDATE_DATE}}", update_date)

    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    _append_dragonball_sitemap()
    return html
