"""Template builder for the monthly ranking article.

Generates monthly-ranking-YYYY-MM.html using the first-day and last-day
snapshots of a completed month. Kept as a separate module so generator.py
stays manageable.
"""

from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))


# Category → display tag
CATEGORY_TAG: dict[str, tuple[str, str]] = {
    "sv": ("tag-sv", "SV"),
    "mega": ("tag-mega", "MEGA"),
    "ss": ("tag-ss", "S&S"),
    "special": ("tag-special", "特別"),
}


# Per-BOX inline commentary used when a BOX lands in the TOP3. Evergreen,
# no time-sensitive claims, so it remains accurate for any month.
BOX_FLAVOR: dict[str, str] = {
    "151": "リザードンex SARを擁する旧世代ファンの定番BOX。SV期で最も長期高騰を続けている象徴。",
    "inferno": "メガリザードンXex MUR/SARの2枚看板。MEGA系で最強格の期待値を持つ拡張パック。",
    "mega-ex": "MEGAハイクラスパック枠で、封入率が絞られておりMUR/SAR狙いで注目されやすい。",
    "mega-brave": "MEGAシリーズ第1弾の記念パック。メガルカリオex+リーリエの決心SARで相場底堅い。",
    "mega-sinfonia": "メガブレイブと同時発売のもう一方。メガミミッキュexのフェアリー人気が下支え。",
    "munikis-zero": "MEGA第3弾。相場形成中のBOXで、SAR引き当て期待で値動きが荒い。",
    "ninja-spinner": "メガゲッコウガex MUR/SARの2枚看板。世界人気No.1ゲッコウガの牽引力が強い。",
    "ruler-of-black-flame": "リザードンex SARの本家。SV期のリザードン相場を牽引してきた象徴的BOX。",
    "ancient-roar": "古代ポケモン人気とトドロクツキex SARでじわじわ地位を上げているBOX。",
    "future-flash": "未来ポケモン路線。テツノカイナex人気を軸にコレクター層の評価が厚い。",
    "shiny-treasure-ex": "色違い大集合のハイクラスパック。封入率の特殊さで開封需要が常に一定。",
    "hengen-no-kamen": "オーガポンex SARを中心に、カナザワ連動需要を残す。",
    "stellar-miracle": "テラパゴスexとコンセプトの独自性で再評価が進みつつある。",
    "chouden-breaker": "ピカチュウex SARの絶対的人気でSV中期の高額BOX枠。",
    "terastal-fes-ex": "テラスタル周年枠のハイクラスパック。収録幅が広くPSA狙いの層に人気。",
    "battle-partners": "レジェンド系SARとサポSR中心で、プレイ用途の需要が継続している。",
    "rocket-dan-no-eiko": "悪路線サポSR・AR多数で、構築デッキ需要×コレクター需要の両輪で強い。",
    "black-bolt": "ゼクロム系・DX構成で、白黒セット需要のうち黒側を支える。",
    "white-flare": "レシラム系・DX構成で、白黒セット需要のうち白側を支える。",
    "black-bolt-dx": "ブラックボルトのDX版。内容物の差でコレクション層に重視される。",
    "white-flare-dx": "ホワイトフレアのDX版。シュリンク状態の差が価格に出やすい。",
    "tohoku": "地域限定のスペシャルBOX。流通量が少なく時間経過とともに希少性が増す。",
    "hiroshima": "地域限定のスペシャルBOX。発売後に在庫が枯れて長期プレミアム化しやすい。",
    "fukuoka": "地域限定のスペシャルBOX。希少性で長期的に右肩上がりの相場。",
    "eevee-heroes": "絶版・封入SAR豪華で、S&S最高峰の投資対象BOX。",
    "vmax-climax": "ハイクラスパックの定番。リザードンVMAX HR等で長期的に高額安定。",
    "lost-abyss": "ギラティナVSTARを軸に、ロスト構築の需要で相場が底堅い。",
    "clay-burst": "ナンジャモSARの希少性でGレギュ絶版観測の代表格。",
    "rakuen-dragona": "アローラナッシーex SARを軸に、ドラゴン人気で安定相場。",
    "neppuu-arena": "強化拡張パック。SV後期の相場上昇基調に乗りやすい立ち位置。",
}


# Spotlight article URL map per box slug (only for boxes that have a spotlight)
SPOTLIGHT_URL: dict[str, tuple[str, str]] = {
    "151": ("151-spotlight.html", "ポケモンカード151がなぜ高い？定価12倍超え"),
    "inferno": ("inferno-x-spotlight.html", "インフェルノXが定価の5倍に高騰"),
    "ruler-of-black-flame": ("kokuen-spotlight.html", "黒炎の支配者が定価の約4倍に高騰"),
    "chouden-breaker": ("chouden-breaker-spotlight.html", "超電ブレイカーが定価7.5倍に高騰"),
    "clay-burst": ("clay-burst-spotlight.html", "クレイバーストとナンジャモSAR相場解説"),
    "ninja-spinner": ("ninja-spinner-spotlight.html", "ニンジャスピナーが定価2.5倍に高騰"),
    "rocket-dan-no-eiko": ("rocket-dan-no-eiko-spotlight.html", "ロケット団の栄光が定価5.8倍に高騰"),
    "mega-ex": ("mega-ex-spotlight.html", "MEGAドリームexが定価3.2倍にW字回復"),
    "mega-brave": ("mega-brave-spotlight.html", "メガブレイブが定価2.6倍で推移"),
}


def _row(rank: int, change: dict) -> str:
    cls, label = CATEGORY_TAG.get(change["category"], ("", ""))
    rank_cls = f"rank-{rank}" if rank <= 3 else ""
    sign = "+" if change["diff"] > 0 else ""
    pct_sign = "+" if change["pct"] > 0 else ""
    direction = "price-up" if change["diff"] > 0 else "price-down"
    return (
        f'<tr class="{rank_cls}"><td class="rank-num">{rank}</td>'
        f'<td><span class="tag {cls}">{label}</span> '
        f'<a href="box/{change["slug"]}.html">{change["short_name"]}</a></td>'
        f'<td>¥{change["first"]:,}</td><td>¥{change["last"]:,}</td>'
        f'<td class="{direction}">{sign}¥{change["diff"]:,} ({pct_sign}{change["pct"]:.1f}%)</td></tr>'
    )


def _short_name(full_name: str) -> str:
    """Strip the leading 'SV ' / 'MEGA ' / 'S&S ' prefix and emoji-marker text."""
    n = full_name
    # Remove 🔥 NEW: prefix added for upcoming packs
    if "NEW:" in n:
        n = n.split("NEW:", 1)[1].strip()
    for prefix in ("SV ", "MEGA ", "S&S ", "S＆S "):
        if n.startswith(prefix):
            n = n[len(prefix):]
            break
    return n


def _commentary_for_top3(rank: int, change: dict) -> str:
    flavor = BOX_FLAVOR.get(change["slug"], "")
    spot = SPOTLIGHT_URL.get(change["slug"])
    sign = "+" if change["diff"] > 0 else ""
    pct_sign = "+" if change["pct"] > 0 else ""
    body = (
        f'月初¥{change["first"]:,}から月末¥{change["last"]:,}と、'
        f'1箱あたり<strong>{sign}¥{change["diff"]:,}</strong>'
        f'（{pct_sign}{change["pct"]:.1f}%）の値動きを記録しました。'
    )
    if flavor:
        body += flavor
    if spot:
        body += f' 詳しくは <a href="{spot[0]}">【特集】{spot[1]}</a> で解説しています。'
    else:
        body += (
            f' 最新の買取価格は <a href="box/{change["slug"]}.html">'
            f'{change["short_name"]} BOXページ</a> で毎日チェックできます。'
        )
    return body


def build_monthly_html(
    year: int,
    month: int,
    first_date: str,
    last_date: str,
    gainers: list[dict],
    losers: list[dict],
    published_date: str,
    prev_ym: str | None = None,
    next_ym: str | None = None,
) -> str:
    """Render the monthly ranking HTML.

    `gainers` and `losers` items must have keys:
      name, short_name, slug, category, first, last, diff, pct
    """
    ym = f"{year}-{month:02d}"
    title = f"【{year}年{month}月】ポケカBOX買取 月間値上がりランキング"
    meta_desc = (
        f"{year}年{month}月のポケカ未開封BOX買取価格の値上がりランキング。"
        f"月初({first_date})から月末({last_date})までの変動を10店舗の実データで集計。"
    )

    # Lead summary highlights for the intro
    if gainers:
        top = gainers[0]
        rise_count = len([g for g in gainers if g["diff"] > 0])
        avg_pct = sum(g["pct"] for g in gainers) / max(1, len(gainers))
        intro_extra = (
            f"上昇したBOXは<strong>{rise_count}商品</strong>、平均上昇率は"
            f"<strong>+{avg_pct:.1f}%</strong>。"
            f'値上がり額1位は <a href="box/{top["slug"]}.html">{top["short_name"]}</a>で'
            f"<strong>+¥{top['diff']:,}</strong>を記録しました。"
        )
    else:
        intro_extra = "今月は上昇BOXが観測されませんでした（全体的に横ばい〜下落相場）。"

    # Build the top10 rows
    top10_rows = "\n".join(_row(i + 1, c) for i, c in enumerate(gainers[:10]))

    # TOP3 commentary blocks (h2 sections)
    top3_html = ""
    for i, c in enumerate(gainers[:3]):
        h2 = f"{i+1}位：{c['short_name']} ― {('+¥' if c['diff'] > 0 else '-¥') + format(abs(c['diff']), ',')}の値動き"
        top3_html += f"<h2>{h2}</h2>\n<p>{_commentary_for_top3(i + 1, c)}</p>\n\n"

    # Losers table
    if losers:
        losers_rows = "\n".join(
            _row(i + 1, c) for i, c in enumerate(losers[:5])
        )
        losers_block = (
            f"<h2>値下がりワースト5</h2>\n"
            f'<table class="rank-table">\n<thead>\n'
            f'<tr><th style="width:32px"></th><th>商品名</th><th>月初</th>'
            f"<th>月末</th><th>変動</th></tr>\n</thead>\n<tbody>\n"
            f"{losers_rows}\n</tbody>\n</table>\n"
        )
    else:
        losers_block = (
            "<h2>値下がり商品なし</h2>\n"
            "<p>今月は値下がりした商品が観測されませんでした。"
            "全体的に上昇〜横ばい相場でした。</p>\n"
        )

    # Related box links (top5 gainers + a few mainstays)
    related_slugs: list[tuple[str, str]] = []
    for c in gainers[:5]:
        related_slugs.append((c["slug"], c["short_name"]))
    # Ensure 151 / kokuen / mega-brave appear if not already there
    for s, n in [("151", "ポケモンカード151"), ("ruler-of-black-flame", "強化拡張パック「黒炎の支配者」"),
                 ("mega-brave", "MEGA 拡張パック「メガブレイブ」")]:
        if not any(s == rs[0] for rs in related_slugs):
            related_slugs.append((s, n))
    related_items = "\n".join(
        f'<li><a href="box/{s}.html">{n}</a> の買取価格をチェック</li>'
        for s, n in related_slugs[:6]
    )

    # Adjacent month navigation (prev / next), shown above and below the article
    nav_links: list[str] = []
    if prev_ym:
        py, pm = int(prev_ym[:4]), int(prev_ym[5:7])
        nav_links.append(
            f'<a href="monthly-ranking-{prev_ym}.html">'
            f'&larr; {py}年{pm}月のランキング</a>'
        )
    if next_ym:
        ny, nm = int(next_ym[:4]), int(next_ym[5:7])
        nav_links.append(
            f'<a href="monthly-ranking-{next_ym}.html">'
            f'{ny}年{nm}月のランキング &rarr;</a>'
        )
    month_nav_html = ""
    if nav_links:
        month_nav_html = (
            '<div style="display:flex;justify-content:space-between;gap:12px;'
            'margin:20px 0;padding:12px 16px;background:#f5f3ff;border-radius:8px;'
            'font-size:13px;font-weight:600">'
            + "".join(f'<span>{l}</span>' for l in nav_links)
            + "</div>"
        )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://h.accesstrade.net">
<link rel="dns-prefetch" href="https://m.media-amazon.com">
<meta name="description" content="{meta_desc}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/monthly-ranking-{ym}.html">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://pokeca-box-hikaku.com/monthly-ranking-{ym}.html">
<meta property="og:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<meta property="og:site_name" content="ポケカ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{meta_desc}">
<meta name="twitter:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<title>{title}｜ポケカ買取チェッカー</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RPTS6CRTCS"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-RPTS6CRTCS');
</script>
<style>
:root{{--bg:#f6f7fb;--card:#fff;--border:#e5e7eb;--text:#111827;--text-sub:#6b7280;--accent:#6366f1}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:var(--bg);color:var(--text);line-height:1.8}}
.header{{position:sticky;top:0;z-index:100;height:56px;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;padding:0 20px}}
.header a{{text-decoration:none}}
.header h1{{font-size:18px;font-weight:700;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.wrap{{max-width:1240px;margin:0 auto;padding:32px 16px 48px}}
.content-layout{{display:flex;gap:24px;align-items:flex-start}}
.content-layout article{{flex:1;min-width:0;max-width:760px}}
.article-nav{{width:180px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}}
.article-nav-title{{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}}
.article-nav a{{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4;transition:all .2s}}
.article-nav a:hover{{color:var(--accent);border-left-color:var(--accent)}}
.article-nav-sub{{font-size:12px;font-weight:700;margin:14px 0 6px;color:#b91c1c;padding-top:10px;border-top:1px solid var(--border)}}
.article-nav a.current{{color:var(--accent);border-left-color:var(--accent);font-weight:600}}
.mobile-footer-nav{{display:none;margin:24px 0;padding:18px 16px;background:#f9fafb;border:1px solid var(--border);border-radius:12px}}
.mfn-title{{font-size:14px;font-weight:700;margin-bottom:10px;color:var(--text)}}
.mfn-section{{margin-top:14px}}
.mfn-section-title{{font-size:12px;font-weight:700;color:#b91c1c;margin-bottom:8px;letter-spacing:.5px}}
.mobile-footer-nav a{{display:block;font-size:13px;padding:10px 12px;border-radius:8px;color:var(--text);text-decoration:none;background:#fff;margin-bottom:6px;border:1px solid var(--border);transition:all .2s}}
.mobile-footer-nav a:hover,.mobile-footer-nav a:active{{color:var(--accent);border-color:var(--accent);background:#f5f3ff}}
.mobile-footer-nav a.spot{{border-left:3px solid #b91c1c;font-weight:600}}
@media(max-width:1023px){{.mobile-footer-nav{{display:block}}}}
@media(max-width:1023px){{.content-layout{{display:block}}.article-nav{{width:100%;position:static;max-height:none;background:#f9fafb;border:1px solid var(--border);border-radius:8px;padding:12px 16px;margin-bottom:12px}}}}
.breadcrumb{{font-size:12px;color:var(--text-sub);margin-bottom:20px}}
.breadcrumb a{{color:var(--accent);text-decoration:none}}
article{{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:32px 28px}}
article h1{{font-size:22px;font-weight:800;margin-bottom:8px;line-height:1.4}}
.meta{{font-size:12px;color:var(--text-sub);margin-bottom:24px}}
article h2{{font-size:17px;font-weight:700;margin:28px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--accent);color:var(--text)}}
article p{{font-size:14px;margin-bottom:14px}}
article ul,article ol{{font-size:14px;padding-left:22px;margin-bottom:14px}}
article li{{margin-bottom:6px}}
.back{{display:inline-block;margin-top:24px;color:var(--accent);text-decoration:none;font-size:14px;font-weight:600}}
.next-article{{background:#f5f3ff;border:1px solid #c4b5fd;border-radius:8px;padding:16px;margin-top:24px;text-decoration:none;display:block;color:var(--text)}}
.next-article:hover{{background:#ede9fe}}
.next-article span{{font-size:12px;color:var(--text-sub)}}
.next-article p{{font-size:15px;font-weight:700;color:var(--accent);margin:4px 0 0}}
.ft{{text-align:center;padding:24px 16px;font-size:11px;color:var(--text-sub)}}
.ft a{{color:var(--accent)}}
.rank-table{{width:100%;border-collapse:collapse;margin:16px 0 20px;font-size:13px}}
.rank-table th{{background:#f5f3ff;padding:8px 10px;text-align:left;font-weight:700;border-bottom:2px solid var(--accent);font-size:12px}}
.rank-table td{{padding:8px 10px;border-bottom:1px solid var(--border)}}
.rank-table tr:hover{{background:#fafafa}}
.rank-num{{font-weight:800;color:var(--accent);font-size:16px;text-align:center;width:32px}}
.rank-1 .rank-num{{color:#f59e0b;font-size:20px}}
.rank-2 .rank-num{{color:#94a3b8;font-size:18px}}
.rank-3 .rank-num{{color:#b45309;font-size:18px}}
.price-up{{color:#16a34a;font-weight:700}}
.price-down{{color:#dc2626;font-weight:700}}
.tag{{display:inline-block;font-size:10px;padding:1px 6px;border-radius:4px;font-weight:600}}
.tag-mega{{background:#fef3c7;color:#92400e}}
.tag-sv{{background:#dbeafe;color:#1e40af}}
.tag-ss{{background:#fce7f3;color:#9d174d}}
.tag-special{{background:#d1fae5;color:#065f46}}
</style>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"}},
    {{"@type": "ListItem", "position": 2, "name": "{year}年{month}月 月間値上がりランキング"}}
  ]
}}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "{title}",
  "description": "{meta_desc}",
  "datePublished": "{published_date}",
  "dateModified": "{published_date}",
  "image": "https://pokeca-box-hikaku.com/ogp.jpg",
  "author": {{"@type": "Organization", "name": "ポケカ買取チェッカー編集部", "url": "https://pokeca-box-hikaku.com/"}},
  "publisher": {{"@type": "Organization", "name": "ポケカ買取チェッカー", "logo": {{"@type": "ImageObject", "url": "https://pokeca-box-hikaku.com/ogp.png"}}}},
  "mainEntityOfPage": {{"@type": "WebPage", "@id": "https://pokeca-box-hikaku.com/monthly-ranking-{ym}.html"}},
  "articleSection": "月間レポート",
  "inLanguage": "ja"
}}
</script>
</head>
<body>
<div class="header"><a href="index.html"><h1>ポケカ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="index.html">トップ</a> &gt; {year}年{month}月 月間値上がりランキング</div>
<div class="content-layout">
<nav class="article-nav">
<div class="article-nav-title">一般記事</div>
<a href="index.html">買取価格比較</a>
<a href="sv-box-list.html">📋 SV全BOX一覧</a>
<a href="mega-box-list.html">📋 MEGA全BOX一覧</a>
<a href="ss-box-list.html">📋 S&S全BOX一覧</a>
<a href="weekly/">🔥 今週の急上昇記事</a>
<a href="ranking.html">上昇ランキング</a>
<a href="kaitori-tips.html">BOX買取のコツ</a>
<a href="about.html">運営者情報</a>
<a href="shop-hikaku.html">10店舗比較</a>
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
<a href="rocket-dan-no-eiko-spotlight.html">【特集】ロケット団の栄光高騰</a>
<a href="mega-ex-spotlight.html">【特集】MEGAドリームex高騰</a>
<a href="mega-brave-spotlight.html">【特集】メガブレイブ高騰</a>
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
<article>
<h1>{title}</h1>
<div class="meta">集計期間: {first_date} 〜 {last_date} ｜ 公開: {published_date}</div>

<p>当サイトが毎日記録している10店舗の買取価格データをもとに、<strong>{year}年{month}月に最も値上がりしたポケカ未開封BOX</strong>をランキング形式でまとめました。{intro_extra} 売り時の判断や投資の参考にどうぞ。</p>

{month_nav_html}

<h2>値上がりTOP10</h2>

<table class="rank-table">
<thead>
<tr><th style="width:32px"></th><th>商品名</th><th>月初</th><th>月末</th><th>変動</th></tr>
</thead>
<tbody>
{top10_rows}
</tbody>
</table>

{top3_html}
{losers_block}

<h2>まとめ：{year}年{month}月の相場の動き</h2>
<p>本月のランキングは <a href="ranking.html">日次の上昇ランキング</a>・<a href="weekly/">週間急上昇ランキング</a> とあわせて確認すると、短期〜長期のトレンドを多角的に把握できます。買取価格は日々変動するため、最新の価格は <a href="index.html">買取価格比較トップ</a> でチェックしてください。</p>

<h2>関連BOXの買取価格をチェック</h2>
<p>このランキングで紹介したBOXを含め、特に比較需要が高いものをまとめました。</p>
<ul>
{related_items}
</ul>

{month_nav_html}

<a href="kaitori-tips.html" class="next-article">
<span>おすすめ記事 &rarr;</span>
<p>ポケカBOX買取で損しない5つのコツ</p>
</a>

<a href="index.html" class="back">&larr; 買取価格比較に戻る</a>
</article>
</div><!-- /content-layout -->
<nav class="mobile-footer-nav">
  <div class="mfn-title">📚 他の記事を読む</div>
  <div class="mfn-section">
    <div class="mfn-section-title">🔥 BOX深掘り特集</div>
    <a class="spot" href="151-spotlight.html">【特集】ポケモンカード151がなぜ高い？12倍超え解説</a>
    <a class="spot" href="inferno-x-spotlight.html">【特集】インフェルノXが定価の5倍に高騰</a>
    <a class="spot" href="kokuen-spotlight.html">【特集】黒炎の支配者がなぜ高い？定価の約4倍</a>
    <a class="spot" href="chouden-breaker-spotlight.html">【特集】超電ブレイカーが定価7.5倍に高騰</a>
    <a class="spot" href="clay-burst-spotlight.html">【特集】クレイバーストとナンジャモSAR相場</a>
    <a class="spot" href="ninja-spinner-spotlight.html">【特集】ニンジャスピナーが定価2.5倍に高騰</a>
    <a class="spot" href="rocket-dan-no-eiko-spotlight.html">【特集】ロケット団の栄光が定価5.8倍に高騰</a>
    <a class="spot" href="mega-ex-spotlight.html">【特集】MEGAドリームexが定価3.2倍にW字回復</a>
    <a class="spot" href="mega-brave-spotlight.html">【特集】メガブレイブが定価2.6倍で推移</a>
  </div>
  <div class="mfn-section">
    <div class="mfn-section-title" style="color:#6d28d9">📘 掘り下げガイド</div>
    <a href="zeppan-ranking-2026-03.html">📊 S&amp;S以降 絶版BOXランキング</a>
    <a href="lizardon-box-guide.html">🔥 リザードン高騰BOX完全ガイド</a>
    <a href="mega-pack-compare.html">⚡ MEGA拡張パック完全比較</a>
    <a href="kokuen-vs-rocket.html">⚔️ 黒炎 vs ロケット団の栄光</a>
  </div>
  <div class="mfn-section">
    <div class="mfn-section-title">📰 一般記事</div>
    <a href="index.html">買取価格比較トップ</a>
    <a href="weekly/">🔥 今週の急上昇記事</a>
    <a href="ranking.html">上昇ランキング</a>
    <a href="kaitori-tips.html">BOX買取のコツ</a>
    <a href="shop-hikaku.html">10店舗比較</a>
    <a href="box-toushi.html">BOX投資の始め方</a>
    <a href="restock-guide.html">再販情報の見つけ方</a>
    <a href="release-schedule-2026.html">📅 2026年 新弾カレンダー</a>
    <a href="price-pattern-guide.html">📈 相場5段階パターン</a>
    <a href="shrink-nashi.html">シュリンクなしBOX</a>
    <a href="psa-guide.html">PSA鑑定ガイド</a>
    <a href="mercari-hikaku.html">メルカリ・スニダン比較</a>
    <a href="single-card-tips.html">シングル売り</a>
  </div>
</nav>
</div>
<div style="text-align:center;padding:16px;font-size:11px;color:#6b7280">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" style="max-width:100%;height:auto" loading="lazy" decoding="async"></a>
  <div style="margin-top:12px"><a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" style="max-width:100%;height:auto" loading="lazy" decoding="async"></a></div>
</div>
<div class="ft">
  <a href="index.html">ポケカ買取チェッカー</a> / <a href="shop-hikaku.html">10店舗比較</a> / <a href="privacy.html">プライバシーポリシー</a>
</div>
</body>
</html>
"""


def build_change_list(
    products,
    first_data: list[dict],
    last_data: list[dict],
    slug_map: dict[str, str],
) -> list[dict]:
    """Combine first/last snapshot data into a list of change dicts."""
    first_prices = {item["name"]: item.get("max_price", 0) for item in first_data}
    last_prices = {item["name"]: item.get("max_price", 0) for item in last_data}

    changes: list[dict] = []
    for p in products:
        fp = first_prices.get(p.name, 0)
        lp = last_prices.get(p.name, 0)
        if fp <= 0 or lp <= 0:
            continue
        diff = lp - fp
        pct = (diff / fp) * 100 if fp > 0 else 0
        changes.append({
            "name": p.name,
            "short_name": _short_name(p.name),
            "slug": slug_map.get(p.name, ""),
            "category": p.category,
            "first": fp,
            "last": lp,
            "diff": diff,
            "pct": pct,
        })
    return changes
