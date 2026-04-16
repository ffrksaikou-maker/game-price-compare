"""Generate index.html from template.html + price data."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .matcher import MasterProduct

logger = logging.getLogger(__name__)

# JST timezone
JST = timezone(timedelta(hours=9))

# Shop IDs in display order
SHOP_IDS = ["morimori", "homura", "icchome", "runto", "sommelier", "kaikyo", "oku", "rudeya"]

# BOX individual images (gamepedia.jp + 楽天から取得、ユーザー目視確認済み)
BOX_IMAGE_FILES: dict[str, str] = {
    "151": "151.jpg",
    "25th-anniversary-collection": "25th-anniversary-collection.jpg",
    "ancient-roar": "ancient-roar.jpg",
    "astonishing-voltecker": "astonishing-voltecker.jpg",
    "battle-collection": "battle-collection.jpg",
    "battle-partners": "battle-partners.jpg",
    "battle-region": "battle-region.jpg",
    "black-bolt-dx": "black-bolt-dx.jpg",
    "black-bolt": "black-bolt.jpg",
    "blue-sky-stream": "blue-sky-stream.jpg",
    "chouden-breaker": "chouden-breaker.jpg",
    "clay-burst": "clay-burst.jpg",
    "crimson-haze": "crimson-haze.jpg",
    "cyber-judge": "cyber-judge.jpg",
    "dark-phantasma": "dark-phantasma.jpg",
    "eevee-heroes": "eevee-heroes.jpg",
    "eruption-walker": "eruption-walker.jpg",
    "fukuoka": "fukuoka.jpg",
    "fusion-arts": "fusion-arts.jpg",
    "future-flash": "future-flash.jpg",
    "hengen-no-kamen": "hengen-no-kamen.jpg",
    "hiroshima": "hiroshima.jpg",
    "incandescent-arcana": "incandescent-arcana.jpg",
    "inferno": "inferno.jpg",
    "infinity-zone": "infinity-zone.jpg",
    "jet-black-geist": "jet-black-geist.jpg",
    "legendary-heartbeat": "legendary-heartbeat.jpg",
    "lost-abyss": "lost-abyss.jpg",
    "matchless-fighters": "matchless-fighters.jpg",
    "mega-brave": "mega-brave.jpg",
    "mega-ex": "mega-ex.jpg",
    "mega-sinfonia": "mega-sinfonia.jpg",
    "munikis-zero": "munikis-zero.jpg",
    "neppuu-arena": "neppuu-arena.jpg",
    "night-wanderer": "night-wanderer.jpg",
    "ninja-spinner": "ninja-spinner.jpg",
    "paradigm-trigger": "paradigm-trigger.jpg",
    "pokemon-go": "pokemon-go.jpg",
    "raging-surf": "raging-surf.jpg",
    "rakuen-dragona": "rakuen-dragona.jpg",
    "rapid-strike-master": "rapid-strike-master.jpg",
    "rebellion-crash": "rebellion-crash.jpg",
    "rocket-dan-no-eiko": "rocket-dan-no-eiko.jpg",
    "ruler-of-black-flame": "ruler-of-black-flame.jpg",
    "scarlet-ex": "scarlet-ex.jpg",
    "shield": "shield.jpg",
    "shiny-star": "shiny-star.jpg",
    "shiny-treasure-ex": "shiny-treasure-ex.jpg",
    "silver-lance": "silver-lance.jpg",
    "single-strike-master": "single-strike-master.jpg",
    "skyscraping-perfect": "skyscraping-perfect.jpg",
    "snow-hazard": "snow-hazard.jpg",
    "space-juggler": "space-juggler.jpg",
    "star-birth": "star-birth.jpg",
    "stellar-miracle": "stellar-miracle.jpg",
    "sword": "sword.jpg",
    "terastal-fes-ex": "terastal-fes-ex.jpg",
    "time-gazer": "time-gazer.jpg",
    "tohoku": "tohoku.jpg",
    "triplet-beat": "triplet-beat.jpg",
    "wild-force": "wild-force.jpg",
    "violet-ex": "violet-ex.jpg",
    "vmax-climax": "vmax-climax.jpg",
    "vmax-rising": "vmax-rising.jpg",
    "vstar-universe": "vstar-universe.jpg",
    "white-flare-dx": "white-flare-dx.jpg",
    "white-flare": "white-flare.jpg",
}

BASE_URL = "https://pokeca-box-hikaku.com"
DEFAULT_OG_IMAGE = f"{BASE_URL}/ogp.jpg"


def get_box_image_url(slug: str) -> str:
    """Return the full URL for a BOX's primary image.
    Returns the individual image if available, else the default OGP image.
    """
    filename = BOX_IMAGE_FILES.get(slug)
    if filename:
        return f"{BASE_URL}/images/boxes/{filename}"
    return DEFAULT_OG_IMAGE

# Blog articles (newest first) - 記事追加時はここに1行足すだけ
BLOG_ARTICLES = [
    {"url": "weekly/", "title": "【今週】ポケカBOX 週間急上昇ランキング", "desc": "SV・MEGA TOP10 + S&S TOP3を毎日自動更新。8店舗実データから抽出した直近7日間で最も値上がりしたBOXをグラフ付きで掲載。", "date": "2026-04-12"},
    {"url": "release-schedule-2026.html", "title": "2026年ポケカ新弾発売カレンダー", "desc": "2026年の発売済み/予想パックを完全整理。ムニキスゼロ・ニンジャスピナー発売済み、5月値上げ(180→200円)、アビスアイ等の商標予想、30周年記念商品(世界同時発売)まで解説。", "date": "2026-04-15"},
    {"url": "inferno-x-spotlight.html", "title": "インフェルノXが定価の5倍に高騰", "desc": "発売半年で定価¥5,400→¥27,000(約5倍)に急騰したインフェルノXの相場推移、収録カード、3つの高騰理由を実データで徹底解説。", "date": "2026-04-12"},
    {"url": "chouden-breaker-spotlight.html", "title": "超電ブレイカーが定価7.5倍に高騰", "desc": "BOX買取¥40,700、定価の7.5倍に達した超電ブレイカー(SV8)。ピカチュウex SAR¥55,000・ぎどら氏イラストの高騰5つの理由、Jレギュ前のスタン現役期の今後を解説。", "date": "2026-04-15"},
    {"url": "clay-burst-spotlight.html", "title": "クレイバーストとナンジャモSAR相場解説", "desc": "BOX買取¥12,200、Gレギュ絶版観測で再評価中のクレイバースト(SV2D)。ナンジャモSAR¥50,000・PSA10で¥108,000・kirisAki氏イラストを含む5つの注目理由を解説。", "date": "2026-04-15"},
    {"url": "ninja-spinner-spotlight.html", "title": "ニンジャスピナー(M4)が定価2.5倍に高騰", "desc": "BOX買取¥13,400、メガゲッコウガex MUR¥95,000(封入率約0.9〜2%)・SAR¥40,000(前屋進氏イラスト進化ライン一枚絵)・HP350の対戦実需・180円定価最後のMEGA弾の5つの高騰理由を解説。", "date": "2026-04-16"},
    {"url": "price-pattern-guide.html", "title": "BOX買取価格の5段階パターン", "desc": "発売前プレ値→初動高値→調整期→底打ち→絶版急騰の5段階を当サイト40日観測データと5スポットライトBOXの具体値で実証解説。買い時売り時の3判断基準、2024年バブル崩壊の教訓も紹介。", "date": "2026-04-16"},
    {"url": "151-spotlight.html", "title": "ポケモンカード151がなぜ高い？定価12倍超え", "desc": "BOX買取¥68,200、定価の12.6倍に達した151の絶版観測、5つの高騰理由、今後どこまで上がるかの3シナリオを実データで解説。", "date": "2026-04-14"},
    {"url": "kokuen-spotlight.html", "title": "黒炎の支配者が定価の約4倍に高騰", "desc": "BOX買取¥21,200、Gレギュ絶版観測で上昇継続中。リザードンex SAR(悪テラスタル)を筆頭に5つの高騰理由と今後の予想を解説。", "date": "2026-04-14"},
    {"url": "zeppan-ranking-2026-03.html", "title": "S&S以降 絶版BOXランキング", "desc": "Gレギュスタン落ち済みBOXを中心に、絶版観測・事実上絶版のBOXを相場順ランキング。中長期投資の判断材料に。", "date": "2026-04-14"},
    {"url": "lizardon-box-guide.html", "title": "リザードン高騰BOX完全ガイド", "desc": "151・黒炎の支配者・インフェルノXなどリザードン封入BOXを横断比較。なぜリザードン系は例外なく高額化するのかを解説。", "date": "2026-04-14"},
    {"url": "mega-pack-compare.html", "title": "MEGA拡張パック完全比較", "desc": "メガブレイブ・メガシンフォニア・インフェルノX・MEGAドリームex・ニンジャスピナーのMEGAシリーズ全体を相場・封入率で徹底比較。", "date": "2026-04-14"},
    {"url": "kokuen-vs-rocket.html", "title": "黒炎 vs ロケット団の栄光 徹底比較", "desc": "人気対決BOX2つを相場・目玉SAR・絶版観測・開封期待値で多角比較。どちらに投資すべきかを6観点で評価。", "date": "2026-04-14"},
    {"url": "mega-lizardon-x-guide.html", "title": "メガリザードンXex MUR/SAR 相場解説", "desc": "MUR¥200,000/SAR¥95,000に急騰したインフェルノX目玉カード。1ヶ月で1.8倍急騰の理由と今後の予想を徹底解説。", "date": "2026-04-14"},
    {"url": "lizardon-sar-kokuen-guide.html", "title": "リザードンex SAR(黒炎)相場解説", "desc": "買取¥37,000・PSA10で¥65,900の黒炎SAR。江川あきら氏イラストと悪テラスタル形態で高騰継続中のカードを詳解。", "date": "2026-04-14"},
    {"url": "erika-sar-guide.html", "title": "エリカの招待SAR 相場解説", "desc": "買取¥8,000・PSA10で¥33,400の151人気SAR。初動¥128,200からの調整と151絶版観測での再上昇を予想。", "date": "2026-04-14"},
    {"url": "pigeot-sar-guide.html", "title": "ピジョットex SAR 相場解説", "desc": "「ピジョリザ」デッキ必須の対戦用SAR。マッハサーチ特性とプレイヤー需要で安定相場の実用SARを徹底解説。", "date": "2026-04-14"},
    {"url": "masterball-mirror-guide.html", "title": "151マスターボールミラー 相場解説", "desc": "全153種のマスターボールミラーをピカチュウ¥55,000・ゲンガー¥60,000などの相場と封入率・コンプ難易度で解説。", "date": "2026-04-14"},
    {"url": "kokuen-atari-guide.html", "title": "黒炎の支配者 当たりカード完全ガイド", "desc": "SAR/UR/SR/AR/RR 全41種の当たりカードを買取相場・封入率・期待値で徹底整理。リザードンex SAR一強の実態も解説。", "date": "2026-04-14"},
    {"url": "restock-guide.html", "title": "再販情報の見つけ方", "desc": "ポケカBOXの再販入荷パターン、通知設定、抽選vs先着の攻略法まで。最速で再販情報をキャッチする方法を解説。", "date": "2026-04-10"},
    {"url": "box-toushi.html", "title": "ポケカBOX投資の始め方", "desc": "値上がりしやすいBOXの特徴、予算別の始め方、保管方法、リスクまで初心者向けに解説。", "date": "2026-04-02"},
    {"url": "shrink-nashi.html", "title": "シュリンクなしBOXの買取事情", "desc": "シュリンクなしポケカBOXの買取対応を買取店・メルカリ・スニダンで比較。高く売るコツも解説。", "date": "2026-03-27"},
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

    # Group by category
    current_cat = None
    for p in products:
        if p.category != current_cat:
            current_cat = p.category
            lines.append(f"// ===== {current_cat.upper()} =====")

        # Build price dict
        prices = {}
        for sid in SHOP_IDS:
            prices[sid] = p.prices.get(sid, 0)

        # Escape product name for JS string
        name_escaped = p.name.replace("\\", "\\\\").replace('"', '\\"')

        slug = _generate_slug(p.name)
        price_parts = ",".join(f"{sid}:{prices[sid]}" for sid in SHOP_IDS)
        line = (
            f'{{c:"{p.category}",n:"{name_escaped}",s:"{slug}",'
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
        active_prices = [v for v in p.prices.values() if v > 0]
        if not active_prices:
            continue
        items.append({
            "@type": "Product",
            "name": p.name,
            "description": f"ポケモンカード {p.name} 未開封BOX 買取価格比較",
            "image": "https://pokeca-box-hikaku.com/ogp.jpg",
            "brand": {"@type": "Brand", "name": "ポケモンカードゲーム"},
            "category": "トレーディングカードゲーム / ポケモンカード / 未開封BOX",
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
        "description": "ポケモンカード未開封BOXの買取価格をラントゥ・ホムラ・一丁目・森森買取等8店舗横断で比較",
        "numberOfItems": len(items),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": item}
            for i, item in enumerate(items)
        ],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"},
        ],
    }
    return (
        '<script type="application/ld+json">\n' + json.dumps(ld, ensure_ascii=False, indent=2) + "\n</script>\n"
        '<script type="application/ld+json">\n' + json.dumps(breadcrumb, ensure_ascii=False, indent=2) + "\n</script>"
    )


def generate_ai_summary(products: list[MasterProduct]) -> str:
    """Generate a natural language summary for AI crawlers."""
    now = datetime.now(JST)
    date_str = now.strftime("%Y年%m月%d日")

    # Collect top products by max buyback price
    ranked = []
    for p in products:
        active = {k: v for k, v in p.prices.items() if v > 0}
        if not active:
            continue
        max_shop = max(active, key=active.get)
        ranked.append((p, active, max_shop))

    ranked.sort(key=lambda x: max(x[1].values()), reverse=True)

    shop_names = {
        "morimori": "森森買取", "homura": "買取ホムラ", "icchome": "買取一丁目",
        "runto": "ラントゥ買取", "sommelier": "買取ソムリエ", "kaikyo": "海峡通信",
        "oku": "買取オク", "rudeya": "買取ルデヤ",
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
    """Generate blog cards: random + two pinned (weekly + new schedule article)."""
    # Pinned固定: BLOG_ARTICLES[0] = weekly, [1] = release-schedule-2026
    pinned = BLOG_ARTICLES[:2]
    pinned_urls = {a["url"] for a in pinned}
    # 残りはJSでランダム選択
    candidates = [a for a in BLOG_ARTICLES if a["url"] not in pinned_urls]

    html = '<div class="blog-links" id="blogLinks">\n'
    # ランダム候補（非表示、JSで1つ選んで表示）
    for article in candidates:
        html += (
            f'  <a href="{article["url"]}" class="blog-card blog-random" style="display:none"'
            f' onclick="gtag(\'event\',\'blog_click\',{{article:\'{article["url"]}\'}})">\n'
            f'    <h3>{article["title"]}</h3>\n'
            f'    <p>{article["desc"]}</p>\n'
            f'  </a>\n'
        )
    # Pinned 2枚を常時表示
    for article in pinned:
        html += (
            f'  <a href="{article["url"]}" class="blog-card"'
            f' onclick="gtag(\'event\',\'blog_click\',{{article:\'{article["url"]}\'}})">\n'
            f'    <h3>{article["title"]}</h3>\n'
            f'    <p>{article["desc"]}</p>\n'
            f'  </a>\n'
        )
    html += '</div>'
    return html


def generate_chart_data(products: list[MasterProduct], project_root: Path) -> str:
    """Generate JS variable with snkrdunk price history for chart display."""
    mapping_path = project_root / "data" / "snkrdunk" / "product_mapping.json"
    if not mapping_path.exists():
        return "const SC={};"

    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "const SC={};"

    snkrdunk_dir = project_root / "data" / "snkrdunk"
    chart_data: dict[str, dict] = {}
    product_map = {p.name: p for p in products}

    for product_name, snkrdunk_id in mapping.items():
        if product_name not in product_map:
            continue
        data_path = snkrdunk_dir / f"{snkrdunk_id}.json"
        if not data_path.exists():
            continue
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
            points = data.get("points", [])
            if points:
                entry: dict = {"p": points}
                rd = product_map[product_name].release_date
                if rd:
                    entry["d"] = rd
                chart_data[product_name] = entry
        except (json.JSONDecodeError, OSError):
            continue

    return "const SC=" + json.dumps(chart_data, ensure_ascii=False) + ";"


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

    # Generate ranking page (before summary, so we can use the data)
    ranking_summary = _generate_ranking_summary(products, project_root)
    html = html.replace("<!-- {{RANKING_SUMMARY}} -->", ranking_summary)

    # Write output
    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    # Generate individual product pages
    generate_product_pages(products, project_root, update_date)

    # Generate ranking page
    generate_ranking_page(products, project_root, update_date)

    # Generate weekly hot-boxes article (task 10)
    generate_weekly_article(products, project_root, update_date)

    return html


# ===== Slug generation =====

# Manual slug overrides for products with tricky names
SLUG_OVERRIDES = {
    "MEGA スタートデッキ100「バトルコレクション」": "battle-collection",
    "S&S 拡張パック「25th ANNIVERSARY COLLECTION」": "25th-anniversary-collection",
    "S&S 拡張パック「ソード」": "sword",
    "S&S 拡張パック「シールド」": "shield",
    "S&S 強化拡張パック「ポケモンGO」": "pokemon-go",
    "SV 拡張パックDX「ブラックボルト」": "black-bolt-dx",
    "SV 拡張パックDX「ホワイトフレア」": "white-flare-dx",
}

# Romanization map for common Pokemon TCG terms
ROMAJI_MAP = {
    "ニンジャスピナー": "ninja-spinner",
    "ムニキスゼロ": "munikis-zero",
    "メガドリーム": "mega-dream",
    "インフェルノ": "inferno",
    "メガブレイブ": "mega-brave",
    "メガシンフォニア": "mega-sinfonia",
    "ブラックボルト": "black-bolt",
    "ホワイトフレア": "white-flare",
    "ロケット団の栄光": "rocket-dan-no-eiko",
    "熱風のアリーナ": "neppuu-arena",
    "バトルパートナーズ": "battle-partners",
    "テラスタルフェス": "terastal-fes",
    "超電ブレイカー": "chouden-breaker",
    "楽園ドラゴーナ": "rakuen-dragona",
    "ステラミラクル": "stellar-miracle",
    "ナイトワンダラー": "night-wanderer",
    "変幻の仮面": "hengen-no-kamen",
    "ワイルドフォース": "wild-force",
    "サイバージャッジ": "cyber-judge",
    "クリムゾンヘイズ": "crimson-haze",
    "シャイニートレジャー": "shiny-treasure",
    "黒炎の支配者": "ruler-of-black-flame",
    "古代の咆哮": "ancient-roar",
    "未来の一閃": "future-flash",
    "レイジングサーフ": "raging-surf",
    "スカーレット": "scarlet",
    "バイオレット": "violet",
    "スノーハザード": "snow-hazard",
    "クレイバースト": "clay-burst",
    "トリプレットビート": "triplet-beat",
    "白熱のアルカナ": "incandescent-arcana",
    "ロストアビス": "lost-abyss",
    "パラダイムトリガー": "paradigm-trigger",
    "トウホク": "tohoku",
    "ヒロシマ": "hiroshima",
    "フクオカ": "fukuoka",
    "イーブイヒーローズ": "eevee-heroes",
    "バトルリージョン": "battle-region",
    "スターバース": "star-birth",
    "フュージョンアーツ": "fusion-arts",
    "蒼空ストリーム": "blue-sky-stream",
    "摩天パーフェクト": "skyscraping-perfect",
    "白銀のランス": "silver-lance",
    "漆黒のガイスト": "jet-black-geist",
    "双璧のファイター": "matchless-fighters",
    "連撃マスター": "rapid-strike-master",
    "一撃マスター": "single-strike-master",
    "シャイニースター": "shiny-star",
    "仰天のボルテッカー": "astonishing-voltecker",
    "伝説の鼓動": "legendary-heartbeat",
    "ムゲンゾーン": "infinity-zone",
    "爆炎ウォーカー": "eruption-walker",
    "反逆クラッシュ": "rebellion-crash",
    "ダークファンタズマ": "dark-phantasma",
    "タイムゲイザー": "time-gazer",
    "スペースジャグラー": "space-juggler",
    "VMAXクライマックス": "vmax-climax",
    "VSTARユニバース": "vstar-universe",
    "VMAXライジング": "vmax-rising",
}


def _generate_slug(product_name: str) -> str:
    """Generate a URL-friendly slug from a product name."""
    if product_name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[product_name]

    # Extract the part in quotes (e.g., 「xxx」)
    m = re.search(r"[「『](.+?)[」』]", product_name)
    if m:
        core = m.group(1)
    else:
        # For special BOX, use the last part
        core = product_name.split()[-1] if " " in product_name else product_name

    # Try romaji map first
    for jp, en in ROMAJI_MAP.items():
        if jp in core:
            # Handle suffixes like "ex"
            slug = en
            if "ex" in core.lower() and "ex" not in en:
                slug += "-ex"
            return slug

    # Fallback: normalize and transliterate
    slug = core.lower()
    slug = unicodedata.normalize("NFKC", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "unknown"


SHOP_NAMES = {
    "morimori": "森森買取",
    "homura": "買取ホムラ",
    "icchome": "買取一丁目",
    "runto": "ラントゥ買取",
    "sommelier": "買取ソムリエ",
    "kaikyo": "海峡通信",
    "oku": "買取オク",
    "rudeya": "買取ルデヤ",
}

SHOP_URLS = {
    "morimori": "https://www.morimori-kaitori.jp/",
    "homura": "https://kaitori-homura.com/",
    "icchome": "https://www.1-chome.com/",
    "runto": "https://runto666.com/",
    "sommelier": "https://somurie-kaitori.com/",
    "kaikyo": "https://www.mobile-ichiban.com/",
    "oku": "https://kaitori-oku.jp/",
    "rudeya": "https://kaitori-rudeya.com/",
}

CATEGORY_LABELS = {
    "mega": "MEGA シリーズ",
    "sv": "SV シリーズ",
    "special": "スペシャルBOX",
    "ss": "S&S ソード&シールド",
}


def _find_product_url(
    product_urls: dict[str, dict[str, str]],
    shop_id: str,
    product: MasterProduct,
) -> str | None:
    """Find product-specific URL from the URL mapping.

    Matches by checking if any of the product's keywords appear in the
    scraped product name from the URL mapping.
    """
    shop_map = product_urls.get(shop_id, {})
    if not shop_map:
        return None

    # Try exact keyword match against scraped names
    for kw in product.keywords:
        if not kw:
            continue
        kw_lower = kw.lower()
        for scraped_name, url in shop_map.items():
            if kw_lower in scraped_name.lower():
                # Avoid matching DX vs non-DX
                is_dx_product = "DX" in product.name
                is_dx_scraped = "dx" in scraped_name.lower() or "デラックス" in scraped_name
                if is_dx_product != is_dx_scraped:
                    continue
                # Avoid matching shrink-nashi / carton
                name_lower = scraped_name.lower()
                if "シュリンクなし" in scraped_name or "シュリンク無" in scraped_name:
                    continue
                if "カートン" in scraped_name or "carton" in name_lower:
                    continue
                return url

    return None


def _format_price(price: int) -> str:
    if price <= 0:
        return "-"
    return f"\u00a5{price:,}"


def _generate_box_chart_section(product: MasterProduct, project_root: Path) -> str:
    """Generate inline chart HTML+JS for an individual product page.

    Uses snkrdunk data for historical prices, then switches to our own
    history data (data/history/) from the date our collection started.
    """
    # --- Load snkrdunk data ---
    snkrdunk_points: list[list] = []
    mapping_path = project_root / "data" / "snkrdunk" / "product_mapping.json"
    if mapping_path.exists():
        try:
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            snkrdunk_id = mapping.get(product.name)
            if snkrdunk_id:
                data_path = project_root / "data" / "snkrdunk" / f"{snkrdunk_id}.json"
                if data_path.exists():
                    data = json.loads(data_path.read_text(encoding="utf-8"))
                    snkrdunk_points = data.get("points", [])
        except (json.JSONDecodeError, OSError):
            pass

    # --- Load our own history data ---
    history_dir = project_root / "data" / "history"
    own_points: list[list] = []  # [timestamp_ms, max_price]
    if history_dir.exists():
        for hist_file in sorted(history_dir.glob("*.json")):
            try:
                date_str = hist_file.stem  # "2026-03-08"
                ts = int(datetime.strptime(date_str, "%Y-%m-%d")
                         .replace(tzinfo=JST).timestamp() * 1000)
                items = json.loads(hist_file.read_text(encoding="utf-8"))
                for item in items:
                    if item.get("name") == product.name:
                        max_price = item.get("max_price", 0)
                        if max_price > 0:
                            own_points.append([ts, max_price])
                        break
            except (json.JSONDecodeError, OSError, ValueError):
                continue

    # --- Merge: snkrdunk before own data starts, then own data ---
    if own_points:
        own_start = own_points[0][0]
        # Keep snkrdunk points before our data starts
        merged = [p for p in snkrdunk_points if p[0] < own_start]
        merged.extend(own_points)
        points = merged
    else:
        points = snkrdunk_points

    if not points:
        return ""

    release_date = product.release_date or ""
    points_json = json.dumps(points, ensure_ascii=False)
    # Number of snkrdunk points at the beginning of merged list
    # スタートデッキ等（定価2000円未満）は単品取引なので0.9倍補正しない
    no_correction = product.retail_price < 2000
    if no_correction:
        snkr_count = 0
    elif own_points:
        own_start = own_points[0][0]
        snkr_count = len([p for p in points if p[0] < own_start])
    else:
        snkr_count = len(points)
    box_name = product.name

    return f"""<h3 class="section-title">{box_name} 価格推移</h3>
<div class="chart-wrap">
<div class="chart-periods">
  <button class="cp-btn active" data-period="all">全期間</button>
  <button class="cp-btn" data-period="3m">3ヶ月</button>
  <button class="cp-btn" data-period="1m">1ヶ月</button>
</div>
<canvas id="boxChart"></canvas>
<div class="chart-note">※ 8店舗の最高買取価格の推移（過去分は参考データ）</div>
</div>
<script>
(function(){{
var pts={points_json};
var rd="{release_date}";
var snkrCount={snkr_count};
var ci=null;
function draw(period){{
  var now=Date.now(),cutoff=0;
  if(period==="3m")cutoff=now-90*86400000;
  else if(period==="1m")cutoff=now-30*86400000;
  var f=cutoff?pts.filter(function(p){{return p[0]>=cutoff}}):pts;
  if(!f.length)f=pts;
  var labels=f.map(function(p){{var d=new Date(p[0]);return d.getFullYear()+"/"+(d.getMonth()+1)+"/"+d.getDate()}});
  var sc=cutoff?pts.slice(0,snkrCount).filter(function(p){{return p[0]>=cutoff}}).length:snkrCount;
  var data=f.map(function(p,i){{return i<sc?Math.round(p[1]*0.9):p[1]}});
  var ridx=-1;
  if(rd){{var rt=new Date(rd+"T00:00:00+09:00").getTime();if(!cutoff||rt>=cutoff){{for(var i=0;i<f.length;i++){{if(f[i][0]>=rt){{ridx=i;break}}}}}}}}
  var ann=undefined;
  if(ridx>=0){{ann={{annotations:{{rl:{{type:"line",drawTime:"beforeDatasetsDraw",xMin:ridx,xMax:ridx,borderColor:"#ef4444",borderWidth:2,borderDash:[6,4],label:{{display:true,content:"発売日",position:"end",backgroundColor:"#ef4444",color:"#fff",font:{{size:11,weight:"bold"}},padding:{{top:3,bottom:3,left:6,right:6}},borderRadius:4}}}}}}}};}}
  if(ci)ci.destroy();
  ci=new Chart(document.getElementById("boxChart").getContext("2d"),{{
    type:"line",
    data:{{labels:labels,datasets:[{{label:"参考価格",data:data,borderColor:"#6366f1",backgroundColor:"rgba(99,102,241,.1)",fill:true,tension:0.3,pointRadius:f.length>60?0:2,pointHoverRadius:5,borderWidth:2}}]}},
    options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:"index",intersect:false}},
      plugins:{{legend:{{display:false}},annotation:ann,tooltip:{{callbacks:{{label:function(c){{return"\\u00a5"+c.parsed.y.toLocaleString()}}}}}}}},
      scales:{{x:{{ticks:{{maxTicksLimit:8,font:{{size:11}},color:"#6b7280"}},grid:{{display:false}}}},y:{{ticks:{{callback:function(v){{return"\\u00a5"+v.toLocaleString()}},font:{{size:11}},color:"#6b7280"}},grid:{{color:"#f3f4f6"}}}}}}
    }}
  }});
}}
draw("all");
document.querySelectorAll(".cp-btn").forEach(function(b){{
  b.addEventListener("click",function(){{
    document.querySelectorAll(".cp-btn").forEach(function(x){{x.classList.remove("active")}});
    b.classList.add("active");draw(b.dataset.period);
  }});
}});
}})();
</script>"""


def generate_product_pages(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """Generate individual product pages for all BOX products."""
    box_dir = project_root / "box"
    box_dir.mkdir(exist_ok=True)

    template_path = project_root / "box-template.html"
    if not template_path.exists():
        logger.warning("box-template.html not found, skipping product pages")
        return

    template = template_path.read_text(encoding="utf-8")

    # Load product URL mapping (shop_id -> {scraped_name -> url})
    product_urls: dict[str, dict[str, str]] = {}
    urls_path = project_root / "data" / "product_urls.json"
    if urls_path.exists():
        try:
            product_urls = json.loads(urls_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Group products by category for related links
    by_cat: dict[str, list[MasterProduct]] = {}
    slug_map: dict[str, str] = {}  # product name -> slug
    for p in products:
        by_cat.setdefault(p.category, []).append(p)
        slug_map[p.name] = _generate_slug(p.name)

    total_products = len(products)
    generated = 0

    for p in products:
        slug = slug_map[p.name]
        active_prices = {sid: p.prices.get(sid, 0) for sid in SHOP_IDS if p.prices.get(sid, 0) > 0}

        if not active_prices:
            continue

        max_price = max(active_prices.values())
        max_shop_id = max(active_prices, key=active_prices.get)
        max_shop_name = SHOP_NAMES.get(max_shop_id, max_shop_id)
        shop_count = len(active_prices)
        diff = max_price - p.retail_price if p.retail_price > 0 and max_price > 0 else 0

        # Build price table rows (sorted by price desc)
        sorted_shops = sorted(
            [(sid, p.prices.get(sid, 0)) for sid in SHOP_IDS],
            key=lambda x: x[1],
            reverse=True,
        )
        table_rows = []
        for sid, price in sorted_shops:
            shop_name = SHOP_NAMES.get(sid, sid)
            # Try to find product-specific URL from mapping
            shop_url = _find_product_url(product_urls, sid, p) or SHOP_URLS.get(sid, "#")
            if price > 0:
                is_best = price == max_price
                tr_class = ' class="best"' if is_best else ""
                table_rows.append(
                    f'<tr{tr_class}>'
                    f'<td class="shop-name"><a href="{shop_url}" target="_blank" rel="noopener noreferrer">{shop_name}</a></td>'
                    f'<td>{_format_price(price)}</td>'
                    f'</tr>'
                )
            else:
                table_rows.append(
                    f'<tr><td class="shop-name">{shop_name}</td><td class="no-price">取扱なし</td></tr>'
                )

        price_table = (
            '<table class="price-table">\n'
            '<tr><th>買取店</th><th>買取価格</th></tr>\n'
            + "\n".join(table_rows)
            + "\n</table>"
        )

        # Related links (same category, exclude self, 同時発売BOXを先頭に)
        related = [
            r for r in by_cat.get(p.category, [])
            if r.name != p.name and any(r.prices.get(s, 0) > 0 for s in SHOP_IDS)
        ]
        related.sort(key=lambda r: (0 if r.release_date == p.release_date and p.release_date else 1))
        related_html = "\n".join(
            f'    <a href="{slug_map[r.name]}.html" class="related-link">{r.name}</a>'
            for r in related
        )

        # Diff text
        if diff > 0:
            diff_text = f"+\u00a5{diff:,}"
        elif diff < 0:
            diff_text = f"-\u00a5{abs(diff):,}"
        else:
            diff_text = "-"

        # Individual BOX image (falls back to ogp.jpg for slugs not yet mapped)
        box_image_url = get_box_image_url(slug)

        # JSON-LD for individual product
        product_jsonld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": p.name,
            "description": f"ポケモンカード {p.name} 未開封BOX 買取価格比較",
            "image": box_image_url,
            "brand": {"@type": "Brand", "name": "ポケモンカードゲーム"},
            "category": "トレーディングカードゲーム / ポケモンカード / 未開封BOX",
            "sku": f"pokeca-box-{slug}",
            "url": f"https://pokeca-box-hikaku.com/box/{slug}.html",
            "offers": {
                "@type": "AggregateOffer",
                "lowPrice": min(active_prices.values()),
                "highPrice": max_price,
                "priceCurrency": "JPY",
                "offerCount": shop_count,
                "availability": "https://schema.org/InStock",
            },
        }, ensure_ascii=False, indent=2)
        breadcrumb_jsonld = json.dumps({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"},
                {"@type": "ListItem", "position": 2, "name": "買取価格比較", "item": "https://pokeca-box-hikaku.com/"},
                {"@type": "ListItem", "position": 3, "name": p.name},
            ],
        }, ensure_ascii=False, indent=2)
        jsonld_tag = (
            f'<script type="application/ld+json">\n{product_jsonld}\n</script>\n'
            f'<script type="application/ld+json">\n{breadcrumb_jsonld}\n</script>'
        )

        # Generate chart section for this product
        chart_section = _generate_box_chart_section(p, project_root)

        # Replace all placeholders
        html = template
        html = html.replace("{{PRODUCT_NAME}}", p.name)
        html = html.replace("{{PRODUCT_DESC}}", p.desc or "")
        # 当たりカードセクション
        if p.hit_cards:
            top_cards = p.hit_cards[:3]
            cards_html = '<div class="hit-cards"><h3>当たりカード</h3><dl class="hit-list">'
            for card in top_cards:
                if isinstance(card, (list, tuple)) and len(card) >= 2:
                    name, comment = card[0], card[1]
                else:
                    name, comment = card, ""
                cards_html += f"<dt>{name}</dt>"
                if comment:
                    cards_html += f"<dd>{comment}</dd>"
            cards_html += '</dl></div>'
        else:
            cards_html = ""
        html = html.replace("{{HIT_CARDS}}", cards_html)
        # description用の当たりカード名テキスト
        if p.hit_cards:
            card_names = [c[0] if isinstance(c, (list, tuple)) else c for c in p.hit_cards[:3]]
            hit_text = "当たりカード: " + "、".join(card_names) + "。"
        else:
            hit_text = ""
        html = html.replace("{{HIT_CARDS_TEXT}}", hit_text)
        html = html.replace("{{SLUG}}", slug)
        html = html.replace("{{MAX_PRICE_TEXT}}", _format_price(max_price))
        html = html.replace("{{MAX_SHOP_NAME}}", max_shop_name)
        html = html.replace("{{SHOP_COUNT}}", str(shop_count))
        html = html.replace("{{RETAIL_PRICE_TEXT}}", _format_price(p.retail_price))
        html = html.replace("{{DIFF_TEXT}}", diff_text)
        html = html.replace("{{CATEGORY_LABEL}}", CATEGORY_LABELS.get(p.category, p.category))
        html = html.replace("{{PRICE_TABLE}}", price_table)
        html = html.replace("{{RELATED_LINKS}}", related_html)
        html = html.replace("{{TOTAL_PRODUCTS}}", str(total_products))
        html = html.replace("{{UPDATE_DATE}}", update_date)
        html = html.replace("{{BOX_IMAGE_URL}}", box_image_url)
        # ヒーロー画像 (マップされたBOXのみ表示、それ以外は空)
        if slug in BOX_IMAGE_FILES:
            # SEO alt: 商品名 + 未開封BOX + 買取価格 + 定価倍率(retailがあれば)
            if p.retail_price and p.retail_price > 0 and max_price > 0:
                ratio = max_price / p.retail_price
                alt_text = f"{p.name} 未開封BOX 買取価格¥{max_price:,} 定価{ratio:.1f}倍"
            elif max_price > 0:
                alt_text = f"{p.name} 未開封BOX 買取価格¥{max_price:,}"
            else:
                alt_text = f"{p.name} 未開封BOX"
            box_hero_html = (
                f'<div class="box-hero">'
                f'<img src="../images/boxes/{BOX_IMAGE_FILES[slug]}" '
                f'alt="{alt_text}" '
                f'loading="lazy" decoding="async">'
                f'</div>'
            )
        else:
            box_hero_html = ""
        html = html.replace("{{BOX_HERO}}", box_hero_html)
        html = html.replace("{{JSONLD}}", jsonld_tag)
        html = html.replace("<!-- {{CHART_SECTION}} -->", chart_section)

        # Write file
        out_path = box_dir / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8")
        generated += 1

    logger.info("Generated %d product pages in %s", generated, box_dir)

    # Update sitemap
    _update_sitemap(products, slug_map, project_root)


def _update_sitemap(
    products: list[MasterProduct],
    slug_map: dict[str, str],
    project_root: Path,
) -> None:
    """Regenerate sitemap.xml including all product pages."""
    base = "https://pokeca-box-hikaku.com"
    today = datetime.now(JST).strftime("%Y-%m-%d")

    # Static pages: (path, changefreq, priority, lastmod)
    # 記事ページは lastmod を個別管理 (手動更新日)
    static_pages = [
        ("/", "daily", "1.0", today),
        ("/ranking.html", "daily", "0.9", today),
        ("/weekly/", "weekly", "0.9", today),
        ("/inferno-x-spotlight.html", "monthly", "0.8", "2026-04-12"),
        ("/151-spotlight.html", "monthly", "0.8", "2026-04-14"),
        ("/kokuen-spotlight.html", "monthly", "0.8", "2026-04-14"),
        ("/chouden-breaker-spotlight.html", "monthly", "0.8", "2026-04-15"),
        ("/clay-burst-spotlight.html", "monthly", "0.8", "2026-04-15"),
        ("/ninja-spinner-spotlight.html", "monthly", "0.8", "2026-04-16"),
        ("/zeppan-ranking-2026-03.html", "monthly", "0.8", "2026-04-14"),
        ("/lizardon-box-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/mega-pack-compare.html", "monthly", "0.8", "2026-04-14"),
        ("/kokuen-vs-rocket.html", "monthly", "0.8", "2026-04-14"),
        ("/mega-lizardon-x-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/lizardon-sar-kokuen-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/erika-sar-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/pigeot-sar-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/masterball-mirror-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/kokuen-atari-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/restock-guide.html", "monthly", "0.8", "2026-04-10"),
        ("/release-schedule-2026.html", "monthly", "0.8", "2026-04-15"),
        ("/price-pattern-guide.html", "monthly", "0.8", "2026-04-16"),
        ("/box-toushi.html", "monthly", "0.8", "2026-04-02"),
        ("/shrink-nashi.html", "monthly", "0.8", "2026-03-27"),
        ("/mercari-hikaku.html", "monthly", "0.8", "2026-03-26"),
        ("/psa-guide.html", "monthly", "0.8", "2026-03-24"),
        ("/single-card-tips.html", "monthly", "0.8", "2026-03-24"),
        ("/shop-hikaku.html", "monthly", "0.8", "2026-03-23"),
        ("/kaitori-tips.html", "monthly", "0.8", "2026-03-23"),
        ("/monthly-ranking-2026-03.html", "monthly", "0.7", "2026-04-01"),
        ("/privacy.html", "yearly", "0.3", "2026-03-23"),
    ]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for path, freq, priority, lastmod in static_pages:
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base}{path}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append(f"  </url>")

    # Product pages (重複URL防止のため slug を set で管理)
    seen_slugs: set[str] = set()
    for p in products:
        slug = slug_map.get(p.name)
        if not slug or slug in seen_slugs:
            continue
        if not any(p.prices.get(s, 0) > 0 for s in SHOP_IDS):
            continue
        seen_slugs.add(slug)
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base}/box/{slug}.html</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <changefreq>daily</changefreq>")
        lines.append(f"    <priority>0.7</priority>")
        lines.append(f"  </url>")

    # Weekly hot-boxes articles (archived)
    weekly_dir = project_root / "weekly"
    if weekly_dir.exists():
        for wf in sorted(weekly_dir.glob("*.html")):
            if wf.name == "index.html":
                continue
            lines.append(f"  <url>")
            lines.append(f"    <loc>{base}/weekly/{wf.name}</loc>")
            lines.append(f"    <lastmod>{today}</lastmod>")
            lines.append(f"    <changefreq>weekly</changefreq>")
            lines.append(f"    <priority>0.8</priority>")
            lines.append(f"  </url>")

    lines.append("</urlset>")
    lines.append("")

    sitemap_path = project_root / "sitemap.xml"
    sitemap_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Updated sitemap.xml (%d URLs)", len([l for l in lines if "<loc>" in l]))


def _generate_ranking_summary(
    products: list[MasterProduct],
    project_root: Path,
) -> str:
    """トップページ用の週間上昇ランキングサマリーを生成する。"""
    history_dir = project_root / "data" / "history"
    if not history_dir.exists():
        return ""

    files = sorted(history_dir.glob("*.json"))
    if len(files) < 2:
        return ""

    today_file = files[-1]
    week_ago_idx = max(0, len(files) - 8)
    week_ago_file = files[week_ago_idx]

    today_data = json.loads(today_file.read_text(encoding="utf-8"))
    week_ago_data = json.loads(week_ago_file.read_text(encoding="utf-8"))

    today_prices = {item["name"]: item.get("max_price", 0) for item in today_data}
    week_ago_prices = {item["name"]: item.get("max_price", 0) for item in week_ago_data}

    slug_map = {p.name: _generate_slug(p.name) for p in products}
    changes = []
    for p in products:
        if p.category not in ("sv", "mega"):
            continue
        tp = today_prices.get(p.name, 0)
        wp = week_ago_prices.get(p.name, 0)
        if tp <= 0 or wp <= 0:
            continue
        diff = tp - wp
        if diff > 0:
            pct = (diff / wp) * 100
            changes.append({"name": p.name, "slug": slug_map.get(p.name, ""), "diff": diff, "pct": pct})

    top5 = sorted(changes, key=lambda x: x["diff"], reverse=True)[:5]
    if not top5:
        return ""

    items_html = ""
    for c in top5:
        items_html += (
            f'<li>'
            f'<span class="rs-name"><a href="box/{c["slug"]}.html">{c["name"]}</a></span>'
            f'<span class="rs-change" style="color:#dc2626">+¥{c["diff"]:,} (+{c["pct"]:.1f}%)</span>'
            f'</li>'
        )

    return (
        '<div class="ranking-summary">'
        '<div class="rs-card">'
        '<h3><a href="ranking.html">週間 上昇ランキング</a></h3>'
        f'<ul class="rs-list">{items_html}</ul>'
        '<a href="ranking.html" class="rs-more">もっと見る &rarr;</a>'
        '</div>'
        '</div>'
    )


def generate_ranking_page(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """週間の上昇ランキングページをグラフ付きで生成する。"""
    history_dir = project_root / "data" / "history"
    if not history_dir.exists():
        return

    files = sorted(history_dir.glob("*.json"))
    if len(files) < 2:
        logger.info("Not enough history data for ranking page")
        return

    today_file = files[-1]
    # 7日前のデータ（なければ最も古いデータ）
    week_ago_idx = max(0, len(files) - 8)
    week_ago_file = files[week_ago_idx]

    today_data = json.loads(today_file.read_text(encoding="utf-8"))
    week_ago_data = json.loads(week_ago_file.read_text(encoding="utf-8"))

    today_prices = {item["name"]: item.get("max_price", 0) for item in today_data}
    week_ago_prices = {item["name"]: item.get("max_price", 0) for item in week_ago_data}

    # 差分計算（カテゴリ付き）
    changes = []
    slug_map = {p.name: _generate_slug(p.name) for p in products}
    cat_map = {p.name: p.category for p in products}
    for p in products:
        tp = today_prices.get(p.name, 0)
        wp = week_ago_prices.get(p.name, 0)
        if tp <= 0 or wp <= 0:
            continue
        diff = tp - wp
        pct = (diff / wp) * 100 if wp > 0 else 0
        changes.append({
            "name": p.name,
            "slug": slug_map.get(p.name, ""),
            "category": cat_map.get(p.name, ""),
            "today": tp,
            "week_ago": wp,
            "diff": diff,
            "pct": pct,
        })

    # MEGA+SV: 上昇TOP5
    sv_mega = [c for c in changes if c["category"] in ("sv", "mega")]
    sv_gainers = sorted([c for c in sv_mega if c["diff"] > 0], key=lambda x: x["diff"], reverse=True)[:10]

    # S&S: 高騰TOP3のみ
    ss = [c for c in changes if c["category"] == "ss"]
    ss_gainers = sorted([c for c in ss if c["diff"] > 0], key=lambda x: x["diff"], reverse=True)[:3]

    # SV+MEGA全BOXの平均上昇額・上昇率
    sv_mega_all = [c for c in changes if c["category"] in ("sv", "mega") and c["week_ago"] > 0]
    if sv_mega_all:
        avg_diff = sum(c["diff"] for c in sv_mega_all) / len(sv_mega_all)
        avg_pct = sum(c["pct"] for c in sv_mega_all) / len(sv_mega_all)
    else:
        avg_diff = 0
        avg_pct = 0

    today_str = today_file.stem
    week_ago_str = week_ago_file.stem

    # 直近7日分の価格推移データ（グラフ用）
    recent_files = files[-8:] if len(files) >= 8 else files
    chart_dates = [f.stem for f in recent_files]

    # 日次データキャッシュ（何度も読まないように）
    daily_cache = []
    for f in recent_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        daily_cache.append({d["name"]: d.get("max_price", 0) for d in data})

    def _short_name(name: str) -> str:
        short = re.sub(r"^(MEGA|SV|S&S)\s*(拡張パック|強化拡張パック|ハイクラスパック|拡張パックDX)\s*", "", name)
        return re.sub(r"[「」]", "", short)

    chart_labels_js = json.dumps(chart_dates, ensure_ascii=False)

    # SV+MEGA全BOXの日次平均価格
    sv_mega_names = [p.name for p in products if p.category in ("sv", "mega")]
    daily_avgs = []
    for dc in daily_cache:
        prices = [dc.get(n, 0) for n in sv_mega_names if dc.get(n, 0) > 0]
        daily_avgs.append(round(sum(prices) / len(prices)) if prices else 0)
    avg_chart_data_js = json.dumps(daily_avgs)

    def _build_mini_charts(items: list, prefix: str, color: str) -> str:
        """各BOXごとの個別ミニグラフHTMLとJSを生成"""
        html_parts = []
        js_parts = []
        for i, item in enumerate(items):
            daily_prices = [dc.get(item["name"], 0) for dc in daily_cache]
            canvas_id = f"{prefix}Chart{i}"
            short = _short_name(item["name"])
            sign = "+" if item["diff"] > 0 else ""
            diff_color = "#dc2626" if item["diff"] > 0 else "#2563eb"
            arrow = "↑" if item["diff"] > 0 else "↓"
            html_parts.append(
                f'<div class="mini-chart-card">'
                f'<div class="mc-header">'
                f'<a href="box/{item["slug"]}.html" class="mc-name">{short}</a>'
                f'<span class="mc-price">¥{item["today"]:,}</span>'
                f'<span class="mc-diff" style="color:{diff_color}">{arrow}{sign}¥{item["diff"]:,} ({sign}{item["pct"]:.1f}%)</span>'
                f'</div>'
                f'<canvas id="{canvas_id}" height="120"></canvas>'
                f'</div>'
            )
            data_js = json.dumps(daily_prices)
            js_parts.append(f"""
new Chart(document.getElementById('{canvas_id}'), {{
  type: 'line',
  data: {{
    labels: {chart_labels_js},
    datasets: [{{ data: {data_js}, borderColor: '{color}', borderWidth: 2, fill: true,
      backgroundColor: '{color}22', tension: 0.3, pointRadius: 2 }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ font: {{ size: 10 }}, maxRotation: 0 }} }},
      y: {{ ticks: {{ callback: v => '¥' + v.toLocaleString(), font: {{ size: 10 }} }} }}
    }}
  }}
}});""")
        return "\n".join(html_parts), "\n".join(js_parts)

    sv_gain_html, sv_gain_js = _build_mini_charts(sv_gainers, "svUp", "#dc2626")
    ss_gain_html, ss_gain_js = _build_mini_charts(ss_gainers, "ssUp", "#f59e0b")

    def _make_table(items: list) -> str:
        if not items:
            return '<p class="no-data">変動なし</p>'
        rows = []
        for i, c in enumerate(items, 1):
            sign = "+" if c["diff"] > 0 else ""
            color = "#dc2626" if c["diff"] > 0 else "#2563eb"
            arrow = "↑" if c["diff"] > 0 else "↓"
            rows.append(
                f'<tr>'
                f'<td class="rank">{i}</td>'
                f'<td class="pname"><a href="box/{c["slug"]}.html">{c["name"]}</a></td>'
                f'<td class="price">¥{c["today"]:,}</td>'
                f'<td style="color:{color};font-weight:700">{arrow} {sign}¥{c["diff"]:,} ({sign}{c["pct"]:.1f}%)</td>'
                f'</tr>'
            )
        return (
            '<table class="ranking-table">'
            '<tr><th>順位</th><th>商品名</th><th>現在価格</th><th>週間変動</th></tr>'
            + "\n".join(rows)
            + '</table>'
        )

    sv_gainers_table = _make_table(sv_gainers)
    ss_gainers_table = _make_table(ss_gainers)

    # JSON-LD 構造化データ (ItemList + BreadcrumbList + Article)
    ranking_products = []
    for c in sv_gainers + ss_gainers:
        ranking_products.append({
            "@type": "Product",
            "name": c["name"],
            "url": f"https://pokeca-box-hikaku.com/box/{c['slug']}.html",
            "image": "https://pokeca-box-hikaku.com/ogp.jpg",
            "brand": {"@type": "Brand", "name": "ポケモンカードゲーム"},
            "offers": {
                "@type": "Offer",
                "price": c["today"],
                "priceCurrency": "JPY",
                "availability": "https://schema.org/InStock",
            },
        })

    ranking_itemlist_obj = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "ポケカBOX 週間上昇ランキング",
        "description": f"ポケモンカード未開封BOX 週間上昇ランキング ({week_ago_str} → {today_str})",
        "numberOfItems": len(ranking_products),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": item}
            for i, item in enumerate(ranking_products)
        ],
    }
    ranking_breadcrumb_obj = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"},
            {"@type": "ListItem", "position": 2, "name": "週間上昇ランキング", "item": "https://pokeca-box-hikaku.com/ranking.html"},
        ],
    }
    ranking_article_obj = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "ポケカBOX 週間上昇ランキング",
        "description": "ポケモンカード未開封BOXの買取価格 週間上昇ランキング。直近7日間で最も値上がり・値下がりしたBOXをグラフ付きで紹介。毎日自動更新。",
        "datePublished": today_str,
        "dateModified": today_str,
        "image": "https://pokeca-box-hikaku.com/ogp.jpg",
        "author": {"@type": "Organization", "name": "ポケカ買取チェッカー編集部"},
        "publisher": {
            "@type": "Organization",
            "name": "ポケカ買取チェッカー",
            "logo": {"@type": "ImageObject", "url": "https://pokeca-box-hikaku.com/ogp.png"},
        },
        "mainEntityOfPage": "https://pokeca-box-hikaku.com/ranking.html",
    }
    ranking_jsonld = (
        '<script type="application/ld+json">\n'
        + json.dumps(ranking_itemlist_obj, ensure_ascii=False, indent=2)
        + '\n</script>\n'
        '<script type="application/ld+json">\n'
        + json.dumps(ranking_breadcrumb_obj, ensure_ascii=False, indent=2)
        + '\n</script>\n'
        '<script type="application/ld+json">\n'
        + json.dumps(ranking_article_obj, ensure_ascii=False, indent=2)
        + '\n</script>'
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Preconnect hints for Core Web Vitals -->
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="preconnect" href="https://h.accesstrade.net">
<meta name="description" content="ポケカ未開封BOXの買取価格 週間上昇ランキング。直近7日間で最も値上がり・値下がりしたBOXをグラフ付きで紹介。毎日自動更新。">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/ranking.html">
<meta property="og:title" content="ポケカBOX 上昇ランキング｜ポケカ買取チェッカー">
<meta property="og:description" content="ポケカ未開封BOXの買取価格 週間上昇ランキング。直近7日間の変動をグラフ付きで紹介。">
<meta property="og:type" content="article">
<meta property="og:url" content="https://pokeca-box-hikaku.com/ranking.html">
<meta property="og:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<meta property="og:site_name" content="ポケカ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="ポケカBOX 上昇ランキング｜ポケカ買取チェッカー">
<meta name="twitter:description" content="ポケカ未開封BOXの買取価格 週間上昇ランキング。毎日自動更新。">
<title>ポケカBOX 週間上昇ランキング｜ポケカ買取チェッカー</title>
{ranking_jsonld}
<!-- Google AdSense -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RPTS6CRTCS"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-RPTS6CRTCS');
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{{--bg:#f6f7fb;--card:#fff;--border:#e5e7eb;--text:#111827;--text-sub:#6b7280;--accent:#6366f1}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:var(--bg);color:var(--text);line-height:1.8}}
.header{{position:sticky;top:0;z-index:100;height:56px;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;padding:0 20px}}
.header a{{text-decoration:none}}
.header h1{{font-size:18px;font-weight:700;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.wrap{{max-width:1240px;margin:0 auto;padding:32px 16px 48px}}
.content-layout{{display:flex;gap:24px;align-items:flex-start}}
.content-layout .main-card{{flex:1;min-width:0}}
.article-nav{{width:180px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}}
.article-nav-title{{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}}
.article-nav a{{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4;transition:all .2s}}
.article-nav a:hover{{color:var(--accent);border-left-color:var(--accent)}}
.article-nav a.current{{color:var(--accent);border-left-color:var(--accent);font-weight:600}}
.article-nav-sub{{font-size:12px;font-weight:700;margin:14px 0 6px;color:#b91c1c;padding-top:10px;border-top:1px solid var(--border)}}
@media(max-width:1023px){{.content-layout{{display:block}}.article-nav{{display:none}}}}
.breadcrumb{{font-size:12px;color:var(--text-sub);margin-bottom:20px}}
.breadcrumb a{{color:var(--accent);text-decoration:none}}
.main-card{{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:32px 28px;margin-bottom:24px}}

.main-card h2{{font-size:22px;font-weight:700;margin-bottom:8px}}
.meta{{font-size:12px;color:var(--text-sub);margin-bottom:24px}}
.section-title{{font-size:17px;font-weight:700;margin:32px 0 16px;padding-bottom:8px;border-bottom:2px solid var(--accent)}}
.section-title.up{{color:#dc2626}}
.section-title.down{{color:#2563eb}}
.chart-wrap{{margin:24px 0;background:#fff;border-radius:8px;padding:16px}}
.chart-wrap canvas{{max-height:320px}}
.ranking-table{{width:100%;border-collapse:collapse;font-size:14px}}
.ranking-table th{{background:#f9fafb;padding:10px 12px;text-align:left;font-size:12px;color:var(--text-sub);border-bottom:2px solid var(--border)}}
.ranking-table td{{padding:10px 12px;border-bottom:1px solid var(--border)}}
.ranking-table .rank{{width:40px;text-align:center;font-weight:700;color:var(--accent)}}
.ranking-table .pname a{{color:var(--text);text-decoration:none}}
.ranking-table .pname a:hover{{color:var(--accent);text-decoration:underline}}
.ranking-table .price{{white-space:nowrap}}
.no-data{{color:var(--text-sub);font-size:14px}}
.mini-charts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:8px}}
.mini-chart-card{{background:#fff;border-radius:10px;border:1px solid var(--border);padding:14px 16px}}
.mc-header{{margin-bottom:8px}}
.mc-name{{font-size:14px;font-weight:700;color:var(--text);text-decoration:none;display:block}}
.mc-name:hover{{color:var(--accent)}}
.mc-price{{font-size:18px;font-weight:700;margin-right:8px}}
.mc-diff{{font-size:13px;font-weight:700}}
.avg-stats{{display:flex;gap:24px;flex-wrap:wrap}}
.avg-item{{background:#f9fafb;border-radius:8px;padding:12px 20px;flex:1;min-width:140px;text-align:center}}
.avg-label{{display:block;font-size:12px;color:var(--text-sub);margin-bottom:4px}}
.avg-value{{font-size:22px;font-weight:700}}
.cta{{display:block;text-align:center;padding:14px;background:linear-gradient(135deg,#6366f1,#818cf8);color:#fff;border-radius:10px;text-decoration:none;font-weight:600;margin-top:32px}}
.footer{{text-align:center;color:var(--text-sub);font-size:12px;margin-top:32px}}
@media(max-width:640px){{.ranking-table{{font-size:12px}}.ranking-table td,.ranking-table th{{padding:8px 6px}}.main-card{{padding:20px 16px}}}}
</style>
</head>
<body>
<div class="header"><a href="index.html"><h1>ポケカ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="index.html">トップ</a> &gt; 週間上昇ランキング</div>

<div class="content-layout">
<nav class="article-nav">
<div class="article-nav-title">一般記事</div>
<a href="index.html">買取価格比較</a>
<a href="weekly/">🔥 今週の急上昇記事</a>
<a href="ranking.html" class="current">上昇ランキング</a>
<a href="kaitori-tips.html">BOX買取のコツ</a>
<a href="shop-hikaku.html">8店舗比較</a>
<a href="single-card-tips.html">シングル売り</a>
<a href="psa-guide.html">PSA鑑定ガイド</a>
<a href="mercari-hikaku.html">メルカリ・スニダン比較</a>
<a href="shrink-nashi.html">シュリンクなしBOX</a>
<a href="box-toushi.html">BOX投資の始め方</a>
<a href="restock-guide.html">再販情報の見つけ方</a>
<a href="release-schedule-2026.html">📅 2026年 新弾カレンダー</a>
<a href="price-pattern-guide.html">📈 相場5段階パターン</a>
<div class="article-nav-sub">🔥 BOX深掘り特集</div>
<a href="151-spotlight.html">【特集】ポケモンカード151高騰</a>
<a href="inferno-x-spotlight.html">【特集】インフェルノX高騰</a>
<a href="kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>
<a href="chouden-breaker-spotlight.html">【特集】超電ブレイカー高騰</a>
<a href="clay-burst-spotlight.html">【特集】クレイバースト高騰</a>
<a href="ninja-spinner-spotlight.html">【特集】ニンジャスピナー高騰</a>
<div class="article-nav-sub" style="color:#6d28d9">📘 掘り下げガイド</div>
<a href="zeppan-ranking-2026-03.html">📊 S&amp;S以降 絶版BOXランキング</a>
<a href="lizardon-box-guide.html">🔥 リザードン高騰BOX完全ガイド</a>
<a href="mega-pack-compare.html">⚡ MEGA拡張パック完全比較</a>
<a href="kokuen-vs-rocket.html">⚔️ 黒炎 vs ロケット団の栄光</a>
<a href="mega-lizardon-x-guide.html">メガリザードンXex MUR/SAR</a>
<a href="lizardon-sar-kokuen-guide.html">リザードンex SAR(黒炎)</a>
<a href="erika-sar-guide.html">エリカの招待 SAR</a>
<a href="pigeot-sar-guide.html">ピジョットex SAR</a>
<a href="masterball-mirror-guide.html">151マスターボールミラー</a>
<a href="kokuen-atari-guide.html">黒炎 当たりカード完全ガイド</a>
</nav>

<div class="main-card">
<h2>ポケカBOX 週間上昇ランキング</h2>
<div class="meta">更新: {update_date}　比較期間: {week_ago_str} → {today_str}（直近7日間）</div>

<h3 class="section-title up">SV・MEGA 上昇 TOP10</h3>
<div class="mini-charts">{sv_gain_html}</div>

<h3 class="section-title up" style="margin-top:48px">S&amp;S 上昇 TOP3</h3>
<div class="mini-charts">{ss_gain_html}</div>

<h3 class="section-title" style="margin-top:48px">SV・MEGA 全BOX平均</h3>
<div class="avg-stats">
<div class="avg-item"><span class="avg-label">平均上昇額</span><span class="avg-value" style="color:{'#dc2626' if avg_diff >= 0 else '#2563eb'}">{"+" if avg_diff >= 0 else ""}¥{avg_diff:,.0f}</span></div>
<div class="avg-item"><span class="avg-label">平均上昇率</span><span class="avg-value" style="color:{'#dc2626' if avg_pct >= 0 else '#2563eb'}">{"+" if avg_pct >= 0 else ""}{avg_pct:.1f}%</span></div>
</div>
<div class="chart-wrap" style="margin-top:16px">
<canvas id="avgChart" height="200"></canvas>
</div>

<a href="index.html" class="cta">全66商品の買取価格を比較する &rarr;</a>

<div class="ad" style="margin-top:32px;text-align:center">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
<div class="ad" style="margin-top:16px;text-align:center">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
</div>
</div>

<div class="footer">&copy; ポケカ買取チェッカー</div>
</div>
<script>
{sv_gain_js}
{ss_gain_js}
new Chart(document.getElementById('avgChart'), {{
  type: 'line',
  data: {{
    labels: {chart_labels_js},
    datasets: [{{
      label: 'SV・MEGA 平均買取価格',
      data: {avg_chart_data_js},
      borderColor: '#6366f1',
      backgroundColor: '#6366f122',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 3
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: true, position: 'bottom' }} }},
    scales: {{
      y: {{ ticks: {{ callback: v => '¥' + v.toLocaleString() }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    out_path = project_root / "ranking.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("Generated ranking page: %s", out_path)


def generate_weekly_article(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """Generate /weekly/YYYY-wWW.html and /weekly/index.html archive.

    The file for the current ISO week is overwritten on each cron run
    with the latest data. Past weeks' files are left untouched and serve
    as permanent archives.
    """
    history_dir = project_root / "data" / "history"
    if not history_dir.exists():
        logger.info("No history dir; skipping weekly article")
        return

    files = sorted(history_dir.glob("*.json"))
    if len(files) < 8:
        logger.info("Insufficient history for weekly article (need >= 8 days)")
        return

    # Import the template module lazily to keep top-level lean
    import sys
    sys.path.insert(0, str(project_root))
    from scripts.weekly_article_template import build_weekly_html, build_weekly_index_html

    # Today = latest snapshot, week ago = 7 days before
    today_file = files[-1]
    week_ago_idx = max(0, len(files) - 8)
    week_ago_file = files[week_ago_idx]

    today_data = json.loads(today_file.read_text(encoding="utf-8"))
    week_ago_data = json.loads(week_ago_file.read_text(encoding="utf-8"))

    today_prices = {item["name"]: item.get("max_price", 0) for item in today_data}
    week_ago_prices = {item["name"]: item.get("max_price", 0) for item in week_ago_data}

    # Build changes list
    slug_map = {p.name: _generate_slug(p.name) for p in products}
    cat_map = {p.name: p.category for p in products}

    all_changes = []
    for p in products:
        tp = today_prices.get(p.name, 0)
        wp = week_ago_prices.get(p.name, 0)
        if tp <= 0 or wp <= 0:
            continue
        diff = tp - wp
        pct = (diff / wp) * 100 if wp > 0 else 0
        all_changes.append({
            "name": p.name,
            "slug": slug_map.get(p.name, ""),
            "category": cat_map.get(p.name, ""),
            "today": tp,
            "week_ago": wp,
            "diff": diff,
            "pct": pct,
        })

    # Split by category: SV+MEGA main ranking (TOP10), S&S secondary (TOP3)
    sv_mega_changes = [c for c in all_changes if c["category"] in ("sv", "mega")]
    ss_changes = [c for c in all_changes if c["category"] == "ss"]

    sv_mega_gainers = sorted([c for c in sv_mega_changes if c["diff"] > 0],
                             key=lambda x: x["diff"], reverse=True)
    ss_gainers = sorted([c for c in ss_changes if c["diff"] > 0],
                        key=lambda x: x["diff"], reverse=True)

    top_gainers = sv_mega_gainers[:10]       # main TOP10 (SV+MEGA)
    minor_gainers = sv_mega_gainers[10:15]   # next 5 (SV+MEGA)
    ss_top_gainers = ss_gainers[:3]          # S&S TOP3 secondary section

    if not top_gainers:
        logger.info("No SV+MEGA gainers this week; skipping weekly article")
        return

    # Build per-BOX 7-day price history for mini charts
    recent_files = files[-8:]  # last 8 days (including today)
    chart_dates = [f.stem for f in recent_files]
    daily_cache: list[dict[str, int]] = []
    for f in recent_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        daily_cache.append({d["name"]: d.get("max_price", 0) for d in data})

    chart_history: dict[str, list[int]] = {}
    for c in top_gainers + ss_top_gainers:
        series = [dc.get(c["name"], 0) for dc in daily_cache]
        chart_history[c["slug"]] = series

    # Determine ISO week from today_file filename (YYYY-MM-DD.json)
    today_str = today_file.stem
    week_ago_str = week_ago_file.stem
    today_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
    iso_year, iso_week, _ = today_dt.isocalendar()

    weekly_dir = project_root / "weekly"
    weekly_dir.mkdir(exist_ok=True)

    # Only publish weekly article on Sunday (Python weekday=6).
    # On other days, keep the existing file untouched and only regenerate the
    # archive index below.
    if today_dt.weekday() == 6:
        out_path = weekly_dir / f"{iso_year}-w{iso_week:02d}.html"
        html = build_weekly_html(
            year=iso_year,
            week_no=iso_week,
            today_str=today_str,
            week_ago_str=week_ago_str,
            update_date=update_date,
            top_gainers=top_gainers,
            minor_gainers=minor_gainers,
            ss_top_gainers=ss_top_gainers,
            all_changes=sv_mega_changes,  # stats use SV+MEGA only (main set)
            chart_dates=chart_dates,
            chart_history=chart_history,
        )
        out_path.write_text(html, encoding="utf-8")
        logger.info("Generated weekly article: %s (%d gainers)", out_path, len(top_gainers))
    else:
        logger.info(
            "Weekly article publish is Sunday-only; today=%s (weekday=%d), skipping write",
            today_dt, today_dt.weekday()
        )

    # Build archive index from all existing weekly files
    all_weekly_files = sorted(weekly_dir.glob("*.html"), reverse=True)
    week_entries = []
    for wf in all_weekly_files:
        if wf.name == "index.html":
            continue
        # Parse filename: 2026-w15.html
        m = re.match(r"(\d{4})-w(\d{2})\.html", wf.name)
        if not m:
            continue
        y, w = int(m.group(1)), int(m.group(2))

        # Extract published date and top gainer from the file if possible
        try:
            content = wf.read_text(encoding="utf-8")
            date_m = re.search(r"公開日:\s*(\d{4}-\d{2}-\d{2})", content)
            published_date = date_m.group(1) if date_m else f"{y}年第{w}週"
            # First BOX name in the ranking table (th after "順位")
            top_m = re.search(
                r'<td class="rank">1</td>\s*<td class="pname"><a[^>]*>([^<]+)</a>',
                content,
            )
            top_gainer_name = top_m.group(1) if top_m else "データなし"
        except Exception:
            published_date = f"{y}年第{w}週"
            top_gainer_name = "データなし"

        week_entries.append({
            "year": y,
            "week": w,
            "filename": wf.name,
            "title": f"{y}年 第{w}週 急上昇TOP10",
            "published_date": published_date,
            "top_gainer_name": top_gainer_name,
        })

    # Write archive index
    index_path = weekly_dir / "index.html"
    index_path.write_text(build_weekly_index_html(week_entries), encoding="utf-8")
    logger.info("Generated weekly index: %s (%d entries)", index_path, len(week_entries))
