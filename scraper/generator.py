"""Generate index.html from template.html + price data."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .matcher import MasterProduct

logger = logging.getLogger(__name__)

# JST timezone
JST = timezone(timedelta(hours=9))

# Shop IDs in display order
SHOP_IDS = ["morimori", "homura", "icchome", "runto", "sommelier", "kaikyo", "shouten", "rudeya"]

# Blog articles (newest first) - 記事追加時はここに1行足すだけ
BLOG_ARTICLES = [
    {"url": "mercari-hikaku.html", "title": "メルカリ・スニダン・買取店どれが得？", "desc": "手数料・送料込みで3つの売却方法を徹底比較。具体的な計算例で最適な売り方がわかります。", "date": "2026-03-26"},
    {"url": "psa-guide.html", "title": "PSA鑑定とは？ポケカの価値を最大化する方法", "desc": "鑑定の流れ、グレードの意味、費用対効果まで。PSA 10で価値が3〜10倍に跳ね上がる具体例も紹介。", "date": "2026-03-24"},
    {"url": "single-card-tips.html", "title": "ポケカBOX開封→シングル売りで利益を出す方法", "desc": "高額カードの当たり例、レアリティの封入率、トレンド変化まで。開封vs未開封売りの判断基準も解説。", "date": "2026-03-24"},
    {"url": "shop-hikaku.html", "title": "ポケカ買取8店舗の特徴を徹底比較", "desc": "当サイトで掲載している8店舗それぞれの強み・特徴をまとめました。自分に合った買取店選びの参考に。", "date": "2026-03-23"},
    {"url": "kaitori-tips.html", "title": "ポケカBOX買取で損しない5つのコツ", "desc": "シュリンク付きの重要性、複数店舗比較のメリット、売り時の見極め方など、高価買取のポイントを解説。", "date": "2026-03-23"},
]


def generate_product_js(products: list[MasterProduct]) -> str:
    """Generate the JavaScript `const P = [...]` array from product data."""
    lines = []
    lines.append("const P=[")

    # Group by category (S&S is on hold, skip)
    current_cat = None
    for p in products:
        if p.category == "ss":
            continue
        if p.category != current_cat:
            current_cat = p.category
            lines.append(f"// ===== {current_cat.upper()} =====")

        # Build price dict
        prices = {}
        for sid in SHOP_IDS:
            prices[sid] = p.prices.get(sid, 0)

        # Escape product name for JS string
        name_escaped = p.name.replace("\\", "\\\\").replace('"', '\\"')

        price_parts = ",".join(f"{sid}:{prices[sid]}" for sid in SHOP_IDS)
        line = (
            f'{{c:"{p.category}",n:"{name_escaped}",'
            f'r:{p.retail_price},d:"{p.release_date}",p:{{{price_parts}}}}}'
        )
        lines.append(line + ",")

    lines.append("];")
    return "\n".join(lines)


def generate_history_js(history_dir: Path) -> str:
    """Generate JS object with price history data from daily snapshots."""
    if not history_dir.exists():
        return "const H={};"

    # Load all history files, sorted by date
    history = {}
    for f in sorted(history_dir.glob("*.json")):
        date = f.stem  # "2026-03-22"
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for item in data:
                name = item["name"]
                if name not in history:
                    history[name] = {}
                history[name][date] = item["max_price"]
        except (json.JSONDecodeError, KeyError):
            continue

    # Build JS: H = { "product name": { "2026-03-22": 18000, ... }, ... }
    return "const H=" + json.dumps(history, ensure_ascii=False) + ";"


def generate_jsonld(products: list[MasterProduct]) -> str:
    """Generate JSON-LD structured data for Google rich results."""
    items = []
    for p in products:
        if p.category == "ss":
            continue
        active_prices = [v for v in p.prices.values() if v > 0]
        if not active_prices:
            continue
        items.append({
            "@type": "Product",
            "name": p.name,
            "description": f"ポケモンカード {p.name} 未開封BOX 買取価格比較",
            "offers": {
                "@type": "AggregateOffer",
                "lowPrice": min(active_prices),
                "highPrice": max(active_prices),
                "priceCurrency": "JPY",
                "offerCount": len(active_prices),
            },
        })
    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "ポケカ買取チェッカー - 未開封BOX買取価格比較",
        "description": "ポケモンカード未開封BOXの買取価格を8店舗横断で比較",
        "numberOfItems": len(items),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": item}
            for i, item in enumerate(items)
        ],
    }
    return '<script type="application/ld+json">\n' + json.dumps(ld, ensure_ascii=False, indent=2) + "\n</script>"


def generate_ai_summary(products: list[MasterProduct]) -> str:
    """Generate a natural language summary for AI crawlers."""
    now = datetime.now(JST)
    date_str = now.strftime("%Y年%m月%d日")

    # Collect top products by max buyback price
    ranked = []
    for p in products:
        if p.category == "ss":
            continue
        active = {k: v for k, v in p.prices.items() if v > 0}
        if not active:
            continue
        max_shop = max(active, key=active.get)
        ranked.append((p, active, max_shop))

    ranked.sort(key=lambda x: max(x[1].values()), reverse=True)

    shop_names = {
        "morimori": "森森買取", "homura": "買取ホムラ", "icchome": "買取一丁目",
        "runto": "ラントゥ買取", "sommelier": "買取ソムリエ", "kaikyo": "海峡通信",
        "shouten": "買取商店", "rudeya": "買取ルデヤ",
    }

    lines = []
    lines.append(f"ポケカ買取チェッカー - {date_str}更新。ポケモンカード未開封BOXの買取価格を8店舗で横断比較。")

    # Top 5 products
    lines.append(f"【{date_str}時点の買取価格ランキング TOP5】")
    for i, (p, active, max_shop) in enumerate(ranked[:5]):
        max_price = max(active.values())
        min_price = min(active.values())
        shop = shop_names.get(max_shop, max_shop)
        lines.append(f"{i+1}位: {p.name} - 最高¥{max_price:,}({shop}) / 最安¥{min_price:,} / {len(active)}店舗掲載")

    lines.append(f"対応店舗: {', '.join(shop_names.values())}。毎日3回（11:00/15:00/18:00）自動更新。")

    summary_text = "\n".join(lines)
    return f'<div style="position:absolute;left:-9999px;font-size:1px;color:transparent" aria-hidden="true">{summary_text}</div>'


def generate_blog_links() -> str:
    """Generate blog cards: left=shop-hikaku(fixed), right=random from others."""
    # Left: 買取店比較 (固定)
    fixed = next(a for a in BLOG_ARTICLES if a["url"] == "shop-hikaku.html")
    # Right candidates: shop-hikaku以外の全記事（JSでランダム選択）
    candidates = [a for a in BLOG_ARTICLES if a["url"] != "shop-hikaku.html"]

    html = '<div class="blog-links" id="blogLinks">\n'
    # 左: 固定カード
    html += (
        f'  <a href="{fixed["url"]}" class="blog-card"'
        f' onclick="gtag(\'event\',\'blog_click\',{{article:\'{fixed["url"]}\'}})">\n'
        f'    <h3>{fixed["title"]}</h3>\n'
        f'    <p>{fixed["desc"]}</p>\n'
        f'  </a>\n'
    )
    # 右: ランダム候補（非表示、JSで1つ選んで表示）
    for article in candidates:
        html += (
            f'  <a href="{article["url"]}" class="blog-card blog-random" style="display:none"'
            f' onclick="gtag(\'event\',\'blog_click\',{{article:\'{article["url"]}\'}})">\n'
            f'    <h3>{article["title"]}</h3>\n'
            f'    <p>{article["desc"]}</p>\n'
            f'  </a>\n'
        )
    html += '</div>'
    return html


def generate_html(
    products: list[MasterProduct],
    template_path: Path | None = None,
    output_path: Path | None = None,
) -> str:
    """Generate index.html from template and product data.

    Args:
        products: List of master products with prices filled in.
        template_path: Path to template.html (default: project root/template.html)
        output_path: Path to write index.html (default: project root/index.html)

    Returns:
        The generated HTML content.
    """
    project_root = Path(__file__).resolve().parent.parent
    if template_path is None:
        template_path = project_root / "template.html"
    if output_path is None:
        output_path = project_root / "index.html"

    template = template_path.read_text(encoding="utf-8")

    # Generate product data JS
    product_js = generate_product_js(products)

    # Generate update date in JST
    now = datetime.now(JST)
    update_date = now.strftime("%Y/%m/%d %H:%M")

    # Generate JSON-LD structured data
    jsonld = generate_jsonld(products)

    # Generate AI-friendly summary
    ai_summary = generate_ai_summary(products)

    # Replace placeholders
    html = template.replace("// {{PRODUCT_DATA}}", product_js)
    html = html.replace("<!-- {{JSONLD}} -->", jsonld)
    html = html.replace("<!-- {{AI_SUMMARY}} -->", ai_summary)
    html = html.replace("{{UPDATE_DATE}}", update_date)
    html = html.replace("<!-- {{BLOG_LINKS}} -->", generate_blog_links())

    # Write output
    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    return html
