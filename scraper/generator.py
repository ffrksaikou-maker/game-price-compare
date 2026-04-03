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
SHOP_IDS = ["morimori", "homura", "icchome", "runto", "sommelier", "kaikyo", "shouten", "rudeya"]

# Blog articles (newest first) - 記事追加時はここに1行足すだけ
BLOG_ARTICLES = [
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
    """Generate blog cards: left=random, right=latest article."""
    # Right: 最新記事 (固定 = BLOG_ARTICLES[0])
    latest = BLOG_ARTICLES[0]
    # Left candidates: 最新記事以外の全記事（JSでランダム選択）
    candidates = [a for a in BLOG_ARTICLES if a["url"] != latest["url"]]

    html = '<div class="blog-links" id="blogLinks">\n'
    # 左: ランダム候補（非表示、JSで1つ選んで表示）
    for article in candidates:
        html += (
            f'  <a href="{article["url"]}" class="blog-card blog-random" style="display:none"'
            f' onclick="gtag(\'event\',\'blog_click\',{{article:\'{article["url"]}\'}})">\n'
            f'    <h3>{article["title"]}</h3>\n'
            f'    <p>{article["desc"]}</p>\n'
            f'  </a>\n'
        )
    # 右: 最新記事（固定）
    html += (
        f'  <a href="{latest["url"]}" class="blog-card"'
        f' onclick="gtag(\'event\',\'blog_click\',{{article:\'{latest["url"]}\'}})">\n'
        f'    <h3>{latest["title"]}</h3>\n'
        f'    <p>{latest["desc"]}</p>\n'
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

    # Write output
    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    # Generate individual product pages
    generate_product_pages(products, project_root, update_date)

    return html


# ===== Slug generation =====

# Manual slug overrides for products with tricky names
SLUG_OVERRIDES = {
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
    "shouten": "買取商店",
    "rudeya": "買取ルデヤ",
}

SHOP_URLS = {
    "morimori": "https://www.morimori-kaitori.jp/",
    "homura": "https://kaitori-homura.com/",
    "icchome": "https://www.1-chome.com/",
    "runto": "https://runto666.com/",
    "sommelier": "https://somurie-kaitori.com/",
    "kaikyo": "https://www.mobile-ichiban.com/",
    "shouten": "https://www.kaitorishouten-co.jp/",
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
    if own_points:
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

        # Related links (same category, exclude self)
        related = [
            r for r in by_cat.get(p.category, [])
            if r.name != p.name and any(r.prices.get(s, 0) > 0 for s in SHOP_IDS)
        ]
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

        # JSON-LD for individual product
        product_jsonld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": p.name,
            "description": f"ポケモンカード {p.name} 未開封BOX 買取価格比較",
            "offers": {
                "@type": "AggregateOffer",
                "lowPrice": min(active_prices.values()),
                "highPrice": max_price,
                "priceCurrency": "JPY",
                "offerCount": shop_count,
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

    # Static pages
    static_pages = [
        ("/", "daily", "1.0"),
        ("/kaitori-tips.html", "monthly", "0.8"),
        ("/shop-hikaku.html", "monthly", "0.8"),
        ("/single-card-tips.html", "monthly", "0.8"),
        ("/psa-guide.html", "monthly", "0.8"),
        ("/mercari-hikaku.html", "monthly", "0.8"),
        ("/shrink-nashi.html", "monthly", "0.8"),
        ("/box-toushi.html", "monthly", "0.8"),
        ("/privacy.html", "yearly", "0.3"),
    ]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for path, freq, priority in static_pages:
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base}{path}</loc>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append(f"  </url>")

    # Product pages
    for p in products:
        slug = slug_map.get(p.name)
        if not slug:
            continue
        if not any(p.prices.get(s, 0) > 0 for s in SHOP_IDS):
            continue
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base}/box/{slug}.html</loc>")
        lines.append(f"    <changefreq>daily</changefreq>")
        lines.append(f"    <priority>0.7</priority>")
        lines.append(f"  </url>")

    lines.append("</urlset>")
    lines.append("")

    sitemap_path = project_root / "sitemap.xml"
    sitemap_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Updated sitemap.xml (%d URLs)", len([l for l in lines if "<loc>" in l]))
