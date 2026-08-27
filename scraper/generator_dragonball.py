"""ドラゴンボール版ページ(dragonball.html)を dragonball-template.html から生成する。

ポケカ側 generator.py / ワンピ側 generator_onepiece.py / ベイ側
generator_beyblade.py は無改修。個別商品ページは作らず、比較表1枚を出力し、
買取ガイド記事(build_dragonball_articles)へのリンクを差し込む。価格履歴は
data/history_db に保存し、前日比(y)に使う。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from html import escape
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


# 弾番号を持たず、商品名に英数字も無い商品のslug。自動生成だと "item" に
# 退化して個別ページのURLが衝突するため明示する。
_SLUG_OVERRIDES = {
    "スーパーダイバーズ アドバンスパック バトルオブサイヤン": "dv-battle-of-saiyan",
}


def _slug(name: str) -> str:
    """弾番号ベースの安定slug。個別ページ(dragonball/box/*.html)のURLになる。"""
    if name in _SLUG_OVERRIDES:
        return _SLUG_OVERRIDES[name]
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
    today = datetime.now(JST).strftime("%Y-%m-%d")

    def _entry(loc: str, freq: str, prio: str) -> str:
        return (f"  <url>\n    <loc>{loc}</loc>\n"
                f"    <lastmod>{today}</lastmod>\n"
                f"    <changefreq>{freq}</changefreq>\n"
                f"    <priority>{prio}</priority>\n  </url>\n")

    blocks = []
    if f"<loc>{SITE_URL}</loc>" not in xml:
        blocks.append(_entry(SITE_URL, "daily", "0.9"))
    for art in sorted((PROJECT_ROOT / "dragonball").glob("*.html")):
        loc = f"{SITE_URL}/{art.name}"
        if f"<loc>{loc}</loc>" not in xml:
            blocks.append(_entry(loc, "weekly", "0.8"))
    for box in sorted(BOX_DIR.glob("*.html")):
        loc = f"{SITE_URL}/box/{box.name}"
        if f"<loc>{loc}</loc>" not in xml:
            blocks.append(_entry(loc, "daily", "0.7"))
    if not blocks:
        return
    xml = xml.replace("</urlset>", "".join(blocks) + "</urlset>")
    path.write_text(xml, encoding="utf-8")
    logger.info("sitemap.xml: added %d dragonball URLs", len(blocks))


def _article_links_block() -> str:
    """買取ガイド記事のカードHTML。記事を足せば自動で並ぶ(単一ソースは
    build_dragonball_articles.HOWTO_ARTICLES)。"""
    try:
        from scraper.build_dragonball_articles import ATARI_ARTICLES, HOWTO_ARTICLES
    except Exception:
        logger.warning("dragonball articles not available; skip link block")
        return ""
    cards = []
    # トップに並べるのは4枚まで(ハウツー→当たりガイドの順で、買取価格の
    # 高い弾から並んでいるリストの先頭を採る)
    for h in (HOWTO_ARTICLES + ATARI_ARTICLES)[:4]:
        cards.append(
            f'<a class="blog-card" href="/dragonball/{h["slug"]}.html">'
            f'<h3>{escape(h["nav_label"])}</h3>'
            f'<p>{escape(h["meta_line"])}</p></a>'
        )
    return "".join(cards)


BOX_DIR = PROJECT_ROOT / "dragonball" / "box"

# 各店のドラゴンボール買取ページURL。判明した店だけ入れる。未設定の店は
# 自サイトの店舗ページだけをリンクする(誤URLを載せないため)。
SHOP_DB_URLS: dict[str, str] = {}


def _esc(s) -> str:
    return escape(str(s), quote=True)


def _fmt(v: int) -> str:
    return f"¥{v:,}"


def _history_series(product_name: str) -> list[list]:
    """[epoch_ms, その日の最高買取額] の時系列。history_db の日次JSONから作る。"""
    pts: list[list] = []
    if not HISTORY_DB_DIR.exists():
        return pts
    for f in sorted(HISTORY_DB_DIR.glob("*.json")):
        try:
            rows = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for x in rows:
            if x.get("name") != product_name:
                continue
            price = x.get("max_price", 0)
            if price > 0:
                try:
                    dt = datetime.strptime(f.stem, "%Y-%m-%d").replace(tzinfo=JST)
                except ValueError:
                    break
                pts.append([int(dt.timestamp() * 1000), price])
            break
    return pts


def _prev_max(product_name: str) -> int:
    if not HISTORY_DB_DIR.exists():
        return 0
    files = sorted(HISTORY_DB_DIR.glob("*.json"))
    if len(files) < 2:
        return 0
    try:
        rows = json.loads(files[-2].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    for x in rows:
        if x.get("name") == product_name:
            return x.get("max_price", 0)
    return 0


def _chart_section(p: MasterProduct) -> str:
    """個別ページ用のインラインChart.js。データ源は自前のhistory_dbのみ。"""
    pts = _history_series(p.name)
    if len(pts) < 2:
        return ""
    points_json = json.dumps(pts, ensure_ascii=False)
    rd = p.release_date or ""
    return f"""<h3 class="section-title">{_esc(p.name)} 価格推移</h3>
<div class="chart-wrap">
<div class="chart-periods">
  <button class="cp-btn active" data-period="all">全期間</button>
  <button class="cp-btn" data-period="3m">3ヶ月</button>
  <button class="cp-btn" data-period="1m">1ヶ月</button>
</div>
<canvas id="boxChart"></canvas>
<div class="chart-note">※ 4店舗の最高買取価格の推移</div>
</div>
<script>
(function(){{
var pts={points_json};
var rd="{rd}";
var ci=null;
function draw(period){{
  var now=Date.now(),cutoff=0;
  if(period==="3m")cutoff=now-90*86400000;
  else if(period==="1m")cutoff=now-30*86400000;
  var f=cutoff?pts.filter(function(p){{return p[0]>=cutoff}}):pts;
  if(!f.length)f=pts;
  var labels=f.map(function(p){{var d=new Date(p[0]);return d.getFullYear()+"/"+(d.getMonth()+1)+"/"+d.getDate()}});
  var data=f.map(function(p){{return p[1]}});
  var ridx=-1;
  if(rd){{var rt=new Date(rd+"T00:00:00+09:00").getTime();if(!cutoff||rt>=cutoff){{for(var i=0;i<f.length;i++){{if(f[i][0]>=rt){{ridx=i;break}}}}}}}}
  var ann=undefined;
  if(ridx>=0){{ann={{annotations:{{rl:{{type:"line",drawTime:"beforeDatasetsDraw",xMin:ridx,xMax:ridx,borderColor:"#ef4444",borderWidth:2,borderDash:[6,4],label:{{display:true,content:"発売日",position:"end",backgroundColor:"#ef4444",color:"#fff",font:{{size:11,weight:"bold"}},padding:{{top:3,bottom:3,left:6,right:6}},borderRadius:4}}}}}}}};}}
  if(ci)ci.destroy();
  ci=new Chart(document.getElementById("boxChart").getContext("2d"),{{
    type:"line",
    data:{{labels:labels,datasets:[{{label:"最高買取価格",data:data,borderColor:"#f57c00",backgroundColor:"rgba(245,124,0,.1)",fill:true,tension:0.3,pointRadius:f.length>60?0:2,pointHoverRadius:5,borderWidth:2}}]}},
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


def generate_dragonball_box_pages(products: list[MasterProduct], update_date: str) -> None:
    """商品ごとの個別ページ(dragonball/box/*.html)を生成する。

    買取価格が1店も付いていない商品(発売前など)はページを作らない。
    """
    template_path = PROJECT_ROOT / "dragonball-box-template.html"
    if not template_path.exists():
        logger.warning("dragonball-box-template.html not found, skipping box pages")
        return
    template = template_path.read_text(encoding="utf-8")
    BOX_DIR.mkdir(parents=True, exist_ok=True)

    by_cat: dict[str, list[MasterProduct]] = {}
    for p in products:
        by_cat.setdefault(p.category, []).append(p)

    total = sum(1 for p in products if p.prices)
    generated = 0
    for p in products:
        active = {sid: p.prices[sid] for sid in SHOP_IDS if p.prices.get(sid, 0) > 0}
        if not active:
            continue
        slug = _slug(p.name)
        max_price = max(active.values())
        low_price = min(active.values())
        max_sid = max(active, key=active.get)
        max_shop = SHOP_NAMES.get(max_sid, max_sid)
        shop_count = len(active)
        diff = max_price - p.retail_price if p.retail_price > 0 else 0

        rows = []
        for sid, price in sorted(((s, p.prices.get(s, 0)) for s in SHOP_IDS),
                                 key=lambda x: x[1], reverse=True):
            name = SHOP_NAMES.get(sid, sid)
            shop_cell = f'<a href="../../shop/{sid}.html">{name}</a>'
            url = SHOP_DB_URLS.get(sid)
            if url:
                shop_cell += (f'<a class="shop-official" href="{url}" target="_blank" '
                              f'rel="noopener noreferrer">公式↗</a>')
            if price > 0:
                cls = ' class="best"' if price == max_price else ""
                rows.append(f'<tr{cls}><td class="shop-name">{shop_cell}</td>'
                            f'<td>{_fmt(price)}</td></tr>')
            else:
                rows.append(f'<tr><td class="shop-name">{shop_cell}</td>'
                            f'<td class="no-price">取扱なし</td></tr>')
        price_table = ('<table class="price-table">\n<tr><th>買取店</th><th>買取価格</th></tr>\n'
                       + "\n".join(rows) + "\n</table>")

        related = [r for r in by_cat.get(p.category, [])
                   if r.name != p.name and any(r.prices.get(s, 0) > 0 for s in SHOP_IDS)]
        related_html = "\n".join(
            f'    <a href="{_slug(r.name)}.html" class="related-link">{_esc(r.name)}</a>'
            for r in related[:8])

        trend = ""
        prev = _prev_max(p.name)
        if prev and max_price:
            ch = max_price - prev
            if ch > 0:
                trend = ('<div class="trend-comment" style="color:#16a34a">'
                         f'<span class="trend-icon">📈</span>前日比 +{_fmt(ch)} 上昇中</div>')
            elif ch < 0:
                trend = ('<div class="trend-comment" style="color:#dc2626">'
                         f'<span class="trend-icon">📉</span>前日比 -{_fmt(abs(ch))} 下落</div>')

        product_ld = json.dumps({
            "@context": "https://schema.org", "@type": "Product", "name": p.name,
            "category": "ドラゴンボールカード / 未開封BOX",
            "offers": {"@type": "AggregateOffer", "priceCurrency": "JPY",
                       "highPrice": max_price, "lowPrice": low_price,
                       "offerCount": shop_count}}, ensure_ascii=False)
        breadcrumb_ld = json.dumps({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "ホーム",
                 "item": "https://pokeca-box-hikaku.com/"},
                {"@type": "ListItem", "position": 2, "name": "ドラゴンボール買取チェッカー",
                 "item": SITE_URL},
                {"@type": "ListItem", "position": 3, "name": p.name,
                 "item": f"{SITE_URL}/box/{slug}.html"},
            ]}, ensure_ascii=False)
        jsonld = ('<script type="application/ld+json">' + product_ld + "</script>\n"
                  '<script type="application/ld+json">' + breadcrumb_ld + "</script>")

        cat_label = CATEGORY_LABELS.get(p.category, "BOX")
        parts = [f"{_esc(p.name)}は"]
        rd_m = re.match(r"(\d{4})-(\d{2})-(\d{2})", p.release_date or "")
        if rd_m:
            rd_jp = f"{int(rd_m.group(1))}年{int(rd_m.group(2))}月{int(rd_m.group(3))}日"
            parts.append(f"{rd_jp}発売の{cat_label}です。")
        else:
            parts.append(f"{cat_label}です。")
        if p.retail_price:
            parts.append(f"参考定価は{_fmt(p.retail_price)}。")
        if low_price < max_price:
            parts.append(
                f"現在の未開封BOX買取価格は{_fmt(low_price)}〜{_fmt(max_price)}で、"
                f"最高値は{_esc(max_shop)}が提示しています（{shop_count}店舗掲載）。")
        else:
            parts.append(
                f"現在の未開封BOX買取価格は{_fmt(max_price)}"
                f"（{_esc(max_shop)}／{shop_count}店舗掲載）。")
        if p.desc:
            parts.append(_esc(p.desc))
        parts.append(
            "買取価格は封入されるトップレアの相場や在庫状況で日々変動します。"
            "売却を検討している場合は、上の価格表で4店舗の最新買取価格を比較し、"
            "価格推移グラフで底値・高値のタイミングを確認するのがおすすめです。")
        box_overview = (f'<h3 class="section-title">{_esc(p.name)}の買取について</h3>'
                        f'<p class="product-desc">{"".join(parts)}</p>')
        if (PROJECT_ROOT / "dragonball" / "hatsubai-schedule.html").exists():
            box_overview += (
                '<p class="product-desc" style="margin-top:6px">'
                '▶ 今後の新弾の発売日とBOX定価は '
                '<a href="/dragonball/hatsubai-schedule.html" '
                'style="color:var(--accent);font-weight:700">'
                'ドラゴンボールカード 新弾発売スケジュール</a> にまとめています。</p>')

        page = template
        for k, v in {
            "{{PRODUCT_NAME}}": _esc(p.name), "{{SLUG}}": slug,
            "{{ROBOTS}}": "index, follow", "{{JSONLD}}": jsonld,
            "{{UPDATE_DATE}}": update_date,
            "{{CATEGORY_LABEL}}": cat_label,
            "{{MAX_PRICE_TEXT}}": _fmt(max_price),
            "{{MAX_SHOP_NAME}}": _esc(max_shop),
            "{{SHOP_COUNT}}": str(shop_count),
            "{{RETAIL_PRICE_TEXT}}": _fmt(p.retail_price) if p.retail_price else "—",
            "{{DIFF_TEXT}}": (f"+{_fmt(diff)}" if diff > 0 else
                              (f"-{_fmt(abs(diff))}" if diff < 0 else "—")),
            "{{PRICE_TABLE}}": price_table,
            "{{RELATED_LINKS}}": related_html,
            "{{TREND_COMMENT}}": trend,
            "{{PRODUCT_DESC}}": _esc(p.desc or ""),
            "{{HIT_CARDS}}": "",
            "{{TOTAL_PRODUCTS}}": str(total),
        }.items():
            page = page.replace(k, v)
        page = page.replace("<!-- {{CHART_SECTION}} -->", _chart_section(p))
        page = page.replace("<!-- {{BOX_OVERVIEW}} -->", box_overview)
        page = page.replace("<!-- {{BOX_IMAGE}} -->", "")
        # テンプレに素の形で残っている枠も潰す(コメント形式でない場合)
        for leftover in ("{{CHART_SECTION}}", "{{BOX_OVERVIEW}}", "{{BOX_IMAGE}}"):
            page = page.replace(leftover, "")

        (BOX_DIR / f"{slug}.html").write_text(page, encoding="utf-8")
        generated += 1

    logger.info("Generated %d dragonball box pages", generated)


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
    html = html.replace("{{ARTICLE_LINKS}}", _article_links_block())
    html = html.replace("{{UPDATE_DATE}}", update_date)

    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    generate_dragonball_box_pages(products, update_date)
    _append_dragonball_sitemap()
    return html
