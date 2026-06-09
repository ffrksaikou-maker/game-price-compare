"""Template builder for the weekly hot-boxes article.

Kept as a separate module to avoid bloating generator.py. Called from
generator.generate_weekly_article().
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path


JST = timezone(timedelta(hours=9))


# BOX-specific flavor notes. When a slug is listed here, its commentary gets
# an extra one-liner grounded in the BOX's known characteristics.
# Keep these factual and evergreen (no time-sensitive claims).
BOX_FLAVOR: dict[str, str] = {
    "inferno": "メガリザードンXex MUR/SARの2枚看板で、MEGA系では別格の期待値BOX。",
    "mega-brave": "MEGAシリーズ第1弾の象徴。メガルカリオexの人気が相場を下支えしている。",
    "mega-sinfonia": "メガブレイブと同時発売のもう一方。鋼タイプ好き・メガルカリオ好きに根強い需要。",
    "mega-ex": "MEGAハイクラスパック枠。封入率が絞られておりMUR/SAR狙いで注目されやすい。",
    "munikis-zero": "MEGA第3弾。相場形成中のBOXで、SAR引き当て期待で値動きが荒い。",
    "ninja-spinner": "最新のMEGA弾として注目度が高く、初動の勢いが相場に反映されやすい。",
    "151": "リザードンex SARを筆頭に、旧世代ファン需要で常時上位に食い込む定番高額BOX。",
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
    "battle-partners": "プレイ層ニーズが厚く、大会シーズンの需要で動きやすい。",
    # S&S (for TOP3 section; keep brief)
    "eevee-heroes": "絶版・封入SAR豪華で、S&S最高峰の投資対象BOX。",
    "vmax-climax": "ハイクラスパックの定番。リザードンVMAX HR 等で長期的に高額安定。",
    "lost-abyss": "ギラティナVSTARを軸に、ロスト構築の需要で相場が底堅い。",
}


def _build_top5_commentary(top5: list[dict]) -> str:
    """Generate varied, deterministic commentary for TOP5 entries.
    Differentiates on rank position, momentum tier, price tier, and BOX-specific flavor.
    """
    # Position-specific lead phrases (rank 1 through 5)
    rank_leads = [
        "今週最大の上昇幅を記録。文句なしの主役クラス。",
        "2位に食い込む堅実な上昇。勢いを維持できるかが次週の焦点。",
        "3位につけた実力派。上位2つに追走できる位置。",
        "4位で観測。ここからが踏ん張りどころで、次週5位以下に下がるか上位に浮上するか見極めたいところ。",
        "5位入賞。TOP3組との差は広いが、相場の安定した底上げに寄与している。",
    ]

    # Momentum pool: multiple phrases per tier, rotated by rank index for variety
    momentum_pool: dict[str, list[str]] = {
        "extreme": [  # pct >= 20
            "2桁後半の上昇率で、短期的な過熱感が否めない水準。追随はタイミング選びが必須。",
            "週単位で+20%超は異常値に近く、加熱相場と呼ぶべき動きが続いている。",
            "過去の相場でも稀な急騰速度で、数字だけで追うと高値掴みのリスクが大きい。",
            "20%超のスパイクは長続きしない傾向。一息つく調整局面を覚悟しておきたい。",
            "短期トレンドが極端に強いタイプで、投機マネーが一気に集まっている局面。",
        ],
        "strong": [  # 12 <= pct < 20
            "2桁中盤の力強い上昇で、トレンド入りと呼べる勢い。継続性があれば来週も上位圏。",
            "週+15%前後の動きは「話題化」の入口。SNSや動画で取り上げられ始めた可能性。",
            "10%台後半の動きは、需給バランスが崩れ始めたサイン。次週の動向で方向性が確定する。",
            "12〜20%の上昇帯は、実需と投機の混在ゾーン。買う側の判断が分かれやすい。",
            "このペースが維持されれば、月次では+40%超になる計算。要注目の加速フェーズ。",
        ],
        "moderate": [  # 7 <= pct < 12
            "1桁後半の安定した上昇。派手さはないが需給の積み上げを感じる動き。",
            "7〜12%の穏やかな上昇は、コレクター需要の静かな流入を示唆している。",
            "急騰ではなくじわ上げ型。長期保有層にとって安心感のある動きと言える。",
            "過熱感は控えめで、ここからのエントリーでも過度なリスクは少ないレンジ。",
            "週次+10%前後は健全な上昇ペース。持続すれば月次で+30%超の可能性。",
        ],
        "gentle": [  # 4 <= pct < 7
            "1桁前半のじわ上げ。静かに相場が押し上げられているタイプで、見落としがちだが無視できない。",
            "5%前後の上昇は、地味だが底堅い需要のサイン。中長期の上昇トレンドの初期に見られる動き。",
            "小さな上昇だが、前週までと違う方向性が出ているかは次週で確認したい。",
            "急騰するBOXとは別の物差しで見るべきゾーン。安定派に好まれる動き方。",
            "過熱相場を避けたい投資層が狙う、静かに積み上がるタイプの上昇。",
        ],
        "minor": [  # < 4
            "わずかな上昇。反転の初動か、単なるノイズかは次週のデータで判断したい。",
            "誤差に近い上げ幅だが、ランクインは「下げ止まり」のシグナルとしては意味がある。",
            "数字としては小さいが、ここ数日の動きに方向感が出たかどうかはチェックすべき。",
            "相場の底値圏で動きが出始めたタイプ。本格反騰の前兆か、見極めどころ。",
            "静かな動きだが、他のBOXが停滞する中での上昇はそれだけで価値がある。",
        ],
    }

    def _momentum(pct: float, idx: int) -> str:
        if pct >= 20:
            bucket = "extreme"
        elif pct >= 12:
            bucket = "strong"
        elif pct >= 7:
            bucket = "moderate"
        elif pct >= 4:
            bucket = "gentle"
        else:
            bucket = "minor"
        pool = momentum_pool[bucket]
        return pool[idx % len(pool)]

    # Price tier pool, also rotated to avoid repetition
    price_pool: dict[str, list[str]] = {
        "ultra": [  # >= 50000
            "既に超高額帯に到達しており、流動性は限られる。",
            "5万円超のBOXは日常的に動く対象ではなく、コレクターの選別買いが中心。",
            "超高額帯ゆえに、下落局面ではまとまった金額が一気に蒸発するリスクも意識したい。",
            "この価格帯は「買える人」が限られるため、相場の薄さに注意が必要。",
        ],
        "high": [  # 25000-50000
            "高額帯BOXとしての地位を固めつつある水準。",
            "¥25,000〜¥50,000のレンジは、投資層の主戦場と言える価格帯。",
            "高額帯に突入すると買い手が減る一方で、手放す側の心理的なハードルも上がる。",
            "このゾーンは短期売買より中長期保有が向いている。",
        ],
        "mid": [  # 12000-25000
            "中堅BOX帯で、投資対象として拾いやすいゾーン。",
            "¥12,000〜¥25,000のミドルレンジは最も取引が活発で、エントリーしやすい水準。",
            "この価格帯は上にも下にも動きやすく、週次のウォッチ対象として最適。",
            "中堅帯は流動性が高く、損切りも利確もしやすいバランスの良い価格。",
        ],
        "low": [  # 6000-12000
            "定価+αの低位置で、仕込み余地がまだ残るレンジ。",
            "定価の1.5〜2倍帯で、まだ投資対象として参入しやすい水準。",
            "このゾーンは値上がり余地が大きい分、再販リスクも相応にある。",
            "低価格帯は買える数量が多く、コレクションの土台作りに向いている。",
        ],
        "floor": [  # < 6000
            "定価割れに近い水準からの反発で、底打ち候補として見ておきたい。",
            "底値圏での上昇は、下落トレンドの終了サインとして意識されやすい。",
            "定価付近まで落ちたBOXは、プレイ層の実需が戻ってくる価格帯。",
            "この水準では投資というより「保険買い」の発想で取りに行く対象。",
        ],
    }

    def _price_tier(price: int, idx: int) -> str:
        if price >= 50000:
            bucket = "ultra"
        elif price >= 25000:
            bucket = "high"
        elif price >= 12000:
            bucket = "mid"
        elif price >= 6000:
            bucket = "low"
        else:
            bucket = "floor"
        pool = price_pool[bucket]
        return pool[idx % len(pool)]

    parts = []
    for i, c in enumerate(top5):
        lead = rank_leads[i] if i < len(rank_leads) else "上位ランクイン。"
        flavor = BOX_FLAVOR.get(c["slug"], "")
        sentences = [
            lead,
            _momentum(c["pct"], i),
        ]
        # Insert BOX-specific flavor at position 2 if available
        if flavor:
            sentences.insert(1, flavor)
        sentences.append(_price_tier(c["today"], i))
        body = "".join(sentences)
        parts.append(
            f'<div class="spotlight">'
            f'<h3>#{i+1} <a href="../box/{c["slug"]}.html">{c["name"]}</a></h3>'
            f'<p class="spot-stats">先週比 <strong>+¥{c["diff"]:,}</strong> '
            f'(<strong>+{c["pct"]:.1f}%</strong>) / '
            f'現在価格 <strong>¥{c["today"]:,}</strong> '
            f'(先週 ¥{c["week_ago"]:,})</p>'
            f'<p class="spot-body">{body}</p>'
            f'</div>'
        )
    return "".join(parts)


def build_weekly_html(
    year: int,
    week_no: int,
    today_str: str,
    week_ago_str: str,
    update_date: str,
    top_gainers: list[dict],
    minor_gainers: list[dict],
    ss_top_gainers: list[dict],
    all_changes: list[dict],
    chart_dates: list[str],
    chart_history: dict[str, list[int]],
    top_losers: list[dict] | None = None,
    ss_top_losers: list[dict] | None = None,
) -> str:
    """Build the complete HTML for a weekly hot-boxes article.

    top_gainers: SV+MEGA TOP10 (main ranking)
    minor_gainers: SV+MEGA next 5 (値上がり次点)
    ss_top_gainers: S&S TOP3 (secondary section)
    all_changes: SV+MEGA changes only (for context stats)
    chart_dates: list of date strings (e.g., ['2026-04-05', ..., '2026-04-12'])
    chart_history: {slug: [price_day1, ..., price_day8]}
    """
    # Week label, e.g., "2026年4月第3週" (approx)
    # Use the start of week date to compute month and week-of-month
    week_label = f"{year}年第{week_no}週"

    # Determine month-week label for Japanese title
    # Get ISO week start date (Monday)
    iso_start = datetime.strptime(f"{year}-W{week_no:02d}-1", "%Y-W%W-%w").date()
    # Compute week of month (1st/2nd/3rd/4th/5th)
    week_of_month = (iso_start.day - 1) // 7 + 1
    wom_jp = ["第1週", "第2週", "第3週", "第4週", "第5週"][week_of_month - 1]
    title_label = f"{iso_start.year}年{iso_start.month}月{wom_jp}"

    # Stats for intro
    total_products = len(all_changes)
    gainers = [c for c in all_changes if c["diff"] > 0]
    avg_diff = sum(c["diff"] for c in gainers) / len(gainers) if gainers else 0
    avg_pct = sum(c["pct"] for c in gainers) / len(gainers) if gainers else 0

    top_losers = top_losers or []
    ss_top_losers = ss_top_losers or []
    losers = [c for c in all_changes if c["diff"] < 0]
    flat = [c for c in all_changes if c["diff"] == 0]

    # Build ranking rows
    def _row(rank: int, c: dict) -> str:
        sign = "+" if c["diff"] > 0 else ""
        cls = "up" if c["diff"] >= 0 else "down"
        return (
            f'<tr>'
            f'<td class="rank">{rank}</td>'
            f'<td class="pname"><a href="../box/{c["slug"]}.html">{c["name"]}</a></td>'
            f'<td class="price-now">¥{c["today"]:,}</td>'
            f'<td class="price-before">¥{c["week_ago"]:,}</td>'
            f'<td class="diff {cls}">{sign}¥{c["diff"]:,} ({sign}{c["pct"]:.1f}%)</td>'
            f'</tr>'
        )

    top_rows = "\n".join(_row(i, c) for i, c in enumerate(top_gainers, 1))
    minor_rows = "\n".join(_row(i, c) for i, c in enumerate(minor_gainers, 1))
    ss_rows = "\n".join(_row(i, c) for i, c in enumerate(ss_top_gainers, 1))
    top_loser_rows = "\n".join(_row(i, c) for i, c in enumerate(top_losers, 1))
    ss_loser_rows = "\n".join(_row(i, c) for i, c in enumerate(ss_top_losers, 1))

    # Build mini chart cards (visual grid) + chart init JS
    def _build_mini_charts(items: list[dict], prefix: str, color: str) -> tuple[str, str]:
        html_parts = []
        js_parts = []
        chart_labels_js = json.dumps(chart_dates, ensure_ascii=False)
        for i, c in enumerate(items):
            canvas_id = f"{prefix}Chart{i}"
            # Short name: strip the category prefix ("SV 拡張パック" etc)
            short = re.sub(r"^(SV|MEGA|S&S)\s*(拡張パック(?:DX)?|強化拡張パック|ハイクラスパック|拡張パックDX)?\s*", "", c["name"])
            short = re.sub(r"[「」]", "", short).strip()
            if not short:
                short = c["name"][:30]
            sign = "+" if c["diff"] > 0 else ""
            arrow = "↑" if c["diff"] > 0 else "↓"
            diff_cls = "up" if c["diff"] >= 0 else "down"
            prices = chart_history.get(c["slug"], [])
            if not prices:
                continue
            data_js = json.dumps(prices)
            html_parts.append(
                f'<div class="mini-chart-card">'
                f'<div class="mc-rank">#{i+1}</div>'
                f'<a href="../box/{c["slug"]}.html" class="mc-name">{short}</a>'
                f'<div class="mc-price-row">'
                f'<span class="mc-price">¥{c["today"]:,}</span>'
                f'<span class="mc-diff {diff_cls}">{arrow}{sign}¥{c["diff"]:,} ({sign}{c["pct"]:.1f}%)</span>'
                f'</div>'
                f'<canvas id="{canvas_id}" height="100"></canvas>'
                f'</div>'
            )
            js_parts.append(f"""
new Chart(document.getElementById('{canvas_id}').getContext('2d'), {{
  type: 'line',
  data: {{
    labels: {chart_labels_js},
    datasets: [{{ data: {data_js}, borderColor: '{color}', borderWidth: 2, fill: true,
      backgroundColor: '{color}22', tension: 0.3, pointRadius: 2 }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }}, tooltip: {{ callbacks: {{ label: function(c) {{ return '\\u00a5' + c.parsed.y.toLocaleString(); }} }} }} }},
    scales: {{
      x: {{ ticks: {{ font: {{ size: 9 }}, maxRotation: 0, maxTicksLimit: 4 }}, grid: {{ display: false }} }},
      y: {{ ticks: {{ callback: v => '\\u00a5' + (v/1000).toFixed(0) + 'k', font: {{ size: 9 }} }}, grid: {{ color: '#f3f4f6' }} }}
    }}
  }}
}});""")
        return "\n".join(html_parts), "\n".join(js_parts)

    top_charts_html, top_charts_js = _build_mini_charts(top_gainers, "svUp", "#dc2626")
    ss_charts_html, ss_charts_js = _build_mini_charts(ss_top_gainers, "ssUp", "#f59e0b")
    loss_charts_html, loss_charts_js = _build_mini_charts(top_losers, "svDown", "#2563eb")
    ss_loss_charts_html, ss_loss_charts_js = _build_mini_charts(ss_top_losers, "ssDown", "#2563eb")

    # Build detailed commentary for each top 5
    top5_commentary = _build_top5_commentary(top_gainers[:5])

    # JSON-LD structured data
    itemlist_items = []
    combined_items = top_gainers + ss_top_gainers
    for i, c in enumerate(combined_items, 1):
        itemlist_items.append({
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "Product",
                "name": c["name"],
                "url": f"https://pokeca-box-hikaku.com/box/{c['slug']}.html",
                "image": f"https://pokeca-box-hikaku.com/images/boxes/{c['slug']}.png",
                "brand": {"@type": "Brand", "name": "ポケモンカードゲーム"},
                "offers": {
                    "@type": "Offer",
                    "price": c["today"],
                    "priceCurrency": "JPY",
                    "availability": "https://schema.org/InStock",
                },
            },
        })

    article_headline = f"【{title_label}】ポケカBOX 週間価格変化ランキング｜値上がり・値下がりTOP"
    article_desc = (
        f"{week_ago_str}〜{today_str}の7日間で買取価格が動いたポケモンカード未開封BOX。"
        "値上がりTOP・値下がりTOP（SV・MEGA TOP10 + S&S TOP3）を10店舗実データから抽出。"
        "現在の下落トレンドもひと目で分かる。毎週更新。"
    )
    article_jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article_headline,
        "description": article_desc,
        "datePublished": today_str,
        "dateModified": today_str,
        "image": "https://pokeca-box-hikaku.com/ogp.jpg",
        "author": {
            "@type": "Organization",
            "name": "ポケカ買取チェッカー編集部",
            "url": "https://pokeca-box-hikaku.com/",
        },
        "publisher": {
            "@type": "Organization",
            "name": "ポケカ買取チェッカー",
            "logo": {"@type": "ImageObject", "url": "https://pokeca-box-hikaku.com/ogp.png"},
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://pokeca-box-hikaku.com/weekly/{year}-w{week_no:02d}.html",
        },
        "articleSection": "週間BOX値動きランキング",
        "inLanguage": "ja",
    }
    itemlist_jsonld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"ポケカBOX 週間価格変化ランキング 値上がりTOP{len(top_gainers)} ({week_ago_str}→{today_str})",
        "description": article_desc,
        "numberOfItems": len(top_gainers),
        "itemListElement": itemlist_items,
    }
    breadcrumb_jsonld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"},
            {"@type": "ListItem", "position": 2, "name": "週間値動き記事", "item": "https://pokeca-box-hikaku.com/weekly/"},
            {"@type": "ListItem", "position": 3, "name": article_headline},
        ],
    }
    jsonld_block = (
        '<script type="application/ld+json">\n'
        + json.dumps(article_jsonld, ensure_ascii=False, indent=2)
        + '\n</script>\n'
        '<script type="application/ld+json">\n'
        + json.dumps(itemlist_jsonld, ensure_ascii=False, indent=2)
        + '\n</script>\n'
        '<script type="application/ld+json">\n'
        + json.dumps(breadcrumb_jsonld, ensure_ascii=False, indent=2)
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
<link rel="preconnect" href="https://h.accesstrade.net">
<meta name="description" content="{article_desc}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/weekly/{year}-w{week_no:02d}.html">
<meta property="og:title" content="{article_headline}">
<meta property="og:description" content="{article_desc}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://pokeca-box-hikaku.com/weekly/{year}-w{week_no:02d}.html">
<meta property="og:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<meta property="og:site_name" content="ポケカ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{article_headline}">
<meta name="twitter:description" content="{article_desc}">
<meta name="twitter:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<title>{article_headline}｜ポケカ買取チェッカー</title>
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
{jsonld_block}
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
.content-layout article{{flex:1;min-width:0;max-width:800px}}
.article-nav{{width:180px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}}
.article-nav-title{{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}}
.article-nav a{{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4;transition:all .2s}}
.article-nav a:hover{{color:var(--accent);border-left-color:var(--accent)}}
.article-nav a.current{{color:var(--accent);border-left-color:var(--accent);font-weight:600}}
.article-nav-sub{{font-size:12px;font-weight:700;margin:14px 0 6px;color:#b91c1c;padding-top:10px;border-top:1px solid var(--border)}}
@media(max-width:1023px){{.content-layout{{display:block}}.article-nav{{display:none}}}}
.breadcrumb{{font-size:12px;color:var(--text-sub);margin-bottom:20px}}
.breadcrumb a{{color:var(--accent);text-decoration:none}}
article{{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:32px 28px;margin-bottom:24px}}
article h1{{font-size:22px;font-weight:800;margin-bottom:8px;line-height:1.4}}
.meta{{font-size:12px;color:var(--text-sub);margin-bottom:24px}}
article h2{{font-size:17px;font-weight:700;margin:32px 0 14px;padding-bottom:6px;border-bottom:2px solid var(--accent)}}
article h3{{font-size:15px;font-weight:700;margin:16px 0 8px;color:var(--accent)}}
article p{{font-size:14px;margin-bottom:14px}}
.lead{{background:#f5f3ff;border:1px solid #c4b5fd;border-radius:8px;padding:16px 20px;margin-bottom:24px;font-size:14px}}
.lead strong{{color:var(--accent)}}
.rank-table{{width:100%;border-collapse:collapse;font-size:13px;margin:14px 0}}
.rank-table th{{background:#f9fafb;padding:10px 8px;text-align:left;font-size:11px;color:var(--text-sub);border-bottom:2px solid var(--border)}}
.rank-table td{{padding:10px 8px;border-bottom:1px solid var(--border)}}
.rank-table .rank{{width:32px;text-align:center;font-weight:700;color:var(--accent)}}
.rank-table .pname a{{color:var(--text);text-decoration:none;font-weight:600}}
.rank-table .pname a:hover{{color:var(--accent);text-decoration:underline}}
.rank-table .price-now,.rank-table .price-before{{white-space:nowrap;font-variant-numeric:tabular-nums}}
.rank-table .price-before{{color:var(--text-sub);font-size:12px}}
.rank-table .diff{{white-space:nowrap;font-weight:700;font-variant-numeric:tabular-nums}}
.rank-table .diff.up{{color:#dc2626}}
.rank-table .diff.down{{color:#2563eb}}
.section-down{{color:#2563eb!important;border-bottom-color:#2563eb!important}}
.mini-charts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;margin:14px 0}}
.mini-chart-card{{background:#fff;border:1px solid var(--border);border-radius:10px;padding:14px 16px;position:relative}}
.mc-rank{{position:absolute;top:10px;right:14px;font-size:11px;font-weight:800;color:var(--accent);background:#eef2ff;padding:2px 8px;border-radius:10px}}
.mc-name{{display:block;font-size:13px;font-weight:700;color:var(--text);text-decoration:none;margin-bottom:6px;padding-right:36px;line-height:1.4}}
.mc-name:hover{{color:var(--accent)}}
.mc-price-row{{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:8px}}
.mc-price{{font-size:17px;font-weight:800;color:var(--text)}}
.mc-diff.up{{font-size:12px;font-weight:700;color:#dc2626}}
.mc-diff.down{{font-size:12px;font-weight:700;color:#2563eb}}
.mini-chart-card canvas{{width:100%!important;height:100px!important}}
.spotlight{{background:#fffbeb;border-left:4px solid #f59e0b;border-radius:4px;padding:14px 18px;margin:12px 0}}
.spotlight h3{{margin:0 0 8px;color:var(--text)}}
.spotlight h3 a{{color:var(--text);text-decoration:none}}
.spotlight h3 a:hover{{color:var(--accent)}}
.spot-stats{{font-size:13px;color:var(--text-sub);margin-bottom:4px}}
.spot-stats strong{{color:var(--text)}}
.disclaimer{{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:14px 18px;margin:24px 0;font-size:12px;color:#9a3412}}
.disclaimer strong{{color:#c2410c}}
.cta{{display:block;margin-top:24px;padding:16px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:12px;text-align:center;text-decoration:none;color:#fff;font-size:15px;font-weight:700}}
.back{{display:inline-block;margin-top:24px;color:var(--accent);text-decoration:none;font-size:14px;font-weight:600}}
.ad{{text-align:center;padding:12px 16px}}
.ft{{text-align:center;padding:24px 16px;font-size:11px;color:var(--text-sub)}}
.ft a{{color:var(--accent)}}
@media(max-width:640px){{
  .rank-table{{font-size:12px}}
  .rank-table th,.rank-table td{{padding:8px 6px}}
  .rank-table .price-before{{display:none}}
  article{{padding:20px 16px}}
}}
</style>
</head>
<body>
<div class="header"><a href="../index.html"><h1>ポケカ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="../index.html">トップ</a> &gt; <a href="index.html">週間記事</a> &gt; {title_label} 価格変化ランキング</div>

<div class="content-layout">
<nav class="article-nav">
<div class="article-nav-title">一般記事</div>
<a href="../index.html">買取価格比較</a>
<a href="index.html" class="current">🔥 今週の値動き記事</a>
<a href="../ranking.html">上昇ランキング</a>
<a href="../souba-mynumber-2026.html">📰 相場下落・膠着とマイナンバー</a>
<a href="../kaitori-tips.html">BOX買取のコツ</a>
<a href="../shop-hikaku.html">10店舗比較</a>
<a href="../single-card-tips.html">シングル売り</a>
<a href="../psa-guide.html">PSA鑑定ガイド</a>
<a href="../mercari-hikaku.html">メルカリ・スニダン比較</a>
<a href="../shrink-nashi.html">シュリンクなしBOX</a>
<a href="../box-toushi.html">BOX投資の始め方</a>
<a href="../restock-guide.html">再販情報の見つけ方</a>
<a href="../release-schedule-2026.html">📅 2026年 新弾カレンダー</a>
<a href="../price-pattern-guide.html">📈 相場5段階パターン</a>
<div class="article-nav-sub">🔥 BOX深掘り特集</div>
<a href="../151-spotlight.html">【特集】ポケモンカード151高騰</a>
<a href="../inferno-x-spotlight.html">【特集】インフェルノX高騰</a>
<a href="../kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>
<a href="../chouden-breaker-spotlight.html">【特集】超電ブレイカー高騰</a>
<a href="../clay-burst-spotlight.html">【特集】クレイバースト高騰</a>
<a href="../ninja-spinner-spotlight.html">【特集】ニンジャスピナー高騰</a>
<a href="../rocket-dan-no-eiko-spotlight.html">【特集】ロケット団の栄光高騰</a>
<a href="../mega-ex-spotlight.html">【特集】MEGAドリームex高騰</a>
<a href="../mega-brave-spotlight.html">【特集】メガブレイブ高騰</a>
<div class="article-nav-sub" style="color:#6d28d9">📘 掘り下げガイド</div>
<a href="../zeppan-ranking-2026-03.html">📊 S&amp;S以降 絶版BOXランキング</a>
<a href="../lizardon-box-guide.html">🔥 リザードン高騰BOX完全ガイド</a>
<a href="../mega-pack-compare.html">⚡ MEGA拡張パック完全比較</a>
<a href="../kokuen-vs-rocket.html">⚔️ 黒炎 vs ロケット団の栄光</a>
<a href="../mega-lizardon-x-guide.html">メガリザードンXex MUR/SAR</a>
<a href="../lizardon-sar-kokuen-guide.html">リザードンex SAR(黒炎)</a>
<a href="../erika-sar-guide.html">エリカの招待 SAR</a>
<a href="../pigeot-sar-guide.html">ピジョットex SAR</a>
<a href="../masterball-mirror-guide.html">151マスターボールミラー</a>
<a href="../kokuen-atari-guide.html">黒炎 当たりカード完全ガイド</a>
</nav>

<article>
<h1>{article_headline}</h1>
<div class="meta">公開日: {today_str} / 比較期間: {week_ago_str} 〜 {today_str} / データ源: 10店舗買取価格の自動収集</div>

<div class="lead">
<p>{week_ago_str}から{today_str}までの7日間で、ポケモンカード未開封BOXの買取価格が<strong>動いた</strong>商品を、10店舗の実データから<strong>値上がり・値下がりの両面</strong>でランキング化しました。<strong>SV・MEGAシリーズ TOP10</strong>をメインとし、別枠でS&Sシリーズ TOP3を掲載。値上がりだけでなく値下がりも並べることで、<strong>今の相場が上向きか下向きか</strong>がひと目で分かります。</p>
</div>

<h2>今週の相場ハイライト (SV・MEGA)</h2>
<p>SV・MEGA全<strong>{len(all_changes)}BOX</strong>のうち、今週は<strong style="color:#dc2626">値上がり {len(gainers)}件</strong> / <strong style="color:var(--text-sub)">横ばい {len(flat)}件</strong> / <strong style="color:#2563eb">値下がり {len(losers)}件</strong>。上昇BOXの平均上昇額は<strong>+¥{avg_diff:,.0f}</strong>（平均+{avg_pct:.1f}%）でした。値上がり・値下がりの順に詳しく見ていきます。</p>

<h2>📈 SV・MEGA 値上がり TOP10 (過去7日間)</h2>
<p>各BOXの直近8日間の買取価格推移をミニグラフで可視化しました。数字だけでは見えない勢いや減速の兆候をグラフで確認してください。</p>
<div class="mini-charts">
{top_charts_html}
</div>
<details style="margin-top:16px">
<summary style="cursor:pointer;font-size:13px;color:var(--text-sub)">▶ 表形式でも表示</summary>
<table class="rank-table" style="margin-top:12px">
<thead>
<tr><th>順位</th><th>商品名</th><th>現在</th><th>先週</th><th>上昇</th></tr>
</thead>
<tbody>
{top_rows}
</tbody>
</table>
</details>

<h2>TOP5 詳細コメント</h2>
{top5_commentary}

<h2>SV・MEGA 値上がり 次点 (11〜15位相当)</h2>
<p>TOP10外で注目したい値上がりBOXです。今週後半に上位圏へ入る可能性があります。</p>
<table class="rank-table">
<thead>
<tr><th>順位</th><th>商品名</th><th>現在</th><th>先週</th><th>上昇</th></tr>
</thead>
<tbody>
{minor_rows}
</tbody>
</table>

<h2>📈 S&amp;S (ソード&シールド) 値上がり TOP3</h2>
<p>旧弾のS&amp;Sシリーズは、イーブイヒーローズやVMAXクライマックスなど絶版の高額BOXが中心です。ボリュームゾーンが違うため別枠で追跡しています。</p>
{'<div class="mini-charts">' + ss_charts_html + '</div>' if ss_charts_html else '<p class="no-data" style="padding:16px;color:var(--text-sub)">今週のS&amp;S上昇BOXはありませんでした</p>'}

<h2 class="section-down">📉 SV・MEGA 値下がり TOP10 (過去7日間)</h2>
<p>今週、買取価格が<strong>下落</strong>したSV・MEGA BOXです。下落幅の大きい順に並べています。相場全体が調整局面にあるときは、ここに有力BOXが並びます。</p>
{'<div class="mini-charts">' + loss_charts_html + '</div>' if loss_charts_html else '<p class="no-data" style="padding:16px;color:var(--text-sub)">今週は値下がりしたSV・MEGA BOXはありませんでした（相場は底堅め）</p>'}
{'<details style="margin-top:16px"><summary style="cursor:pointer;font-size:13px;color:var(--text-sub)">▶ 表形式でも表示</summary><table class="rank-table" style="margin-top:12px"><thead><tr><th>順位</th><th>商品名</th><th>現在</th><th>先週</th><th>変動</th></tr></thead><tbody>' + top_loser_rows + '</tbody></table></details>' if top_loser_rows else ''}

<h2 class="section-down">📉 S&amp;S (ソード&シールド) 値下がり TOP3</h2>
<p>旧弾S&amp;Sシリーズの値下がりBOXです。高額帯のため下落額が大きく出やすく、相場の重しになりやすい区分です。</p>
{'<div class="mini-charts">' + ss_loss_charts_html + '</div>' if ss_loss_charts_html else '<p class="no-data" style="padding:16px;color:var(--text-sub)">今週のS&amp;S値下がりBOXはありませんでした</p>'}

<h2>来週チェックすべきポイント</h2>
<ul style="font-size:14px;padding-left:22px;margin-bottom:14px">
<li>TOP3のBOXが翌週も維持できるか (ピーク後の調整か、継続上昇か)</li>
<li>新弾発売直前は既存弾の在庫が動きやすい</li>
<li>値上がり次点ランクインBOXがTOP10入りする週は狙い目</li>
</ul>

<div class="disclaimer">
<strong>ご注意:</strong> 本記事は10店舗の買取価格データを元にした参考情報です。投資助言を目的とするものではありません。価格変動は需給や再販情報等により急変する場合があります。売買判断はご自身の責任でお願いします。価格は{update_date}時点の取得値です。
</div>

<a href="../index.html" class="cta">全66商品の最新買取価格を比較する &rarr;</a>

<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>

<a href="../ranking.html" class="back">&larr; 週間ランキング(TOP10グラフ版)へ</a>
<a href="index.html" class="back" style="margin-left:16px">&larr; 週間値動き記事 一覧</a>
</article>
</div><!-- /content-layout -->
</div>
<div class="ft"><a href="../index.html">ポケカ買取チェッカー</a> / <a href="../privacy.html">プライバシーポリシー</a></div>
<script>
{top_charts_js}
{ss_charts_js}
{loss_charts_js}
{ss_loss_charts_js}
</script>
</body>
</html>"""
    return html


def build_weekly_index_html(week_entries: list[dict]) -> str:
    """Build /weekly/index.html archive listing all weekly articles.
    week_entries: list of {year, week, filename, title, published_date, top_gainer_name}
    """
    items_html = ""
    for e in week_entries:
        items_html += (
            f'<li class="week-item">'
            f'<a href="{e["filename"]}" class="week-link">'
            f'<div class="week-label">{e["title"]}</div>'
            f'<div class="week-date">{e["published_date"]} 公開</div>'
            f'<div class="week-top">値動きTOP: {e["top_gainer_name"]}</div>'
            f'</a></li>'
        )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<meta name="description" content="ポケカBOX 週間値動きランキング記事のアーカイブ一覧。毎週更新のBOX買取価格値動きレポート。">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/weekly/">
<meta property="og:title" content="週間値動き記事アーカイブ｜ポケカ買取チェッカー">
<meta property="og:description" content="毎週更新のポケカBOX 買取値動きランキング記事の一覧。">
<meta property="og:type" content="website">
<meta property="og:url" content="https://pokeca-box-hikaku.com/weekly/">
<meta property="og:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<meta property="og:site_name" content="ポケカ買取チェッカー">
<title>週間値動き記事アーカイブ｜ポケカ買取チェッカー</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RPTS6CRTCS"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-RPTS6CRTCS');
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "週間値動き記事アーカイブ",
  "description": "ポケカBOX 週間値動きランキング記事の一覧",
  "url": "https://pokeca-box-hikaku.com/weekly/"
}}
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
.main-card{{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:32px 28px}}
.main-card h2{{font-size:22px;font-weight:800;margin-bottom:8px}}
.main-card p.desc{{font-size:14px;color:var(--text-sub);margin-bottom:24px}}
.week-list{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}}
.week-item{{}}
.week-link{{display:block;background:#f9fafb;border:1px solid var(--border);border-radius:8px;padding:16px 20px;text-decoration:none;color:var(--text);transition:all .15s}}
.week-link:hover{{border-color:var(--accent);background:#f5f3ff;transform:translateY(-1px)}}
.week-label{{font-size:15px;font-weight:700;color:var(--text);margin-bottom:4px;line-height:1.4}}
.week-date{{font-size:11px;color:var(--text-sub);margin-bottom:6px}}
.week-top{{font-size:12px;color:var(--accent)}}
.back{{display:inline-block;margin-top:24px;color:var(--accent);text-decoration:none;font-size:14px;font-weight:600}}
.ft{{text-align:center;padding:24px 16px;font-size:11px;color:var(--text-sub)}}
.ft a{{color:var(--accent)}}
</style>
</head>
<body>
<div class="header"><a href="../index.html"><h1>ポケカ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="../index.html">トップ</a> &gt; 週間値動き記事</div>
<div class="content-layout">
<nav class="article-nav">
<div class="article-nav-title">一般記事</div>
<a href="../index.html">買取価格比較</a>
<a href="index.html" class="current">🔥 今週の値動き記事</a>
<a href="../ranking.html">上昇ランキング</a>
<a href="../souba-mynumber-2026.html">📰 相場下落・膠着とマイナンバー</a>
<a href="../kaitori-tips.html">BOX買取のコツ</a>
<a href="../shop-hikaku.html">10店舗比較</a>
<a href="../single-card-tips.html">シングル売り</a>
<a href="../psa-guide.html">PSA鑑定ガイド</a>
<a href="../mercari-hikaku.html">メルカリ・スニダン比較</a>
<a href="../shrink-nashi.html">シュリンクなしBOX</a>
<a href="../box-toushi.html">BOX投資の始め方</a>
<a href="../restock-guide.html">再販情報の見つけ方</a>
<a href="../release-schedule-2026.html">📅 2026年 新弾カレンダー</a>
<a href="../price-pattern-guide.html">📈 相場5段階パターン</a>
<div class="article-nav-sub">🔥 BOX深掘り特集</div>
<a href="../151-spotlight.html">【特集】ポケモンカード151高騰</a>
<a href="../inferno-x-spotlight.html">【特集】インフェルノX高騰</a>
<a href="../kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>
<a href="../chouden-breaker-spotlight.html">【特集】超電ブレイカー高騰</a>
<a href="../clay-burst-spotlight.html">【特集】クレイバースト高騰</a>
<a href="../ninja-spinner-spotlight.html">【特集】ニンジャスピナー高騰</a>
<a href="../rocket-dan-no-eiko-spotlight.html">【特集】ロケット団の栄光高騰</a>
<a href="../mega-ex-spotlight.html">【特集】MEGAドリームex高騰</a>
<a href="../mega-brave-spotlight.html">【特集】メガブレイブ高騰</a>
<div class="article-nav-sub" style="color:#6d28d9">📘 掘り下げガイド</div>
<a href="../zeppan-ranking-2026-03.html">📊 S&amp;S以降 絶版BOXランキング</a>
<a href="../lizardon-box-guide.html">🔥 リザードン高騰BOX完全ガイド</a>
<a href="../mega-pack-compare.html">⚡ MEGA拡張パック完全比較</a>
<a href="../kokuen-vs-rocket.html">⚔️ 黒炎 vs ロケット団の栄光</a>
<a href="../mega-lizardon-x-guide.html">メガリザードンXex MUR/SAR</a>
<a href="../lizardon-sar-kokuen-guide.html">リザードンex SAR(黒炎)</a>
<a href="../erika-sar-guide.html">エリカの招待 SAR</a>
<a href="../pigeot-sar-guide.html">ピジョットex SAR</a>
<a href="../masterball-mirror-guide.html">151マスターボールミラー</a>
<a href="../kokuen-atari-guide.html">黒炎 当たりカード完全ガイド</a>
</nav>
<div class="main-card">
<h2>週間値動き記事 アーカイブ</h2>
<p class="desc">10店舗の実データから自動抽出したポケカBOX値動きランキングを週次で記録。毎週更新・履歴は永続保存。</p>
<ul class="week-list">
{items_html}
</ul>
<a href="../index.html" class="back">&larr; トップに戻る</a>
</div>
</div><!-- /content-layout -->
</div>
<div class="ft"><a href="../index.html">ポケカ買取チェッカー</a> / <a href="../privacy.html">プライバシーポリシー</a></div>
</body>
</html>"""
