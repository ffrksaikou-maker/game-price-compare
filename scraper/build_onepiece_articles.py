"""ワンピBOX掘り下げ記事(onepiece/{slug}-atari-guide.html)を生成する。

ポケカ atari-guide 型を赤テーマで踏襲した静的記事を、共通ボイラープレート
(head/style/nav/footer/アフィ2点)＋弾別データから生成する。BOX買取価格は
data/history_op の当サイト実データを参照(記事内のBOX価格は自動更新)。
カード相場はWebSearchで裏取りした2026年7月時点の目安(免責明記)。

再実行で全記事を再生成(冪等)。nav相互リンクは全記事を自動列挙する。
"""
from __future__ import annotations

import json
from html import escape as _esc
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART_DIR = ROOT / "onepiece"
HISTORY_OP_DIR = ROOT / "data" / "history_op"

AFFILIATE = """<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>"""

STYLE = """<style>
:root{--bg:#f6f7fb;--card:#fff;--border:#e5e7eb;--text:#111827;--text-sub:#6b7280;--accent:#e53935;--highlight:#ffe0e0}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:var(--bg);color:var(--text);line-height:1.8}
.gswitch{display:flex;align-items:center;justify-content:center;gap:8px;padding:11px 16px;font-size:14px;font-weight:800;text-decoration:none;color:#fff;background:linear-gradient(135deg,#4aa3ff,#1e88e5);box-shadow:inset 0 -2px 0 rgba(0,0,0,.12)}
.gswitch .ar{font-size:18px;line-height:1}
.header{position:sticky;top:0;z-index:100;height:56px;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;padding:0 20px}
.header a{text-decoration:none}
.header h1{font-size:18px;font-weight:700;background:linear-gradient(135deg,#ff6b6b,#e53935);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.wrap{max-width:1240px;margin:0 auto;padding:32px 16px 48px}
.content-layout{display:flex;gap:24px;align-items:flex-start}
.content-layout article{flex:1;min-width:0}
.article-nav{width:200px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}
.article-nav-title{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}
.article-nav a{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4;transition:all .2s}
.article-nav a:hover{color:var(--accent);border-left-color:var(--accent)}
.article-nav a.current{color:var(--accent);border-left-color:var(--accent);font-weight:600}
.article-nav-sub{font-size:12px;font-weight:700;margin:14px 0 6px;color:#b91c1c;padding-top:10px;border-top:1px solid var(--border)}
.mobile-footer-nav{display:none;margin:24px 0;padding:18px 16px;background:#f9fafb;border:1px solid var(--border);border-radius:12px}
.mfn-title{font-size:14px;font-weight:700;margin-bottom:10px;color:var(--text)}
.mfn-section{margin-top:14px}
.mfn-section-title{font-size:12px;font-weight:700;color:#b91c1c;margin-bottom:8px;letter-spacing:.5px}
.mobile-footer-nav a{display:block;font-size:13px;padding:10px 12px;border-radius:8px;color:var(--text);text-decoration:none;background:#fff;margin-bottom:6px;border:1px solid var(--border);transition:all .2s}
.mobile-footer-nav a:hover,.mobile-footer-nav a:active{color:var(--accent);border-color:var(--accent);background:#fff5f5}
@media(max-width:1023px){.mobile-footer-nav{display:block}.content-layout{display:block}.article-nav{display:none}}
.breadcrumb{font-size:12px;color:var(--text-sub);margin-bottom:20px}
.breadcrumb a{color:var(--accent);text-decoration:none}
article{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:32px 28px;margin-bottom:24px}
article h1{font-size:24px;font-weight:800;margin-bottom:8px;line-height:1.4;background:linear-gradient(135deg,#ff6b6b,#e53935);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.meta{font-size:12px;color:var(--text-sub);margin-bottom:24px}
article h2{font-size:18px;font-weight:700;margin:32px 0 14px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
article h3{font-size:15px;font-weight:700;margin:16px 0 8px;color:var(--accent)}
article p{font-size:14px;margin-bottom:14px}
article ul,article ol{font-size:14px;padding-left:22px;margin-bottom:14px}
article li{margin-bottom:8px}
.hero{margin-bottom:24px;padding:22px;background:linear-gradient(135deg,#fff5f5,#ffe3e3);border-radius:12px;border:1px solid #ffabab}
.hero .stat-label{font-size:11px;color:#b91c1c;font-weight:700;letter-spacing:.5px}
.hero .stat-big{font-size:30px;font-weight:800;color:#b91c1c;line-height:1.2;margin:4px 0 12px}
.hero .stat-sub{font-size:12px;color:#991b1b;line-height:1.7}
.price-table{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}
.price-table th,.price-table td{padding:10px 12px;border-bottom:1px solid var(--border)}
.price-table th{background:#f9fafb;text-align:left;font-size:11px;color:var(--text-sub);letter-spacing:.5px}
.price-table tr.best td{background:#ffe0e0;font-weight:700}
.price-table td.price{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.callout{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 18px;margin:14px 0;font-size:13px}
.callout strong{color:#1d4ed8}
.disclaimer{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:14px 18px;margin:24px 0;font-size:12px;color:#9a3412}
.disclaimer strong{color:#c2410c}
.cta{display:block;text-align:center;padding:16px;background:linear-gradient(135deg,#ff6b6b,#e53935);color:#fff;border-radius:12px;text-decoration:none;font-weight:700;margin:24px 0}
.back{display:inline-block;margin-top:16px;color:var(--accent);text-decoration:none;font-size:14px;font-weight:600;margin-right:16px}
.ad{text-align:center;padding:12px 0}
.ft{text-align:center;padding:24px 16px;font-size:11px;color:var(--text-sub)}
.ft a{color:var(--accent)}
@media(max-width:640px){article{padding:22px 18px}article h1{font-size:20px}.hero .stat-big{font-size:24px}}
</style>"""

BASE = "https://pokeca-box-hikaku.com"


def _box_data() -> dict:
    """data/history_op 最新から slug -> (max_price, store_count) を得る。"""
    files = sorted(HISTORY_OP_DIR.glob("*.json"))
    if not files:
        return {}
    data = json.loads(files[-1].read_text(encoding="utf-8"))
    out = {}
    for r in data:
        import re
        m = re.search(r"(OP|EB|PRB|ST)-?(\d+)", r["name"])
        if not m:
            continue
        slug = f"{m.group(1).lower()}-{int(m.group(2)):02d}"
        prices = {k: v for k, v in r["prices"].items() if v > 0}
        if prices:
            out[slug] = (max(prices.values()), len(prices))
    return out


def _ranking_table(rows: list) -> str:
    body = ""
    for i, (name, rarity, price) in enumerate(rows, 1):
        cls = ' class="best"' if i == 1 else ""
        body += (f'<tr{cls}><td>{i}位</td><td>{_esc(name)}</td>'
                 f'<td>{_esc(rarity)}</td><td class="price">{_esc(price)}</td></tr>')
    return ('<table class="price-table"><thead><tr><th>順位</th><th>カード名</th>'
            '<th>レアリティ</th><th style="text-align:right">買取相場の目安</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def _nav(current_slug: str, articles: list) -> str:
    links = ""
    for a in articles:
        cur = ' class="current"' if a["slug"] == current_slug else ""
        links += f'<a href="{a["slug"]}-atari-guide.html"{cur}>{_esc(a["nav_label"])}</a>\n'
    return (f'<nav class="article-nav">\n'
            f'<div class="article-nav-title">ワンピ買取</div>\n'
            f'<a href="/onepiece">買取価格比較トップ</a>\n'
            f'<a href="weekly.html">📊 週間値動きランキング</a>\n'
            f'<div class="article-nav-sub">📘 BOX掘り下げガイド</div>\n{links}</nav>')


def _mobile_nav(articles: list) -> str:
    links = "".join(
        f'<a href="{a["slug"]}-atari-guide.html">{_esc(a["nav_label"])}</a>\n'
        for a in articles)
    return (f'<nav class="mobile-footer-nav">\n<div class="mfn-title">📚 他のページを見る</div>\n'
            f'<div class="mfn-section"><div class="mfn-section-title">📘 BOX掘り下げガイド</div>\n{links}</div>\n'
            f'<div class="mfn-section"><div class="mfn-section-title">📰 ワンピ買取</div>\n'
            f'<a href="/onepiece">買取価格比較トップ</a>\n<a href="weekly.html">📊 週間値動きランキング</a>\n</div>\n</nav>')


def _render(a: dict, articles: list, box: dict) -> str:
    slug = a["slug"]
    box_max, box_n = box.get(slug, (0, 0))
    box_price_txt = f"¥{box_max:,}" if box_max else "—"
    box_line = (f'当サイト実データのBOX買取最高{box_price_txt}({box_n}店舗)'
                if box_max else 'BOX買取価格は個別ページ参照')
    ratio = f"（定価¥{a['retail']:,}の約{box_max / a['retail']:.1f}倍）" if box_max else ""

    blog_ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": a["h1_short"], "description": a["meta_desc"],
        "datePublished": "2026-07-14", "dateModified": "2026-07-14",
        "image": f"{BASE}/ogp.jpg",
        "author": {"@type": "Organization", "name": "ワンピ買取チェッカー編集部", "url": f"{BASE}/onepiece"},
        "publisher": {"@type": "Organization", "name": "ワンピ買取チェッカー",
                      "logo": {"@type": "ImageObject", "url": f"{BASE}/ogp.png"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{BASE}/onepiece/{slug}-atari-guide.html"},
        "articleSection": "当たりカードガイド", "inLanguage": "ja",
        "about": {"@type": "Thing", "name": a["about"], "url": f"{BASE}/onepiece/box/{slug}.html"},
    }
    crumb_ld = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{BASE}/"},
            {"@type": "ListItem", "position": 2, "name": "ワンピ買取チェッカー", "item": f"{BASE}/onepiece"},
            {"@type": "ListItem", "position": 3, "name": a["h1_short"]},
        ],
    }

    body = a["body"].format(
        box_price=box_price_txt, box_n=box_n, ratio=ratio,
        ranking_table=_ranking_table(a["ranking"]))

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://h.accesstrade.net">
<meta name="description" content="{_esc(a['meta_desc'])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{BASE}/onepiece/{slug}-atari-guide.html">
<meta property="og:title" content="{_esc(a['og_title'])}">
<meta property="og:description" content="{_esc(a['og_desc'])}">
<meta property="og:type" content="article">
<meta property="og:url" content="{BASE}/onepiece/{slug}-atari-guide.html">
<meta property="og:image" content="{BASE}/ogp.jpg">
<meta property="og:site_name" content="ワンピ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_esc(a['h1_short'])}">
<meta name="twitter:description" content="{_esc(a['og_desc'])}">
<meta name="twitter:image" content="{BASE}/ogp.jpg">
<title>{_esc(a['title'])}｜ワンピ買取チェッカー</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RPTS6CRTCS"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-RPTS6CRTCS');
</script>
<script type="application/ld+json">
{json.dumps(blog_ld, ensure_ascii=False, indent=0)}
</script>
<script type="application/ld+json">
{json.dumps(crumb_ld, ensure_ascii=False, indent=0)}
</script>
{STYLE}
</head>
<body>
<a class="gswitch" href="/"><span class="ar">◀</span> ポケモンカードの買取比較はこちら</a>
<div class="header"><a href="/onepiece"><h1>ワンピ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="/">ホーム</a> &gt; <a href="/onepiece">ワンピ買取チェッカー</a> &gt; {_esc(a['crumb'])}</div>

<div class="content-layout">
{_nav(slug, articles)}

<article>
<h1>{a['h1']}</h1>
<div class="meta">公開: 2026年7月14日 / {_esc(a['meta_line'])} / ワンピ買取チェッカー編集部</div>

<div class="hero">
<div class="stat-label">看板当たり {_esc(a['hero_card'])} 買取相場(2026年7月時点)</div>
<div class="stat-big">{_esc(a['hero_big'])}</div>
<div class="stat-sub">{a['hero_sub']} / <a href="box/{slug}.html" style="color:#b91c1c;font-weight:700">{box_line}</a></div>
</div>

{body}

<a href="box/{slug}.html" class="cta">{_esc(a['box_name'])}の最新買取価格を最大11店舗で比較する &rarr;</a>

<div class="disclaimer">
<strong>ご注意:</strong> 本記事の当たりカード・収録種類・封入率は、複数の公開情報(カードショップの買取相場・大量開封報告等)と当サイトが自動収集した買取価格データに基づく参考情報です。封入率は公式発表ではなく推定値を含みます。買取相場は需給で日々変動し、本記事のカード金額は2026年7月時点の目安です。BOX買取価格は当サイトが最大11店舗から自動取得した実データを基準にしています。売買・開封の判断はご自身の責任で行ってください。
</div>

<h2>関連BOX・記事もチェック</h2>
<ul>
<li><a href="box/{slug}.html">{_esc(a['box_name'])}</a> — 本商品の店舗別最新買取価格(毎日更新)</li>
<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全23種のBOX買取価格を最大11店舗で横断比較</li>
<li><a href="weekly.html">週間値動きランキング</a> — 全ワンピBOXの急上昇・急落ランキング(毎日更新)</li>
</ul>

<a href="box/{slug}.html" class="back">&larr; {_esc(a['short_name'])} 個別ページへ</a>
<a href="/onepiece" class="back">&larr; ワンピ買取比較トップ</a>
</article>
</div><!-- /content-layout -->
{_mobile_nav(articles)}

</div>

{AFFILIATE}

<div class="ft">
  <a href="/onepiece">ワンピ買取チェッカー</a> / <a href="/privacy.html">プライバシーポリシー</a>
</div>
</body>
</html>
"""


def build() -> None:
    from scraper.article_data_onepiece import ARTICLES
    box = _box_data()
    ART_DIR.mkdir(parents=True, exist_ok=True)
    for a in ARTICLES:
        html = _render(a, ARTICLES, box)
        (ART_DIR / f"{a['slug']}-atari-guide.html").write_text(html, encoding="utf-8")
        print(f"wrote onepiece/{a['slug']}-atari-guide.html")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build()
