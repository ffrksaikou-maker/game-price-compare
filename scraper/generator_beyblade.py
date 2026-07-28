"""ベイブレード版ページ(beyblade.html)を beyblade-template.html から生成する。

ポケカ側 generator.py / ワンピ側 generator_onepiece.py は無改修。
記事・個別商品ページは作らず、比較表1枚だけを出力する。
価格履歴は data/history_bey に保存し、前日比(y)に使う。
メルカリの売却相場(mercari.py が取得したキャッシュ)を f として同じ表に載せる。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import mercari
from .matcher import MasterProduct

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_BEY_DIR = PROJECT_ROOT / "data" / "history_bey"

# ベイブレードを扱っている4店のみ(ポケカ/ワンピの店舗リストとは別)
SHOP_IDS = ["morimori", "rudeya", "homura", "icchome"]
SHOP_NAMES = {
    "morimori": "森森", "rudeya": "ルデヤ",
    "homura": "ホムラ", "icchome": "一丁目",
}
CATEGORY_LABELS = {
    "ux": "UX (アルティメット)", "cx": "CX (カスタム)",
    "bx": "BX (ベーシック)", "limited": "限定品",
}
# 表示順(新しいライン順。テンプレの絞り込みボタンと揃える)
CATEGORY_ORDER = ["ux", "cx", "bx", "limited"]

SITE_URL = "https://pokeca-box-hikaku.com/beyblade"


def _slug(name: str) -> str:
    """型番ベースの安定slug(個別ページは作らないがデータキーとして持たせる)。"""
    m = re.search(r"(BX|UX|CX)-?(\d+)", name)
    if m:
        base = f"{m.group(1).lower()}-{int(m.group(2)):02d}"
        if m.group(2) == "00":
            # 00番台は同じ型番に複数商品があるので名前側で一意化する
            tail = re.sub(r"[^\wぁ-んァ-ヶ一-龠]+", "-", name[m.end():].strip().lower())
            return f"{base}-{tail.strip('-')[:24]}" if tail.strip("-") else base
        return base
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "item"


def save_history_bey(products: list[MasterProduct]) -> None:
    """当日のベイブレード価格スナップショットを保存(前日比用)。"""
    HISTORY_BEY_DIR.mkdir(parents=True, exist_ok=True)
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
    (HISTORY_BEY_DIR / f"{today}.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    logger.info("BEY history saved: %d products", len(snapshot))


def _sorted_products(products: list[MasterProduct]) -> list[MasterProduct]:
    """カテゴリ順に並べ、各カテゴリ内は発売日の新しい順にする。

    表は「UX→CX→BX→限定品」のグループ見出しを挟んで描画されるので、
    カテゴリを第1キーに保ったまま日付だけ降順にする。
    """
    order = {c: i for i, c in enumerate(CATEGORY_ORDER)}

    def key(p: MasterProduct):
        # "2026-07-11" -> -20260711。新しいほど小さくなるので昇順で新しい順になる。
        d = -int(p.release_date.replace("-", "")) if p.release_date else 0
        return (order.get(p.category, 99), d)

    return sorted(products, key=key)


def _product_js(products: list[MasterProduct], market: dict) -> str:
    """クライアント用 const P 配列を生成。

    f  = メルカリ直近30日の最高売却額
    fa = そのうち高値上位の平均 / fn = 平均に使った件数
    """
    prev_max: dict[str, int] = {}
    if HISTORY_BEY_DIR.exists():
        files = sorted(HISTORY_BEY_DIR.glob("*.json"))
        # 当日分は save_history_bey で書き済みなので直前(files[-2])が前日
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
        mk = market.get(p.name) or {}
        f = mk.get("price", 0)
        fa = mk.get("top_avg", 0)
        fn = mk.get("top_n", 0)
        lines.append(
            f'{{c:"{p.category}",n:"{name_esc}",s:"{_slug(p.name)}",'
            f'r:{p.retail_price},d:"{p.release_date}",y:{y},'
            f'f:{f},fa:{fa},fn:{fn},'
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
                "category": "ホビー / ベイブレードX",
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
        "name": "ベイブレードX 買取価格比較",
        "itemListElement": items,
    }
    website = {
        "@context": "https://schema.org", "@type": "WebSite",
        "name": "ベイブレード買取チェッカー",
        "url": SITE_URL,
    }
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム",
             "item": "https://pokeca-box-hikaku.com/"},
            {"@type": "ListItem", "position": 2, "name": "ベイブレード買取チェッカー",
             "item": SITE_URL},
        ],
    }
    return "\n".join(
        '<script type="application/ld+json">'
        + json.dumps(d, ensure_ascii=False) + "</script>"
        for d in (item_list, website, breadcrumb)
    )


def _ai_summary(products: list[MasterProduct], market: dict) -> str:
    priced = [p for p in products if p.prices]
    n = len(priced)
    m = len([p for p in priced if (market.get(p.name) or {}).get("price")])
    return (f'<div style="display:none" aria-hidden="true">'
            f'ベイブレードX {n}商品の買取価格を森森・ルデヤ・ホムラ・一丁目の4店舗で横断比較。'
            f'うち{m}商品はメルカリの売却相場(中央値)も併記し、買取とフリマのどちらが'
            f'高いかを比較できる。UX・CX・BXの各ラインと限定品を毎日自動更新。</div>')


def _append_beyblade_sitemap() -> None:
    """sitemap.xml に /beyblade を追記する(冪等)。

    ポケカ generator が sitemap.xml を毎回全書換えするため、その後に呼ぶ前提。
    """
    path = PROJECT_ROOT / "sitemap.xml"
    if not path.exists():
        logger.warning("sitemap.xml not found; skip beyblade entry")
        return
    xml = path.read_text(encoding="utf-8")
    if "/beyblade" in xml:
        return
    today = datetime.now(JST).strftime("%Y-%m-%d")
    entry = (f"  <url>\n    <loc>{SITE_URL}</loc>\n"
             f"    <lastmod>{today}</lastmod>\n"
             f"    <changefreq>daily</changefreq>\n"
             f"    <priority>0.9</priority>\n  </url>\n")
    xml = xml.replace("</urlset>", entry + "</urlset>")
    path.write_text(xml, encoding="utf-8")
    logger.info("sitemap.xml: added %s", SITE_URL)


def generate_beyblade_html(products: list[MasterProduct],
                           market: dict | None = None) -> str:
    template_path = PROJECT_ROOT / "beyblade-template.html"
    output_path = PROJECT_ROOT / "beyblade.html"

    if market is None:
        market = mercari.load_cache()

    products = _sorted_products(products)
    save_history_bey(products)

    template = template_path.read_text(encoding="utf-8")
    update_date = datetime.now(JST).strftime("%Y/%m/%d %H:%M")

    html = template.replace("// {{PRODUCT_DATA}}", _product_js(products, market))
    html = html.replace("<!-- {{JSONLD}} -->", _jsonld(products))
    html = html.replace("<!-- {{AI_SUMMARY}} -->", _ai_summary(products, market))
    html = html.replace("{{UPDATE_DATE}}", update_date)

    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    _append_beyblade_sitemap()
    return html
