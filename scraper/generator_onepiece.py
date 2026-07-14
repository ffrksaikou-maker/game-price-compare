"""ONE PIECE版ページ(onepiece.html)を onepiece-template.html から生成する軽量ジェネレータ。

ポケカ側 generator.py は無改修のまま。共通の店舗ID(SHOP_IDS)だけ流用する。
最小構成のため個別BOXページ・記事・ランキングは生成しない(プレースホルダは空で埋める)。
価格履歴は data/history_op に保存し、前日比(y)に使う。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .generator import SHOP_IDS
from .matcher import MasterProduct

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_OP_DIR = PROJECT_ROOT / "data" / "history_op"


def _slug(name: str) -> str:
    """弾番号ベースの簡易slug(個別ページは作らないが安定値として付与)。"""
    m = re.search(r"(OP|EB|PRB|ST)-?(\d+)", name)
    if m:
        return f"{m.group(1).lower()}-{int(m.group(2)):02d}"
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "box"


def save_history_op(products: list[MasterProduct]) -> None:
    """当日のワンピ価格スナップショットを保存(前日比・将来のグラフ用)。"""
    HISTORY_OP_DIR.mkdir(parents=True, exist_ok=True)
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
    (HISTORY_OP_DIR / f"{today}.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("OP history saved: %d products", len(snapshot))


def _product_js(products: list[MasterProduct]) -> str:
    """クライアント用 const P 配列を生成(カテゴリ順にグループ化)。"""
    prev_max: dict[str, int] = {}
    if HISTORY_OP_DIR.exists():
        files = sorted(HISTORY_OP_DIR.glob("*.json"))
        # 当日分は save_history_op で既に書かれているので直前(files[-2])が前日
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
            f'r:{p.retail_price},d:"{p.release_date}",y:{y},p:{{{price_parts}}}}},'
        )
    lines.append("];")
    return "\n".join(lines)


def _jsonld(products: list[MasterProduct]) -> str:
    priced = [p for p in products if p.prices]
    items = []
    for i, p in enumerate(priced, 1):
        max_price = max(p.prices.values())
        items.append({
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "Product",
                "name": p.name,
                "category": "トレーディングカードゲーム / ONE PIECEカードゲーム / 未開封BOX",
                "offers": {
                    "@type": "AggregateOffer",
                    "priceCurrency": "JPY",
                    "highPrice": max_price,
                    "lowPrice": min(v for v in p.prices.values() if v > 0),
                    "offerCount": len([v for v in p.prices.values() if v > 0]),
                },
            },
        })
    data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "ONE PIECEカード 未開封BOX 買取価格比較",
        "itemListElement": items,
    }
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False) + "</script>")


def _ai_summary(products: list[MasterProduct]) -> str:
    priced = [p for p in products if p.prices]
    n = len(priced)
    return (f'<div style="display:none" aria-hidden="true">'
            f'ONE PIECEカードゲーム未開封BOX {n}商品の買取価格を最大11店舗で横断比較。'
            f'通常ブースター(OP)・エクストラブースター(EB)・プレミアムブースター(PRB)・'
            f'スタートデッキを毎日自動更新。</div>')


def generate_onepiece_html(products: list[MasterProduct]) -> str:
    template_path = PROJECT_ROOT / "onepiece-template.html"
    output_path = PROJECT_ROOT / "onepiece.html"

    save_history_op(products)

    template = template_path.read_text(encoding="utf-8")
    update_date = datetime.now(JST).strftime("%Y/%m/%d %H:%M")

    html = template.replace("// {{PRODUCT_DATA}}", _product_js(products))
    html = html.replace("<!-- {{JSONLD}} -->", _jsonld(products))
    html = html.replace("<!-- {{AI_SUMMARY}} -->", _ai_summary(products))
    html = html.replace("{{UPDATE_DATE}}", update_date)
    html = html.replace("<!-- {{BLOG_LINKS}} -->", "")
    html = html.replace("<!-- {{RANKING_SUMMARY}} -->", "")

    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)
    return html
