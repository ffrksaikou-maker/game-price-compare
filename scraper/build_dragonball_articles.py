"""ドラゴンボール買取チェッカーの記事ビルダー。

ワンピ版(build_onepiece_articles.py)と同じ構成だが、ワンピ/ポケカ側は
一切参照しない独立実装。記事を足すときは HOWTO_ARTICLES に dict を
append して `python -m scraper.build_dragonball_articles` を実行する。
"""
from __future__ import annotations

import html as _html
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "dragonball"
BASE = "https://pokeca-box-hikaku.com"
SITE_NAME = "ドラゴンボール買取チェッカー"

AFFILIATE = """<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>"""

STYLE = """<style>
:root{--bg:#f6f7fb;--card:#fff;--border:#e5e7eb;--text:#111827;--text-sub:#6b7280;--accent:#f57c00;--highlight:#ffe8cc}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:var(--bg);color:var(--text);line-height:1.8}
.gswitch{display:flex;align-items:center;justify-content:center;gap:8px;padding:11px 16px;font-size:14px;font-weight:800;text-decoration:none;color:#fff;background:linear-gradient(135deg,#ffa726,#f57c00);box-shadow:inset 0 -2px 0 rgba(0,0,0,.12)}
.gswitch .ar{font-size:18px;line-height:1}
.header{position:sticky;top:0;z-index:100;height:56px;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;padding:0 20px}
.header a{text-decoration:none}
.header h1{font-size:18px;font-weight:700;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.wrap{max-width:1240px;margin:0 auto;padding:32px 16px 48px}
.content-layout{display:flex;gap:24px;align-items:flex-start}
.content-layout article{flex:1;min-width:0}
.article-nav{width:200px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}
.article-nav-title{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}
.article-nav a{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4;transition:all .2s}
.article-nav a:hover{color:var(--accent);border-left-color:var(--accent)}
.article-nav a.current{color:var(--accent);border-left-color:var(--accent);font-weight:600}
.article-nav-sub{font-size:12px;font-weight:700;margin:14px 0 6px;color:#c2410c;padding-top:10px;border-top:1px solid var(--border)}
.article-nav-more{display:block;margin-top:12px;padding:8px 12px;font-size:12px;font-weight:700;text-align:center;color:var(--accent);background:#f9fafb;border:1px solid var(--border);border-radius:8px;text-decoration:none}
.article-nav-more:hover{border-color:var(--accent)}
@media(max-width:1023px){.content-layout{flex-direction:column;align-items:stretch}.article-nav{order:2;width:auto;position:static;max-height:none;overflow-y:visible;margin-top:24px;padding-top:16px;border-top:1px solid var(--border)}.article-nav a{font-size:13px;padding:8px 0 8px 12px}}
.breadcrumb{font-size:12px;color:var(--text-sub);margin-bottom:20px}
.breadcrumb a{color:var(--accent);text-decoration:none}
article{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:32px 28px;margin-bottom:24px}
article h1{font-size:24px;font-weight:800;margin-bottom:8px;line-height:1.4;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.meta{font-size:12px;color:var(--text-sub);margin-bottom:24px}
article h2{font-size:18px;font-weight:700;margin:32px 0 14px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
article h3{font-size:15px;font-weight:700;margin:16px 0 8px;color:var(--accent)}
article p{font-size:14px;margin-bottom:14px}
article ul,article ol{font-size:14px;padding-left:22px;margin-bottom:14px}
article li{margin-bottom:8px}
.hero{margin-bottom:24px;padding:22px;background:linear-gradient(135deg,#fff7ed,#ffedd5);border-radius:12px;border:1px solid #fed7aa}
.hero .stat-label{font-size:11px;color:#c2410c;font-weight:700;letter-spacing:.5px}
.hero .stat-big{font-size:30px;font-weight:800;color:#c2410c;line-height:1.2;margin:4px 0 12px}
.hero .stat-sub{font-size:12px;color:#9a3412;line-height:1.7}
.tbl{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}
.tbl th,.tbl td{padding:10px 12px;border-bottom:1px solid var(--border);text-align:left}
.tbl th{background:#f9fafb;font-size:11px;color:var(--text-sub);letter-spacing:.5px}
.tbl td.num{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.callout{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 18px;margin:14px 0;font-size:13px}
.callout strong{color:#1d4ed8}
.disclaimer{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:14px 18px;margin:24px 0;font-size:12px;color:#9a3412}
.disclaimer strong{color:#c2410c}
.back{display:inline-block;margin-top:16px;color:var(--accent);text-decoration:none;font-size:14px;font-weight:600;margin-right:16px}
.ad{text-align:center;padding:12px 0}
.ft{text-align:center;padding:24px 16px;font-size:11px;color:var(--text-sub)}
.ft a{color:var(--accent)}
@media(max-width:640px){article{padding:22px 18px}article h1{font-size:20px}.hero .stat-big{font-size:24px}}
</style>"""


def _esc(s) -> str:
    return _html.escape(str(s), quote=True)


HOWTO_ARTICLES = [
    {
        "slug": "hatsubai-schedule",
        "nav_label": "新弾発売スケジュール",
        "crumb": "新弾発売スケジュール",
        "date": "2026-08-27",
        "title": "ドラゴンボールカード 新弾発売スケジュール｜FB-11・FB-12の発売日と定価改定",
        "h1": "ドラゴンボールカード 新弾発売スケジュール｜FB-11・FB-12の発売日とBOX定価",
        "meta_desc": "ドラゴンボールスーパーカードゲーム フュージョンワールドの新弾発売スケジュール。FB-11「BRIGHTNESS OF HOPE」(2026年9月12日)とFB-12「REACH THE GOD」(2026年12月12日・BOX5,760円)の発売日、FB-12から実施される1パック240円への定価改定、発売前後の買取相場の動きを実データ視点で解説します。",
        "og_title": "ドラゴンボールカード 新弾発売スケジュール｜FB-11・FB-12",
        "og_desc": "FB-11は2026年9月12日、FB-12「REACH THE GOD」は12月12日発売でBOX定価5,760円。1パック240円への改定と相場への影響を整理。",
        "meta_line": "フュージョンワールド新弾の発売日・BOX定価・相場への影響",
        "hero_label": "新弾発売スケジュール",
        "hero_big": "次はFB-11(9/12)とFB-12(12/12)",
        "hero_sub": "ドラゴンボールスーパーカードゲーム フュージョンワールドの発売予定を整理。FB-12からは1パック240円へ改定され、BOX定価も5,280円→5,760円に変わります。発売日・定価・相場の動きをまとめて確認できます。",
        "body": """<p>ドラゴンボールスーパーカードゲーム フュージョンワールドは定期的に新弾が発売され、<strong>発売の前後で未開封BOXの買取相場が動きます</strong>。「次の弾はいつか」「手元のBOXを新弾前に売るべきか」を判断するには、発売スケジュールの把握が出発点になります。本記事では<strong>これから発売される弾の日程・BOX定価</strong>と、<strong>FB-12から実施される定価改定</strong>を整理します。各弾の実際の買取価格は <a href="/dragonball">ドラゴンボールBOX買取価格比較トップ</a> で毎日更新しています。</p>

<h2>これから発売される弾</h2>
<p>2026年8月27日時点で判明している発売予定です。</p>
<table class="tbl">
<thead><tr><th>発売日</th><th>商品名</th><th>弾番号</th><th>BOX定価(税込)</th></tr></thead>
<tbody>
<tr><td>2026年9月12日</td><td>ブースターパック<br>BRIGHTNESS OF HOPE</td><td>FB-11</td><td class="num">5,280円</td></tr>
<tr><td>2026年12月12日</td><td>ブースターパック<br>REACH THE GOD</td><td>FB-12</td><td class="num">5,760円</td></tr>
</tbody>
</table>

<h3>FB-11「BRIGHTNESS OF HOPE」(2026年9月12日)</h3>
<p>ブースターパック第11弾です。1パック220円×24パックで、<strong>BOX定価は5,280円</strong>。<a href="box/fb-10.html">FB-10「CROSS FORCE」</a>(2026年6月13日)に続く弾で、<strong>従来価格で発売される最後のブースター</strong>にあたります。</p>

<h3>FB-12「REACH THE GOD」(2026年12月12日)</h3>
<p>ブースターパック第12弾。<strong>ビルスをはじめとする「神」の領域のキャラクター</strong>が中心のラインナップとされています。この弾から価格が改定されます。</p>
<ul>
<li><strong>発売日</strong>: 2026年12月12日(土)</li>
<li><strong>1パック</strong>: 240円(税込)・カード6枚入り</li>
<li><strong>1BOX</strong>: 24パック入り・<strong>5,760円(税込)</strong></li>
</ul>

<h2>FB-12から定価が上がります</h2>
<p>スケジュール上で最も重要な変化が<strong>パック単価の改定</strong>です。FB-11までは1パック220円でしたが、<strong>FB-12から240円</strong>になります。BOXの構成は24パック入りのまま変わらないため、BOX定価は5,280円から5,760円へ、<strong>1BOXあたり480円の値上げ</strong>となります。</p>
<table class="tbl">
<thead><tr><th>区分</th><th>1パック</th><th>BOX構成</th><th>BOX定価</th></tr></thead>
<tbody>
<tr><td>FB-11以前</td><td>220円</td><td>24パック</td><td class="num">5,280円</td></tr>
<tr><td><strong>FB-12以降</strong></td><td><strong>240円</strong></td><td>24パック</td><td class="num"><strong>5,760円</strong></td></tr>
</tbody>
</table>
<div class="callout"><strong>比較のポイント</strong>：買取価格を「定価の何倍か」で評価する場合、旧弾と新弾では基準となる定価が異なります。同じ買取10,000円でも、5,280円の弾なら約1.89倍、5,760円の弾なら約1.74倍と実質的な評価が変わります。当サイトの比較表は弾ごとに定価を保持しているため、定価改定をまたいでも正しい倍率で比較できます。</div>

<h2>フュージョンワールドの発売ペース</h2>
<p>ブースターパックはおおむね<strong>3か月に1弾</strong>のペースで発売されています。直近の実績は次の通りです。</p>
<table class="tbl">
<thead><tr><th>発売日</th><th>弾</th><th>タイトル</th></tr></thead>
<tbody>
<tr><td>2025年12月13日</td><td>FB-08</td><td><a href="box/fb-08.html">誇り高き戦闘民族</a></td></tr>
<tr><td>2026年3月14日</td><td>FB-09</td><td><a href="box/fb-09.html">DUAL EVOLUTION</a></td></tr>
<tr><td>2026年6月13日</td><td>FB-10</td><td><a href="box/fb-10.html">CROSS FORCE</a></td></tr>
<tr><td>2026年9月12日</td><td>FB-11</td><td>BRIGHTNESS OF HOPE</td></tr>
<tr><td>2026年12月12日</td><td>FB-12</td><td>REACH THE GOD</td></tr>
</tbody>
</table>
<p>ブースター以外にも、MANGA BOOSTER(SB)・STORY BOOSTER(ST)・スーパーダイバーズのアドバンスパックなど別ラインの商品があり、これらはブースターとは異なるタイミングで発売されます。2026年8月8日には<strong>STORY BOOSTER 01(ST-01)</strong>と<strong>スーパーダイバーズ アドバンスパック バトルオブサイヤン</strong>が同日発売されました。各商品の買取価格は <a href="/dragonball">比較トップ</a> でシリーズ別に絞り込んで確認できます。</p>

<h2>新弾の発売は買取相場にどう影響するか</h2>
<h3>発売直後は動きやすい</h3>
<p>発売直後は流通量が限られ注目度も高いため、<strong>需要が供給を上回ると買取価格が上がりやすい</strong>時期です。逆に初動の評価が伸びない場合は早い段階で落ち着くこともあります。</p>
<h3>供給が安定すると水準が定まる</h3>
<p>再販や追加出荷で在庫が行き渡ると、相場は一定の水準に落ち着き、店舗間の価格差も縮まりやすくなります。</p>
<h3>旧弾は環境の変化で動く</h3>
<p>新弾で強力なカードが登場したり、既存カードが再録されたりすると、旧弾の需要が変わることがあります。値動きは日々変わるため、売却前に最新の比較データを確認するのが確実です。</p>

<h2>スケジュールを踏まえた売買の考え方</h2>
<ul>
<li><strong>売却を考えているBOXがある</strong>: 新弾発売の前後は相場が動きやすい時期です。急がないなら値動きを見てから判断するのが有利になり得ます。</li>
<li><strong>新弾を買う予定がある</strong>: FB-12以降はBOX定価が5,760円に上がるため、購入コストの前提が変わります。</li>
<li><strong>複数店を比較する</strong>: どのタイミングでも店舗ごとの価格差は残ります。売る直前に <a href="/dragonball">店舗別の比較</a> で最新値を確認してください。</li>
</ul>
<p>本記事の発売日・価格はメーカー発表および各販売店の告知に基づく2026年8月27日時点の情報です。<strong>発売日や仕様は変更される場合がある</strong>ため、購入・売却の判断前には最新の公式情報をあわせてご確認ください。</p>""",
        "faq": [
            {"q": "FB-12「REACH THE GOD」の発売日はいつですか?",
             "a": "2026年12月12日(土)発売予定です。1パック240円(税込・カード6枚入り)、1BOX24パック入りでBOX定価は5,760円(税込)となっています。ビルスをはじめとする「神」の領域のキャラクターが中心のラインナップとされています。"},
            {"q": "BOXの定価が5,280円から5,760円に変わるのはなぜですか?",
             "a": "FB-12から1パックの価格が220円から240円に改定されるためです。BOXの構成は24パック入りのまま変わらないため、24パック×240円で定価が5,760円になります。FB-11「BRIGHTNESS OF HOPE」までは従来通り220円×24パックの5,280円です。"},
            {"q": "フュージョンワールドの新弾はどのくらいの頻度で出ますか?",
             "a": "ブースターパックはおおむね3か月に1弾のペースです。直近ではFB-09が2026年3月14日、FB-10が6月13日、FB-11が9月12日、FB-12が12月12日と、3か月間隔で発売されています。これとは別にMANGA BOOSTER・STORY BOOSTER・スーパーダイバーズなどのラインもあります。"},
            {"q": "新弾が出ると既存BOXの買取価格は下がりますか?",
             "a": "必ず下がるとは限りません。新弾の内容や再録カード、環境の変化によって既存弾の需要が動くため、上がる弾もあれば下がる弾もあります。当サイトでは各弾の買取価格を毎日自動更新しているので、売却前に最新値を確認してください。"},
            {"q": "発売前のBOXも買取価格を比較できますか?",
             "a": "発売前は買取受付をしていない店舗がほとんどのため、価格は表示されません。各店が買取を開始し価格が付いた時点で、当サイトの比較表に自動的に反映されます。"},
        ],
    },
]

# 弾別の当たりカードガイド。買取価格の高い弾から順に用意する。
# 本文の {BOX_PRICE} / {BOX_RATIO} / {BOX_RETAIL} はビルド時に当サイトの
# 実データ(data/history_db)で置換される。
ATARI_ARTICLES = [
    {
        "slug": "sb-01-atari-guide",
        "box_slug": "sb-01",
        "box_name": "MANGA BOOSTER 01【SB-01】",
        "retail": 7920,
        "nav_label": "MANGA BOOSTER 01(SB-01)",
        "crumb": "MANGA BOOSTER 01(SB-01) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "MANGA BOOSTER 01(SB-01) 当たりカードランキング｜エナジーマーカー1巻表紙の買取相場と封入率",
        "h1": "MANGA BOOSTER 01(SB-01) 当たりカードランキング｜エナジーマーカー★(1巻表紙)の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「MANGA BOOSTER 01」(SB-01)の当たりカードランキング・買取相場・封入率を解説。1位はエナジーマーカー★(1巻表紙)で約180万円、2位は孫悟空SCR★★が約60〜65万円。スーパーパラレルは240BOXに1枚、エナジーマーカーパラレルは12BOXに約1枚。BOX買取価格は当サイトの実データで毎日更新しています。",
        "og_title": "MANGA BOOSTER 01(SB-01) 当たりカードランキング｜エナジーマーカー1巻表紙",
        "og_desc": "SB-01の当たりカード・買取相場・封入率を解説。1位はエナジーマーカー★(1巻表紙)約180万円。BOX買取は定価の約20倍と全弾トップ水準。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド MANGA BOOSTER 01(SB-01・2025年6月28日発売)",
        "hero_label": "SB-01 トップレア",
        "hero_big": "エナジーマーカー★ 約180万円",
        "hero_sub": "1巻表紙のエナジーマーカーが突出。2位は孫悟空SCR★★で約60〜65万円。BOX買取も{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})と、当サイト掲載のドラゴンボールBOXで最も高い水準です。",
        "body": """<p>2025年6月28日発売の <strong><a href="box/sb-01.html">MANGA BOOSTER 01【SB-01】</a></strong> は、原作コミックスの表紙を「エナジーマーカー」として収録した特殊な弾です。当サイトが4店舗から毎日収集している実データでも、<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>と、掲載中のドラゴンボールBOXで最も高い水準にあります。この記事では、その相場を支えている当たりカードを買取価格順に整理します。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th></tr></thead>
<tbody>
<tr><td>1位</td><td>エナジーマーカー★(1巻表紙)<br>E-42</td><td>★</td><td class="num">約180万円</td></tr>
<tr><td>2位</td><td>孫悟空<br>FB05-119</td><td>SCR★★</td><td class="num">約60〜65万円</td></tr>
<tr><td>3位</td><td>エナジーマーカー★(30巻表紙)<br>E-60</td><td>★</td><td class="num">約60万円</td></tr>
<tr><td>4位</td><td>エナジーマーカー★(3巻表紙)<br>E-44</td><td>★</td><td class="num">約50万円</td></tr>
<tr><td>5位</td><td>エナジーマーカー★(2巻表紙)<br>E-43</td><td>★</td><td class="num">約40万円</td></tr>
</tbody>
</table>
<p>上位5枚のうち<strong>4枚をエナジーマーカーが占めています</strong>。通常のブースターがキャラクターのパラレルカードを頂点に据えるのに対し、この弾は原作コミックスの表紙イラストがトップレアになっている点が最大の特徴です。</p>

<h2>なぜ「1巻表紙」だけ突出しているのか</h2>
<p>1位のエナジーマーカー★(1巻表紙)は約180万円で、2位以下の3倍前後という差がついています。同じエナジーマーカーでも30巻表紙が約60万円、3巻表紙が約50万円、2巻表紙が約40万円ですから、<strong>レアリティや封入率が同じでも「1巻」という記号性が価格を決めている</strong>構図です。</p>
<p>ドラゴンボールの単行本1巻の表紙は、作品を象徴するビジュアルとして広く知られています。カードゲームのプレイ用途というより<strong>コレクション需要が価格を形成している</strong>タイプのカードで、この点は同じ弾の孫悟空SCR★★(約60〜65万円)とは需要の性質が異なります。</p>

<h2>封入率</h2>
<table class="tbl">
<thead><tr><th>レアリティ</th><th>封入率</th></tr></thead>
<tbody>
<tr><td>スーパーパラレル(SCR★★)</td><td>240BOXに1枚</td></tr>
<tr><td>エナジーマーカーパラレル</td><td>12BOXに約1枚</td></tr>
<tr><td>Lパラレル</td><td>12BOXに約1枚</td></tr>
<tr><td>SCRパラレル</td><td>12BOXに約1枚</td></tr>
</tbody>
</table>
<div class="callout"><strong>注意</strong>：エナジーマーカーパラレルの「12BOXに約1枚」は<strong>エナジーマーカー枠全体</strong>の確率です。この枠には複数の巻の表紙が存在するため、<strong>狙いの1枚(1巻表紙)を引く確率はこれよりさらに低くなります</strong>。「12BOXでトップレアが当たる」という意味ではない点に注意してください。</div>
<p>2位の孫悟空SCR★★に至っては<strong>240BOXに1枚</strong>です。BOX定価{BOX_RETAIL}で計算すると240BOXで約190万円分となり、狙って引きに行く対象ではないことがわかります。</p>

<h2>BOX買取が定価の20倍を超える理由</h2>
<p>当サイトの実データでは、SB-01のBOX買取は<strong>{BOX_PRICE}</strong>、定価{BOX_RETAIL}に対して<strong>{BOX_RATIO}</strong>です。当サイトが扱うドラゴンボールBOXの中で突出しており、通常のブースターパック(FBシリーズ)が定価の1〜3倍台で推移しているのとは水準が違います。</p>
<p>背景には、上位カードの相場が数十万円〜百万円台という点があります。1BOXから高額カードが出る可能性がある以上、未開封BOX自体に「抽選券」としての価値が付き、買取価格が押し上げられる構造です。実際の最新価格と店舗ごとの差は <a href="box/sb-01.html">SB-01の個別ページ</a> で毎日更新しています。</p>

<h2>開封するか、未開封のまま売るか</h2>
<p>封入率から考えると、<strong>特定の高額カードを狙った開封は現実的ではありません</strong>。エナジーマーカー枠は12BOXに約1枚で、そのうち1巻表紙に当たる確率はさらに低く、スーパーパラレルは240BOXに1枚です。一方でBOX買取は{BOX_PRICE}と既に高い水準にあります。</p>
<p>売却を考えている場合は、まず <a href="box/sb-01.html">店舗別の買取価格</a> を比較してください。同じBOXでも店舗によって価格差が出ます。シュリンク付きの未開封状態が最も評価されるため、売る可能性があるなら開けないことが前提になります。詳しくは <a href="hatsubai-schedule.html">新弾発売スケジュール</a> で相場が動きやすいタイミングも確認できます。</p>""",
        "faq": [
            {"q": "MANGA BOOSTER 01(SB-01)の一番の当たりカードは何ですか?",
             "a": "エナジーマーカー★(1巻表紙・E-42)で、買取相場は約180万円です。2位の孫悟空SCR★★(約60〜65万円)、3位のエナジーマーカー★(30巻表紙・約60万円)と比べても3倍前後の差があり、単独で突出しています。"},
            {"q": "エナジーマーカーの封入率はどのくらいですか?",
             "a": "エナジーマーカーパラレルは12BOXに約1枚とされています。ただしこれはエナジーマーカー枠全体の確率で、この枠には複数の巻の表紙が存在するため、狙いの1枚(1巻表紙など)を引く確率はさらに低くなります。"},
            {"q": "SB-01のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。掲載中のドラゴンボールBOXで最も高い水準ですが、相場は日々変動するため個別ページで最新値をご確認ください。"},
            {"q": "SB-01は開封した方が得ですか?",
             "a": "封入率から見ると、特定の高額カードを狙った開封は現実的ではありません。エナジーマーカー枠は12BOXに約1枚、スーパーパラレルは240BOXに1枚です。一方でBOX買取自体が定価の20倍前後と高い水準にあるため、未開封のまま売却する選択肢も十分に成立します。"},
            {"q": "なぜ1巻表紙だけ価格が高いのですか?",
             "a": "レアリティや封入率が同じでも、単行本1巻の表紙という記号性がコレクション需要を集めているためです。30巻表紙が約60万円、3巻表紙が約50万円であるのに対し、1巻表紙だけが約180万円と別格の評価になっています。"},
        ],
    },
    {
        "slug": "sb-02-atari-guide",
        "box_slug": "sb-02",
        "box_name": "MANGA BOOSTER 02【SB-02】",
        "retail": 7920,
        "nav_label": "MANGA BOOSTER 02(SB-02)",
        "crumb": "MANGA BOOSTER 02(SB-02) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "MANGA BOOSTER 02(SB-02) 当たりカードランキング｜エナジーマーカー42巻表紙の買取相場と封入率",
        "h1": "MANGA BOOSTER 02(SB-02) 当たりカードランキング｜エナジーマーカー★(42巻表紙)の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「MANGA BOOSTER 02」(SB-02)の当たりカードランキング・買取相場・封入率を解説。1位はエナジーマーカー★(42巻表紙)で約100万円、2位は孫悟飯:少年期SCR★★が約50万円。スーパーパラレルは240BOXに約1枚、エナジーマーカーパラレルは12BOXに約1枚。BOX買取価格は当サイトの実データで毎日更新しています。",
        "og_title": "MANGA BOOSTER 02(SB-02) 当たりカードランキング｜エナジーマーカー42巻表紙",
        "og_desc": "SB-02の当たりカード・買取相場・封入率を解説。1位はエナジーマーカー★(42巻表紙)約100万円。最終巻の表紙が最高額という構図をSB-01と比較。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド MANGA BOOSTER 02(SB-02・2025年11月8日発売)",
        "hero_label": "SB-02 トップレア",
        "hero_big": "エナジーマーカー★ 約100万円",
        "hero_sub": "42巻(最終巻)表紙のエナジーマーカーが最高額。2位は孫悟飯:少年期SCR★★で約50万円。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2025年11月8日発売の <strong><a href="box/sb-02.html">MANGA BOOSTER 02【SB-02】</a></strong> は、原作コミックスの表紙を「エナジーマーカー」として収録するシリーズの第2弾です。当サイトが4店舗から毎日収集している実データでは、<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>となっています。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th><th>封入率</th></tr></thead>
<tbody>
<tr><td>1位</td><td>エナジーマーカー★(42巻表紙)<br>E-90</td><td>エナジーマーカーパラレル</td><td class="num">約100万円</td><td>12BOXに約1枚</td></tr>
<tr><td>2位</td><td>孫悟飯:少年期<br>FB01-140</td><td>SCR★★<br>(スーパーパラレル)</td><td class="num">約50万円</td><td>240BOXに約1枚</td></tr>
<tr><td>3位</td><td>エナジーマーカー★(10巻表紙)<br>E-73</td><td>エナジーマーカーパラレル</td><td class="num">約40万円</td><td>12BOXに約1枚</td></tr>
<tr><td>4位</td><td>エナジーマーカー★(35巻表紙)<br>E-83</td><td>エナジーマーカーパラレル</td><td class="num">約25万円</td><td>12BOXに約1枚</td></tr>
<tr><td>5位</td><td>ピッコロ<br>SB02-043</td><td>SR★★<br>(ウルトラパラレル)</td><td class="num">約20万円</td><td>記載なし</td></tr>
</tbody>
</table>

<h2>SB-01との違い｜「最終巻」が頂点</h2>
<p>SB-02でも上位5枚のうち3枚をエナジーマーカーが占めており、構造は <a href="sb-01-atari-guide.html">SB-01</a> と共通です。ただし頂点に立つ表紙が違います。</p>
<table class="tbl">
<thead><tr><th>弾</th><th>1位のカード</th><th>買取相場</th><th>2位との差</th></tr></thead>
<tbody>
<tr><td>SB-01</td><td>エナジーマーカー★(<strong>1巻</strong>表紙)</td><td class="num">約180万円</td><td>約2.8倍</td></tr>
<tr><td>SB-02</td><td>エナジーマーカー★(<strong>42巻</strong>表紙)</td><td class="num">約100万円</td><td>約2.0倍</td></tr>
</tbody>
</table>
<p>SB-01は<strong>連載の始まりである1巻</strong>、SB-02は<strong>完結巻である42巻</strong>が最高額です。どちらも「シリーズの節目」を象徴する巻が選ばれており、<strong>中間の巻より始点と終点が評価される</strong>傾向が読み取れます。実際、SB-02では10巻表紙が約40万円、35巻表紙が約25万円と、42巻表紙との差が明確です。</p>
<p>金額そのものはSB-01の1巻表紙(約180万円)が上で、2位との開きもSB-01の方が大きくなっています。</p>

<h2>封入率とBOX相場の関係</h2>
<p>エナジーマーカーパラレルは<strong>12BOX(1カートン)に約1枚</strong>、スーパーパラレル(SCR★★)は<strong>240BOXに約1枚</strong>です。エナジーマーカー枠には複数の巻の表紙が含まれるため、<strong>42巻表紙を狙って引く確率は12分の1よりさらに低くなります</strong>。</p>
<div class="callout"><strong>240BOXの意味</strong>：2位の孫悟飯:少年期SCR★★は240BOXに約1枚です。BOX定価{BOX_RETAIL}で240BOX分を買うと約190万円になり、狙って引きに行く対象ではありません。</div>
<p>当サイトの実データでのBOX買取は{BOX_PRICE}({BOX_RATIO})です。<a href="sb-01-atari-guide.html">SB-01</a>が定価の20倍前後で推移しているのに対し、SB-02はそれより低い水準にあります。トップレアの金額差(180万円 vs 100万円)がBOX相場にも反映されている形です。店舗ごとの最新価格は <a href="box/sb-02.html">SB-02の個別ページ</a> で確認できます。</p>

<h2>売却を考えている場合</h2>
<p>封入率から見て、特定の高額カードを狙った開封は現実的ではありません。一方でBOX買取は{BOX_PRICE}と定価を大きく上回っています。シュリンク付きの未開封状態が最も高く評価されるため、売る可能性があるなら開けないことが前提です。<a href="box/sb-02.html">店舗別の買取価格</a>を比較してから判断してください。</p>""",
        "faq": [
            {"q": "MANGA BOOSTER 02(SB-02)の一番の当たりカードは何ですか?",
             "a": "エナジーマーカー★(42巻表紙・E-90)で、買取相場は約100万円です。2位は孫悟飯:少年期SCR★★(FB01-140)の約50万円で、1位とは約2倍の差があります。"},
            {"q": "なぜ42巻表紙が最高額なのですか?",
             "a": "42巻は原作ドラゴンボールの完結巻にあたります。SB-01では連載の始まりである1巻表紙が最高額(約180万円)であり、SB-02では終点である42巻が頂点です。シリーズの節目を象徴する巻がコレクション需要を集める傾向が見られます。"},
            {"q": "SB-01とSB-02はどちらが高いですか?",
             "a": "トップレアはSB-01の1巻表紙が約180万円、SB-02の42巻表紙が約100万円でSB-01が上です。BOX買取も当サイトの実データではSB-01の方が高い水準にあります。SB-02のBOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。"},
            {"q": "エナジーマーカーの封入率はどのくらいですか?",
             "a": "エナジーマーカーパラレルは12BOX(1カートン)に約1枚とされています。ただしこれは枠全体の確率で、複数の巻の表紙が含まれるため、狙いの1枚を引く確率はさらに低くなります。"},
            {"q": "SB-02のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値と店舗ごとの差をご確認ください。"},
        ],
    },
    {
        "slug": "fb-07-atari-guide",
        "box_slug": "fb-07",
        "box_name": 'ブースターパック「神龍への願い」【FB-07】',
        "retail": 5280,
        "nav_label": "神龍への願い(FB-07)",
        "crumb": "神龍への願い(FB-07) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "神龍への願い(FB-07) 当たりカードランキング｜孫悟飯:SH スーパーパラレルの買取相場と封入率",
        "h1": "神龍への願い(FB-07) 当たりカードランキング｜孫悟飯:SH SCR★★の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「神龍への願い」(FB-07)の当たりカードランキング・買取相場・封入率を解説。1位は孫悟飯:SH SCR★★(スーパーパラレル)で約4〜4.8万円、240BOXに1枚。通常ブースターで最も高いBOX買取水準の弾で、カード相場とBOX相場の関係も実データで整理しています。",
        "og_title": "神龍への願い(FB-07) 当たりカードランキング｜孫悟飯:SH SCR★★",
        "og_desc": "FB-07の当たりカード・買取相場・封入率を解説。1位は孫悟飯:SH SCR★★で約4〜4.8万円。通常ブースターで最高水準のBOX買取との関係も整理。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「神龍への願い」(FB-07・2025年9月13日発売)",
        "hero_label": "FB-07 トップレア",
        "hero_big": "孫悟飯:SH SCR★★ 約4〜4.8万円",
        "hero_sub": "240BOXに1枚のスーパーパラレル。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})で、通常ブースター(FBシリーズ)では最も高い水準です。",
        "body": """<p>2025年9月13日発売の <strong><a href="box/fb-07.html">ブースターパック「神龍への願い」【FB-07】</a></strong> は、通常ブースター(FBシリーズ)の中で当サイト掲載BOXの買取価格が最も高い弾です。実データでは<strong>{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>で、同じFBシリーズの直近弾が定価の1〜3倍台で推移しているのと比べても突出しています。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th><th>封入率</th></tr></thead>
<tbody>
<tr><td>1位</td><td>孫悟飯:SH</td><td>SCR★★<br>(スーパーパラレル)</td><td class="num">約4〜4.8万円</td><td>240BOXに1枚</td></tr>
<tr><td>2位</td><td>孫悟飯:SH</td><td>SCRパラレル</td><td class="num">約6,000〜6,500円</td><td>12BOXに約1枚</td></tr>
<tr><td>3位</td><td>孫悟空:GT</td><td>SCRパラレル</td><td class="num">約5,000〜5,500円</td><td>12BOXに約1枚</td></tr>
<tr><td>4位</td><td>神龍</td><td>Lパラレル</td><td class="num">約4,200〜4,800円</td><td>12BOXに約1枚</td></tr>
<tr><td>5位</td><td>孫悟飯:SH</td><td>SCR</td><td class="num">約4,200〜5,000円</td><td>3BOXに約1枚</td></tr>
</tbody>
</table>
<p>買取価格は参照する店舗・時期によって幅があるため、上表はレンジで示しています。<strong>1位と2位の差が約7倍</strong>と大きく、実質的に孫悟飯:SH SCR★★の一枚勝ちという構成です。</p>

<h2>この弾の特徴｜カード相場とBOX相場が近い</h2>
<p>FB-07で目を引くのは、<strong>トップレアの買取(約4〜4.8万円)とBOX買取({BOX_PRICE})がほぼ同じ水準にある</strong>点です。他の弾では、トップレアが数十万円でBOXが数万円という開きがあるのが一般的です。</p>
<div class="callout"><strong>期待値では説明しにくい水準</strong>：孫悟飯:SH SCR★★は240BOXに1枚です。仮に4.8万円としても1BOXあたりの期待値は約200円で、2位以下(数千円・12BOXに約1枚)を足してもBOX買取{BOX_PRICE}には届きません。<strong>カードの期待値だけでこのBOX価格を説明することはできません</strong>。</div>
<p>この差が何によるものかを当サイトのデータだけで断定することはできませんが、発売から時間が経った弾で在庫が絞られていること、「神龍」という題材のコレクション需要などが考えられます。いずれにせよ、<strong>開封して当てるより未開封BOXそのものが評価されている状態</strong>である点は実データから読み取れます。</p>

<h2>買取価格には店舗差があります</h2>
<p>当サイトが取得している4店舗の中でも、FB-07は店舗による価格差が大きい弾です。最高値と他店の間に開きがあるため、<strong>1店舗だけを見て判断すると数千円〜1万円以上損をする可能性があります</strong>。<a href="box/fb-07.html">FB-07の個別ページ</a>で店舗別の価格と価格推移グラフを確認してから売却先を決めてください。</p>

<h2>開封するか、未開封のまま売るか</h2>
<p>封入率から見ると、<strong>240BOXに1枚のトップレアを狙った開封は現実的ではありません</strong>。2位以下は12BOXに約1枚で数千円台のため、開封してこれらが出ても、BOX買取{BOX_PRICE}を上回るのは難しい計算になります。</p>
<p>売却を考えている場合、シュリンク付きの未開封状態が最も高く評価されます。今後の新弾で相場が動く可能性もあるため、<a href="hatsubai-schedule.html">新弾発売スケジュール</a>もあわせて確認しておくと判断しやすくなります。</p>""",
        "faq": [
            {"q": "FB-07「神龍への願い」の一番の当たりカードは何ですか?",
             "a": "孫悟飯:SH の SCR★★(スーパーパラレル)で、買取相場は約4〜4.8万円です(参照する店舗・時期により幅があります)。封入率は240BOXに1枚とされ、2位の孫悟飯:SH SCRパラレル(約6,000〜6,500円)とは約7倍の差があります。"},
            {"q": "なぜFB-07のBOX買取は他のFB弾より高いのですか?",
             "a": "当サイトのデータだけで理由を断定することはできません。ただし、トップレアが240BOXに1枚である点を踏まえると、カードの期待値だけでこのBOX価格を説明することはできません。発売から時間が経ち在庫が絞られていることや、題材のコレクション需要などが影響していると考えられます。"},
            {"q": "FB-07は開封した方が得ですか?",
             "a": "封入率から見ると現実的ではありません。トップレアは240BOXに1枚、2位以下は12BOXに約1枚で数千円台です。開封してこれらが出ても、BOX買取{BOX_PRICE}を上回るのは難しい計算になります。"},
            {"q": "FB-07のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。この弾は店舗による価格差が大きいため、個別ページで店舗別の価格を必ず比較してください。"},
            {"q": "通常のブースターパックで一番高い弾はどれですか?",
             "a": "当サイトが掲載しているFBシリーズの中では、FB-07「神龍への願い」が最も高い買取水準です。MANGA BOOSTER(SBシリーズ)まで含めると、SB-01が定価の20倍前後でさらに上位になります。"},
        ],
    },
]


def _nav_links(current_slug: str) -> str:
    def _items(arts):
        out = []
        for h in arts:
            cls = ' class="current"' if h["slug"] == current_slug else ""
            out.append(f'<a href="{h["slug"]}.html"{cls}>{_esc(h["nav_label"])}</a>')
        return "\n".join(out)

    blocks = ['<div class="article-nav-title">📰 買取ガイド</div>', _items(HOWTO_ARTICLES)]
    if ATARI_ARTICLES:
        blocks.append('<div class="article-nav-sub">★ 弾別 当たりカード</div>')
        blocks.append(_items(ATARI_ARTICLES))
    blocks.append('<a class="article-nav-more" href="/dragonball">BOX買取価格を比較する</a>')
    return "\n".join(blocks)


def _box_max_prices() -> dict[str, int]:
    """商品名 -> 直近の最高買取額。data/history_db の最新JSONから読む。

    記事に載せるBOX相場は当サイトの実データを使う(外部の相場記事を引き写さない)。
    """
    hist = PROJECT_ROOT / "data" / "history_db"
    if not hist.exists():
        return {}
    files = sorted(hist.glob("*.json"))
    for f in reversed(files):
        try:
            rows = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        prices = {x["name"]: x.get("max_price", 0) for x in rows if x.get("max_price", 0) > 0}
        if prices:
            return prices
    return {}


def _subst_box(text: str, box_price: int, retail: int) -> str:
    """記事本文の相場プレースホルダを当サイト実データで埋める。"""
    if box_price > 0:
        price_txt = f"最高約{box_price:,}円"
        ratio_txt = f"約{box_price / retail:.1f}倍" if retail else "—"
    else:
        price_txt = "各店の最新価格"
        ratio_txt = "—"
    return (text.replace("{BOX_PRICE}", price_txt)
                .replace("{BOX_RATIO}", ratio_txt)
                .replace("{BOX_RETAIL}", f"{retail:,}円"))


def _render_howto(h: dict) -> str:
    slug = h["slug"]
    url = f"{BASE}/dragonball/{slug}.html"
    date = h.get("date", "2026-08-27")

    blog_ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": h["title"], "description": h["meta_desc"],
        "datePublished": date, "dateModified": date,
        "image": f"{BASE}/ogp.jpg",
        "author": {"@type": "Organization", "name": f"{SITE_NAME}編集部", "url": f"{BASE}/dragonball"},
        "publisher": {"@type": "Organization", "name": SITE_NAME,
                      "logo": {"@type": "ImageObject", "url": f"{BASE}/ogp.png"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "articleSection": "買取ガイド", "inLanguage": "ja",
    }
    crumb_ld = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{BASE}/"},
            {"@type": "ListItem", "position": 2, "name": SITE_NAME, "item": f"{BASE}/dragonball"},
            {"@type": "ListItem", "position": 3, "name": h["crumb"]},
        ],
    }
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in h["faq"]
        ],
    }

    faq_html = "".join(
        f'<h3>{_esc(f["q"])}</h3>\n<p>{f["a"]}</p>\n' for f in h["faq"])

    rel = []
    if h.get("box_slug"):
        rel.append(f'<li><a href="box/{h["box_slug"]}.html">{_esc(h.get("box_name", ""))} の買取価格</a>'
                   ' — 店舗別の最新価格と価格推移グラフ(毎日更新)</li>')
    rel.append('<li><a href="/dragonball">ドラゴンボールBOX買取価格比較トップ</a>'
               ' — 全BOXの買取価格を店舗横断で比較(毎日更新)</li>')
    for _a in ATARI_ARTICLES:
        if _a["slug"] != h["slug"]:
            rel.append(f'<li><a href="{_a["slug"]}.html">{_esc(_a["box_name"])} 当たりカードランキング</a>'
                       ' — トップレアの買取相場と封入率</li>')
    if h["slug"] != "hatsubai-schedule":
        rel.append('<li><a href="hatsubai-schedule.html">新弾発売スケジュール</a>'
                   ' — 今後の新弾の発売日とBOX定価</li>')
    related_html = "\n".join(rel)

    disclaimer = (
        "本記事は、ドラゴンボールカードの未開封BOXを売買する際の一般的な考え方をまとめた参考情報です。"
        "発売日・価格はメーカーおよび各販売店の告知に基づく執筆時点の情報であり、変更される場合があります。"
        "買取価格・相場は需給や各店の在庫状況により日々変動し、店舗ごとに査定基準(シュリンク・外箱状態の減額幅等)も異なります。"
        "掲載する金額は目安であり、特定の買取価格を保証するものではありません。"
        "実際の売買の判断はご自身の責任で行ってください。")

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://h.accesstrade.net">
<meta name="description" content="{_esc(h['meta_desc'])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{_esc(h['og_title'])}">
<meta property="og:description" content="{_esc(h['og_desc'])}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/ogp.jpg">
<meta property="og:site_name" content="{SITE_NAME}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_esc(h['og_title'])}">
<meta name="twitter:description" content="{_esc(h['og_desc'])}">
<meta name="twitter:image" content="{BASE}/ogp.jpg">
<title>{_esc(h['title'])}｜{SITE_NAME}</title>
<script type="application/ld+json">{json.dumps(blog_ld, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(crumb_ld, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
{STYLE}
</head>
<body>
<a class="gswitch" href="/dragonball"><span class="ar">&larr;</span> ドラゴンボールBOX買取価格を比較する</a>
<div class="header"><a href="/dragonball"><h1>{SITE_NAME}</h1></a></div>

<div class="wrap">
<div class="breadcrumb"><a href="/">ホーム</a> &rsaquo; <a href="/dragonball">{SITE_NAME}</a> &rsaquo; {_esc(h['crumb'])}</div>

<div class="content-layout">
<nav class="article-nav">
{_nav_links(slug)}
</nav>

<article>
<h1>{_esc(h['h1'])}</h1>
<div class="meta">{_esc(h['meta_line'])} ／ 最終更新: {date}</div>

<div class="hero">
<div class="stat-label">{_esc(h['hero_label'])}</div>
<div class="stat-big">{_esc(h['hero_big'])}</div>
<div class="stat-sub">{h['hero_sub']}</div>
</div>

{h['body']}

<h2>よくある質問(FAQ)</h2>
{faq_html}

<div class="disclaimer"><strong>ご注意</strong>：{disclaimer}</div>

<h2>関連ページ</h2>
<ul>
{related_html}
</ul>

<a href="/dragonball" class="back">&larr; ドラゴンボール買取比較トップ</a>
</article>
</div><!-- /content-layout -->

</div>

{AFFILIATE}

<div class="ft">
  <a href="/dragonball">{SITE_NAME}</a> / <a href="/privacy.html">プライバシーポリシー</a>
</div>
</body>
</html>
"""


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for h in HOWTO_ARTICLES:
        path = OUT_DIR / f"{h['slug']}.html"
        path.write_text(_render_howto(h), encoding="utf-8")
        print(f"wrote dragonball/{h['slug']}.html")

    box_prices = _box_max_prices()
    for a in ATARI_ARTICLES:
        price = box_prices.get(a["box_name"], 0)
        art = dict(a)
        for key in ("body", "hero_sub", "meta_desc", "og_desc"):
            if key in art:
                art[key] = _subst_box(art[key], price, a["retail"])
        art["faq"] = [{"q": f["q"], "a": _subst_box(f["a"], price, a["retail"])}
                      for f in a["faq"]]
        path = OUT_DIR / f"{a['slug']}.html"
        path.write_text(_render_howto(art), encoding="utf-8")
        print(f"wrote dragonball/{a['slug']}.html  (BOX相場 {price:,}円)")


if __name__ == "__main__":
    build()
