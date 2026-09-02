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
    {'slug': 'kougaku-ranking',
     'nav_label': '高額BOXランキング',
     'crumb': '高額BOXランキング',
     'date': '2026-09-02',
     'title': 'ドラゴンボールカード 高額BOXランキング｜MANGA BOOSTERだけ定価の18倍になる理由',
     'h1': 'ドラゴンボールカード 高額BOXランキング｜MANGA BOOSTERだけが突出する理由',
     'meta_desc': 'ドラゴンボールカード(フュージョンワールド・スーパーダイバーズ)の未開封BOX買取価格を、当サイトが4店舗から毎日自動収集した実データで高い順にランキング。1位のMANGA BOOSTER '
                  '01は定価7,920円に対し{{TOP1_PRICE}}と突出し、通常ブースター(FB)の水準とは別物です。定価割れしている商品まで含めて全{{DB_COUNT}}商品を掲載しています。',
     'og_title': 'ドラゴンボールカード 高額BOXランキング｜MANGA BOOSTERだけ別格',
     'og_desc': '全{{DB_COUNT}}商品の最高買取と定価比を当サイト実データでランキング。MANGA BOOSTER 01は{{TOP1_PRICE}}({{TOP1_MULT}})。',
     'meta_line': 'ドラゴンボールカードの未開封BOX 最高買取ランキング(当サイト実データ・毎日更新)',
     'hero_label': 'BOX最高買取ランキング 1位',
     'hero_big': 'MANGA BOOSTER 01 {{TOP1_PRICE}}',
     'hero_sub': '{{TOP1_MULT}}。2位 MANGA BOOSTER 02 {{TOP2_PRICE}}({{TOP2_MULT}})、3位 {{TOP3_NAME}} {{TOP3_PRICE}}({{TOP3_MULT}})。全{{DB_COUNT}}商品の最高買取と定価比を4店舗の実データで毎日更新しています。',
     'body': '<p>ドラゴンボールのカードは、同じ「BOX」でも商品によって買取価格が<strong>20倍以上</strong>開きます。定価5,280円前後の通常ブースターが1万円台で落ち着く一方、<strong>MANGA '
             'BOOSTERは10万円を超える</strong>のが実情です。本記事では、当サイトが4店舗から毎日自動収集している買取データをもとに、<strong>全{{DB_COUNT}}商品を最高買取価格の高い順にランキング</strong>し、なぜMANGA BOOSTERだけが別格なのかを整理します。</p>\n'
             '\n'
             '<h2>高額BOXランキング｜全{{DB_COUNT}}商品(当サイト実データ)</h2>\n'
             '<p>各商品の<strong>最高買取価格</strong>(当サイト掲載店舗のうち最も高い店の価格)と、<strong>定価に対する倍率</strong>を並べたものが以下の表です。商品名をクリックすると、その弾の当たりカードガイドに移動できます。</p>\n'
             '{{DB_RANKING}}\n'
             '<div class="callout"><strong>表の見方:</strong> 定価はBOX想定定価(1パック税込定価×BOX封入パック数)です。実売価格ではないため、倍率は「定価どおりに買えた場合」の目安として見てください。最新値は <a href="/dragonball">ドラゴンボールBOX買取価格比較トップ</a> でご確認ください。</div>\n'
             '\n'
             '<h2>なぜMANGA BOOSTERだけが突出するのか</h2>\n'
             '<p>1位と2位を <strong>MANGA BOOSTER</strong> が占めています。通常ブースター(FBシリーズ)は上の表のとおり最高でも4万円台で、明らかに別の商品カテゴリとして扱われていることが分かります。</p>\n'
             '<p>理由は<strong>「エナジーマーカー★」</strong>という原作コミックスの表紙をそのまま使った特別なカードにあります。</p>\n'
             '<ul>\n'
             '<li><a href="sb-01-atari-guide.html">MANGA BOOSTER 01(SB-01)</a>: <strong>1巻表紙のエナジーマーカー★が約180万円</strong>。2位の孫悟空SCR★★でも約60〜65万円</li>\n'
             '<li><a href="sb-02-atari-guide.html">MANGA BOOSTER 02(SB-02)</a>: <strong>42巻(最終巻)表紙のエナジーマーカー★が約100万円</strong></li>\n'
             '</ul>\n'
             '<p>カード1枚で100万円を超える枠が存在するため、未開封BOXの価値がそこに引っ張られます。当サイトが他タイトルでも確認している<strong>「BOX価格を決めるのは看板カードがどこまで高くなれるか」</strong>という構造が、ここでも当てはまっています。</p>\n'
             '<div class="callout"><strong>注意:</strong> エナジーマーカー★は極端な低確率です。BOXを買えば当たるものではなく、BOX買取価格が高いこと自体は「開封して回収できる」という意味ではありません。</div>\n'
             '\n'
             '<h2>通常ブースター(FB)で最も高いのはFB-07</h2>\n'
             '<p>FBシリーズの中では <a href="fb-07-atari-guide.html">「神龍への願い」(FB-07)</a> が突出しています。看板は<strong>孫悟飯:SH '
             'SCR★★(約4〜4.8万円)</strong>で、240BOXに1枚とされるスーパーパラレル枠です。ほかのFBが定価の1.3〜3.4倍に収まるなかで、この弾だけ倍率が跳ね上がっています。</p>\n'
             '<p>逆に言えば、<strong>FBシリーズは基本的に定価の1〜3倍のレンジ</strong>で動く商品群です。MANGA BOOSTERの倍率をFBに当てはめて考えると、期待値を大きく見誤ります。</p>\n'
             '\n'
             '<h2>定価割れしている商品もある</h2>\n'
             '<p>ランキング最下位の<strong>スーパーダイバーズ アドバンスパック「バトルオブサイヤン」</strong>は、当サイト掲載の中で唯一<strong>定価を下回っています</strong>。同じスーパーダイバーズでも「DRAGON BALL 40th Anniversary」は上位に入っており、シリーズ名ではなく商品単位で見る必要があることが分かります。</p>\n'
             '<p>「ドラゴンボールのカードは値上がりする」と一括りにできない、というのがデータから言えることです。</p>\n'
             '\n'
             '<h2>売るとき・買うときの考え方</h2>\n'
             '<ul>\n'
             '<li><strong>売る場合</strong>: 当サイトは4店舗の買取価格を毎日取得しています。同じBOXでも店によって価格が違うため、<a href="/dragonball">比較トップ</a>で最高値の店を確認してから持ち込んでください</li>\n'
             '<li><strong>買う場合</strong>: 定価比が高い商品ほど、すでに評価が織り込まれています。倍率が低い弾は「まだ上がっていない」のではなく、看板カードの水準がそのまま反映されていると考えるほうが実態に近いです</li>\n'
             '<li><strong>新弾</strong>: 発売直後は相場が動きやすい時期です。今後の発売予定は <a href="hatsubai-schedule.html">ドラゴンボールカード 新弾スケジュール</a> にまとめています</li>\n'
             '</ul>\n',
     'faq': [{'q': 'ドラゴンボールカードで一番高いBOXはどれですか？',
              'a': '当サイトが4店舗から毎日取得している実データでは、MANGA BOOSTER 01(SB-01)が{{TOP1_PRICE}}で1位です。BOX想定定価7,920円に対して{{TOP1_MULT}}にあたります。2位はMANGA BOOSTER 02(SB-02)の{{TOP2_PRICE}}です。'},
             {'q': 'なぜMANGA BOOSTERは通常のブースターパックより高いのですか？', 'a': '原作コミックスの表紙をそのまま使った「エナジーマーカー★」という枠があり、SB-01の1巻表紙は約180万円、SB-02の42巻表紙は約100万円という水準で取引されているためです。カード1枚の天井が通常ブースターと桁違いで、その価値がBOX価格に反映されています。'},
             {'q': '通常ブースター(FB)はどのくらいの倍率になりますか？', 'a': '多くは定価の1.3〜3.4倍のレンジです。例外は「神龍への願い」(FB-07)で、孫悟飯:SH SCR★★という240BOXに1枚とされる枠があるため倍率が跳ね上がっています。'},
             {'q': '定価より安くなっているBOXはありますか？', 'a': 'あります。スーパーダイバーズ アドバンスパック「バトルオブサイヤン」は当サイト掲載の中で唯一、最高買取がBOX想定定価を下回っています。同じスーパーダイバーズでも40th Anniversaryは上位に入っており、シリーズ単位ではなく商品単位で見る必要があります。'}]},
    {
        "slug": "fb-11-forecast",
        "nav_label": "【予想】BRIGHTNESS OF HOPE(FB-11)",
        "crumb": "BRIGHTNESS OF HOPE(FB-11) 発売前予想",
        "date": "2026-08-30",
        "title": "【発売前予想】BRIGHTNESS OF HOPE(FB-11) BOX相場と当たりカード｜9月12日発売・この弾から値上げ",
        "h1": "【発売前予想】BRIGHTNESS OF HOPE(FB-11) BOX相場と当たりカード｜9月12日発売",
        "meta_desc": "2026年9月12日発売のドラゴンボールカード「BRIGHTNESS OF HOPE」(FB-11)を発売前に予想。この弾から1パック240円・BOX5,760円へ値上げされます。SCRは孫悟空・シャレット・バーダックの3種が公開済み。SCR★★が3種構成だった過去弾(FB-09・FB-10)の実績から、BOX相場と当たりカードの水準を当サイトの実データで整理します。",
        "og_title": "【発売前予想】BRIGHTNESS OF HOPE(FB-11) BOX相場と当たりカード",
        "og_desc": "9月12日発売のFB-11を発売前予想。この弾から値上げでBOX5,760円。SCR3種構成の過去弾FB-09・FB-10の実績から相場水準を整理。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「BRIGHTNESS OF HOPE」(FB-11・2026年9月12日発売)",
        "hero_label": "FB-11 発売前予想",
        "hero_big": "9月12日発売・BOX5,760円",
        "hero_sub": "この弾から1パック220円→240円に値上げ。SCRは孫悟空・シャレット・バーダックの3種が公開済みで、SCR★★が3種だった過去弾と同じ構成です。発売後は当サイトが4店舗の買取価格を毎日自動収集します。",
        "body": """<p>2026年9月12日(土)、ドラゴンボールスーパーカードゲーム フュージョンワールドのブースターパック第11弾 <strong>「BRIGHTNESS OF HOPE」【FB-11】</strong> が発売されます。本記事では発売前に判明している情報を整理し、<strong>過去弾の実績から相場の水準を見積もり</strong>ます。発売後の実際の買取価格は <a href="/dragonball">ドラゴンボールBOX買取価格比較トップ</a> で毎日更新します。</p>

<div class="callout"><strong>この記事は発売前の予想を含みます。</strong> 確定情報(発売日・定価・公開済みカード)と、過去弾の実績にもとづく<strong>推定</strong>を分けて記載しています。実際の相場は発売後の需給で決まるため、予想が外れる可能性があります。売買の判断はご自身の責任でお願いします。</p></div>

<h2>確定している基本情報</h2>
<table class="tbl">
<thead><tr><th>項目</th><th>内容</th></tr></thead>
<tbody>
<tr><td>発売日</td><td>2026年9月12日(土)</td></tr>
<tr><td>1パック</td><td><strong>240円(税込)</strong>・カード6枚＋デジタル版連動コード1枚</td></tr>
<tr><td>1BOX</td><td>24パック入り・<strong>5,760円(税込)</strong></td></tr>
<tr><td>1カートン</td><td>12BOX(288パック)入り・69,120円(税込)</td></tr>
<tr><td>収録種類</td><td>全123種(＋パラレル)</td></tr>
</tbody>
</table>

<h3>この弾から値上げされます</h3>
<p>見落としやすい変更点として、<strong>FB-11から1パックが220円→240円に改定</strong>されます。BOXの構成は24パック入りのまま変わらないため、<strong>BOX定価は5,280円→5,760円</strong>、1BOXあたり480円の値上げです。</p>
<div class="callout"><strong>定価比で見るときの注意</strong>：買取価格を「定価の何倍か」で評価する場合、FB-10以前とFB-11以降では基準が変わります。同じ買取15,000円でも、5,280円の弾なら約2.84倍、5,760円の弾なら約2.60倍です。当サイトの比較表は弾ごとに定価を保持しているので、改定をまたいでも正しい倍率で比較できます。詳しくは <a href="hatsubai-schedule.html">新弾発売スケジュール</a> にまとめています。</div>

<h2>レアリティ構成</h2>
<p>全123種の内訳は次のとおりです(パラレル版を除いた種類数)。</p>
<table class="tbl">
<thead><tr><th>レアリティ</th><th>種類数</th></tr></thead>
<tbody>
<tr><td>SCR(シークレットレア)</td><td>3種</td></tr>
<tr><td>L(リーダーカード)</td><td>5種</td></tr>
<tr><td>SR(スーパーレア)</td><td>15種</td></tr>
<tr><td>R(レア)</td><td>25種</td></tr>
<tr><td>UC(アンコモン)</td><td>35種</td></tr>
<tr><td>C(コモン)</td><td>40種</td></tr>
<tr><td><strong>合計</strong></td><td><strong>123種</strong></td></tr>
</tbody>
</table>
<p>これに加えて<strong>パラレル版</strong>が別途封入されます。スーパーパラレル・パラレル・ビジュアルパラレル・スーパーコンボパラレルの各仕様が確認されており、当たりの中心はSCR3種とこれらのパラレルになります。</p>
<div class="callout"><strong>封入率は公表されていません。</strong> 情報源によって数字に開きがあるため、当サイトでは確定していない封入率は掲載しません。発売後、実際に買取価格が付いた時点で比較表と当たりガイドに反映します。</div>

<h2>公開されている注目カード</h2>
<p>発売前時点で、シークレットレア(SCR)は次の3種が公開されています。</p>
<table class="tbl">
<thead><tr><th>カード番号</th><th>カード名</th><th>種別</th></tr></thead>
<tbody>
<tr><td>FB11-121</td><td>孫悟空</td><td>SCR</td></tr>
<tr><td>FB11-122</td><td>シャレット</td><td>SCR</td></tr>
<tr><td>FB11-123</td><td>バーダック</td><td>SCR</td></tr>
<tr><td>FB11-001</td><td>孫悟空</td><td>リーダーカード(覚醒前/覚醒後の両面)</td></tr>
<tr><td>FB11-073</td><td>シャロット／ジブレット／シャレット</td><td>リーダーカード</td></tr>
</tbody>
</table>
<p>SCRが3種という構成は、<a href="fb-10-atari-guide.html">FB-10「CROSS FORCE」</a>(ベジット・孫悟飯:少年期・セル)や <a href="fb-09-atari-guide.html">FB-09「DUAL EVOLUTION」</a>(ゴジータ3バージョン)と同じです。</p>

<h2>過去弾の実績から見た相場の水準</h2>
<p>予想の土台になるのは、<strong>同じ構成の弾が実際にどの水準にあるか</strong>です。当サイトが4店舗から収集している実データ(2026年8月30日時点)では次のようになっています。</p>
<table class="tbl">
<thead><tr><th>弾</th><th>発売日</th><th>定価</th><th>BOX買取(最高)</th><th>定価比</th></tr></thead>
<tbody>
<tr><td><a href="box/fb-10.html">FB-10 CROSS FORCE</a></td><td>2026-06-13</td><td>5,280円</td><td class="num">16,500円</td><td>約3.1倍</td></tr>
<tr><td><a href="box/fb-09.html">FB-09 DUAL EVOLUTION</a></td><td>2026-03-14</td><td>5,280円</td><td class="num">16,500円</td><td>約3.1倍</td></tr>
<tr><td><a href="box/fb-08.html">FB-08 誇り高き戦闘民族</a></td><td>2025-12-13</td><td>5,280円</td><td class="num">12,800円</td><td>約2.4倍</td></tr>
<tr><td><a href="box/fb-07.html">FB-07 神龍への願い</a></td><td>2025-09-13</td><td>5,280円</td><td class="num">41,500円</td><td>約7.9倍</td></tr>
</tbody>
</table>
<p>SCR★★が3種だったFB-09・FB-10はいずれも定価の約3.1倍で並んでいます。一方、トップレア1枚に集中する構成の <a href="fb-07-atari-guide.html">FB-07</a> は約7.9倍と大きく外れており、<strong>構成の違いだけで水準が決まるわけではない</strong>ことがわかります。FB-07については、240BOXに1枚という封入率を踏まえるとカードの期待値ではBOX価格を説明できず、当サイトでも理由を断定していません。</p>

<h3>FB-11の見立て</h3>
<p>以上から、FB-11は<strong>SCR★★3種構成という点でFB-09・FB-10に近い</strong>と考えられます。ただし相場は需給で決まるため、次の点で振れ幅があります。</p>
<ul>
<li><strong>発売直後は流通量が限られる</strong> — 注目度が高い時期で、初動が高く出る弾もあれば早く落ち着く弾もあります</li>
<li><strong>定価が5,760円に上がる</strong> — 買取額が同じでも定価比の数字は下がります。過去弾と横並びで比較する際は注意が必要です</li>
<li><strong>収録カードの人気</strong> — FB-09では上位5枚のうち4枚がゴジータでした。FB-11は孫悟空・シャレット・バーダックと分散しており、どのカードに需要が集中するかは発売後の実データを待つ必要があります</li>
</ul>
<p>当サイトでは<strong>具体的な予想金額は掲載しません</strong>。発売前の予想価格は各社で大きく食い違うことが多く、実データで比較する当サイトの方針と合わないためです。発売後に各店が買取を開始した時点で、実際の価格を自動的に掲載します。</p>

<h2>発売後にこのページで確認できること</h2>
<ul>
<li><strong>店舗別の買取価格</strong> — 4店舗の最新価格と最高値の店舗(<a href="/dragonball">比較トップ</a>で毎日更新)</li>
<li><strong>価格推移グラフ</strong> — 発売日からの値動きを個別ページで確認できます</li>
<li><strong>当たりカードランキング</strong> — 相場が固まった段階で、他弾と同じ形式の当たりガイドを追加します。既存分は <a href="fb-10-atari-guide.html">FB-10</a>・<a href="fb-09-atari-guide.html">FB-09</a> などをご覧ください</li>
</ul>
<p>発売前は買取受付をしていない店舗がほとんどのため、比較表では価格が空欄になります。各店が買取を開始し価格が付いた時点で自動的に反映されます。</p>""",
        "faq": [
            {"q": "FB-11「BRIGHTNESS OF HOPE」の発売日と定価は?",
             "a": "2026年9月12日(土)発売です。1パック240円(税込・カード6枚入り)、1BOX24パック入りでBOX定価は5,760円(税込)。全123種が収録されます。"},
            {"q": "FB-11から値上げされるのですか?",
             "a": "はい。FB-11から1パックが220円→240円に改定されます。BOXの構成は24パック入りのまま変わらないため、BOX定価は5,280円から5,760円へ、1BOXあたり480円の値上げになります。FB-10「CROSS FORCE」までは220円×24パックの5,280円でした。"},
            {"q": "FB-11の当たりカードは何ですか?",
             "a": "発売前のため確定していません。シークレットレア(SCR)は孫悟空(FB11-121)・シャレット(FB11-122)・バーダック(FB11-123)の3種が公開されています。SCRが3種という構成はFB-09・FB-10と同じです。実際の買取価格は発売後に当サイトへ掲載します。"},
            {"q": "FB-11のBOX買取価格はどのくらいになりそうですか?",
             "a": "当サイトでは発売前の具体的な予想金額は掲載していません。参考として、SCR★★が3種だったFB-09・FB-10はいずれも現在(2026年8月30日時点)定価の約3.1倍で推移しています。ただし相場は需給で決まり、FB-07のように約7.9倍まで離れる弾もあるため、発売後の実データでご確認ください。"},
            {"q": "FB-11のレアリティ構成はどうなっていますか?",
             "a": "全123種の内訳はSCR3種・リーダーカード5種・SR15種・R25種・UC35種・C40種です。これに加えてパラレル版(スーパーパラレル・パラレル・ビジュアルパラレル・スーパーコンボパラレル)が封入されます。封入率は公表されていないため、当サイトでは掲載していません。"},
            {"q": "発売前でも買取価格を比較できますか?",
             "a": "発売前は買取受付をしていない店舗がほとんどのため、比較表では価格が空欄になります。各店が買取を開始し価格が付いた時点で、当サイトの比較表と個別ページに自動的に反映されます。"},
        ],
    },
    {
        "slug": "hatsubai-schedule",
        "nav_label": "新弾発売スケジュール",
        "crumb": "新弾発売スケジュール",
        "date": "2026-08-27",
        "title": "ドラゴンボールカード 新弾発売スケジュール｜FB-11・FB-12の発売日と定価改定",
        "h1": "ドラゴンボールカード 新弾発売スケジュール｜FB-11・FB-12の発売日とBOX定価",
        "meta_desc": "ドラゴンボールスーパーカードゲーム フュージョンワールドの新弾発売スケジュール。FB-11「BRIGHTNESS OF HOPE」(2026年9月12日・BOX5,760円)とFB-12「REACH THE GOD」(2026年12月12日)の発売日、FB-11から実施される1パック240円への定価改定、発売前後の買取相場の動きを実データ視点で解説します。",
        "og_title": "ドラゴンボールカード 新弾発売スケジュール｜FB-11・FB-12",
        "og_desc": "FB-11は2026年9月12日、FB-12「REACH THE GOD」は12月12日発売でBOX定価5,760円。1パック240円への改定と相場への影響を整理。",
        "meta_line": "フュージョンワールド新弾の発売日・BOX定価・相場への影響",
        "hero_label": "新弾発売スケジュール",
        "hero_big": "次はFB-11(9/12)とFB-12(12/12)",
        "hero_sub": "ドラゴンボールスーパーカードゲーム フュージョンワールドの発売予定を整理。FB-11からは1パック240円へ改定され、BOX定価も5,280円→5,760円に変わります。発売日・定価・相場の動きをまとめて確認できます。",
        "body": """<p>ドラゴンボールスーパーカードゲーム フュージョンワールドは定期的に新弾が発売され、<strong>発売の前後で未開封BOXの買取相場が動きます</strong>。「次の弾はいつか」「手元のBOXを新弾前に売るべきか」を判断するには、発売スケジュールの把握が出発点になります。本記事では<strong>これから発売される弾の日程・BOX定価</strong>と、<strong>FB-11から実施される定価改定</strong>を整理します。各弾の実際の買取価格は <a href="/dragonball">ドラゴンボールBOX買取価格比較トップ</a> で毎日更新しています。</p>

<h2>これから発売される弾</h2>
<p>2026年8月27日時点で判明している発売予定です。</p>
<table class="tbl">
<thead><tr><th>発売日</th><th>商品名</th><th>弾番号</th><th>BOX定価(税込)</th></tr></thead>
<tbody>
<tr><td>2026年9月12日</td><td>ブースターパック<br>BRIGHTNESS OF HOPE</td><td>FB-11</td><td class="num">5,760円</td></tr>
<tr><td>2026年12月12日</td><td>ブースターパック<br>REACH THE GOD</td><td>FB-12</td><td class="num">5,760円</td></tr>
</tbody>
</table>

<h3>FB-11「BRIGHTNESS OF HOPE」(2026年9月12日)</h3>
<p>ブースターパック第11弾で全123種。1パック240円×24パックで、<strong>BOX定価は5,760円</strong>です。<a href="box/fb-10.html">FB-10「CROSS FORCE」</a>(2026年6月13日)に続く弾で、<strong>この弾から1パックが220円→240円に値上げ</strong>されます。シークレットレアは孫悟空(FB11-121)・シャレット(FB11-122)・バーダック(FB11-123)の3種が公開されています。</p>

<h3>FB-12「REACH THE GOD」(2026年12月12日)</h3>
<p>ブースターパック第12弾。<strong>ビルスをはじめとする「神」の領域のキャラクター</strong>が中心のラインナップとされています。価格はFB-11に続き1パック240円・BOX5,760円です。</p>
<ul>
<li><strong>発売日</strong>: 2026年12月12日(土)</li>
<li><strong>1パック</strong>: 240円(税込)・カード6枚入り</li>
<li><strong>1BOX</strong>: 24パック入り・<strong>5,760円(税込)</strong></li>
</ul>

<h2>FB-11から定価が上がります</h2>
<p>スケジュール上で最も重要な変化が<strong>パック単価の改定</strong>です。FB-10までは1パック220円でしたが、<strong>FB-11から240円</strong>になります。BOXの構成は24パック入りのまま変わらないため、BOX定価は5,280円から5,760円へ、<strong>1BOXあたり480円の値上げ</strong>となります。</p>
<table class="tbl">
<thead><tr><th>区分</th><th>1パック</th><th>BOX構成</th><th>BOX定価</th></tr></thead>
<tbody>
<tr><td>FB-10以前</td><td>220円</td><td>24パック</td><td class="num">5,280円</td></tr>
<tr><td><strong>FB-11以降</strong></td><td><strong>240円</strong></td><td>24パック</td><td class="num"><strong>5,760円</strong></td></tr>
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
<li><strong>新弾を買う予定がある</strong>: FB-11以降はBOX定価が5,760円に上がるため、購入コストの前提が変わります。</li>
<li><strong>複数店を比較する</strong>: どのタイミングでも店舗ごとの価格差は残ります。売る直前に <a href="/dragonball">店舗別の比較</a> で最新値を確認してください。</li>
</ul>
<p>本記事の発売日・価格はメーカー発表および各販売店の告知に基づく2026年8月27日時点の情報です。<strong>発売日や仕様は変更される場合がある</strong>ため、購入・売却の判断前には最新の公式情報をあわせてご確認ください。</p>""",
        "faq": [
            {"q": "FB-12「REACH THE GOD」の発売日はいつですか?",
             "a": "2026年12月12日(土)発売予定です。1パック240円(税込・カード6枚入り)、1BOX24パック入りでBOX定価は5,760円(税込)となっています。ビルスをはじめとする「神」の領域のキャラクターが中心のラインナップとされています。"},
            {"q": "BOXの定価が5,280円から5,760円に変わるのはなぜですか?",
             "a": "FB-11「BRIGHTNESS OF HOPE」(2026年9月12日発売)から1パックの価格が220円から240円に改定されるためです。BOXの構成は24パック入りのまま変わらないため、24パック×240円で定価が5,760円になります。FB-10「CROSS FORCE」までは従来通り220円×24パックの5,280円でした。"},
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
    {
        "slug": "st-01-atari-guide",
        "box_slug": "st-01",
        "box_name": "STORY BOOSTER 01【ST-01】",
        "retail": 6600,
        "nav_label": "STORY BOOSTER 01(ST-01)",
        "crumb": "STORY BOOSTER 01(ST-01) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "STORY BOOSTER 01(ST-01) 当たりカードランキング｜ベジットSCR★★の買取相場",
        "h1": "STORY BOOSTER 01(ST-01) 当たりカードランキング｜ベジットSCR★★の買取相場を解説",
        "meta_desc": "ドラゴンボールカード「STORY BOOSTER 01」(ST-01)の当たりカードランキング・買取相場を解説。1位はベジットSCR★★で約50〜60万円、2位はベジータSCR★★が約35〜50万円。2026年8月8日発売の新シリーズで、発売直後のため相場変動が大きい点も含めて実データで整理しています。",
        "og_title": "STORY BOOSTER 01(ST-01) 当たりカードランキング｜ベジットSCR★★",
        "og_desc": "ST-01の当たりカード・買取相場を解説。1位はベジットSCR★★で約50〜60万円。発売直後で相場が動きやすい新シリーズ第1弾。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド STORY BOOSTER 01(ST-01・2026年8月8日発売)",
        "hero_label": "ST-01 トップレア",
        "hero_big": "ベジット SCR★★ 約50〜60万円",
        "hero_sub": "2026年8月8日発売の新シリーズ第1弾。2位はベジータSCR★★で約35〜50万円。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2026年8月8日発売の <strong><a href="box/st-01.html">STORY BOOSTER 01【ST-01】</a></strong> は、「STORY BOOSTER」という新しいシリーズの第1弾です。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>となっています。</p>
<div class="callout"><strong>発売直後の弾です</strong>：ST-01は発売から日が浅く、<strong>相場が最も動きやすい時期</strong>にあります。本記事の金額は複数の情報源を突き合わせたレンジで示していますが、実際の価格は日々変わります。売買の前に <a href="box/st-01.html">個別ページ</a> で最新値をご確認ください。</div>

<h2>当たりカードランキング TOP3</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th></tr></thead>
<tbody>
<tr><td>1位</td><td>ベジット</td><td>SCR★★</td><td class="num">約50〜60万円</td></tr>
<tr><td>2位</td><td>ベジータ</td><td>SCR★★</td><td class="num">約35〜50万円</td></tr>
<tr><td>3位</td><td>エナジーマーカー★<br>E-157</td><td>パラレル</td><td class="num">約10〜16万円</td></tr>
</tbody>
</table>
<p>4位以下はエナジーマーカーの各種パラレルが並びますが、<strong>参照する情報源によって順位も金額も一致しません</strong>(4〜6万円台のレンジ)。発売直後で相場が固まっていないため、本記事では上位3枚に絞って掲載しています。</p>

<h2>ベジットとベジータのSCR★★が二枚看板</h2>
<p>ST-01は<strong>上位2枚をSCR★★が占め、3位以下とは大きな差</strong>がついています。1位のベジットが約50〜60万円、2位のベジータが約35〜50万円に対し、3位のエナジーマーカー(E-157)は約10〜16万円です。</p>
<p>この弾でもエナジーマーカーが上位に食い込んでいる点は <a href="sb-01-atari-guide.html">SB-01</a>・<a href="sb-02-atari-guide.html">SB-02</a> と共通ですが、MANGA BOOSTERではエナジーマーカーが頂点だったのに対し、<strong>ST-01ではキャラクターのSCR★★が上</strong>という違いがあります。</p>

<h2>封入率は公表されていません</h2>
<p>ST-01については、参照した情報源のいずれにも<strong>レアリティ別の封入率が記載されていません</strong>。フュージョンワールドの他弾ではSCR★★が240BOXに1枚前後とされるケースが多いものの、ST-01に同じ数字が当てはまるという確認は取れていないため、本記事では推測を書かない方針としています。</p>

<h2>BOX買取と売却の考え方</h2>
<p>当サイトの実データでのBOX買取は{BOX_PRICE}、定価{BOX_RETAIL}に対して{BOX_RATIO}です。発売直後の弾は<strong>初動の需給で相場が上下しやすく</strong>、供給が安定すると水準が落ち着く傾向があります。急いで売る必要がなければ、<a href="box/st-01.html">価格推移グラフ</a>で動きを見てから判断するのが有利になり得ます。</p>
<p>今後の新弾の発売予定は <a href="hatsubai-schedule.html">新弾発売スケジュール</a> にまとめています。新弾の発売前後は既存弾の相場も動きやすいため、あわせて確認しておくと判断材料になります。</p>""",
        "faq": [
            {"q": "STORY BOOSTER 01(ST-01)の一番の当たりカードは何ですか?",
             "a": "ベジットのSCR★★で、買取相場は約50〜60万円です(参照する情報源・時期により幅があります)。2位はベジータのSCR★★で約35〜50万円、3位はエナジーマーカー★(E-157)の約10〜16万円です。"},
            {"q": "ST-01の封入率はどのくらいですか?",
             "a": "参照した情報源のいずれにもレアリティ別の封入率の記載がなく、確認が取れていません。フュージョンワールドの他弾ではSCR★★が240BOXに1枚前後とされるケースが多いものの、ST-01に同じ数字が当てはまるとは限らないため、当サイトでは推測を掲載していません。"},
            {"q": "ST-01のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。2026年8月8日発売と日が浅く相場が動きやすい時期のため、個別ページで最新値をご確認ください。"},
            {"q": "ST-01はMANGA BOOSTERと何が違いますか?",
             "a": "どちらもエナジーマーカーが上位に入る点は共通ですが、MANGA BOOSTER(SB-01・SB-02)ではエナジーマーカーが最高額だったのに対し、ST-01ではキャラクターのSCR★★(ベジット・ベジータ)が上位を占めています。"},
        ],
    },
    {
        "slug": "fb-06-atari-guide",
        "box_slug": "fb-06",
        "box_name": 'ブースターパック「迫り来る脅威」【FB-06】',
        "retail": 5280,
        "nav_label": "迫り来る脅威(FB-06)",
        "crumb": "迫り来る脅威(FB-06) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "迫り来る脅威(FB-06) 当たりカードランキング｜ブロリー:BR SCR★★の買取相場と封入率",
        "h1": "迫り来る脅威(FB-06) 当たりカードランキング｜ブロリー:BR SCR★★の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「迫り来る脅威」(FB-06)の当たりカードランキング・買取相場・封入率を解説。1位はブロリー:BR SCR★★で約4〜5.5万円、封入率は20カートン(約240BOX)に約1枚。2位以下は7,000〜9,000円台で、1位との差が明確な一枚勝ちの構成です。",
        "og_title": "迫り来る脅威(FB-06) 当たりカードランキング｜ブロリー:BR SCR★★",
        "og_desc": "FB-06の当たりカード・買取相場・封入率を解説。1位はブロリー:BR SCR★★で約4〜5.5万円、240BOXに約1枚。2位以下とは5倍以上の差。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「迫り来る脅威」(FB-06・2025年4月26日発売)",
        "hero_label": "FB-06 トップレア",
        "hero_big": "ブロリー:BR SCR★★ 約4〜5.5万円",
        "hero_sub": "映画『ドラゴンボール超 ブロリー』がテーマの弾。封入率は20カートン(約240BOX)に約1枚。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2025年4月26日発売の <strong><a href="box/fb-06.html">ブースターパック「迫り来る脅威」【FB-06】</a></strong> は、映画『ドラゴンボール超 ブロリー』のブロリーを軸に、少年期の孫悟空やピッコロ大魔王など天下一武道会編のキャラクターを収録した弾です。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>となっています。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th><th>封入率</th></tr></thead>
<tbody>
<tr><td>1位</td><td>ブロリー:BR</td><td>SCR★★</td><td class="num">約4〜5.5万円</td><td>20カートン(約240BOX)に約1枚</td></tr>
<tr><td>2位</td><td>ブロリー:BR</td><td>L★</td><td class="num">約8,000〜9,000円</td><td>記載なし</td></tr>
<tr><td>3位</td><td>ブロリー:BR</td><td>SCR★</td><td class="num">約7,000〜7,500円</td><td>1カートン(12BOX)に約1枚</td></tr>
<tr><td>4位</td><td>極限の煌めき<br>(金文字)</td><td>R★</td><td class="num">約7,000円</td><td>記載なし</td></tr>
<tr><td>5位</td><td>人造人間18号<br>(AWAKEN)</td><td>L★</td><td class="num">約5,000円</td><td>1カートンに約1〜2枚</td></tr>
</tbody>
</table>
<p>買取価格は参照する情報源・時期によって幅があるため、上表はレンジで示しています。2位以下の順位は情報源によって前後します。</p>

<h2>ブロリー一枚勝ちの構成</h2>
<p>FB-06の特徴は、<strong>上位を同一キャラクター(ブロリー:BR)が占めている</strong>点です。1位のSCR★★が約4〜5.5万円なのに対し、2位のL★は約8,000〜9,000円で、<strong>約5〜6倍の差</strong>があります。</p>
<p>この構造は <a href="fb-07-atari-guide.html">FB-07「神龍への願い」</a>(1位と2位で約7倍差)と似ています。通常ブースターでは<strong>トップレア1枚に価値が集中し、2位以下は数千円台に落ちる</strong>のが一般的なパターンです。<a href="fb-10-atari-guide.html">FB-10「CROSS FORCE」</a>のようにSCR★★が3種類あり上位が高値で並ぶ弾とは対照的です。</p>

<h2>封入率とBOX価格の関係</h2>
<p>ブロリー:BR SCR★★の封入率は<strong>20カートン(約240BOX)に約1枚</strong>とされています。BOX定価{BOX_RETAIL}で240BOX分を買うと約127万円になる計算で、狙って引きに行く対象ではありません。</p>
<p>一方、3位のSCR★は1カートン(12BOX)に約1枚と現実的な確率ですが、買取は約7,000〜7,500円です。BOX買取が{BOX_PRICE}であることを踏まえると、<strong>12BOX開封してSCR★が1枚出ても、BOXのまま売った方が金額は上</strong>という計算になります。</p>

<h2>売却を考えている場合</h2>
<p>シュリンク付きの未開封状態が最も高く評価されます。売る可能性があるなら開けないことが前提です。<a href="box/fb-06.html">FB-06の個別ページ</a>で店舗別の買取価格と価格推移を比較してから判断してください。</p>""",
        "faq": [
            {"q": "FB-06「迫り来る脅威」の一番の当たりカードは何ですか?",
             "a": "ブロリー:BR の SCR★★で、買取相場は約4〜5.5万円です(参照する情報源・時期により幅があります)。封入率は20カートン(約240BOX)に約1枚とされ、2位のブロリー:BR L★(約8,000〜9,000円)とは5〜6倍の差があります。"},
            {"q": "FB-06は開封した方が得ですか?",
             "a": "トップレアは約240BOXに1枚で現実的ではありません。1カートン(12BOX)に約1枚のSCR★は買取約7,000〜7,500円ですが、BOX買取が{BOX_PRICE}であることを踏まえると、12BOX開封してSCR★が1枚出てもBOXのまま売った方が金額は上になります。"},
            {"q": "FB-06のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値と店舗ごとの差をご確認ください。"},
            {"q": "FB-06はどんなカードが収録されていますか?",
             "a": "映画『ドラゴンボール超 ブロリー』のブロリーを軸に、少年期の孫悟空やピッコロ大魔王など天下一武道会編のキャラクターが収録されています。買取上位もブロリー:BRのパラレル各種が占めています。"},
        ],
    },
    {
        "slug": "fb-09-atari-guide",
        "box_slug": "fb-09",
        "box_name": 'ブースターパック「DUAL EVOLUTION」【FB-09】',
        "retail": 5280,
        "nav_label": "DUAL EVOLUTION(FB-09)",
        "crumb": "DUAL EVOLUTION(FB-09) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "DUAL EVOLUTION(FB-09) 当たりカードランキング｜ゴジータSCR★★の買取相場と封入率",
        "h1": "DUAL EVOLUTION(FB-09) 当たりカードランキング｜ゴジータSCR★★の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「DUAL EVOLUTION」(FB-09)の当たりカードランキング・買取相場・封入率を解説。上位はゴジータ系のSCR★★が独占し約13〜19.5万円。ゴジータ:BR L★★も約10万円と、フュージョンをテーマにした弾らしい構成です。BOX買取価格は当サイトの実データで毎日更新しています。",
        "og_title": "DUAL EVOLUTION(FB-09) 当たりカードランキング｜ゴジータSCR★★",
        "og_desc": "FB-09の当たりカード・買取相場・封入率を解説。上位をゴジータ系SCR★★が独占し約13〜19.5万円。トップレアが1枚に集中しない構成。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「DUAL EVOLUTION」(FB-09・2026年3月14日発売)",
        "hero_label": "FB-09 トップレア",
        "hero_big": "ゴジータ系SCR★★ 約13〜19.5万円",
        "hero_sub": "フュージョンがテーマの弾で、上位をゴジータ系が独占。ゴジータ:BR L★★も約10万円。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2026年3月14日発売の <strong><a href="box/fb-09.html">ブースターパック「DUAL EVOLUTION」【FB-09】</a></strong> は、フュージョン(合体)をテーマにした弾です。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>となっています。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th></tr></thead>
<tbody>
<tr><td>1位</td><td>ゴジータ:GT</td><td>SCR★★</td><td class="num">約13〜19.5万円</td></tr>
<tr><td>2位</td><td>ゴジータ:BR</td><td>SCR★★</td><td class="num">約13〜17万円</td></tr>
<tr><td>3位</td><td>ゴジータ</td><td>SCR★★</td><td class="num">約15万円</td></tr>
<tr><td>4位</td><td>ゴジータ:BR</td><td>L★★</td><td class="num">約10万円</td></tr>
<tr><td>5位</td><td>孫悟空</td><td>L★★</td><td class="num">約7.5〜8.3万円</td></tr>
</tbody>
</table>
<p>1〜3位はいずれも<strong>ゴジータのSCR★★</strong>で、参照する情報源によって順位が入れ替わります。金額差が小さいため、本記事ではレンジで示しています。</p>

<h2>「ゴジータ尽くし」の弾</h2>
<p>FB-09の最大の特徴は、<strong>上位5枚のうち4枚がゴジータ</strong>という点です。フュージョンをテーマにした弾らしく、ゴジータ(原作)・ゴジータ:BR(映画『ブロリー』版)・ゴジータ:GT(GT版)と、異なる作品のゴジータが揃って高額帯に並んでいます。</p>
<p>他の弾ではトップレア1枚に価値が集中し、2位以下が大きく落ちるパターンが多くみられます。たとえば <a href="fb-06-atari-guide.html">FB-06</a> は1位と2位で約5〜6倍、<a href="fb-07-atari-guide.html">FB-07</a> は約7倍の差です。これに対しFB-09は<strong>1位から3位までが同水準</strong>で、4位のL★★も約10万円と厚みがあります。狙いの1枚に絞りにくい反面、高額帯の枚数が多い構成といえます。</p>

<h2>封入率は情報源によって開きがあります</h2>
<p>SCR★★の封入率について、参照した情報源では<strong>「120BOXに約1枚」と「20カートン(約240BOX)に約1枚」で数値が一致しません</strong>。公式から明確な数値が公表されているわけではないため、当サイトではどちらかを断定することはせず、両方の記載があるという事実のみをお伝えします。</p>
<p>いずれの数値であっても、BOX定価{BOX_RETAIL}換算で60万円〜127万円分に相当します。<strong>狙って引きに行く対象ではない</strong>という結論は変わりません。</p>

<h2>売却を考えている場合</h2>
<p>当サイトの実データでのBOX買取は{BOX_PRICE}({BOX_RATIO})です。シュリンク付きの未開封状態が最も高く評価されるため、売る可能性があるなら開けないことが前提になります。<a href="box/fb-09.html">FB-09の個別ページ</a>で店舗別の価格と価格推移を確認してください。</p>""",
        "faq": [
            {"q": "FB-09「DUAL EVOLUTION」の一番の当たりカードは何ですか?",
             "a": "ゴジータ系のSCR★★で、買取相場は約13〜19.5万円です。ゴジータ:GT、ゴジータ:BR、ゴジータ(原作)の3種がいずれも同水準にあり、参照する情報源によって順位が入れ替わります。"},
            {"q": "なぜゴジータばかりが高いのですか?",
             "a": "FB-09はフュージョン(合体)をテーマにした弾で、ゴジータ(原作)・ゴジータ:BR(映画『ブロリー』版)・ゴジータ:GT(GT版)と複数バージョンのゴジータがSCR★★として収録されているためです。上位5枚のうち4枚をゴジータが占めています。"},
            {"q": "FB-09の封入率はどのくらいですか?",
             "a": "SCR★★について、参照した情報源では「120BOXに約1枚」と「20カートン(約240BOX)に約1枚」で数値が一致していません。公式から明確な数値が公表されていないため、当サイトではどちらかを断定していません。いずれにしても狙って引きに行ける確率ではありません。"},
            {"q": "FB-09のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値をご確認ください。"},
        ],
    },
    {
        "slug": "fb-10-atari-guide",
        "box_slug": "fb-10",
        "box_name": 'ブースターパック「CROSS FORCE」【FB-10】',
        "retail": 5280,
        "nav_label": "CROSS FORCE(FB-10)",
        "crumb": "CROSS FORCE(FB-10) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "CROSS FORCE(FB-10) 当たりカードランキング｜ベジットSCR★★の買取相場と封入率",
        "h1": "CROSS FORCE(FB-10) 当たりカードランキング｜ベジットSCR★★の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「CROSS FORCE」(FB-10)の当たりカードランキング・買取相場・封入率を解説。1位はベジットSCR★★で約35〜50万円、2位の孫悟飯:少年期・3位のセルも20万円超。SCR★★が3種収録され高額帯に厚みがある弾です。BOX買取価格は当サイトの実データで毎日更新しています。",
        "og_title": "CROSS FORCE(FB-10) 当たりカードランキング｜ベジットSCR★★",
        "og_desc": "FB-10の当たりカード・買取相場・封入率を解説。1位はベジットSCR★★で約35〜50万円。SCR★★が3種あり高額帯に厚みがある構成。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「CROSS FORCE」(FB-10・2026年6月13日発売)",
        "hero_label": "FB-10 トップレア",
        "hero_big": "ベジット SCR★★ 約35〜50万円",
        "hero_sub": "SCR★★が3種収録され、2位の孫悟飯:少年期・3位のセルも20万円超。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2026年6月13日発売の <strong><a href="box/fb-10.html">ブースターパック「CROSS FORCE」【FB-10】</a></strong> は、ベジット・孫悟飯:少年期・セルの3種がSCR★★として収録された弾です。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>となっています。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th></tr></thead>
<tbody>
<tr><td>1位</td><td>ベジット<br>FB10-121</td><td>SCR★★</td><td class="num">約35〜50万円</td></tr>
<tr><td>2位</td><td>孫悟飯:少年期<br>FB10-122</td><td>SCR★★</td><td class="num">約22〜33万円</td></tr>
<tr><td>3位</td><td>セル<br>FB10-123</td><td>SCR★★</td><td class="num">約22〜32万円</td></tr>
<tr><td>4位</td><td>孫悟空<br>FB10-001</td><td>L★</td><td class="num">約5.5〜8万円</td></tr>
<tr><td>5位</td><td>孫悟飯:少年期<br>FB10-122</td><td>SCR★</td><td class="num">約3.2万円</td></tr>
</tbody>
</table>
<p>買取価格は参照する情報源・時期によって幅があるため、レンジで示しています。</p>

<h2>SCR★★が3種｜高額帯に厚みがある</h2>
<p>FB-10は<strong>SCR★★が3種類収録され、いずれも20万円を超えています</strong>。1位のベジットが約35〜50万円、2位の孫悟飯:少年期と3位のセルが約22〜33万円で、上位3枚の差が比較的小さい構成です。</p>
<p>この点は <a href="fb-09-atari-guide.html">FB-09「DUAL EVOLUTION」</a>(ゴジータ系SCR★★が3種)と似ています。一方、<a href="fb-06-atari-guide.html">FB-06</a> や <a href="fb-07-atari-guide.html">FB-07</a> のようにトップレア1枚に価値が集中する弾とは性格が異なります。<strong>高額カードの種類が多い弾は、狙いの1枚を引く確率が種類数で割られる</strong>点に注意が必要です。</p>

<h2>封入率は情報源によって開きがあります</h2>
<p>SCR★★の封入率について、参照した情報源では<strong>「60BOXに約1枚」と「20カートン(約240BOX)に約1枚」で数値が4倍違います</strong>。公式から明確な数値が公表されているわけではないため、当サイトではどちらかを断定することはしません。</p>
<div class="callout"><strong>なお</strong>：この弾はL★★(リーダースーパーパラレル)が収録されていない代わりにSCR★★の封入率が上がっているという指摘もあります。ただしこれも公式発表ではないため、参考情報として扱ってください。</div>
<p>4位の孫悟空L★は12BOXに約1枚、5位の孫悟飯:少年期SCR★は8BOXに約1枚とされ、こちらは現実的な確率です。ただし買取は3.2万円〜8万円で、BOX買取{BOX_PRICE}との比較では、8〜12BOX開封するコストに見合うかは慎重な判断が要ります。</p>

<h2>売却を考えている場合</h2>
<p>シュリンク付きの未開封状態が最も高く評価されます。<a href="box/fb-10.html">FB-10の個別ページ</a>で店舗別の買取価格と価格推移グラフを確認し、複数店を比較してから売却先を決めてください。今後の新弾予定は <a href="hatsubai-schedule.html">新弾発売スケジュール</a> にまとめています。</p>""",
        "faq": [
            {"q": "FB-10「CROSS FORCE」の一番の当たりカードは何ですか?",
             "a": "ベジットのSCR★★(FB10-121)で、買取相場は約35〜50万円です(参照する情報源・時期により幅があります)。2位の孫悟飯:少年期SCR★★、3位のセルSCR★★もいずれも20万円を超えています。"},
            {"q": "FB-10の封入率はどのくらいですか?",
             "a": "SCR★★について、参照した情報源では「60BOXに約1枚」と「20カートン(約240BOX)に約1枚」で数値が4倍違っており、公式発表もないため当サイトでは断定していません。4位の孫悟空L★は12BOXに約1枚、5位の孫悟飯:少年期SCR★は8BOXに約1枚とされています。"},
            {"q": "FB-09とFB-10はどちらが当たりやすいですか?",
             "a": "どちらもSCR★★が3種収録されており、高額カードの種類が多い分、狙いの1枚を引く確率は種類数で割られます。封入率はいずれも情報源によって数値が食い違うため、単純な比較はできません。BOX買取価格は当サイトの実データで両弾とも確認できます。"},
            {"q": "FB-10のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値と店舗ごとの差をご確認ください。"},
        ],
    },
    {
        "slug": "fb-04-atari-guide",
        "box_slug": "fb-04",
        "box_name": 'ブースターパック「限界を超えし者」【FB-04】',
        "retail": 5280,
        "nav_label": "限界を超えし者(FB-04)",
        "crumb": "限界を超えし者(FB-04) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "限界を超えし者(FB-04) 当たりカードランキング｜孫悟空SCR★★の買取相場と封入率",
        "h1": "限界を超えし者(FB-04) 当たりカードランキング｜孫悟空SCR★★の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「限界を超えし者」(FB-04)の当たりカードランキング・買取相場・封入率を解説。1位は孫悟空SCR★★で約3.3〜5.2万円、封入率は240BOXに1枚。2位以下は4,000〜5,500円台で、トップレア1枚に価値が集中する構成です。",
        "og_title": "限界を超えし者(FB-04) 当たりカードランキング｜孫悟空SCR★★",
        "og_desc": "FB-04の当たりカード・買取相場・封入率を解説。1位は孫悟空SCR★★で約3.3〜5.2万円、240BOXに1枚。2位以下は数千円台。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「限界を超えし者」(FB-04・2024年11月8日発売)",
        "hero_label": "FB-04 トップレア",
        "hero_big": "孫悟空 SCR★★ 約3.3〜5.2万円",
        "hero_sub": "ホログラム加工のシークレットレア。封入率は240BOXに1枚。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2024年11月8日発売の <strong><a href="box/fb-04.html">ブースターパック「限界を超えし者」【FB-04】</a></strong> の当たりカードを、買取価格順に整理します。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>です。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th><th>封入率</th></tr></thead>
<tbody>
<tr><td>1位</td><td>孫悟空</td><td>SCR★★</td><td class="num">約3.3〜5.2万円</td><td>240BOXに1枚</td></tr>
<tr><td>2位</td><td>孫悟空</td><td>SCR★</td><td class="num">約4,200〜5,500円</td><td>12BOXに約1枚</td></tr>
<tr><td>3位</td><td>ベジット</td><td>SCR★</td><td class="num">約4,500〜5,000円</td><td>12BOXに約1枚</td></tr>
<tr><td>4位</td><td>孫悟空</td><td>L★</td><td class="num">約4,000〜5,500円</td><td>12BOXに約1〜2枚</td></tr>
<tr><td>5位</td><td>10倍かめはめ波</td><td>R★</td><td class="num">約3,600円</td><td>記載なし</td></tr>
</tbody>
</table>
<p>買取価格は参照する情報源・時期によって幅があるため、レンジで示しています。2位以下の順位は情報源によって前後します。</p>

<h2>トップレア1枚に集中する典型的な構成</h2>
<p>FB-04は<strong>1位の孫悟空SCR★★(約3.3〜5.2万円)と2位以下(4,000〜5,500円台)で約8〜10倍の差</strong>があります。ホログラム加工が施されたシークレットレアで、この弾の目玉です。</p>
<p>同じ構成は <a href="fb-06-atari-guide.html">FB-06</a>(1位と2位で5〜6倍差)や <a href="fb-08-atari-guide.html">FB-08</a> にも見られます。一方 <a href="fb-09-atari-guide.html">FB-09</a> や <a href="fb-10-atari-guide.html">FB-10</a> のようにSCR★★が3種あって高額帯に厚みがある弾もあり、<strong>弾によって当たりの分布が大きく違う</strong>のがフュージョンワールドの特徴です。</p>

<h2>封入率から見た開封の現実性</h2>
<p>孫悟空SCR★★の封入率は<strong>240BOXに1枚</strong>で、2つの情報源で一致しています。BOX定価{BOX_RETAIL}で240BOX分を買うと約127万円になる計算です。</p>
<p>現実的に狙えるのは12BOXに約1枚のSCR★・L★ですが、いずれも買取は4,000〜5,500円台です。BOX買取が{BOX_PRICE}であることを踏まえると、<strong>12BOX開封してこれらが1枚出ても、BOXのまま売った方が金額は上</strong>になります。</p>

<h2>売却を考えている場合</h2>
<p>シュリンク付きの未開封状態が最も高く評価されます。<a href="box/fb-04.html">FB-04の個別ページ</a>で店舗別の買取価格と価格推移を確認し、複数店を比較してから判断してください。</p>""",
        "faq": [
            {"q": "FB-04「限界を超えし者」の一番の当たりカードは何ですか?",
             "a": "孫悟空のSCR★★で、買取相場は約3.3〜5.2万円です(参照する情報源・時期により幅があります)。ホログラム加工のシークレットレアで、封入率は240BOXに1枚とされています。"},
            {"q": "FB-04は開封した方が得ですか?",
             "a": "トップレアは240BOXに1枚で現実的ではありません。12BOXに約1枚のSCR★・L★は買取4,000〜5,500円台のため、BOX買取{BOX_PRICE}と比べると、12BOX開封してもBOXのまま売った方が金額は上になります。"},
            {"q": "FB-04のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値をご確認ください。"},
        ],
    },
    {
        "slug": "fb-08-atari-guide",
        "box_slug": "fb-08",
        "box_name": 'ブースターパック「誇り高き戦闘民族」【FB-08】',
        "retail": 5280,
        "nav_label": "誇り高き戦闘民族(FB-08)",
        "crumb": "誇り高き戦闘民族(FB-08) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "誇り高き戦闘民族(FB-08) 当たりカードランキング｜孫悟天SCR★★の買取相場と封入率",
        "h1": "誇り高き戦闘民族(FB-08) 当たりカードランキング｜孫悟天SCR★★の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「誇り高き戦闘民族」(FB-08)の当たりカードランキング・買取相場・封入率を解説。1位は孫悟天SCR★★で約3.8〜5万円、封入率は240BOXに1枚。SCRパラレル・Lパラレルは12BOXに約1枚です。BOX買取価格は当サイトの実データで毎日更新しています。",
        "og_title": "誇り高き戦闘民族(FB-08) 当たりカードランキング｜孫悟天SCR★★",
        "og_desc": "FB-08の当たりカード・買取相場・封入率を解説。1位は孫悟天SCR★★で約3.8〜5万円、240BOXに1枚。上位を孫悟天が占める構成。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「誇り高き戦闘民族」(FB-08・2025年12月13日発売)",
        "hero_label": "FB-08 トップレア",
        "hero_big": "孫悟天 SCR★★ 約3.8〜5万円",
        "hero_sub": "サイヤ人がテーマの弾。封入率は240BOXに1枚。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2025年12月13日発売の <strong><a href="box/fb-08.html">ブースターパック「誇り高き戦闘民族」【FB-08】</a></strong> の当たりカードを、買取価格順に整理します。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>です。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th><th>封入率</th></tr></thead>
<tbody>
<tr><td>1位</td><td>孫悟天</td><td>SCR★★</td><td class="num">約3.8〜5万円</td><td>240BOXに1枚</td></tr>
<tr><td>2位</td><td>孫悟天</td><td>SCR★</td><td class="num">約6,000〜7,500円</td><td>12BOXに約1枚</td></tr>
<tr><td>3位</td><td>孫悟空Jr.</td><td>L★</td><td class="num">約7,000円</td><td>12BOXに約1〜2枚</td></tr>
<tr><td>4位</td><td>孫悟飯:青年期</td><td>L★</td><td class="num">約6,000円</td><td>12BOXに約1〜2枚</td></tr>
<tr><td>5位</td><td>孫悟天</td><td>SCR</td><td class="num">約4,500〜5,000円</td><td>記載なし</td></tr>
</tbody>
</table>
<p>買取価格は参照する情報源・時期によって幅があるため、レンジで示しています。情報源によってはブロリーのSCR★・L★(各約4,000円)が上位に入る場合もあります。</p>

<h2>孫悟天が上位を占める構成</h2>
<p>FB-08は<strong>上位に孫悟天のパラレル各種が並ぶ</strong>のが特徴です。1位のSCR★★が約3.8〜5万円、2位のSCR★が約6,000〜7,500円で、<strong>1位と2位の差は約6〜7倍</strong>です。</p>
<p>この「トップレア1枚に集中する」形は <a href="fb-04-atari-guide.html">FB-04</a> や <a href="fb-06-atari-guide.html">FB-06</a> と共通で、通常ブースターでは最も多いパターンです。</p>

<h2>封入率</h2>
<p>SCRスーパーパラレル(SCR★★)は<strong>240BOXに1枚</strong>、SCRパラレル・Lパラレルはいずれも<strong>12BOXに約1枚</strong>とされ、2つの情報源で一致しています。</p>
<p>12BOXに約1枚のSCR★・L★は買取6,000〜7,500円台です。BOX買取が{BOX_PRICE}であることを踏まえると、12BOX開封してこれらが1枚出ても、<strong>BOXのまま売った方が金額は上</strong>という計算になります。</p>

<h2>売却を考えている場合</h2>
<p>シュリンク付きの未開封状態が最も高く評価されます。<a href="box/fb-08.html">FB-08の個別ページ</a>で店舗別の買取価格と価格推移を確認してから判断してください。</p>""",
        "faq": [
            {"q": "FB-08「誇り高き戦闘民族」の一番の当たりカードは何ですか?",
             "a": "孫悟天のSCR★★(スーパーパラレル)で、買取相場は約3.8〜5万円です(参照する情報源・時期により幅があります)。封入率は240BOXに1枚とされています。"},
            {"q": "FB-08の封入率はどのくらいですか?",
             "a": "SCRスーパーパラレル(SCR★★)が240BOXに1枚、SCRパラレルとLパラレルがいずれも12BOXに約1枚とされており、2つの情報源で一致しています。"},
            {"q": "FB-08のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値をご確認ください。"},
        ],
    },
    {
        "slug": "fb-05-atari-guide",
        "box_slug": "fb-05",
        "box_name": 'ブースターパック「未知なる冒険」【FB-05】',
        "retail": 5280,
        "nav_label": "未知なる冒険(FB-05)",
        "crumb": "未知なる冒険(FB-05) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "未知なる冒険(FB-05) 当たりカードランキング｜孫悟空SCR★★の買取相場と封入率",
        "h1": "未知なる冒険(FB-05) 当たりカードランキング｜孫悟空SCR★★の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「未知なる冒険」(FB-05)の当たりカードランキング・買取相場・封入率を解説。1位は孫悟空SCR★★で約6〜7.8万円、2位のフリーザSCR★★も約2〜4万円。SCR★★が2種収録され、いずれも240BOXに1枚です。",
        "og_title": "未知なる冒険(FB-05) 当たりカードランキング｜孫悟空SCR★★",
        "og_desc": "FB-05の当たりカード・買取相場・封入率を解説。1位は孫悟空SCR★★で約6〜7.8万円。SCR★★が2種収録、いずれも240BOXに1枚。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「未知なる冒険」(FB-05・2025年2月8日発売)",
        "hero_label": "FB-05 トップレア",
        "hero_big": "孫悟空 SCR★★ 約6〜7.8万円",
        "hero_sub": "SCR★★が孫悟空とフリーザの2種。いずれも240BOXに1枚。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2025年2月8日発売の <strong><a href="box/fb-05.html">ブースターパック「未知なる冒険」【FB-05】</a></strong> の当たりカードを、買取価格順に整理します。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>です。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th><th>封入率</th></tr></thead>
<tbody>
<tr><td>1位</td><td>孫悟空</td><td>SCR★★</td><td class="num">約6〜7.8万円</td><td>240BOXに1枚</td></tr>
<tr><td>2位</td><td>フリーザ</td><td>SCR★★</td><td class="num">約2〜4万円</td><td>240BOXに1枚</td></tr>
<tr><td>3位</td><td>ベジット</td><td>L★</td><td class="num">約5,000〜1.2万円</td><td>12BOXに約1枚</td></tr>
<tr><td>4位</td><td>ゴジータ</td><td>L★</td><td class="num">約7,500円</td><td>12BOXに約1枚</td></tr>
<tr><td>5位</td><td>ビーデル</td><td>SR★</td><td class="num">約5,000円</td><td>2BOXに約1枚</td></tr>
</tbody>
</table>
<p>買取価格は参照する情報源・時期によって幅があるため、レンジで示しています。特に3位のベジットL★は情報源による開きが大きくなっています。</p>

<h2>SCR★★が2種｜1位と2位で2〜3倍差</h2>
<p>FB-05は<strong>孫悟空とフリーザの2種がSCR★★</strong>として収録されています。1位の孫悟空が約6〜7.8万円、2位のフリーザが約2〜4万円で、<strong>同じレアリティ・同じ封入率(240BOXに1枚)でも2〜3倍の価格差</strong>がついています。</p>
<p>レアリティと封入率が同じでも価格が揃わないのは、キャラクターの人気がそのまま需要に反映されるためです。同様の構図は <a href="sb-01-atari-guide.html">SB-01</a> のエナジーマーカー(1巻表紙が他の巻の3倍前後)にも見られます。</p>

<h2>封入率</h2>
<p>SCR★★はいずれも<strong>240BOXに1枚</strong>で、2つの情報源で一致しています。BOX定価{BOX_RETAIL}換算で約127万円分に相当し、狙って引きに行く対象ではありません。</p>
<p>この弾で目を引くのは<strong>5位のビーデルSR★が2BOXに約1枚</strong>と、比較的引きやすい確率でありながら買取約5,000円がついている点です。ただしBOX買取{BOX_PRICE}と比べると、2BOX開封して1枚出ても収支が合う水準ではありません。</p>

<h2>売却を考えている場合</h2>
<p>シュリンク付きの未開封状態が最も高く評価されます。<a href="box/fb-05.html">FB-05の個別ページ</a>で店舗別の買取価格と価格推移を確認してから判断してください。</p>""",
        "faq": [
            {"q": "FB-05「未知なる冒険」の一番の当たりカードは何ですか?",
             "a": "孫悟空のSCR★★で、買取相場は約6〜7.8万円です(参照する情報源・時期により幅があります)。2位はフリーザのSCR★★で約2〜4万円です。"},
            {"q": "孫悟空とフリーザは同じレアリティなのになぜ価格が違うのですか?",
             "a": "どちらもSCR★★で封入率も240BOXに1枚と同じですが、買取相場には2〜3倍の差があります。レアリティや封入率が同じでも、キャラクターの人気がそのまま需要に反映されるためです。"},
            {"q": "FB-05のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値をご確認ください。"},
        ],
    },
    {
        "slug": "fb-03-atari-guide",
        "box_slug": "fb-03",
        "box_name": 'ブースターパック「怒りの咆哮」【FB-03】',
        "retail": 5280,
        "nav_label": "怒りの咆哮(FB-03)",
        "crumb": "怒りの咆哮(FB-03) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "怒りの咆哮(FB-03) 当たりカードランキング｜孫悟空:GT SCR★★の買取相場",
        "h1": "怒りの咆哮(FB-03) 当たりカードランキング｜孫悟空:GT SCR★★の買取相場を解説",
        "meta_desc": "ドラゴンボールカード「怒りの咆哮」(FB-03)の当たりカードランキング・買取相場を解説。1位は孫悟空:GT SCR★★で約4〜6万円。上位を孫悟空:GTのパラレル各種が占める構成で、封入率は公表されていません。BOX買取価格は当サイトの実データで毎日更新しています。",
        "og_title": "怒りの咆哮(FB-03) 当たりカードランキング｜孫悟空:GT SCR★★",
        "og_desc": "FB-03の当たりカード・買取相場を解説。1位は孫悟空:GT SCR★★で約4〜6万円。上位を孫悟空:GTが占める構成。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「怒りの咆哮」(FB-03・2024年8月9日発売)",
        "hero_label": "FB-03 トップレア",
        "hero_big": "孫悟空:GT SCR★★ 約4〜6万円",
        "hero_sub": "全143種中20種にパラレルが存在する弾。上位を孫悟空:GTのパラレル各種が占めます。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2024年8月9日発売の <strong><a href="box/fb-03.html">ブースターパック「怒りの咆哮」【FB-03】</a></strong> の当たりカードを、買取価格順に整理します。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>です。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th></tr></thead>
<tbody>
<tr><td>1位</td><td>孫悟空:GT</td><td>SCR★★</td><td class="num">約4〜6万円</td></tr>
<tr><td>2位</td><td>孫悟空:GT</td><td>L★</td><td class="num">約5,000〜6,000円</td></tr>
<tr><td>3位</td><td>孫悟空:GT</td><td>SCR★</td><td class="num">約4,200〜5,000円</td></tr>
<tr><td>4位</td><td>孫悟空</td><td>L★</td><td class="num">約3,000円</td></tr>
<tr><td>5位</td><td>孫悟空:GT</td><td>SCR</td><td class="num">約2,700円</td></tr>
</tbody>
</table>
<p>買取価格は参照する情報源・時期によって幅があるため、レンジで示しています。上位5枚のうち4枚が<strong>孫悟空:GT</strong>のバージョン違いという構成です。</p>

<h2>発売直後から相場が下がった弾</h2>
<p>FB-03は<strong>発売直後に高値をつけ、その後下落した</strong>推移が報告されています。あるフリマ相場の調査では、孫悟空:GT SCR★★が発売日時点で約10.6万円、同年11月時点で約4万円と記録されています。</p>
<div class="callout"><strong>参照データの性質にご注意ください</strong>：上記の推移は<strong>フリマアプリの取引価格</strong>を参照したもので、買取価格とは異なる指標です。当サイトが掲載しているのは各店の<strong>買取価格</strong>なので、両者を直接比較することはできません。あくまで「発売直後から時間が経つと水準が変わり得る」ことの参考としてご覧ください。</div>
<p>発売から時間が経った弾の現在の買取水準は、<a href="box/fb-03.html">FB-03の個別ページ</a>の価格推移グラフで確認できます。</p>

<h2>封入率は公表されていません</h2>
<p>FB-03については、参照した情報源のいずれにも<strong>レアリティ別の封入率が記載されていません</strong>。フュージョンワールドの他弾ではSCR★★が240BOXに1枚とされるケースが多いものの、FB-03に同じ数字が当てはまるという確認は取れていないため、本記事では推測を書かない方針としています。</p>
<p>封入率が確認できている弾については <a href="fb-04-atari-guide.html">FB-04</a>・<a href="fb-05-atari-guide.html">FB-05</a>・<a href="fb-08-atari-guide.html">FB-08</a> の各記事で解説しています。</p>

<h2>売却を考えている場合</h2>
<p>シュリンク付きの未開封状態が最も高く評価されます。<a href="box/fb-03.html">FB-03の個別ページ</a>で店舗別の買取価格を比較してから判断してください。</p>""",
        "faq": [
            {"q": "FB-03「怒りの咆哮」の一番の当たりカードは何ですか?",
             "a": "孫悟空:GT の SCR★★で、買取相場は約4〜6万円です(参照する情報源・時期により幅があります)。上位5枚のうち4枚が孫悟空:GTのバージョン違いで占められています。"},
            {"q": "FB-03の封入率はどのくらいですか?",
             "a": "参照した情報源のいずれにもレアリティ別の封入率の記載がなく、確認が取れていません。フュージョンワールドの他弾ではSCR★★が240BOXに1枚とされるケースが多いものの、FB-03に同じ数字が当てはまるとは限らないため、当サイトでは推測を掲載していません。"},
            {"q": "FB-03の相場は下がったのですか?",
             "a": "フリマアプリの取引価格を参照した調査では、孫悟空:GT SCR★★が発売日時点で約10.6万円、同年11月時点で約4万円と記録されています。ただしこれは買取価格とは異なる指標なので直接の比較はできません。現在の買取水準は当サイトの個別ページで確認できます。"},
            {"q": "FB-03のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値をご確認ください。"},
        ],
    },
    {
        "slug": "fb-01-atari-guide",
        "box_slug": "fb-01",
        "box_name": 'ブースターパック「覚醒の鼓動」【FB-01】',
        "retail": 5280,
        "nav_label": "覚醒の鼓動(FB-01)",
        "crumb": "覚醒の鼓動(FB-01) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "覚醒の鼓動(FB-01) 当たりカードランキング｜孫悟空SCR★★の買取相場と封入率",
        "h1": "覚醒の鼓動(FB-01) 当たりカードランキング｜孫悟空SCR★★の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「覚醒の鼓動」(FB-01)の当たりカードランキング・買取相場・封入率を解説。1位は孫悟空SCR★★で約10〜15万円と全弾でも高額帯ですが、BOX買取は定価の1.4倍前後。トップレアが高額でもBOXが高いとは限らない理由を実データで整理しています。",
        "og_title": "覚醒の鼓動(FB-01) 当たりカードランキング｜孫悟空SCR★★",
        "og_desc": "FB-01の当たりカード・買取相場・封入率を解説。1位は孫悟空SCR★★で約10〜15万円。トップレアが高額でもBOX買取は定価の1.4倍前後という構造。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「覚醒の鼓動」(FB-01・2024年2月16日発売)",
        "hero_label": "FB-01 トップレア",
        "hero_big": "孫悟空 SCR★★ 約10〜15万円",
        "hero_sub": "シリーズ第1弾。トップレアは高額帯ですが、BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})にとどまります。",
        "body": """<p>2024年2月16日発売の <strong><a href="box/fb-01.html">ブースターパック「覚醒の鼓動」【FB-01】</a></strong> は、フュージョンワールドのシリーズ第1弾です。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>となっています。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th><th>封入率</th></tr></thead>
<tbody>
<tr><td>1位</td><td>孫悟空</td><td>SCR★★</td><td class="num">約10〜15万円</td><td>約10〜20カートン<br>(120〜240BOX)に1枚</td></tr>
<tr><td>2位</td><td>孫悟飯:少年期</td><td>SCR★</td><td class="num">約1〜1.6万円</td><td>1カートンに0〜2枚</td></tr>
<tr><td>3位</td><td>孫悟空</td><td>SCR★</td><td class="num">約8,500〜1.5万円</td><td>1カートンに0〜1枚</td></tr>
<tr><td>4位</td><td>孫悟飯:少年期</td><td>L★</td><td class="num">約7,000〜1.3万円</td><td>記載なし</td></tr>
<tr><td>5位</td><td>ゴクウブラック</td><td>L★</td><td class="num">約6,500〜1.2万円</td><td>記載なし</td></tr>
</tbody>
</table>
<p>買取価格は参照する情報源・時期によって幅があるため、レンジで示しています。</p>

<h2>トップレアが高額でもBOXが高いとは限らない</h2>
<p>FB-01で最も注目すべきは、<strong>トップレアが約10〜15万円と高額帯にありながら、BOX買取は{BOX_PRICE}({BOX_RATIO})にとどまっている</strong>点です。当サイト掲載のドラゴンボールBOXで最も高い <a href="sb-01-atari-guide.html">SB-01</a> が定価の20倍前後であることと比べると、水準が大きく違います。</p>
<div class="callout"><strong>なぜ差がつくのか</strong>：カード1枚の価格とBOXの価格は連動しません。BOX価格に効くのは<strong>「1BOXあたりで期待できる金額」</strong>です。FB-01のトップレアは約120〜240BOXに1枚なので、15万円としても1BOXあたりの期待値は600〜1,250円程度にしかなりません。2位以下も1カートン(12BOX)単位の封入で1万円前後です。</div>
<p>加えてFB-01はシリーズ第1弾で発売から時間が経っており、流通量も他弾と条件が異なります。当サイトのデータだけで理由を断定することはできませんが、<strong>「トップレアが高い弾＝BOXが高い弾」ではない</strong>ことは実データから読み取れます。</p>

<h2>2位以下は現実的な確率で狙える帯</h2>
<p>2位の孫悟飯:少年期SCR★は1カートン(12BOX)に0〜2枚、3位の孫悟空SCR★は0〜1枚とされ、買取は8,500円〜1.6万円です。BOX買取が{BOX_PRICE}であることを踏まえると、<strong>12BOX開封してこれらが複数枚出れば収支が合う可能性はあります</strong>が、0枚の場合もある確率なので確実ではありません。</p>

<h2>売却を考えている場合</h2>
<p>シュリンク付きの未開封状態が最も高く評価されます。<a href="box/fb-01.html">FB-01の個別ページ</a>で店舗別の買取価格と価格推移を確認してから判断してください。</p>""",
        "faq": [
            {"q": "FB-01「覚醒の鼓動」の一番の当たりカードは何ですか?",
             "a": "孫悟空のSCR★★で、買取相場は約10〜15万円です(参照する情報源・時期により幅があります)。封入率は約10〜20カートン(120〜240BOX)に1枚とされています。"},
            {"q": "トップレアが10万円を超えるのに、なぜBOX買取は安いのですか?",
             "a": "カード1枚の価格とBOX価格は連動しないためです。BOX価格に効くのは1BOXあたりで期待できる金額で、FB-01のトップレアは約120〜240BOXに1枚のため、15万円としても1BOXあたりの期待値は600〜1,250円程度にとどまります。加えて第1弾で発売から時間が経っており流通量の条件も他弾と異なります。"},
            {"q": "FB-01のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値をご確認ください。"},
        ],
    },
    {
        "slug": "fb-02-atari-guide",
        "box_slug": "fb-02",
        "box_name": 'ブースターパック「烈火の闘気」【FB-02】',
        "retail": 5280,
        "nav_label": "烈火の闘気(FB-02)",
        "crumb": "烈火の闘気(FB-02) 当たりカードランキング",
        "date": "2026-08-27",
        "title": "烈火の闘気(FB-02) 当たりカードランキング｜ベジットSCR★★の買取相場",
        "h1": "烈火の闘気(FB-02) 当たりカードランキング｜ベジットSCR★★の買取相場を解説",
        "meta_desc": "ドラゴンボールカード「烈火の闘気」(FB-02)の当たりカードランキング・買取相場を解説。1位はベジットSCR★★で約5万円、2位以下は数千円台と差が大きい構成です。封入率は各社とも独自調査値で公式発表がない点も含めて整理しています。",
        "og_title": "烈火の闘気(FB-02) 当たりカードランキング｜ベジットSCR★★",
        "og_desc": "FB-02の当たりカード・買取相場を解説。1位はベジットSCR★★で約5万円。2位以下は数千円台で差が大きい構成。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「烈火の闘気」(FB-02・2024年5月10日発売)",
        "hero_label": "FB-02 トップレア",
        "hero_big": "ベジット SCR★★ 約5万円",
        "hero_sub": "シリーズ第2弾。2位以下は数千円台で、1位との差が大きい構成です。BOX買取は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})です。",
        "body": """<p>2024年5月10日発売の <strong><a href="box/fb-02.html">ブースターパック「烈火の闘気」【FB-02】</a></strong> の当たりカードを、買取価格順に整理します。当サイトの実データでは<strong>BOX買取価格は{BOX_PRICE}(定価{BOX_RETAIL}の{BOX_RATIO})</strong>です。</p>

<h2>当たりカードランキング TOP5</h2>
<table class="tbl">
<thead><tr><th>順位</th><th>カード名</th><th>レアリティ</th><th>買取相場</th></tr></thead>
<tbody>
<tr><td>1位</td><td>ベジット</td><td>SCR★★</td><td class="num">約5万円</td></tr>
<tr><td>2位</td><td>ギガンティックミーティア</td><td>C★</td><td class="num">約4,500〜7,000円</td></tr>
<tr><td>3位</td><td>ベジット</td><td>SCR★</td><td class="num">約4,200円</td></tr>
<tr><td>4位</td><td>ベジット</td><td>SCR</td><td class="num">約2,800円</td></tr>
<tr><td>5位</td><td>ファイナルホープスラッシュ</td><td>R★</td><td class="num">約1,600円</td></tr>
</tbody>
</table>
<p>買取価格は参照する情報源・時期によって幅があるため、レンジで示しています。</p>

<h2>ベジット一枚勝ちの構成</h2>
<p>FB-02は<strong>1位のベジットSCR★★(約5万円)と2位以下(数千円台)で7〜10倍の差</strong>があります。上位にはベジットのパラレル各種が並び、この弾の看板カードであることがわかります。</p>
<p>2位に<strong>「ギガンティックミーティア」というイベントカード</strong>が入っているのが特徴です。フュージョンワールドではキャラクターカード以外も高値がつくことがあり、同様の例は <a href="fb-04-atari-guide.html">FB-04</a> の「10倍かめはめ波」(R★・約3,600円)にも見られます。</p>

<h2>封入率は公式発表がありません</h2>
<p>FB-02の封入率について、参照した情報源には<strong>「独自調査であり封入率を保証するものではない」との注記付きの数値</strong>しかなく、公式発表された数値は確認できませんでした。そのため本記事では具体的な封入率を掲載していません。</p>
<p>封入率が複数ソースで一致している弾については <a href="fb-04-atari-guide.html">FB-04</a>・<a href="fb-05-atari-guide.html">FB-05</a>・<a href="fb-08-atari-guide.html">FB-08</a>(いずれもSCR★★が240BOXに1枚)の各記事で解説しています。</p>

<h2>初期弾のBOX相場について</h2>
<p>FB-02のBOX買取は{BOX_PRICE}({BOX_RATIO})で、<a href="fb-01-atari-guide.html">FB-01</a>と並んで当サイト掲載のドラゴンボールBOXでは低い水準にあります。トップレアが約5万円であることを考えると意外に見えますが、<strong>カード1枚の価格とBOX価格は連動しません</strong>。BOX価格に効くのは1BOXあたりで期待できる金額で、トップレアの封入率が低ければBOX価格には反映されにくくなります。</p>

<h2>売却を考えている場合</h2>
<p>シュリンク付きの未開封状態が最も高く評価されます。<a href="box/fb-02.html">FB-02の個別ページ</a>で店舗別の買取価格を比較してから判断してください。</p>""",
        "faq": [
            {"q": "FB-02「烈火の闘気」の一番の当たりカードは何ですか?",
             "a": "ベジットのSCR★★で、買取相場は約5万円です(参照する情報源・時期により幅があります)。2位以下は数千円台で、1位とは7〜10倍の差があります。"},
            {"q": "FB-02の封入率はどのくらいですか?",
             "a": "参照した情報源には「独自調査であり封入率を保証するものではない」との注記付きの数値しかなく、公式発表された数値は確認できませんでした。そのため当サイトでは具体的な封入率を掲載していません。"},
            {"q": "FB-02のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。トップレアが約5万円である一方でBOX買取が低めなのは、カード1枚の価格とBOX価格が連動しないためです。"},
        ],
    },
    {
        # 発売前の仕込み。9/12発売後に当たりカードの買取相場を入れて draft を外す。
        # 埋める箇所: TOP5の表(カード名・レアリティ・買取相場)、封入率、hero_big、meta_desc の金額
        "draft": True,
        "slug": "fb-11-atari-guide",
        "box_slug": "fb-11",
        "box_name": 'ブースターパック「BRIGHTNESS OF HOPE」【FB-11】',
        "retail": 5760,
        "nav_label": "BRIGHTNESS OF HOPE(FB-11)",
        "crumb": "BRIGHTNESS OF HOPE(FB-11) 当たりカードランキング",
        "date": "2026-09-12",
        "title": "BRIGHTNESS OF HOPE(FB-11) 当たりカードランキング｜SCR3種の買取相場と封入率",
        "h1": "BRIGHTNESS OF HOPE(FB-11) 当たりカードランキング｜SCR3種の買取相場・封入率を解説",
        "meta_desc": "ドラゴンボールカード「BRIGHTNESS OF HOPE」(FB-11)の当たりカードランキング・買取相場・封入率を解説。SCRは孫悟空・シャレット・バーダックの3種。この弾から1パック240円・BOX5,760円に改定されています。BOX買取価格は当サイトが4店舗から毎日収集した実データで更新しています。",
        "og_title": "BRIGHTNESS OF HOPE(FB-11) 当たりカードランキング",
        "og_desc": "FB-11の当たりカードと買取相場を実データで解説。SCRは孫悟空・シャレット・バーダックの3種。BOX定価は5,760円。",
        "meta_line": "ドラゴンボールスーパーカードゲーム フュージョンワールド ブースターパック「BRIGHTNESS OF HOPE」(FB-11・2026年9月12日発売)",
        "hero_label": "FB-11 当たりカード",
        "hero_big": "BOX買取 {BOX_PRICE}",
        "hero_sub": "2026年9月12日発売。SCRは孫悟空・シャレット・バーダックの3種で、全123種＋パラレル構成です。BOX買取価格は当サイトが4店舗から毎日収集しています。",
        "body": """<p>2026年9月12日に発売されたドラゴンボールスーパーカードゲーム フュージョンワールドのブースターパック第11弾 <strong>「BRIGHTNESS OF HOPE」【FB-11】</strong> の当たりカードと買取相場をまとめます。BOXの買取価格は <a href="/dragonball">ドラゴンボールBOX買取価格比較トップ</a> で毎日更新しています。</p>

<h2>当たりカードランキング TOP5</h2>
<p>※発売直後は各店の買取価格が出そろっていないため、価格が固まった段階で掲載します。</p>

<h2>レアリティ構成</h2>
<p>全123種の内訳はSCR3種・リーダーカード5種・SR15種・R25種・UC35種・C40種です。これに加えてスーパーパラレル・パラレル・ビジュアルパラレル・スーパーコンボパラレルの各仕様が封入されます。</p>

<h2>この弾から定価が変わっています</h2>
<p>FB-11から1パックが220円→240円に改定され、BOX定価は5,280円→5,760円になりました。<strong>定価比で過去弾と比較する場合は基準が変わる</strong>点に注意してください。詳しくは <a href="hatsubai-schedule.html">新弾発売スケジュール</a> にまとめています。</p>

<h2>封入率について</h2>
<p>封入率は公式から公表されていません。情報源によって数値に開きがあるため、当サイトでは断定していません。</p>

<h2>売却を考えている場合</h2>
<p>BOXの買取価格は店舗によって差が出ます。当サイトは4店舗の価格を毎日収集しているので、<a href="/dragonball">比較トップ</a>で最高値の店舗を確認できます。</p>""",
        "faq": [
            {"q": "FB-11「BRIGHTNESS OF HOPE」の当たりカードは何ですか?",
             "a": "シークレットレア(SCR)は孫悟空(FB11-121)・シャレット(FB11-122)・バーダック(FB11-123)の3種です。買取相場は各店の価格が出そろい次第、当サイトの実データで掲載します。"},
            {"q": "FB-11のBOX定価はいくらですか?",
             "a": "1パック240円(税込・カード6枚＋デジタル版連動コード1枚)、1BOX24パック入りで5,760円(税込)です。FB-10までは1パック220円・BOX5,280円でした。"},
            {"q": "FB-11のレアリティ構成はどうなっていますか?",
             "a": "全123種の内訳はSCR3種・リーダーカード5種・SR15種・R25種・UC35種・C40種です。これに加えてパラレル版が封入されます。"},
            {"q": "FB-11のBOX買取価格はいくらですか?",
             "a": "当サイトが4店舗から収集している実データでは{BOX_PRICE}です(定価{BOX_RETAIL}の{BOX_RATIO})。相場は日々変動するため、個別ページで最新値をご確認ください。"},
        ],
    },
]


def _nav_links(current_slug: str) -> str:
    def _items(arts):
        out = []
        for h in arts:
            if h.get("draft"):
                continue
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


def _set_code(name: str) -> str:
    """商品名から弾コードを取り出す。スーパーダイバーズなど無い商品は空文字。"""
    if "【" in name and "】" in name:
        return name.split("【")[1].split("】")[0]
    return ""


def _ranking_rows() -> list:
    """(商品名, 弾コード, 定価, 最高買取, 定価比) を買取の高い順に返す。"""
    from scraper.products_dragonball import DRAGONBALL_PRODUCTS
    retail = {p.name: p.retail_price for p in DRAGONBALL_PRODUCTS}
    rows = []
    for name, price in _box_max_prices().items():
        r = retail.get(name, 0)
        rows.append((name, _set_code(name), r, price, price / r if r else 0))
    rows.sort(key=lambda x: x[3], reverse=True)
    return rows


def _ranking_table(rows: list) -> str:
    body = ""
    for i, (name, code, r, price, mult) in enumerate(rows, 1):
        slug = code.lower()
        label = _esc(name)
        if slug and (OUT_DIR / f"{slug}-atari-guide.html").exists():
            label = f'<a href="{slug}-atari-guide.html">{label}</a>'
        cls = ' class="best"' if i == 1 else ""
        mult_txt = f"{mult:.1f}倍" if mult else "—"
        retail_txt = f"¥{r:,}" if r else "—"
        body += (f'<tr{cls}><td>{i}位</td><td>{label}</td>'
                 f'<td class="price">{retail_txt}</td>'
                 f'<td class="price">¥{price:,}</td>'
                 f'<td class="price">{mult_txt}</td></tr>')
    return ('<table class="tbl"><thead><tr><th>順位</th><th>商品</th>'
            '<th class="price">定価</th><th class="price">最高買取</th>'
            '<th class="price">定価比</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def _subst_ranking(text: str) -> str:
    """高額ランキング記事のプレースホルダを当サイト実データで埋める。"""
    rows = _ranking_rows()
    if not rows:
        return text
    text = text.replace("{{DB_RANKING}}", _ranking_table(rows))
    text = text.replace("{{DB_COUNT}}", str(len(rows)))
    for i in range(1, 6):
        if i > len(rows):
            break
        name, code, r, price, mult = rows[i - 1]
        short = name.split("「")[-1].split("」")[0] if "「" in name else name
        text = text.replace("{{TOP%d_NAME}}" % i, short)
        text = text.replace("{{TOP%d_CODE}}" % i, code)
        text = text.replace("{{TOP%d_PRICE}}" % i, f"¥{price:,}")
        text = text.replace("{{TOP%d_MULT}}" % i, f"定価の{mult:.1f}倍" if mult else "—")
    return text


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
        if _a["slug"] != h["slug"] and not _a.get("draft"):
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
        art = dict(h)
        for key in ("body", "hero_big", "hero_sub", "meta_desc", "og_desc"):
            if key in art:
                art[key] = _subst_ranking(art[key])
        art["faq"] = [{"q": f["q"], "a": _subst_ranking(f["a"])} for f in h["faq"]]
        path = OUT_DIR / f"{h['slug']}.html"
        path.write_text(_render_howto(art), encoding="utf-8")
        print(f"wrote dragonball/{h['slug']}.html")

    box_prices = _box_max_prices()
    for a in ATARI_ARTICLES:
        # draft は発売前の仕込み。相場を入れてフラグを外すまで生成しない
        if a.get("draft"):
            print(f"skip dragonball/{a['slug']}.html (draft)")
            continue
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
