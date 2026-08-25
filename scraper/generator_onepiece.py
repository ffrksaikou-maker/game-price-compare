"""ONE PIECE版ページ(onepiece.html)を onepiece-template.html から生成する軽量ジェネレータ。

ポケカ側 generator.py は無改修のまま。共通の店舗ID/店名/価格整形だけ流用する。
個別BOXページ(onepiece/box/*.html)・スニダングラフ・週間ランキングを生成する。
価格履歴は data/history_op に保存し、前日比(y)とグラフに使う。
"""

from __future__ import annotations

import json
import logging
import random
import re
from html import escape as _esc
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .generator import SHOP_IDS, SHOP_NAMES, _format_price
from .matcher import MasterProduct

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_OP_DIR = PROJECT_ROOT / "data" / "history_op"
SNKRDUNK_OP_DIR = PROJECT_ROOT / "data" / "snkrdunk_op"
BOX_DIR = PROJECT_ROOT / "onepiece" / "box"

CATEGORY_LABELS = {
    "op": "通常ブースター", "eb": "エクストラブースター",
    "prb": "プレミアムブースター", "st": "スタートデッキ",
}
# 店舗別ワンピ買取ページ(判明分。無い店は汎用トップ)
SHOP_OP_URLS = {
    "morimori": "https://www.morimori-kaitori.jp/category/2403",
    "homura": "https://kaitori-homura.com/products?q%5Bproduct_sub_category_id_eq%5D=132&q%5Bproduct_sub_category_product_category_id_eq%5D=14",
    "icchome": "https://www.1-chome.com/tradeCards?category=SEbO7gSBevo6KsPE",
    "runto": "https://runto666.com/product-category/onepiece/",
    "oku": "https://kaitori-oku.jp/category.html?cat1=340&cat2=364",
    "rudeya": "https://kaitori-rudeya.com/category/detail/224",
    "shinsoku": "https://shinsoku-tcg.com/yuso-kaitori?title=%E3%83%AF%E3%83%B3%E3%83%94%E3%83%BC%E3%82%B9",
    "kaikyo": "https://www.mobile-ichiban.com/",
    "collect_tendo": "https://x.com/collect_tendo",
}

# ===== BOX掘り下げ記事のレジストリ(トップからの導線+sitemap用) =====
# (ファイル名, タイトル, リード文)。ファイルが存在する記事だけリンクされる。
# トップのブログカード用レジストリは記事データ(article_data_onepiece)から自動生成。
# (ファイル名, カードタイトル, リード文)。記事を追加すればここも自動で増える。
try:
    from scraper.article_data_onepiece import ARTICLES as _OP_ARTICLE_DATA
    ONEPIECE_ARTICLES = [
        (f"{a['slug']}-atari-guide.html", a["crumb"], a["og_desc"])
        for a in _OP_ARTICLE_DATA
    ]
except Exception:  # 記事データが読めない環境でも生成は続行
    ONEPIECE_ARTICLES = []

# ハウツー記事(atari自動生成とは別枠・手動append)
ONEPIECE_ARTICLES.append(
    ("kaitori-hikaku.html", "ワンピBOX買取比較・高く売るコツ",
     "最大9店舗の実データでワンピBOXを高く売るコツと店舗の選び方を解説。"))
ONEPIECE_ARTICLES.append(
    ("toushi.html", "ワンピBOX投資の始め方",
     "値上がりしやすいBOXの特徴・予算別の始め方・保管・リスクを解説。"))
ONEPIECE_ARTICLES.append(
    ("kougaku-ranking.html", "高額BOXランキング・絶版ガイド",
     "全弾の最高買取・定価比ランキングと、絶版の実態・ブロックアイコン制度の影響を解説。"))
ONEPIECE_ARTICLES.append(
    ("op-17-forecast.html", "【予想】世界最強の戦士(OP-17) BOX相場3シナリオ",
     "8/22発売の4周年弾OP-17のBOX相場を過去弾の実データから3シナリオで予想。新レアリティL-SPと値上げの影響も解説。"))
ONEPIECE_ARTICLES.append(
    ("shikou-treasure-get.html", "4周年！四皇トレジャーゲット全7種",
     "8/22配布開始の4周年プロモパック全7種を解説。当たりのルフィP-099の相場と、未開封で売るか開封するかの期待値検証。"))
ONEPIECE_ARTICLES.append(
    ("nika-luffy-comipara.html", "ニカルフィ コミパラ徹底解説",
     "OP05-119の買取80万・PSA10相場133万、288BOXに1枚の封入率と取得率71.7%が示す状態難を解説。"))
ONEPIECE_ARTICLES.append(
    ("red-comipara-guide.html", "レッドコミパラ3種 徹底解説",
     "OP-13のルフィ230万・エース80万・サボ60万。631BOXに1枚の封入率と1年9倍の価格推移を解説。"))
ONEPIECE_ARTICLES.append(
    ("roger-gold-comipara.html", "ロジャー 金コミパラ徹底解説",
     "OP09-118の買取70万・PSA10 109万。360BOXに1枚の封入率と、初動割れから2.8倍に戻した推移。"))
ONEPIECE_ARTICLES.append(
    ("comipara-ranking.html", "歴代コミパラ相場ランキング",
     "全22弾のコミックパラレルを横断ランキング。最高は230万、TOP12の6枚がルフィ。BOX買取と連動しない理由も解説。"))
ONEPIECE_ARTICLES.append(
    ("psa-guide.html", "ワンピカードPSA鑑定ガイド",
     "PSA10相場は素体買取の1.4〜1.66倍、取得率は71.7〜93.2%。出すべきカードの判断基準を実データで解説。"))
ONEPIECE_ARTICLES.append(
    ("box-price-pattern.html", "BOX相場の値動きパターン",
     "最大9店舗の実データで全弾の値動きを横断分析。新しい弾ほど下がる傾向と、カード相場と連動しない理由。"))
ONEPIECE_ARTICLES.append(
    ("anniversary-sp-guide.html", "3周年スペシャル(金/銀)徹底解説",
     "ルフィ金140万・ティーチ25万・バギー18万。金は銀の約2倍、ルフィ金だけBOX代を上回る理由を解説。"))
ONEPIECE_ARTICLES.append(
    ("kaigun-taisho-guide.html", "海軍大将トリオ 徹底解説",
     "OP-16のサカズキ・クザン・ボルサリーノ。3枚が横並びになる理由と302BOXに1枚の封入率を解説。"))
ONEPIECE_ARTICLES.append(
    ("restock-guide.html", "再販・入荷ガイド",
     "絶版制度がない仕組み、2026年の再販実績、コンビニ入荷の傾向、再販が相場に効く弾・効かない弾。"))


def _article_links_block() -> str:
    """トップに記事カードを出す(ポケカ同型: 最新3枚固定+ローテーション1枚=計4表示)。

    ローテーション枠はビルド時に1枚選ぶ。以前は候補全部を display:none で
    出力してJSで1枚だけ表示していたが、残りが隠しリンクとして残るため
    表示されるものだけを出力する。
    """
    existing = [(f, t, d) for (f, t, d) in ONEPIECE_ARTICLES
                if (PROJECT_ROOT / "onepiece" / f).exists()]
    if not existing:
        return ""
    # 先頭2枚は最新弾の当たりガイド、末尾1枚は直近に追加した記事(ハウツー枠は
    # リスト末尾にappendされるため、末尾を取ることで新着が必ず常時表示に載る)
    pinned = existing[:2] + existing[-1:]
    candidates = list(existing[2:-1])
    # ポケカ同様、週間値動きランキングもローテーション候補に含める
    candidates.insert(0, ("weekly.html", "【今週】ワンピBOX 週間値動きランキング",
                          "最大9店舗の実データで直近7日間の値上がり・値下がりBOXを毎日自動更新。"))
    featured = [random.choice(candidates)] if candidates else []

    def _card(f: str, t: str, d: str) -> str:
        return (f'  <a href="onepiece/{f}" class="blog-card"'
                f' onclick="gtag(\'event\',\'blog_click\',{{article:\'onepiece/{f}\'}})">\n'
                f'    <h3>{_esc(t)}</h3>\n    <p>{_esc(d)}</p>\n  </a>\n')

    html = '<div class="blog-links" id="blogLinks">\n'
    for f, t, d in featured:
        html += _card(f, t, d)
    for f, t, d in pinned:
        html += _card(f, t, d)
    html += '</div>'
    return html


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
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "ONE PIECEカード 未開封BOX 買取価格比較",
        "itemListElement": items,
    }
    website = {
        "@context": "https://schema.org", "@type": "WebSite",
        "name": "ワンピ買取チェッカー",
        "url": "https://pokeca-box-hikaku.com/onepiece",
    }
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム",
             "item": "https://pokeca-box-hikaku.com/"},
            {"@type": "ListItem", "position": 2, "name": "ワンピ買取チェッカー",
             "item": "https://pokeca-box-hikaku.com/onepiece"},
        ],
    }
    return "\n".join(
        '<script type="application/ld+json">'
        + json.dumps(d, ensure_ascii=False) + "</script>"
        for d in (item_list, website, breadcrumb)
    )


def _ai_summary(products: list[MasterProduct]) -> str:
    """AI検索向けサマリーの差し込み位置。現在は何も出力しない。

    display:none + aria-hidden はユーザーにも支援技術にも見えず
    クローラーだけが読む隠しテキストになるため出力を止めた。
    """
    return ""


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
    html = html.replace("<!-- {{BLOG_LINKS}} -->", _article_links_block())
    html = html.replace("<!-- {{RANKING_SUMMARY}} -->", _weekly_summary_block(products))

    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    # 個別BOXページ + 週間ランキングページ + 週次アーカイブ記事
    generate_onepiece_box_pages(products, update_date)
    generate_onepiece_weekly(products, update_date)
    generate_onepiece_weekly_articles(products)

    # sitemap.xml にワンピ系URLを追記(ポケカ generator が全書換えした直後に呼ばれる)
    _append_onepiece_sitemap(products)
    return html


# ===== sitemap へのワンピURL追記 =====
def _append_onepiece_sitemap(products: list[MasterProduct]) -> None:
    """ポケカ側 generator が書いた sitemap.xml にワンピ系URLを注入する。

    ポケカ generator は毎回 sitemap を全書換えするため、ここで追記しないと
    /onepiece 配下(トップ・個別BOX・週間)が永久にクロール対象から漏れる。
    main.py で generate_html(ポケカ) → generate_onepiece_html(ワンピ) の順に
    呼ばれるので、この時点の sitemap.xml にはポケカURLだけが入っている。
    冪等性のため既存のワンピ <url> ブロックを一旦除去してから再追記する。
    """
    base = "https://pokeca-box-hikaku.com"
    today = datetime.now(JST).strftime("%Y-%m-%d")
    sitemap_path = PROJECT_ROOT / "sitemap.xml"
    if not sitemap_path.exists():
        logger.warning("sitemap.xml not found, skip onepiece sitemap injection")
        return

    xml = sitemap_path.read_text(encoding="utf-8")

    # 既存の /onepiece を含む <url>...</url> ブロックを除去(冪等化)
    xml = re.sub(
        r"[ \t]*<url>\s*<loc>[^<]*/onepiece[^<]*</loc>.*?</url>\s*",
        "",
        xml,
        flags=re.DOTALL,
    )

    def _url(path: str, freq: str, priority: str) -> str:
        return (f"  <url>\n    <loc>{base}{path}</loc>\n"
                f"    <lastmod>{today}</lastmod>\n"
                f"    <changefreq>{freq}</changefreq>\n"
                f"    <priority>{priority}</priority>\n  </url>\n")

    blocks = [
        _url("/onepiece", "daily", "0.9"),
        _url("/onepiece/weekly.html", "weekly", "0.8"),
    ]
    seen: set[str] = set()
    for p in products:
        if not any(p.prices.get(s, 0) > 0 for s in SHOP_IDS):
            continue
        slug = _slug(p.name)
        if slug in seen:
            continue
        seen.add(slug)
        blocks.append(_url(f"/onepiece/box/{slug}.html", "daily", "0.7"))

    # BOX掘り下げ記事(onepiece/*-atari-guide.html)を自動収録
    for art in sorted((PROJECT_ROOT / "onepiece").glob("*-atari-guide.html")):
        blocks.append(_url(f"/onepiece/{art.name}", "weekly", "0.8"))

    # ハウツー記事(globは*-atari-guide.htmlしか拾わないため明示追加)
    if (PROJECT_ROOT / "onepiece" / "kaitori-hikaku.html").exists():
        blocks.append(_url("/onepiece/kaitori-hikaku.html", "weekly", "0.7"))
    if (PROJECT_ROOT / "onepiece" / "toushi.html").exists():
        blocks.append(_url("/onepiece/toushi.html", "weekly", "0.7"))
    if (PROJECT_ROOT / "onepiece" / "kougaku-ranking.html").exists():
        blocks.append(_url("/onepiece/kougaku-ranking.html", "weekly", "0.7"))
    if (PROJECT_ROOT / "onepiece" / "op-17-forecast.html").exists():
        blocks.append(_url("/onepiece/op-17-forecast.html", "weekly", "0.8"))
    if (PROJECT_ROOT / "onepiece" / "shikou-treasure-get.html").exists():
        blocks.append(_url("/onepiece/shikou-treasure-get.html", "weekly", "0.8"))
    for _name in ("nika-luffy-comipara", "red-comipara-guide", "roger-gold-comipara", "comipara-ranking", "psa-guide", "box-price-pattern", "anniversary-sp-guide", "kaigun-taisho-guide", "restock-guide"):
        if (PROJECT_ROOT / "onepiece" / f"{_name}.html").exists():
            blocks.append(_url(f"/onepiece/{_name}.html", "weekly", "0.8"))

    injection = "".join(blocks)
    xml = xml.replace("</urlset>", injection + "</urlset>")
    sitemap_path.write_text(xml, encoding="utf-8")
    logger.info("Injected %d ONE PIECE URLs into sitemap.xml", len(blocks))


# ===== 価格履歴の読み込み(グラフ用) =====
def _own_history_points(product_name: str) -> list[list]:
    """data/history_op から自前の日次最高値推移 [[ts_ms, price], ...] を作る。"""
    pts: list[list] = []
    if not HISTORY_OP_DIR.exists():
        return pts
    for f in sorted(HISTORY_OP_DIR.glob("*.json")):
        try:
            ts = int(datetime.strptime(f.stem, "%Y-%m-%d")
                     .replace(tzinfo=JST).timestamp() * 1000)
            for item in json.loads(f.read_text(encoding="utf-8")):
                if item.get("name") == product_name and item.get("max_price", 0) > 0:
                    pts.append([ts, item["max_price"]])
                    break
        except (json.JSONDecodeError, OSError, ValueError):
            continue
    return pts


def _snkrdunk_op_points(product_name: str) -> list[list]:
    """スニダンの価格推移点をマッピング経由で読む。"""
    mapping_path = SNKRDUNK_OP_DIR / "product_mapping_op.json"
    if not mapping_path.exists():
        return []
    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        sid = mapping.get(product_name)
        if not sid:
            return []
        data_path = SNKRDUNK_OP_DIR / f"{sid}.json"
        if data_path.exists():
            return json.loads(data_path.read_text(encoding="utf-8")).get("points", [])
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _op_chart_section(product: MasterProduct) -> str:
    """個別ページ用のインラインChart.js。スニダン(過去)＋自前history。"""
    snkr = _snkrdunk_op_points(product.name)
    own = _own_history_points(product.name)
    if own:
        own_start = own[0][0]
        points = [p for p in snkr if p[0] < own_start] + own
    else:
        points = snkr
    if not points:
        return ""

    # スニダンは単品/相場なので買取推定に0.9倍補正(定価2000未満のデッキは補正しない)
    no_corr = product.retail_price < 2000
    if no_corr:
        snkr_count = 0
    elif own:
        snkr_count = len([p for p in points if p[0] < own[0][0]])
    else:
        snkr_count = len(points)

    points_json = json.dumps(points, ensure_ascii=False)
    rd = product.release_date or ""
    box_name = _esc(product.name)
    return f"""<h3 class="section-title">{box_name} 価格推移</h3>
<div class="chart-wrap">
<div class="chart-periods">
  <button class="cp-btn active" data-period="all">全期間</button>
  <button class="cp-btn" data-period="3m">3ヶ月</button>
  <button class="cp-btn" data-period="1m">1ヶ月</button>
</div>
<canvas id="boxChart"></canvas>
<div class="chart-note">※ 最大9店舗の最高買取価格の推移（発売初期はスニダン相場を参考値として表示）</div>
</div>
<script>
(function(){{
var pts={points_json};
var rd="{rd}";
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
    data:{{labels:labels,datasets:[{{label:"参考価格",data:data,borderColor:"#e53935",backgroundColor:"rgba(229,57,53,.1)",fill:true,tension:0.3,pointRadius:f.length>60?0:2,pointHoverRadius:5,borderWidth:2}}]}},
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


# ===== 個別BOXページ生成 =====
def generate_onepiece_box_pages(products: list[MasterProduct], update_date: str) -> None:
    template_path = PROJECT_ROOT / "onepiece-box-template.html"
    if not template_path.exists():
        logger.warning("onepiece-box-template.html not found, skipping box pages")
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
        max_sid = max(active, key=active.get)
        max_shop = SHOP_NAMES.get(max_sid, max_sid)
        shop_count = len(active)
        diff = max_price - p.retail_price if p.retail_price > 0 else 0

        rows = []
        for sid, price in sorted(((s, p.prices.get(s, 0)) for s in SHOP_IDS),
                                 key=lambda x: x[1], reverse=True):
            name = SHOP_NAMES.get(sid, sid)
            url = SHOP_OP_URLS.get(sid, "#")
            # 店舗名は自サイトの店舗別ページへ内部リンク、公式サイトは「公式↗」で併記
            shop_cell = (f'<a href="../../shop/{sid}.html">{name}</a>'
                         f'<a class="shop-official" href="{url}" target="_blank" rel="noopener noreferrer">公式↗</a>')
            if price > 0:
                cls = ' class="best"' if price == max_price else ""
                rows.append(f'<tr{cls}><td class="shop-name">{shop_cell}</td><td>{_format_price(price)}</td></tr>')
            else:
                rows.append(f'<tr><td class="shop-name">{shop_cell}</td><td class="no-price">取扱なし</td></tr>')
        price_table = ('<table class="price-table">\n<tr><th>買取店</th><th>買取価格</th></tr>\n'
                       + "\n".join(rows) + "\n</table>")

        # hit cards
        hit_html = ""
        if p.hit_cards:
            dts = "".join(f'<dt>{_esc(n)}</dt><dd>{_esc(c)}</dd>' for n, c in p.hit_cards)
            hit_html = f'<div class="hit-cards"><h3>★ 注目カード（トップレア）</h3><dl class="hit-list">{dts}</dl></div>'

        # related (same category)
        related = [r for r in by_cat.get(p.category, [])
                   if r.name != p.name and any(r.prices.get(s, 0) > 0 for s in SHOP_IDS)]
        related_html = "\n".join(
            f'    <a href="{_slug(r.name)}.html" class="related-link">{_esc(r.name)}</a>'
            for r in related[:8])

        # trend comment (前日比)
        trend = ""
        prev = _prev_max(p.name)
        if prev and max_price:
            ch = max_price - prev
            if ch > 0:
                trend = f'<div class="trend-comment" style="color:#16a34a"><span class="trend-icon">📈</span>前日比 +{_format_price(ch)} 上昇中</div>'
            elif ch < 0:
                trend = f'<div class="trend-comment" style="color:#dc2626"><span class="trend-icon">📉</span>前日比 {_format_price(ch)} 下落</div>'

        product_ld = json.dumps({
            "@context": "https://schema.org", "@type": "Product", "name": p.name,
            "category": "ONE PIECEカードゲーム / 未開封BOX",
            "offers": {"@type": "AggregateOffer", "priceCurrency": "JPY",
                       "highPrice": max_price, "lowPrice": min(active.values()),
                       "offerCount": shop_count}}, ensure_ascii=False)
        # パンくずリスト(ホーム > ワンピ買取 > 商品名) → SERPにパンくず表示
        breadcrumb_ld = json.dumps({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "ホーム",
                 "item": "https://pokeca-box-hikaku.com/"},
                {"@type": "ListItem", "position": 2, "name": "ワンピ買取チェッカー",
                 "item": "https://pokeca-box-hikaku.com/onepiece"},
                {"@type": "ListItem", "position": 3, "name": p.name,
                 "item": f"https://pokeca-box-hikaku.com/onepiece/box/{slug}.html"},
            ]}, ensure_ascii=False)
        jsonld = ('<script type="application/ld+json">' + product_ld + "</script>\n"
                  '<script type="application/ld+json">' + breadcrumb_ld + "</script>")

        # 本文解説(コンテンツSEO)。すべて手元データからの生成で新規の事実主張はしない。
        low_price = min(active.values())
        cat_label = CATEGORY_LABELS.get(p.category, "BOX")
        parts = [f"{_esc(p.name)}は"]
        rd_m = re.match(r"(\d{4})-(\d{2})-(\d{2})", p.release_date or "")
        if rd_m:
            rd_jp = f"{int(rd_m.group(1))}年{int(rd_m.group(2))}月{int(rd_m.group(3))}日"
            parts.append(f"{rd_jp}発売の{cat_label}です。")
        else:
            parts.append(f"{cat_label}です。")
        if p.retail_price:
            parts.append(f"参考定価は{_format_price(p.retail_price)}。")
        if low_price < max_price:
            parts.append(
                f"現在の未開封BOX買取価格は{_format_price(low_price)}〜"
                f"{_format_price(max_price)}で、最高値は{_esc(max_shop)}が提示しています"
                f"（{shop_count}店舗掲載）。")
        else:
            parts.append(
                f"現在の未開封BOX買取価格は{_format_price(max_price)}"
                f"（{_esc(max_shop)}／{shop_count}店舗掲載）。")
        if p.desc:
            parts.append(_esc(p.desc))
        parts.append(
            "買取価格は封入されるトップレアの相場や在庫状況で日々変動します。"
            "売却を検討している場合は、上の価格表で最大9店舗の最新買取価格を比較し、"
            "価格推移グラフで底値・高値のタイミングを確認するのがおすすめです。")
        box_overview = (
            f'<h3 class="section-title">{_esc(p.name)}の買取について</h3>'
            f'<p class="product-desc">{"".join(parts)}</p>')
        # 対応する当たりカードガイド記事があれば相互リンク(内部リンク強化)
        if (PROJECT_ROOT / "onepiece" / f"{slug}-atari-guide.html").exists():
            box_overview += (
                f'<p class="product-desc" style="margin-top:6px">'
                f'▶ 詳しくは <a href="/onepiece/{slug}-atari-guide.html" style="color:var(--accent);font-weight:700">'
                f'{_esc(p.name)}の当たりカードランキング・買取相場・封入率ガイド</a> で解説しています。</p>')

        page = template
        for k, v in {
            "{{PRODUCT_NAME}}": _esc(p.name), "{{SLUG}}": slug,
            "{{ROBOTS}}": "index, follow", "{{JSONLD}}": jsonld,
            "{{UPDATE_DATE}}": update_date,
            "{{CATEGORY_LABEL}}": CATEGORY_LABELS.get(p.category, ""),
            "{{PRODUCT_DESC}}": _esc(p.desc or ""),
            "{{TREND_COMMENT}}": trend,
            "{{MAX_PRICE_TEXT}}": _format_price(max_price),
            "{{MAX_SHOP_NAME}}": max_shop,
            "{{RETAIL_PRICE_TEXT}}": _format_price(p.retail_price) if p.retail_price else "—",
            "{{DIFF_TEXT}}": (f"+{_format_price(diff)}" if diff > 0 else _format_price(diff)) if p.retail_price else "—",
            "{{SHOP_COUNT}}": str(shop_count),
            "{{PRICE_TABLE}}": price_table,
            "{{HIT_CARDS}}": hit_html,
            "{{RELATED_LINKS}}": related_html,
            "{{TOTAL_PRODUCTS}}": str(total),
        }.items():
            page = page.replace(k, v)
        page = page.replace("<!-- {{CHART_SECTION}} -->", _op_chart_section(p))
        page = page.replace("<!-- {{BOX_OVERVIEW}} -->", box_overview)
        # 公式BOX/パック画像がある弾のみ表示(無い弾は枠ごと省略)
        box_img = ""
        if (PROJECT_ROOT / "images" / "boxes" / f"{slug}.webp").exists():
            box_img = (
                '<div style="text-align:center;margin:4px 0 18px">'
                f'<picture><source srcset="/images/boxes/{slug}.webp" type="image/webp">'
                f'<img src="/images/boxes/{slug}.jpg" alt="{_esc(p.name)} パッケージ画像 買取価格比較" '
                'width="240" height="240" loading="lazy" decoding="async" '
                'style="max-width:240px;width:60%;height:auto;border-radius:8px"></picture></div>')
        page = page.replace("<!-- {{BOX_IMAGE}} -->", box_img)

        (BOX_DIR / f"{slug}.html").write_text(page, encoding="utf-8")
        generated += 1
    logger.info("Generated %d ONE PIECE box pages", generated)


def _prev_max(product_name: str) -> int:
    """前日のmax_price(グラフ/前日比用)。"""
    if not HISTORY_OP_DIR.exists():
        return 0
    files = sorted(HISTORY_OP_DIR.glob("*.json"))
    if len(files) < 2:
        return 0
    try:
        for item in json.loads(files[-2].read_text(encoding="utf-8")):
            if item.get("name") == product_name:
                return item.get("max_price", 0)
    except (json.JSONDecodeError, OSError):
        pass
    return 0


# ===== 週間値動きランキング =====
def _weekly_changes(products: list[MasterProduct]) -> list[dict]:
    """7日前(なければ最古)との最高値変化を算出。"""
    files = sorted(HISTORY_OP_DIR.glob("*.json")) if HISTORY_OP_DIR.exists() else []
    if len(files) < 2:
        return []
    # 7日前に最も近いスナップショット
    latest = files[-1]
    try:
        latest_date = datetime.strptime(latest.stem, "%Y-%m-%d")
    except ValueError:
        return []
    base_file = files[0]
    for f in files[:-1]:
        try:
            d = datetime.strptime(f.stem, "%Y-%m-%d")
        except ValueError:
            continue
        if (latest_date - d).days >= 7:
            base_file = f
    def load(f):
        try:
            return {x["name"]: x.get("max_price", 0) for x in json.loads(f.read_text(encoding="utf-8"))}
        except (json.JSONDecodeError, OSError):
            return {}
    now, past = load(latest), load(base_file)
    out = []
    for p in products:
        cur = now.get(p.name, 0)
        old = past.get(p.name, 0)
        if cur > 0 and old > 0:
            out.append({"name": p.name, "slug": _slug(p.name), "cur": cur,
                        "old": old, "change": cur - old,
                        "pct": (cur - old) / old * 100})
    out.sort(key=lambda x: x["change"], reverse=True)
    return out


def _weekly_summary_block(products: list[MasterProduct]) -> str:
    """トップページ下部の週間ランキング要約(上位/下位3件)。"""
    ch = _weekly_changes(products)
    if not ch:
        return ""
    ups = [c for c in ch if c["change"] > 0][:3]
    downs = [c for c in ch if c["change"] < 0][-3:]
    def row(c):
        sign = "+" if c["change"] > 0 else "-"
        col = "#16a34a" if c["change"] > 0 else "#dc2626"
        return (f'<a href="onepiece/box/{c["slug"]}.html" style="display:flex;justify-content:space-between;'
                f'padding:8px 12px;border-bottom:1px solid #f3f4f6;text-decoration:none;color:inherit">'
                f'<span>{_esc(c["name"])}</span><span style="color:{col};font-weight:700">'
                f'{sign}{_format_price(abs(c["change"]))} ({sign}{abs(c["pct"]):.1f}%)</span></a>')
    body = ""
    if ups:
        body += '<div style="font-weight:700;margin:10px 0 4px;color:#16a34a">📈 値上がり</div>' + "".join(row(c) for c in ups)
    if downs:
        body += '<div style="font-weight:700;margin:14px 0 4px;color:#dc2626">📉 値下がり</div>' + "".join(row(c) for c in reversed(downs))
    return (f'<div style="max-width:1280px;margin:24px auto 0;padding:0 16px">'
            f'<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px 20px">'
            f'<div style="font-size:15px;font-weight:800;margin-bottom:6px">📊 今週の値動き（<a href="onepiece/weekly.html" style="color:#e53935">週間ランキングを見る</a>）</div>'
            f'{body}</div></div>')


def generate_onepiece_weekly(products: list[MasterProduct], update_date: str) -> None:
    """週間値動きランキングページ onepiece/weekly.html を生成。"""
    ch = _weekly_changes(products)
    B = "padding:9px;border:1px solid #e5e7eb"
    rows = []
    for i, c in enumerate(ch, 1):
        sign = "+" if c["change"] > 0 else ("-" if c["change"] < 0 else "")
        col = "#16a34a" if c["change"] > 0 else ("#dc2626" if c["change"] < 0 else "#6b7280")
        rows.append(
            f'<tr><td style="{B};text-align:center">{i}</td>'
            f'<td style="{B};text-align:left"><a href="box/{c["slug"]}.html" style="color:#e53935;text-decoration:none">{_esc(c["name"])}</a></td>'
            f'<td style="{B};text-align:center">{_format_price(c["cur"])}</td>'
            f'<td style="{B};text-align:center;color:{col};font-weight:700">{sign}{_format_price(abs(c["change"]))}</td>'
            f'<td style="{B};text-align:center;color:{col};font-weight:700">{sign}{abs(c["pct"]):.1f}%</td></tr>')
    if not rows:
        table = "<p style='color:#6b7280;font-size:13px'>データ蓄積中です。数日後から値動きが表示されます。</p>"
    else:
        head = (f'<tr style="background:#f9fafb"><th style="{B}">#</th><th style="{B}">商品名</th>'
                f'<th style="{B}">現在の最高値</th><th style="{B}">週間変化</th><th style="{B}">変化率</th></tr>')
        table = ('<table style="width:100%;border-collapse:collapse;font-size:14px">'
                 + head + "".join(rows) + '</table>')

    # 構造化データ(ランキングItemList + パンくず)
    wk_lds = [{
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": "https://pokeca-box-hikaku.com/"},
            {"@type": "ListItem", "position": 2, "name": "ワンピ買取チェッカー", "item": "https://pokeca-box-hikaku.com/onepiece"},
            {"@type": "ListItem", "position": 3, "name": "週間値動きランキング"},
        ]}]
    if ch:
        wk_lds.insert(0, {
            "@context": "https://schema.org", "@type": "ItemList",
            "name": "ワンピBOX 週間値動きランキング",
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": c["name"],
                 "url": f"https://pokeca-box-hikaku.com/onepiece/box/{c['slug']}.html"}
                for i, c in enumerate(ch[:20], 1)],
        })
    wk_jsonld = "\n".join('<script type="application/ld+json">'
                          + json.dumps(d, ensure_ascii=False) + "</script>" for d in wk_lds)

    page = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="ONE PIECEカード未開封BOXの週間買取価格変化ランキング。値上がり・値下がりBOXを最大9店舗の実データで毎日更新。">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/onepiece/weekly.html">
{wk_jsonld}
<meta property="og:title" content="ワンピBOX 週間値動きランキング｜ワンピ買取チェッカー">
<meta property="og:description" content="ONE PIECEカード未開封BOXの週間買取価格変化ランキング。値上がり・値下がりBOXを最大9店舗の実データで毎日更新。">
<meta property="og:type" content="article">
<meta property="og:url" content="https://pokeca-box-hikaku.com/onepiece/weekly.html">
<meta property="og:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<meta property="og:site_name" content="ワンピ買取チェッカー">
<meta property="og:locale" content="ja_JP">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="ワンピBOX 週間値動きランキング｜ワンピ買取チェッカー">
<meta name="twitter:description" content="ONE PIECEカード未開封BOXの週間買取価格変化ランキング。最大9店舗の実データで毎日更新。">
<meta name="twitter:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<title>ワンピBOX 週間値動きランキング｜ワンピ買取チェッカー</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:#f6f7fb;color:#111827;line-height:1.7;margin:0}}
.gswitch{{display:flex;align-items:center;justify-content:center;gap:8px;padding:11px 16px;font-size:14px;font-weight:800;text-decoration:none;color:#fff;background:linear-gradient(135deg,#4aa3ff,#1e88e5)}}
.header{{height:52px;display:flex;align-items:center;justify-content:center;background:#fff;border-bottom:1px solid #e5e7eb}}
.header h1{{font-size:17px;font-weight:700;background:linear-gradient(135deg,#ff6b6b,#e53935);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.header a{{text-decoration:none}}
.wrap{{max-width:840px;margin:0 auto;padding:26px 16px 48px}}
h2{{font-size:20px;margin:0 0 4px}}.upd{{font-size:12px;color:#6b7280;margin-bottom:18px}}
th{{background:#f9fafb}}
.back{{display:inline-block;margin-top:20px;color:#e53935;text-decoration:none;font-weight:600}}
</style></head><body>
<a class="gswitch" href="/">◀ ポケモンカードの買取比較はこちら</a>
<div class="header"><a href="/onepiece"><h1>ワンピ買取チェッカー</h1></a></div>
<div class="wrap">
<h2>📊 ワンピBOX 週間値動きランキング</h2>
<div class="upd">更新: {update_date} ／ 7日前比・最大9店舗の最高買取価格ベース</div>
{table}
<a class="back" href="weekly/index.html">📚 過去の週間値動き記事アーカイブ</a>
<a class="back" href="/onepiece">← ワンピ買取比較に戻る</a>
</div>
</body></html>"""
    (PROJECT_ROOT / "onepiece").mkdir(exist_ok=True)
    (PROJECT_ROOT / "onepiece" / "weekly.html").write_text(page, encoding="utf-8")
    logger.info("Generated onepiece/weekly.html (%d ranked)", len(rows))


# ===== 週間値動きランキング記事(アーカイブ)の自動生成 =====
_WK_AFFILIATE = (
    '<div class="ad" style="text-align:center;padding:12px 0">'
    '<a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade">'
    '<img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a></div>'
    '<div class="ad" style="text-align:center;padding:12px 0">'
    '<a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade">'
    '<img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a></div>'
)

_WK_STYLE = (
    'body{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:#f6f7fb;color:#111827;line-height:1.7;margin:0}'
    '.gswitch{display:flex;align-items:center;justify-content:center;gap:8px;padding:11px 16px;font-size:14px;font-weight:800;text-decoration:none;color:#fff;background:linear-gradient(135deg,#4aa3ff,#1e88e5)}'
    '.header{height:52px;display:flex;align-items:center;justify-content:center;background:#fff;border-bottom:1px solid #e5e7eb}'
    '.header h1{font-size:17px;font-weight:700;background:linear-gradient(135deg,#ff6b6b,#e53935);-webkit-background-clip:text;-webkit-text-fill-color:transparent}'
    '.header a{text-decoration:none}.wrap{max-width:840px;margin:0 auto;padding:26px 16px 48px}'
    '.breadcrumb{font-size:12px;color:#6b7280;margin-bottom:16px}.breadcrumb a{color:#e53935;text-decoration:none}'
    'h2{font-size:20px;margin:0 0 4px}.upd{font-size:12px;color:#6b7280;margin-bottom:18px}'
    'h3{font-size:16px;margin:24px 0 8px;padding-bottom:5px;border-bottom:2px solid #e53935}'
    'table{width:100%;border-collapse:collapse;font-size:14px;margin:8px 0 4px}'
    'th{background:#f9fafb;padding:9px;border:1px solid #e5e7eb}td{padding:9px;border:1px solid #e5e7eb;text-align:center}'
    'td.nm{text-align:left}td.nm a{color:#e53935;text-decoration:none}'
    'p{font-size:14px;margin:14px 0}.disc{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:13px 16px;margin:20px 0;font-size:12px;color:#9a3412}'
    '.back{display:inline-block;margin-top:18px;color:#e53935;text-decoration:none;font-weight:600;margin-right:16px}'
    '.ft{text-align:center;padding:22px 16px;font-size:11px;color:#6b7280}.ft a{color:#e53935}'
)


def _wk_change_table(title: str, rows: list[dict], up: bool) -> str:
    if not rows:
        return ""
    trs = ""
    for i, c in enumerate(rows, 1):
        sign = "+" if c["change"] > 0 else "-"
        amt = _format_price(abs(c["change"]))
        col = "#16a34a" if up else "#dc2626"
        trs += (f'<tr><td>{i}</td>'
                f'<td class="nm"><a href="box/{c["slug"]}.html">{_esc(c["name"])}</a></td>'
                f'<td>{_format_price(c["cur"])}</td>'
                f'<td style="color:{col};font-weight:700">{sign}{amt}</td>'
                f'<td style="color:{col};font-weight:700">{sign}{abs(c["pct"]):.1f}%</td></tr>')
    return (f'<h3>{title}</h3><table><tr><th>#</th><th>BOX</th><th>現在の最高値</th>'
            f'<th>変化</th><th>変化率</th></tr>{trs}</table>')


def generate_onepiece_weekly_articles(products: list[MasterProduct]) -> None:
    """onepiece/weekly/YYYY-wWW.html(週次アーカイブ記事)+ index.html を生成。

    ISO週ごとに1本。当週分は毎回上書き、過去週はアーカイブとして残す。
    値動きが1件も無い(履歴が浅い等)場合は当週記事の生成のみスキップし、
    アーカイブindexは常に生成する(weekly.htmlからのリンク切れ防止)。
    data/history_op が貯まるほど内容が充実する。
    """
    wk_dir = PROJECT_ROOT / "onepiece" / "weekly"
    wk_dir.mkdir(parents=True, exist_ok=True)
    # change==0 は掲載しない(履歴が浅く前日比が全て0の初期はアーカイブindexのみ)
    changes = [c for c in _weekly_changes(products) if c["change"] != 0]
    if not changes:
        logger.info("ONE PIECE weekly: no nonzero changes yet, index only")
        _write_onepiece_weekly_index(wk_dir, None)
        return

    now = datetime.now(JST)
    iso = now.isocalendar()
    week_id = f"{iso[0]}-w{iso[1]:02d}"
    date_txt = now.strftime("%Y/%m/%d %H:%M")
    ups = [c for c in changes if c["change"] > 0][:10]
    downs = sorted([c for c in changes if c["change"] < 0], key=lambda x: x["change"])[:10]

    top_up = ups[0] if ups else None
    top_down = downs[0] if downs else None
    lead = []
    if top_up:
        lead.append(f'今週の値上がり首位は<strong>{_esc(top_up["name"])}</strong>'
                    f'(+{_format_price(top_up["change"])}／+{top_up["pct"]:.1f}%)')
    if top_down:
        lead.append(f'値下がり首位は<strong>{_esc(top_down["name"])}</strong>'
                    f'({_format_price(top_down["change"])}／{top_down["pct"]:.1f}%)')
    lead_txt = "、".join(lead) + "でした。" if lead else "今週の主要な値動きをまとめました。"

    blog_ld = json.dumps({
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": f"ワンピBOX 週間値動きランキング【{iso[0]}年 第{iso[1]}週】",
        "datePublished": now.strftime("%Y-%m-%d"), "dateModified": now.strftime("%Y-%m-%d"),
        "author": {"@type": "Organization", "name": "ワンピ買取チェッカー編集部", "url": "https://pokeca-box-hikaku.com/onepiece"},
        "publisher": {"@type": "Organization", "name": "ワンピ買取チェッカー", "logo": {"@type": "ImageObject", "url": "https://pokeca-box-hikaku.com/ogp.png"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"https://pokeca-box-hikaku.com/onepiece/weekly/{week_id}.html"},
        "inLanguage": "ja",
    }, ensure_ascii=False)

    page = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="ワンピースカード未開封BOXの週間買取価格変化ランキング【{iso[0]}年第{iso[1]}週】。値上がり・値下がりBOXを最大9店舗の実データでまとめた週次レポート。">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/onepiece/weekly/{week_id}.html">
<meta property="og:title" content="ワンピBOX 週間値動きランキング【{iso[0]}年 第{iso[1]}週】｜ワンピ買取チェッカー">
<meta property="og:description" content="値上がり・値下がりワンピBOXを最大9店舗の実データでまとめた週次レポート。">
<meta property="og:type" content="article">
<meta property="og:url" content="https://pokeca-box-hikaku.com/onepiece/weekly/{week_id}.html">
<meta property="og:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<meta property="og:site_name" content="ワンピ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<title>ワンピBOX 週間値動きランキング【{iso[0]}年 第{iso[1]}週】｜ワンピ買取チェッカー</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<script type="application/ld+json">{blog_ld}</script>
<style>{_WK_STYLE}</style></head><body>
<a class="gswitch" href="/">◀ ポケモンカードの買取比較はこちら</a>
<div class="header"><a href="/onepiece"><h1>ワンピ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="/">ホーム</a> &gt; <a href="/onepiece">ワンピ買取チェッカー</a> &gt; <a href="index.html">週間値動き記事</a> &gt; {iso[0]}年 第{iso[1]}週</div>
<h2>📊 ワンピBOX 週間値動きランキング【{iso[0]}年 第{iso[1]}週】</h2>
<div class="upd">更新: {date_txt} ／ 7日前比・最大9店舗の最高買取価格ベース</div>
<p>{lead_txt} 各BOX名をタップすると店舗別の最新買取価格・価格推移グラフを確認できます。</p>
{_wk_change_table("📈 値上がりランキング", ups, True)}
{_wk_change_table("📉 値下がりランキング", downs, False)}
<div class="disc"><strong>ご注意:</strong> 本記事の価格は当サイトが最大9店舗から自動取得した未開封BOX買取価格の最高値ベースで、7日前(履歴が浅い場合は取得できた最古)との比較です。相場は日々変動します。売買の判断はご自身の責任で行ってください。</div>
{_WK_AFFILIATE}
<a class="back" href="weekly.html">← 最新の週間ランキングへ</a>
<a class="back" href="index.html">← 週間記事アーカイブ</a>
<a class="back" href="/onepiece">← ワンピ買取比較トップ</a>
<div class="ft"><a href="/onepiece">ワンピ買取チェッカー</a> / <a href="/privacy.html">プライバシーポリシー</a></div>
</div></body></html>"""
    (wk_dir / f"{week_id}.html").write_text(page, encoding="utf-8")
    _write_onepiece_weekly_index(wk_dir, week_id)
    logger.info("Generated onepiece/weekly/%s.html (+index)", week_id)


def _write_onepiece_weekly_index(wk_dir: Path, current_week: str | None) -> None:
    """週次アーカイブindex(onepiece/weekly/index.html)を生成。記事0本でも出す。"""
    weeks = sorted((f.stem for f in wk_dir.glob("*.html") if f.stem != "index"), reverse=True)
    if weeks:
        li = ""
        for w in weeks:
            m = re.match(r"(\d{4})-w(\d{1,2})", w)
            label = f"{m.group(1)}年 第{int(m.group(2))}週" if m else w
            cur = "（最新）" if w == current_week else ""
            li += (f'<a href="{w}.html" style="display:block;padding:12px 14px;border-bottom:1px solid #f3f4f6;'
                   f'text-decoration:none;color:#111827;font-weight:600">📊 {label}の値動きランキング{cur}</a>')
    else:
        li = ('<p style="color:#6b7280;font-size:13px">週間の値動き記事はデータ蓄積中です。'
              '価格履歴が貯まり次第、毎週の値上がり・値下がりレポートを自動掲載します。'
              '最新の値動きは <a href="../weekly.html" style="color:#e53935">週間ランキング</a> をご覧ください。</p>')
    idx = f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="ワンピースカード未開封BOXの週間値動きランキング記事アーカイブ。過去の値上がり・値下がりレポートを一覧。">
<meta name="robots" content="noindex, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/onepiece/weekly/index.html">
<title>ワンピBOX 週間値動きランキング 記事アーカイブ｜ワンピ買取チェッカー</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<style>{_WK_STYLE}</style></head><body>
<a class="gswitch" href="/">◀ ポケモンカードの買取比較はこちら</a>
<div class="header"><a href="/onepiece"><h1>ワンピ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="/">ホーム</a> &gt; <a href="/onepiece">ワンピ買取チェッカー</a> &gt; 週間値動き記事</div>
<h2>📚 ワンピBOX 週間値動きランキング 記事アーカイブ</h2>
<div class="upd">最新の週間ランキングは <a href="../weekly.html" style="color:#e53935">こちら</a></div>
{li}
<a class="back" href="/onepiece">← ワンピ買取比較トップ</a>
<div class="ft"><a href="/onepiece">ワンピ買取チェッカー</a> / <a href="/privacy.html">プライバシーポリシー</a></div>
</div></body></html>"""
    (wk_dir / "index.html").write_text(idx, encoding="utf-8")
