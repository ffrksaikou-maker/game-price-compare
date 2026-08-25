"""ワンピBOX掘り下げ記事(onepiece/{slug}-atari-guide.html)を生成する。

ポケカ atari-guide 型を赤テーマで踏襲した静的記事を、共通ボイラープレート
(head/style/nav/footer/アフィ2点)＋弾別データから生成する。BOX買取価格は
data/history_op の当サイト実データを参照(記事内のBOX価格は自動更新)。
カード相場は CARD_ASOF 時点の altema(カードラッシュ買取)実測値(免責明記)。
更新時は article_data_onepiece.py の ranking を差し替え、CARD_ASOF / CARD_ASOF_ISO を更新する。

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
.article-nav-more{display:block;margin-top:12px;padding:8px 12px;font-size:12px;font-weight:700;text-align:center;color:var(--accent);background:#f9fafb;border:1px solid var(--border);border-radius:8px;text-decoration:none}
.article-nav-more:hover{border-color:var(--accent)}
@media(max-width:1023px){.content-layout{flex-direction:column;align-items:stretch}.article-nav{order:2;width:auto;position:static;max-height:none;overflow-y:visible;margin-top:24px;padding-top:16px;border-top:1px solid var(--border)}.article-nav a{font-size:13px;padding:8px 0 8px 12px}}
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


# ===== ハウツー記事(onepiece/{slug}.html・atari接尾辞なし) =====
# 弾別 atari-guide とは別枠の「買取ガイド」記事。body は .format() せず直接埋め込む
# ため、リテラルの波括弧を自由に使ってよい。faq から可視FAQ+FAQPage JSON-LDを生成。
CARD_ASOF = "2026年8月24日"
CARD_ASOF_ISO = "2026-08-24"
# altema未掲載などで基準日が異なる弾だけ個別指定
CARD_ASOF_OVERRIDE = {"op-17": "2026年8月22日(発売初日)"}

HOWTO_ARTICLES = [
    {
        "slug": "kaitori-hikaku",
        "nav_label": "ワンピBOX買取比較ガイド",
        "crumb": "ワンピBOX買取比較ガイド",
        "title": "ワンピBOX買取比較ガイド｜最大9店舗の実データで高く売るコツと店舗の選び方",
        "h1": "ワンピBOX買取比較ガイド｜未開封BOXを最大9店舗の実データで高く売るコツと店舗の選び方",
        "meta_desc": "ワンピースカードの未開封BOXを高く売るための店舗比較・売り方ガイド。シュリンクや外箱状態などの査定ポイント、最大9店舗を毎日自動比較する当サイトの使い方、高く売る5つのコツ、今買取が高い傾向のBOXまで実データ視点で解説。",
        "og_title": "ワンピBOX買取比較ガイド｜最大9店舗の実データで高く売るコツ",
        "og_desc": "ワンピースカードの未開封BOXを高く売る店舗比較・売り方ガイド。シュリンク・外箱の査定ポイント、最大9店舗比較の使い方、高く売る5つのコツを実データ視点で解説。",
        "meta_line": "ワンピBOX買取の基礎知識・店舗比較・高く売るコツ",
        "hero_label": "ワンピBOX買取比較ガイド",
        "hero_big": "最大9店舗を毎日自動比較",
        "hero_sub": "シュリンク維持・複数店比較・売却タイミングの見極めで、ワンピースカードの未開封BOXをできるだけ高く売るための実践ガイド。相場は当サイトの実データで毎日チェックできます。",
        "body": """<p>ワンピースカードゲームの未開封BOXは、弾(タイトル)によって買取価格が大きく異なり、<strong>同じ弾でも店舗ごとに数百円〜数千円の差</strong>が出ることが珍しくありません。せっかく売るなら、少しでも高い店で・良いタイミングで手放したいところです。本記事では、<strong>ワンピBOXをできるだけ高く売るための店舗比較・売り方のコツ</strong>を、当サイトが最大9店舗から毎日自動収集している買取価格データの視点で整理します。「どこで売れば一番高いのか」「今売るべきか」を判断する材料としてご活用ください。最新の店舗別買取価格は <a href="/onepiece">ワンピBOX買取価格比較トップ</a> で毎日更新しています。</p>

<h2>ワンピBOX買取の基礎｜査定で見られるポイント</h2>
<p>未開封BOXの買取価格は「弾ごとの相場」だけでなく、<strong>個々のBOXの状態</strong>によっても上下します。まずは査定でチェックされる基本ポイントを押さえましょう。</p>
<h3>シュリンク(外装フィルム)の有無</h3>
<p>最も重要なのが<strong>シュリンク(BOX全体を包む透明フィルム)</strong>の有無です。シュリンク付きは「未開封・すり替えなしの証明」として扱われ、多くの店で買取価格が最も高くなります。シュリンクを剥がしてしまうと、たとえパックを開けていなくても「シュリンクなし」区分となり、査定額が下がるのが一般的です。売却を視野に入れているなら、シュリンクは剥がさないでおくのが鉄則です。</p>
<h3>外箱(BOX)の状態</h3>
<p>外箱の<strong>潰れ・角のつぶれ・スレ・日焼け</strong>なども査定に影響します。特に高額弾ほど状態の影響が出やすいため、保管時は重い物を上に置かない・直射日光を避けるなどの配慮が有効です。輸送中の潰れを防ぐため、発送買取では緩衝材でしっかり梱包しましょう。</p>
<h3>付属品・封入形態</h3>
<p>カートン(BOXが複数入った輸送箱)単位で売る場合は<strong>カートン未開封</strong>がより高評価になることがあります。また、店舗によっては「初回生産版」「再販版」などの区別や、同梱プロモの有無を見る場合もあります。基本的には<strong>買った状態のまま手を加えず保管する</strong>のが最も無難です。</p>

<h2>当サイトの強み｜最大9店舗を毎日自動比較</h2>
<p>当サイト「ワンピ買取チェッカー」は、ワンピースカードのBOX買取に対応した<strong>最大9店舗</strong>の買取価格を毎日自動で収集し、弾ごとに横断比較できるようにしています。1店舗ずつ公式サイトを見て回る必要がなく、<strong>「今どの店が一番高いか」を一目で確認</strong>できるのが最大の強みです。</p>
<ul>
<li><strong>毎日自動更新</strong>: 各店の買取ページから最新価格を自動取得し、日々の値動きを反映します。</li>
<li><strong>弾別に横断比較</strong>: OP-01〜最新弾・EB・PRB・スタートデッキまで、弾ごとに全店の価格を並べて比較できます。</li>
<li><strong>値動きも追える</strong>: <a href="weekly.html">週間値動きランキング</a>で、直近7日間で値上がり・値下がりしたBOXを毎日チェックできます。</li>
</ul>
<p>相場は日々変動するため、売る直前に最新の比較データを確認するのが失敗しないコツです。具体的な金額は断定せず、<strong>当サイトの最大9店舗比較の実データで最新値を確認</strong>してから判断してください。</p>

<h2>ワンピBOXを高く売る5つのコツ</h2>
<h3>1. 複数店舗を必ず比較する</h3>
<p>同じBOXでも店舗によって買取価格は異なります。1店舗だけで決めず、<strong>複数店を比較</strong>するだけで数百円〜数千円、高額弾なら万単位で差が出ることもあります。当サイトの比較トップで全店の価格を並べて、最高値の店を選びましょう。</p>
<h3>2. 相場の良いタイミングを狙う</h3>
<p>BOX相場は<strong>新弾発売前後・再販・話題化</strong>などで動きます。発売直後は品薄で高騰しやすく、供給が安定すると落ち着く傾向があります。急いで売る必要がなければ、<a href="weekly.html">週間値動きランキング</a>で上昇局面かどうかを見てからの売却が有利です。</p>
<h3>3. シュリンク・外箱をきれいに保つ</h3>
<p>前述の通り、<strong>シュリンク付き・外箱美品</strong>は査定で有利です。売る可能性があるBOXは、シュリンクを剥がさず、潰れ・日焼けを避けて保管しましょう。ちょっとした状態の差が最終的な買取額を左右します。</p>
<h3>4. まとめ売りを活用する</h3>
<p>複数BOXやカートン単位で売る場合、<strong>まとめ売りで買取額がアップする</strong>キャンペーンを行う店舗もあります。同じ弾を複数持っているなら、まとめ査定の条件を確認してみましょう。ただし1点ずつ別の店の方が高いケースもあるため、比較は忘れずに。</p>
<h3>5. こまめに相場をチェックする</h3>
<p>相場は生き物です。「先週より上がっている/下がっている」を把握しておくと、売り時を逃しません。当サイトは毎日自動更新のため、<strong>ブックマークして定期的にチェック</strong>するだけで相場の流れがつかめます。</p>

<h2>今、買取が高い傾向のワンピBOX</h2>
<p>ワンピースカードの中でも、特に高額で取引されやすい傾向のある弾を紹介します。金額は需給で日々変動するため、必ず<strong>当サイトの最大9店舗比較の実データで最新値を確認</strong>してください(下記は各弾の看板カードや傾向であり、BOX買取価格の断定ではありません)。</p>
<ul>
<li><strong><a href="op-13-atari-guide.html">受け継がれる意志(OP-13)</a></strong> — ルフィ・エース・サボの「レッドスーパーパラレル(レッドコミパラ)」を擁する3周年記念弾。看板カードが超高額で、BOX需要も高い傾向です。</li>
<li><strong><a href="op-15-atari-guide.html">神の島の冒険(OP-15)</a></strong> — 空の神「エネル」のコミックパラレルが看板のスカイピア編テーマ弾。</li>
<li><strong><a href="op-16-atari-guide.html">決戦の刻(OP-16)</a></strong> — 海軍大将トリオのコミパラと日本版初のトレジャーレアが話題の最新弾。</li>
<li><strong><a href="op-09-atari-guide.html">新たなる皇帝(OP-09)</a></strong> — 海賊王ロジャーの初ゴールドコミパラを擁する2周年記念の豪華弾。</li>
<li><strong><a href="op-05-atari-guide.html">新時代の主役(OP-05)</a></strong> — ルフィ「ギア5(ニカ)」コミパラを象徴とする人気弾。</li>
<li><strong><a href="op-11-atari-guide.html">神速の拳(OP-11)</a></strong> — ルフィ3周年スペシャル(金/銀)の超低封入が相場を牽引した弾。</li>
</ul>
<p>各弾の当たりカード・封入率・相場の目安は、上記リンク先の弾別ガイドで詳しく解説しています。BOXそのものの店舗別買取価格は <a href="/onepiece">比較トップ</a> から各BOXの個別ページで確認できます。</p>

<h2>買取店の選び方</h2>
<p>「一番高い店」を選ぶのが基本ですが、価格以外にも次の点を確認すると失敗しにくくなります。</p>
<ul>
<li><strong>買取価格の高さ</strong>: まずは当サイトで全店比較し、最高値の店を候補に。</li>
<li><strong>買取方法</strong>: 店頭・宅配(発送)・出張など。宅配は送料・振込手数料の負担有無を確認しましょう。</li>
<li><strong>入金スピード</strong>: 査定後すぐ振り込む店ほど相場変動リスクが小さくなります。</li>
<li><strong>状態の減額基準</strong>: シュリンクなし・外箱ダメージの減額幅は店により差があります。</li>
<li><strong>キャンペーン</strong>: まとめ売り・買取アップなどの条件が上乗せになる場合があります。</li>
</ul>
<p>当サイトは各店のワンピBOX買取ページへ直接リンクしているため、<strong>比較 → 最高値の店へ移動 → 条件確認</strong>という流れをスムーズに進められます。</p>""",
        "faq": [
            {"q": "ワンピBOXはどこで売るのが一番高いですか？",
             "a": "弾やタイミングによって最高値の店舗は変わります。当サイトはワンピBOX買取に対応した最大9店舗の価格を毎日自動比較しているため、<a href=\"/onepiece\">比較トップ</a>で売りたい弾の最新価格を並べて、その時点で最も高い店を選ぶのが確実です。"},
            {"q": "シュリンクを剥がしてしまうと買取価格は下がりますか？",
             "a": "一般的に下がります。シュリンク付きは未開封・すり替えなしの証明として扱われ最も高値になりやすく、シュリンクなしは区分が変わって減額されるのが通例です。売却を考えているBOXはシュリンクを剥がさず保管するのが鉄則です。"},
            {"q": "いつ売るのが得ですか？",
             "a": "相場は新弾発売前後・再販・話題化などで動きます。急ぎでなければ、当サイトの週間値動きランキングで上昇局面かどうかを確認してから売却するのが有利です。相場は毎日変動するため、売る直前の最新比較データの確認をおすすめします。"},
            {"q": "外箱に傷や潰れがあると売れませんか？",
             "a": "売れないわけではありませんが、外箱の潰れ・スレ・日焼けは査定に影響し減額されることがあります。減額幅は店舗により差があるため、状態が気になる場合は複数店の基準を比較するとよいでしょう。"},
            {"q": "この比較サイトの価格はどのくらいの頻度で更新されますか？",
             "a": "毎日自動で各店の買取ページから最新価格を取得して更新しています。値動きは週間値動きランキングでも確認できます。表示金額は目安のため、実際の売却時は各店の公式ページで最終価格をご確認ください。"},
        ],
    },
    {
        "slug": "toushi",
        "nav_label": "ワンピBOX投資の始め方",
        "crumb": "ワンピBOX投資の始め方",
        "title": "ワンピカードBOX投資の始め方｜値上がりしやすいBOXの特徴・予算別の買い方・保管・リスクを実データで解説",
        "h1": "ワンピカードBOX投資の始め方｜値上がりしやすいBOXの特徴・予算別の始め方・保管方法・リスクを実データで解説",
        "meta_desc": "ワンピースカードの未開封BOX投資の始め方を初心者向けに解説。なぜBOXが値上がりするのかの基礎、値上がりしやすいBOXの特徴、予算別の始め方、シュリンク・湿度・日光を避ける保管方法、再販や相場変動などのリスクと注意点、今狙い目の高額弾までを最大9店舗比較の実データ視点で整理します。",
        "og_title": "ワンピカードBOX投資の始め方｜値上がりBOXの特徴・予算別・保管・リスク",
        "og_desc": "ワンピBOX投資の始め方を初心者向けに解説。値上がりしやすいBOXの特徴、予算別の始め方、シュリンク・湿度・日光を避ける保管、再販・相場変動のリスクを最大9店舗比較の実データ視点で整理。",
        "meta_line": "ワンピBOX投資の基礎・値上がりBOXの特徴・予算別の始め方・保管・リスク",
        "hero_label": "ワンピカードBOX投資の始め方",
        "hero_big": "基礎・銘柄選び・保管・リスクを網羅",
        "hero_sub": "なぜBOXが値上がりするのかの基礎から、値上がりしやすいBOXの特徴・予算別の始め方・正しい保管・再販や相場変動のリスクまでを初心者向けに整理。相場は断定せず、当サイトの最大9店舗比較の実データで最新値を確認しながら判断できます。",
        "body": """<p>ワンピースカードゲームの未開封BOXは、発売から時間が経つほど市場の在庫が減り、人気弾では<strong>定価を大きく上回る価格で取引される</strong>ことがあります。この「未開封BOXを値上がり目的で保有する」という考え方が、いわゆる<strong>ワンピBOX投資</strong>です。本記事では、これからワンピBOX投資を始めたい方向けに、<strong>なぜBOXが値上がりするのかの基礎・値上がりしやすいBOXの特徴・予算別の始め方・正しい保管方法・リスクと注意点</strong>を、当サイトが最大9店舗から毎日自動収集している買取価格データの視点で整理します。相場は日々変動するため、金額は断定せず、必ず <a href="/onepiece">ワンピBOX買取価格比較トップ</a> の実データで最新値を確認しながら読み進めてください。すでに売却を考えている方は、姉妹記事の <a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> も参考になります。</p>

<h2>ワンピBOX投資の基礎｜なぜBOXが値上がりするのか</h2>
<p>ワンピBOXの価格は、基本的に<strong>需要と供給のバランス</strong>で決まります。投資として考えるうえで、まずは値上がりの仕組みを押さえておきましょう。</p>
<h3>供給が絞られていく</h3>
<p>ブースターパック(BOX)は発売直後がもっとも流通量が多く、時間の経過とともに<strong>開封されて未開封BOXの数が減っていく</strong>のが基本です。再販がかからない弾や、初動で人気が集中した弾は、市場に出回る未開封BOXが少なくなり、希少性が価格を押し上げます。</p>
<h3>看板カードの相場が牽引する</h3>
<p>BOXの価値は、その弾に収録される<strong>看板カード(コミックパラレルや周年スペシャル等)の相場</strong>に強く連動します。高額カードを狙って開封する需要が続くほど、未開封BOXの買取・販売価格も高く維持されやすくなります。逆に看板カードの相場が落ち着くと、BOX価格も緩やかに下がる傾向があります。</p>
<h3>イベント・話題性で動く</h3>
<p>アニメの放送、大会環境の変化、周年記念、SNSでの話題化などをきっかけに需要が一時的に高まり、相場が動くことがあります。こうした短期の変動は、<a href="weekly.html">週間値動きランキング</a>で直近7日間の上昇・下落として確認できます。</p>
<div class="callout"><strong>ポイント:</strong> BOX投資は「必ず値上がりする」ものではありません。あくまで需給で上下する現物であり、下落もあり得ます。値上がりの根拠(供給の少なさ・看板カード人気)を理解したうえで、余剰資金の範囲で始めるのが基本です。</div>

<h2>値上がりしやすいBOXの特徴</h2>
<p>過去の傾向から、比較的値上がり・価格維持がされやすいBOXには共通点があります。あくまで傾向であり将来を保証するものではありませんが、銘柄選びの目安になります。</p>
<h3>1. 超高額の看板カードを擁する弾</h3>
<p>ルフィ・エースなどの人気キャラの<strong>コミックパラレルや周年スペシャル</strong>など、単体で数十万円〜数百万円クラスのカードを収録する弾は、開封需要が続きやすくBOX価格も高止まりしやすい傾向です。</p>
<h3>2. 周年記念・特別レアリティ導入の弾</h3>
<p>3周年記念弾や、新レアリティが初めて導入された弾は記念性・話題性が高く、コレクション需要が集まりやすい枠です。</p>
<h3>3. 再販が絞られている弾</h3>
<p>再販が少ない・初回生産のみに近い弾は、市場の未開封BOXが増えにくいため希少性が保たれやすくなります。逆に大量再販がかかる弾は供給が増え、値上がりしにくい傾向があります。</p>
<h3>4. 発売から時間が経ち在庫が枯れてきた弾</h3>
<p>発売直後は供給過多で価格が伸びにくいことがありますが、時間の経過とともに未開封BOXが減り、人気弾は徐々に価格が切り上がっていくことがあります。</p>
<p>これらの特徴に当てはまる弾でも、実際の相場は日々変動します。気になる弾は <a href="/onepiece">比較トップ</a> で各BOXの店舗別買取価格を、<a href="weekly.html">週間値動きランキング</a>で値動きの方向を確認してください。</p>

<h2>予算別の始め方</h2>
<p>ワンピBOX投資は、少額からでも始められます。予算に応じた進め方の一例を紹介します(金額はあくまで目安で、実際の相場は変動します)。</p>
<h3>〜1万円台｜まず1BOXで相場感をつかむ</h3>
<p>最初は定価前後で買える弾を<strong>1BOXだけ</strong>買って、相場の動きを観察するのがおすすめです。当サイトで買取価格の推移を追いながら「どのくらい動くのか」を体感すると、次の判断がしやすくなります。いきなり高額弾に手を出さず、値動きに慣れることを優先しましょう。</p>
<h3>数万円〜10万円台｜複数弾に分散する</h3>
<p>ある程度予算がある場合は、<strong>1つの弾に集中せず複数弾へ分散</strong>すると、特定弾の下落リスクを抑えられます。「高額看板の人気弾」と「発売後に在庫が枯れてきた弾」など、性格の異なる弾を組み合わせるのが一案です。</p>
<h3>高予算｜カートン・高額弾も選択肢に</h3>
<p>資金に余裕がある場合、カートン(BOX複数入りの輸送箱)単位での保有や、超高額看板を持つ人気弾のBOXも選択肢になります。ただし高額になるほど<strong>1点あたりの下落リスク・保管リスク</strong>も大きくなるため、分散と保管には特に注意が必要です。購入前・売却前には必ず最大9店舗の実データで最新の相場を確認しましょう。</p>
<div class="callout"><strong>共通の鉄則:</strong> どの予算帯でも、買うときも売るときも<strong>複数店舗を比較</strong>するのが基本です。同じBOXでも店舗により数百円〜数千円、高額弾なら万単位の差が出ることがあります。</div>

<h2>保管方法｜資産価値を守るコツ</h2>
<p>未開封BOXは状態が査定に直結します。せっかく値上がりしても、状態が悪化すると買取額が下がってしまいます。次のポイントを守りましょう。</p>
<h3>シュリンクは絶対に剥がさない</h3>
<p>BOX全体を包む透明フィルム「<strong>シュリンク</strong>」は、未開封・すり替えなしの証明として扱われ、買取価格が最も高くなる条件です。投資目的で保有するBOXは、<strong>シュリンクを剥がさずそのまま保管</strong>するのが鉄則です。</p>
<h3>湿度を避ける</h3>
<p>高温多湿はカードや外箱の劣化・カビの原因になります。<strong>直置きを避け、乾燥剤と一緒に保管</strong>する、梅雨〜夏場は湿度の低い場所に置くなどの対策が有効です。</p>
<h3>直射日光・照明を避ける</h3>
<p>日光や強い照明に長時間さらすと、外箱が<strong>日焼け・退色</strong>します。窓際を避け、光の当たらない収納にしまいましょう。</p>
<h3>圧力・衝撃を避ける</h3>
<p>重い物を上に載せると外箱が潰れ、角つぶれ・スレの原因になります。<strong>立てて・重ねずに</strong>保管し、発送買取に出す際は緩衝材でしっかり梱包して輸送中の潰れを防ぎましょう。</p>

<h2>リスクと注意点</h2>
<p>ワンピBOX投資には値上がりの可能性がある一方、次のようなリスクがあります。始める前に必ず理解しておきましょう。</p>
<h3>相場変動リスク</h3>
<p>BOX相場は需給で上下し、<strong>買った価格より下がる</strong>ことも当然あります。看板カードの相場が落ち着けばBOX価格も下がりやすく、値上がりは保証されません。</p>
<h3>再販リスク</h3>
<p>人気弾は<strong>再販(追加生産)</strong>がかかることがあり、供給が増えると希少性が薄れて相場が下がる場合があります。再販情報には注意が必要です。</p>
<h3>状態悪化リスク</h3>
<p>前述の通り、シュリンク剥がれ・日焼け・潰れなどで<strong>査定額が下がる</strong>リスクがあります。保管の質がそのまま資産価値に影響します。</p>
<h3>流動性・タイミングリスク</h3>
<p>売りたいときに希望額で売れるとは限りません。相場が下降局面のときに現金化を迫られると、安値で手放すことになる場合があります。<strong>余剰資金で・急いで売らずに済む範囲</strong>で行うのが安全です。</p>
<div class="disclaimer" style="margin-top:14px"><strong>免責:</strong> 本記事は投資助言ではなく、一般的な情報提供です。ワンピBOXは価格が変動する現物であり、値上がり・利益を保証するものではありません。購入・売却の最終判断は、必ずご自身の責任で行ってください。</div>

<h2>今、狙い目・高額な弾の例</h2>
<p>ワンピースカードの中でも、超高額の看板カードを擁し需要が高い傾向のある弾を紹介します。金額は需給で日々変動するため、必ず<strong>当サイトの最大9店舗比較の実データで最新値を確認</strong>してください(下記は各弾の看板や傾向であり、BOX価格の断定ではありません)。</p>
<ul>
<li><strong><a href="op-13-atari-guide.html">受け継がれる意志(OP-13)</a></strong> — ルフィ・エース・サボの「レッドスーパーパラレル(レッドコミパラ)」を擁する3周年記念弾。看板カードが超高額で、BOX需要も高い傾向です。</li>
<li><strong><a href="op-15-atari-guide.html">神の島の冒険(OP-15)</a></strong> — 空の神「エネル」のコミックパラレルが看板のスカイピア編テーマ弾。</li>
<li><strong><a href="op-16-atari-guide.html">決戦の刻(OP-16)</a></strong> — 海軍大将トリオのコミパラと日本版初のトレジャーレアが話題の最新弾。</li>
<li><strong><a href="op-14-atari-guide.html">蒼海の七傑(OP-14)</a></strong> — 3周年スペシャルのバギー(金/銀)が超低封入の目玉となった王下七武海テーマ弾。</li>
<li><strong><a href="op-12-atari-guide.html">師弟の絆(OP-12)</a></strong> — 3周年スペシャルの黒ひげ(金/銀)を擁する弾。</li>
</ul>
<p>各弾の当たりカード・封入率・相場の目安は、上記リンク先の弾別ガイドで詳しく解説しています。BOXそのものの店舗別買取価格は <a href="/onepiece">比較トップ</a> から各BOXの個別ページで確認できます。「今どの弾が上昇/下落しているか」は <a href="weekly.html">週間値動きランキング</a> でチェックできます。</p>

<h2>売るときは必ず複数店舗を比較</h2>
<p>投資したBOXを現金化するときも、<strong>複数店舗の比較</strong>が利益を最大化する基本です。同じBOXでも店舗ごとに買取価格が異なり、高額弾ほど差が大きくなります。当サイトはワンピBOX買取に対応した最大9店舗の価格を毎日自動比較しているため、<a href="/onepiece">比較トップ</a>で売りたい弾の最新価格を並べて最高値の店を選べます。売り方のコツは <a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> で詳しく解説しています。</p>""",
        "faq": [
            {"q": "ワンピBOX投資は初心者でも始められますか？",
             "a": "はい、まずは定価前後で買える弾を1BOXだけ買って相場の動きを観察するところから始めるのがおすすめです。当サイトで買取価格の推移や週間値動きを追いながら値動きに慣れると、次の判断がしやすくなります。ただし値上がりは保証されないため、必ず余剰資金の範囲で行ってください。"},
            {"q": "どんなBOXが値上がりしやすいですか？",
             "a": "超高額の看板カード(コミックパラレルや周年スペシャル等)を擁する弾、周年記念・特別レアリティ導入の弾、再販が絞られている弾、発売から時間が経ち在庫が減ってきた弾などが、傾向として価格を維持・上昇しやすいとされます。ただし将来を保証するものではないため、実際の相場は当サイトの最大9店舗比較の実データで確認してください。"},
            {"q": "BOXはどう保管すればいいですか？",
             "a": "シュリンクは剥がさず、直射日光・強い照明を避け、乾燥剤とともに湿度の低い場所で保管します。重い物を載せず、立てて重ねずに置くと外箱の潰れを防げます。状態は査定額に直結するため、資産価値を守るうえで保管の質が重要です。"},
            {"q": "再販されると価格はどうなりますか？",
             "a": "再販(追加生産)がかかると市場の供給が増え、希少性が薄れて相場が下がる場合があります。人気弾ほど再販の可能性があるため、購入・売却の前には再販情報と、当サイトの週間値動きランキングでの直近の値動きを確認するとよいでしょう。"},
            {"q": "損をすることはありますか？",
             "a": "あります。BOX相場は需給で変動する現物であり、買った価格より下がることも当然あります。本記事は投資助言ではなく一般的な情報提供です。値上がりや利益は保証されないため、余剰資金で・急いで売らずに済む範囲で行い、最終判断はご自身の責任で行ってください。"},
        ],
    },
    {
        "slug": "kougaku-ranking",
        "nav_label": "高額BOXランキング・絶版ガイド",
        "crumb": "高額BOXランキング・絶版ガイド",
        "date": "2026-07-26",
        "date_jp": "2026年7月26日",
        "title": "ワンピカード 高額BOXランキング全{{BOX_COUNT}}弾｜買取価格・定価比と絶版/ブロックアイコンの実態を実データで解説",
        "h1": "ワンピカード 高額BOXランキング｜全{{BOX_COUNT}}弾の買取価格・定価比と「絶版」「ブロックアイコン制度」の実態を実データで解説",
        "meta_desc": "ワンピースカードの未開封BOX全弾を最高買取価格でランキング。1位は新時代の主役(OP-05)で最高買取{{TOP1_PRICE}}・定価の{{TOP1_MULT}}。定価比・発売年つきの一覧表と、公式の絶版アナウンスがない実態、2026年4月導入のブロックアイコン制度がBOX相場に与える影響を最大9店舗の実データで解説します。",
        "og_title": "ワンピカード 高額BOXランキング｜全弾の買取価格・定価比と絶版/ブロックアイコンの実態",
        "og_desc": "ワンピBOX全弾を最高買取価格でランキング。1位は新時代の主役(OP-05)で最高買取{{TOP1_PRICE}}・定価の{{TOP1_MULT}}。絶版の実態と2026年4月導入のブロックアイコン制度がBOX相場に与える影響を最大9店舗の実データで解説。",
        "meta_line": "全弾の高額BOXランキング・定価比・絶版とブロックアイコン制度の実態",
        "hero_label": "ワンピBOX 最高買取ランキング(当サイト実データ)",
        "hero_big": "1位 新時代の主役(OP-05) {{TOP1_PRICE}}",
        "hero_sub": "定価¥5,280に対して{{TOP1_MULT}}。2位 ROMANCE DAWN(OP-01) {{TOP2_PRICE}}({{TOP2_MULT}})、3位 神速の拳(OP-11) {{TOP3_PRICE}}({{TOP3_MULT}})。全{{BOX_COUNT}}弾の最高買取・定価比を毎日自動収集した実データで一覧化しています。",
        "disclaimer": "本記事のBOX買取価格は、当サイトが最大9店舗から自動取得した実データの記事更新時点のスナップショットです。相場は需給・再販・各店の在庫状況により日々変動するため、金額はあくまで目安であり特定の買取価格を保証するものではありません。また、ONE PIECEカードゲームには「絶版」「生産終了」の公式アナウンス制度がなく、本記事の入手性に関する記述は流通状況からの観測にとどまります。ブロックアイコン制度の適用区分は公式発表に基づきますが、エクストラブースター・プレミアムブースター等の個別の割り当てについては断定を避けています。最新・正確な情報は公式サイトをご確認ください。売買の判断はご自身の責任で行ってください。",
        "related": '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較(毎日更新)</li>\n'
                   '<li><a href="weekly.html">週間値動きランキング</a> — 直近7日間で値上がり・値下がりしたBOXを毎日自動更新</li>\n'
                   '<li><a href="toushi.html">ワンピカードBOX投資の始め方</a> — 値上がりしやすいBOXの特徴・保管・リスク</li>\n'
                   '<li><a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> — 高く売るコツと店舗選びの手順</li>\n'
                   '<li><a href="op-05-atari-guide.html">新時代の主役(OP-05) 当たりカードガイド</a> — 全弾トップの高額弾の中身</li>\n'
                   '<li><a href="op-01-atari-guide.html">ROMANCE DAWN(OP-01) 当たりカードガイド</a> — 記念すべき第1弾の当たり</li>',
        "body": """<p>ワンピースカードゲームの未開封BOXは、弾によって買取価格に<strong>数倍の開き</strong>があります。定価¥5,280前後の同じブースターパックでも、1万円台で落ち着くものから<strong>6万円を超える</strong>ものまで存在するのが実情です。本記事では、当サイトが最大9店舗から毎日自動収集している買取データをもとに、<strong>全{{BOX_COUNT}}弾を最高買取価格の高い順にランキング</strong>し、あわせて「ワンピカードに絶版はあるのか」「2026年4月に導入されたブロックアイコン制度はBOX相場にどう影響するのか」を整理します。なお、BOXではなく<strong>カード単体</strong>の最高額ランキングは <a href="comipara-ranking.html">歴代コミックパラレル相場ランキング全22弾</a> にまとめています。両者の順位は連動しないため、あわせて読むと弾ごとの実力を立体的に把握できます。</p>

<h2>ワンピBOX 高額ランキング｜全{{BOX_COUNT}}弾(当サイト実データ)</h2>
<p>各弾の<strong>最高買取価格</strong>(当サイト掲載店舗のうち最も高い店の価格)と、<strong>定価に対する倍率</strong>を並べたものが以下の表です。弾名をクリックすると、その弾の当たりカードガイドに移動できます。</p>
{{BOX_RANKING}}
<div class="callout"><strong>表の見方:</strong> 「最高買取」は当サイト掲載店舗の最高値、「定価比」は定価に対する倍率です。スタートデッキEX ルフィ＆エース(ST-30)のみ定価¥1,980のスタートデッキのため、ブースターパックとは倍率の意味合いが異なります。最新値は必ず <a href="/onepiece">比較トップ</a> でご確認ください。</div>

<h2>高額BOX TOP4を解説</h2>
<h3>1位 新時代の主役【OP-05】｜{{TOP1_PRICE}}({{TOP1_MULT}})</h3>
<p>全弾で頭ひとつ抜けた1位が、2023年8月発売の1周年記念弾 <strong>新時代の主役(OP-05)</strong> です。最高買取は<strong>{{TOP1_PRICE}}</strong>、定価¥5,280に対して<strong>{{TOP1_MULT}}</strong>という水準で、発売から3年近く経ってなお高値を維持しています。評価の中心は<strong>コミックパラレル(コミパラ)が3種同時に収録された前例のない仕様</strong>で、看板であるルフィのコミパラは単体で数十万円規模の取引が報告されています。当たりの詳細は <a href="op-05-atari-guide.html">新時代の主役 当たりカードガイド</a> をご覧ください。</p>
<h3>2位 ROMANCE DAWN【OP-01】｜{{TOP2_PRICE}}({{TOP2_MULT}})</h3>
<p>記念すべき第1弾 <strong>ROMANCE DAWN(OP-01)</strong> が2位です。最高買取は<strong>{{TOP2_PRICE}}</strong>で、定価¥4,752に対し<strong>{{TOP2_MULT}}</strong>。2022年7月発売と最も古く、市場に残る未開封BOXが少ないことが価格を支えています。後述する<strong>ブロックアイコン制度で2026年4月からスタンダード大会では使えなくなった弾</strong>ですが、それでも高値圏にある点が本作の相場構造を象徴しています。</p>
<h3>3位 神速の拳【OP-11】｜{{TOP3_PRICE}}({{TOP3_MULT}})</h3>
<p>2025年3月発売の <strong>神速の拳(OP-11)</strong> が3位。比較的新しい弾ながら<strong>{{TOP3_PRICE}}</strong>({{TOP3_MULT}})という水準で、上位陣に食い込んでいます。詳細は <a href="op-11-atari-guide.html">神速の拳 当たりカードガイド</a> で解説しています。</p>
<h3>4位 ONE PIECE Anime 25th collection【EB-02】｜{{TOP4_PRICE}}({{TOP4_MULT}})</h3>
<p>エクストラブースターから唯一トップ5に入るのが <strong>Anime 25th collection(EB-02)</strong> です。アニメ25周年の記念商品という位置づけで、<strong>{{TOP4_PRICE}}</strong>({{TOP4_MULT}})。エクストラブースターは通常のブースターパックより流通量が絞られる傾向があり、記念性が加わると相場が伸びやすい枠です。</p>

<h2>ワンピカードに「絶版」はある？｜公式アナウンスは存在しない</h2>
<p>高額弾を語るときによく使われる「絶版」という言葉ですが、<strong>ONE PIECEカードゲームには、特定の弾を絶版・生産終了とする公式アナウンスの制度がありません</strong>。この点は、レギュレーション変更にともなって「事実上の絶版」が意識されやすいポケモンカードとは事情が異なります。</p>
<h3>むしろ再販・増産は継続している</h3>
<p>実態としては、バンダイは人気商品の<strong>増産と再販を継続</strong>しています。新弾は発売直後こそ品薄になりやすいものの、発売から1か月前後で追加生産がかかるケースが多く報じられており、一時期のような極端な品薄・転売の過熱は落ち着いてきたと評価されています。つまり<strong>「今買えないこと」と「二度と手に入らないこと」はイコールではありません</strong>。</p>
<h3>それでも旧弾が高いのはなぜか</h3>
<p>では、なぜOP-01やOP-05のような旧弾が高値を保つのか。理由は絶版宣言ではなく、次の3点です。</p>
<ul>
<li><strong>開封されて未開封BOXが物理的に減る</strong> — 時間が経つほど市場の未開封在庫は目減りします</li>
<li><strong>再販の頻度・数量が新弾に偏る</strong> — 生産リソースは基本的に最新弾に向けられ、数年前の弾が大量再販される例は多くありません</li>
<li><strong>看板カードの相場が下支えする</strong> — コミパラなど超高額カードを狙う開封需要が続く限り、BOXの需要も残ります</li>
</ul>
<div class="callout"><strong>結論:</strong> ワンピカードの旧弾は「絶版だから高い」のではなく、<strong>「再販が新弾に集中し、未開封在庫が自然減しているから高い」</strong>と理解するのが実態に近い見方です。当サイトでは公式発表のない絶版・生産終了の断定は行っていません。</div>

<h2>ブロックアイコン制度(2026年4月導入)とBOX相場</h2>
<p>2026年4月1日より、ONE PIECEカードゲームに<strong>ブロックアイコン制度</strong>が導入されました。カード右下に記された数字(ブロックアイコン)をもとに、スタンダードレギュレーションの大会で使用できるカードを制限する仕組みで、他のTCGでいう「スタン落ち」「ローテーション」にあたります。</p>
<h3>ブロックの区分と適用スケジュール</h3>
<ul>
<li><strong>ブロック①</strong>: 第1弾〜第4弾(OP-01〜OP-04)およびスタートデッキST-01〜ST-09 — <strong>2026年4月1日以降、スタンダードの公式大会で使用不可</strong></li>
<li><strong>ブロック②</strong>: 第5弾〜第8弾(OP-05〜OP-08) — 2027年4月に対象予定</li>
<li><strong>ブロック③</strong>: 第9弾〜第12弾(OP-09〜OP-12) — 2028年4月に対象予定</li>
<li><strong>特例</strong>: スーパーパラレルと同一カードナンバーのカードなど、一部は継続して使用可能とされています</li>
</ul>
<p>※エクストラブースター(EB)・プレミアムブースター(PRB)・ST-30などの個別のブロック割り当ては、収録時期に応じて振られますが、弾ごとの正確な対応は公式サイトの案内をご確認ください。当サイトでは断定を避けています。</p>
<h3>スタン落ちしてもBOX相場は下がっていない</h3>
<p>ここが重要な点です。<strong>ブロック①(OP-01〜OP-04)は2026年4月にスタンダードで使えなくなりましたが、BOX買取価格は下がるどころか高値圏にあります</strong>。実データを見ると、OP-01 ROMANCE DAWNは<strong>{{OP01_PRICE}}</strong>({{OP01_MULT}})で全弾2位、OP-02 頂上決戦も<strong>{{OP02_PRICE}}</strong>({{OP02_MULT}})と上位です。</p>
<p>これは、旧弾BOXの価格を支えているのが<strong>対戦需要ではなくコレクション需要・開封需要</strong>だからです。同じ構造はポケモンカードでも観測されており、Gレギュでスタン落ちした<a href="/shiny-treasure-ex-atari-guide.html">シャイニートレジャーex</a>が現在もBOX買取¥20,000(定価の約3.6倍)を維持しているのが好例です。<strong>「スタン落ち＝BOX暴落」ではない</strong>という点は、売り時を考えるうえで押さえておきたい前提です。</p>

<h2>定価比で見る「買い方・売り方」の目安</h2>
<p>ランキング表の<strong>定価比</strong>は、その弾がどれだけプレミア化しているかを示す指標として使えます。</p>
<h3>定価比が高い弾(約5倍以上)</h3>
<p>OP-05・OP-01・OP-11・EB-02などが該当します。すでに大きく値上がりしているため、<strong>これから買って値上がりを狙うより、手元にあるなら売却先を厳選する</strong>フェーズにある弾といえます。高額弾ほど店舗間の価格差が金額として大きくなるため、<a href="kaitori-hikaku.html">複数店舗の比較</a>が効きます。</p>
<h3>定価比が低い弾(約2〜3倍)</h3>
<p>比較的新しい弾や、再販が行き渡った弾がここに入ります。供給が多いぶん現時点の評価は控えめですが、時間の経過で未開封在庫が減れば水準が切り上がる可能性もあります。投資として考える場合の基本的な考え方は <a href="toushi.html">ワンピカードBOX投資の始め方</a> で解説しています。</p>
<div class="callout"><strong>注意:</strong> 定価比はあくまで現時点のスナップショットです。新弾の発売、再販、アニメ・イベントの話題化などで順位は入れ替わります。直近の値動きは <a href="weekly.html">週間値動きランキング</a> で確認してください。なお、次弾となる4周年弾 ブースターパック「世界最強の戦士」(OP-17)は2026年8月発売が予定されており、新弾発売の前後は相場が動きやすい時期です。</div>

<h2>高額BOXを売るときの3つの注意点</h2>
<ol>
<li><strong>シュリンクは剥がさない</strong> — 未開封・すり替えなしの証明として扱われ、剥がすと区分が変わって減額されるのが通例です。高額弾ほど減額幅も大きくなります</li>
<li><strong>必ず複数店舗を比較する</strong> — 同じ弾でも店舗により買取価格は異なります。6万円クラスの弾なら、店舗差がそのまま数千円〜1万円の差になり得ます</li>
<li><strong>売る直前の相場を確認する</strong> — 再販や新弾発売で相場は動きます。当サイトは毎日自動更新のため、売却直前に <a href="/onepiece">比較トップ</a> で最新の最高値を確認してから持ち込むのが確実です</li>
</ol>""",
        "faq": [
            {"q": "ワンピースカードで一番高いBOXはどれですか？",
             "a": "当サイトが最大9店舗から自動収集した実データでは、ブースターパック「新時代の主役」(OP-05)が最高買取{{TOP1_PRICE}}で全弾トップです。定価¥5,280に対して{{TOP1_MULT}}の水準になります。次いでROMANCE DAWN(OP-01)が{{TOP2_PRICE}}、神速の拳(OP-11)が{{TOP3_PRICE}}と続きます。相場は日々変動するため、最新値は比較トップページでご確認ください。"},
            {"q": "ワンピースカードに絶版のパックはありますか？",
             "a": "ONE PIECEカードゲームには、特定の弾を絶版・生産終了とする公式アナウンスの制度がありません。バンダイは人気商品の増産・再販を継続しており、新弾は発売から1か月前後で追加生産されるケースが多く報じられています。旧弾が高値なのは絶版宣言のためではなく、開封によって未開封BOXが自然減し、再販が新弾に集中するためと理解するのが実態に近い見方です。"},
            {"q": "ブロックアイコン制度とは何ですか？",
             "a": "2026年4月1日より導入された、カード右下の数字(ブロックアイコン)をもとにスタンダードレギュレーションの大会で使用できるカードを制限する制度です。ブロック①にあたる第1弾〜第4弾(OP-01〜OP-04)とスタートデッキST-01〜ST-09は、2026年4月1日以降スタンダードの公式大会で使用できません。ブロック②(OP-05〜OP-08)は2027年4月、ブロック③(OP-09〜OP-12)は2028年4月が対象予定とされています。"},
            {"q": "スタン落ちした弾のBOXは値下がりしますか？",
             "a": "当サイトの実データでは、値下がりしていません。2026年4月にスタンダードで使用不可となったOP-01 ROMANCE DAWNは最高買取{{OP01_PRICE}}({{OP01_MULT}})で全弾2位、OP-02 頂上決戦も{{OP02_PRICE}}({{OP02_MULT}})と上位を維持しています。旧弾BOXの価格を支えているのは対戦需要ではなくコレクション需要・開封需要のため、スタン落ちが直ちに暴落を招くわけではありません。ただし将来の相場を保証するものではありません。"},
            {"q": "高額BOXはどこで売るのが一番高いですか？",
             "a": "弾によって最高値の店舗は異なります。当サイトはワンピBOX買取に対応した最大9店舗の価格を毎日自動比較しているため、売りたい弾のページで最高値の店を確認するのが確実です。高額弾ほど店舗間の価格差が金額として大きくなるため、比較の効果も大きくなります。"},
            {"q": "これから値上がりしそうな弾はどれですか？",
             "a": "将来の値上がりを断定することはできません。傾向としては、超高額の看板カードを擁する弾、周年記念・特別レアリティ導入の弾、再販が絞られている弾、発売から時間が経ち在庫が減ってきた弾が価格を維持・上昇しやすいとされます。直近の値動きは週間値動きランキングで確認できます。相場は下落もあり得るため、余剰資金の範囲で判断してください。"},
        ],
    },
    {
        "slug": "op-17-forecast",
        "nav_label": "【予想】世界最強の戦士(OP-17)相場予想",
        "crumb": "世界最強の戦士(OP-17) BOX相場予想",
        "date": "2026-08-02",
        "date_jp": "2026年8月2日",
        "title": "【発売前予想】世界最強の戦士(OP-17) BOX相場3シナリオ｜4周年弾×新レアリティL-SPを過去弾の実データで分析",
        "h1": "【発売前予想】世界最強の戦士(OP-17) BOX相場3シナリオ｜4周年弾×新レアリティL-SPを過去弾の実データで分析",
        "meta_desc": "2026年8月22日発売のワンピカード新弾「世界最強の戦士」(OP-17)のBOX相場を、当サイト最大9店舗の過去弾実データから3シナリオ(弱気¥11,000/中立¥16,000/強気¥24,000)で予想。1パック240円への値上げ、新レアリティL-SP、四皇テーマ、過去の周年記念弾(OP-05/OP-09/OP-13)の実績を踏まえて、買い時・売り時の判断基準まで解説します。",
        "og_title": "【発売前予想】世界最強の戦士(OP-17) BOX相場3シナリオ｜4周年弾を実データ分析",
        "og_desc": "2026年8月22日発売のOP-17「世界最強の戦士」BOX相場を過去弾の実データから3シナリオ(弱気¥11,000/中立¥16,000/強気¥24,000)で予想。値上げ・新レアリティL-SP・周年弾の実績から分析。",
        "meta_line": "OP-17の発売前BOX相場3シナリオ予想・判断基準",
        "hero_label": "🔮 発売前予想 - 2026年8月22日(土)発売",
        "hero_big": "BOX相場は¥11,000〜¥24,000のどこに着地するか",
        "hero_sub": "定価¥5,760(24パック・1パック240円)の4周年タイミングの新弾。エルバフ編と四皇がテーマで、新レアリティ「スーパーリーダーパラレル(L-SP)」が初登場します。当サイトが最大9店舗から毎日自動収集している過去弾の実データをもとに、発売後のBOX相場を3シナリオで予想します。",
        "disclaimer": "本記事は2026年8月2日時点で公表されている情報と、当サイトが最大9店舗から自動取得した過去弾のBOX買取実データに基づく<strong>発売前の予想記事</strong>です。3シナリオのBOX相場・確率感は筆者の分析であり、公式発表や確定情報ではありません。収録カードの買取相場予想・封入率は各メディア(トレカの地図・トレカプロ・アルテマ等)が公開している<strong>非公式の予想値</strong>で、ソースにより数値に幅があります。封入率は公式から発表されていません。実際の相場は需給・再販・大会環境など多くの要因で大きく変動し、購入価格を下回ることもあります。投資助言を目的とするものではありません。売買の判断はご自身の責任で行ってください。実際のBOX買取価格は発売後に当サイトの実データで随時更新します。",
        "related": '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較(毎日更新)。OP-17も買取掲載が始まり次第反映します</li>\n'
                   '<li><a href="kougaku-ranking.html">高額BOXランキング・絶版ガイド</a> — 全弾の最高買取・定価比ランキングと、ブロックアイコン制度の影響</li>\n'
                   '<li><a href="toushi.html">ワンピカードBOX投資の始め方</a> — 値上がりしやすいBOXの特徴・保管・リスク</li>\n'
                   '<li><a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> — 発売後に売る場合の店舗選びと高く売るコツ</li>\n'
                   '<li><a href="op-13-atari-guide.html">受け継がれる意志(OP-13) 当たりカードガイド</a> — 3周年記念弾の中身と相場</li>\n'
                   '<li><a href="op-16-atari-guide.html">決戦の刻(OP-16) 当たりカードガイド</a> — OP-17の直前弾。初動比較の基準になります</li>\n'
                   '<li><a href="shikou-treasure-get.html">4周年！四皇トレジャーゲットキャンペーンパック全7種</a> — OP-17発売と同日に配布開始したプロモパックの収録内容と相場</li>\n'
                   '<li><a href="weekly.html">週間値動きランキング</a> — 発売後の値動きを毎日自動更新</li>',
        "body": """<p>ONE PIECEカードゲームのブースターパック第17弾<strong>「世界最強の戦士」(OP-17)</strong>が、<strong>2026年8月22日(土)</strong>に発売されます。巨兵海賊団の島<strong>エルバフ</strong>と<strong>四皇</strong>をテーマにした弾で、シリーズ4周年の節目にあたる時期の新弾として各メディアで注目されています。さらにこの弾から<strong>1パック240円へ値上げ</strong>され、1BOX(24パック)の定価は<strong>¥5,760</strong>になりました。</p>

<p>本記事では、当サイトが最大9店舗から毎日自動収集している<strong>過去弾のBOX買取実データ</strong>をもとに、OP-17のBOX相場を3シナリオで予想します。発売前の予想であり実際の相場は大きく変動しますが、「どのくらいの水準なら高値掴みなのか」を判断する材料としてご活用ください。</p>

<h2>① OP-17「世界最強の戦士」の基本情報</h2>
<table class="price-table">
<thead><tr><th>項目</th><th>内容</th></tr></thead>
<tbody>
<tr><td>正式名称</td><td>ONE PIECEカードゲーム ブースターパック「世界最強の戦士」【OP-17】</td></tr>
<tr><td>発売日</td><td>2026年8月22日(土)</td></tr>
<tr><td>定価</td><td>1パック¥240(税込) / 1BOX(24パック)¥5,760(税込)</td></tr>
<tr><td>価格改定</td><td>この弾から1パック¥220→¥240へ値上げ(BOXで¥480の上昇)</td></tr>
<tr><td>テーマ</td><td>エルバフ編・四皇</td></tr>
<tr><td>新レアリティ</td><td>スーパーリーダーパラレル(L-SP)が初登場</td></tr>
<tr><td>収録種類数</td><td>全131種+4種(メディア情報。8月1日時点で60種が判明)</td></tr>
<tr><td>発売記念イベント</td><td>2026年8月22日(土)〜9月6日(日)に公式ショップで交流会。四皇にちなんだリーダーカードのみ使用可のフォーマット(公式発表)</td></tr>
</tbody>
</table>

<p>注目点は<strong>「値上げ後の最初の通常ブースター」</strong>である点です。定価が¥5,280から¥5,760へ上がったため、これまでと同じ買取額でも<strong>定価倍率は下がって見える</strong>ことになります。相場を比べるときは金額と倍率の両方を見る必要があります。</p>

<h2>② 過去弾の現在相場｜当サイト実データのスナップショット</h2>
<p>予想の出発点は、実際に取引されている過去弾の相場です。当サイトが観測している主要な弾の最高買取価格は以下のとおりです(記事更新時点)。</p>

<table class="price-table">
<thead><tr><th>弾</th><th>発売日</th><th>定価</th><th>最高買取</th><th>定価比</th></tr></thead>
<tbody>
<tr class="best"><td><a href="op-05-atari-guide.html">新時代の主役(OP-05)</a></td><td>2023-08-26</td><td>¥5,280</td><td class="price">{{OP05_PRICE}}</td><td class="price">{{OP05_MULT}}</td></tr>
<tr><td><a href="op-13-atari-guide.html">受け継がれる意志(OP-13)</a></td><td>2025-08-23</td><td>¥5,280</td><td class="price">{{OP13_PRICE}}</td><td class="price">{{OP13_MULT}}</td></tr>
<tr><td><a href="op-09-atari-guide.html">新たなる皇帝(OP-09)</a></td><td>2024-08-31</td><td>¥5,280</td><td class="price">{{OP09_PRICE}}</td><td class="price">{{OP09_MULT}}</td></tr>
<tr><td><a href="op-15-atari-guide.html">神の島の冒険(OP-15)</a></td><td>2026-02-28</td><td>¥5,280</td><td class="price">{{OP15_PRICE}}</td><td class="price">{{OP15_MULT}}</td></tr>
<tr><td><a href="op-14-atari-guide.html">蒼海の七傑(OP-14)</a></td><td>2025-11-22</td><td>¥5,280</td><td class="price">{{OP14_PRICE}}</td><td class="price">{{OP14_MULT}}</td></tr>
<tr><td><a href="op-16-atari-guide.html">決戦の刻(OP-16)</a></td><td>2026-05-30</td><td>¥5,280</td><td class="price">{{OP16_PRICE}}</td><td class="price">{{OP16_MULT}}</td></tr>
</tbody>
</table>

<p>この表から読み取れるのは、<strong>直前弾ほど倍率が低く、時間の経過とともに上がっていく</strong>という構造です。最新弾の<a href="op-16-atari-guide.html">決戦の刻(OP-16)</a>は{{OP16_PRICE}}({{OP16_MULT}})にとどまる一方、1年前の<a href="op-13-atari-guide.html">受け継がれる意志(OP-13)</a>は{{OP13_PRICE}}({{OP13_MULT}})、3年前の<a href="op-05-atari-guide.html">新時代の主役(OP-05)</a>は{{OP05_PRICE}}({{OP05_MULT}})に達しています。開封によって未開封BOXが減っていく一方、再販は新弾に集中するためです。全弾の一覧は<a href="kougaku-ranking.html">高額BOXランキング</a>で確認できます。</p>

<div class="callout"><strong>💡 ポイント:</strong> ワンピBOXの相場は「発売直後がピーク」ではなく、<strong>発売直後にいったん高値 → 再販で落ち着く → 時間経過で再上昇</strong>という動き方をする弾が多く見られます。発売直後の価格だけで「高い/安い」を判断しないことが重要です。</div>

<h2>③ 8月弾=周年タイミングの系譜｜OP-05・OP-09・OP-13の実績</h2>
<p>OP-17を読むうえで最も重要な参照点が、<strong>毎年8月末に発売されてきた「周年タイミングの弾」</strong>です。ONE PIECEカードゲームは2022年7月にスタートし、以降の8月弾は節目の弾として扱われてきました。</p>

<table class="price-table">
<thead><tr><th>弾</th><th>発売日</th><th>位置づけ</th><th>現在の最高買取</th><th>定価比</th></tr></thead>
<tbody>
<tr class="best"><td>新時代の主役(OP-05)</td><td>2023-08-26</td><td>1年目の8月弾。コミパラ3種同時収録</td><td class="price">{{OP05_PRICE}}</td><td class="price">{{OP05_MULT}}</td></tr>
<tr><td>新たなる皇帝(OP-09)</td><td>2024-08-31</td><td>2年目の8月弾。初のゴールドコミパラ</td><td class="price">{{OP09_PRICE}}</td><td class="price">{{OP09_MULT}}</td></tr>
<tr><td>受け継がれる意志(OP-13)</td><td>2025-08-23</td><td>3年目の8月弾。レッドスーパーパラレル導入</td><td class="price">{{OP13_PRICE}}</td><td class="price">{{OP13_MULT}}</td></tr>
<tr><td><strong>世界最強の戦士(OP-17)</strong></td><td><strong>2026-08-22</strong></td><td><strong>4年目の8月弾。L-SP導入・四皇テーマ</strong></td><td class="price">発売前</td><td class="price">—</td></tr>
</tbody>
</table>

<p>3弾に共通するのは、<strong>いずれも新しいレアリティや特別仕様が導入されている</strong>点です。OP-05はコミックパラレルを3種同時に収録し、OP-09は初のゴールドコミパラ、OP-13はレッドスーパーパラレルを導入しました。そして現在の相場は<strong>3弾とも定価の4.5倍以上</strong>を維持しています。同時期の通常弾(OP-14・OP-16など)が{{OP16_MULT}}〜{{OP14_MULT}}にとどまることを踏まえると、<strong>8月弾には明確なプレミアムが乗っている</strong>と言えます。</p>

<p>OP-17も<strong>新レアリティ「スーパーリーダーパラレル(L-SP)」を初導入</strong>し、四皇という原作屈指の人気カテゴリをテーマに据えています。この系譜を継ぐなら、中長期では過去3弾と同じ「定価の4倍以上」を狙える構成です。ただし<strong>それは発売直後の話ではない</strong>という点が、次のシナリオ設計で最も重要になります。</p>

<h2>④ 目玉カードと新レアリティ L-SP(メディア予想・非公式)</h2>
<p>発売前のため公式の封入率・相場は存在しませんが、各メディアが予想値を公開しています。以下は<strong>いずれも非公式の予想</strong>で、ソースにより数値に幅があります。</p>

<table class="price-table">
<thead><tr><th>カード</th><th>レアリティ</th><th>買取相場の予想(非公式)</th></tr></thead>
<tbody>
<tr class="best"><td>ロックス・D・ジーベック</td><td>スーパーパラレル(SEC)</td><td class="price">約45万円(販売予想 約60万円)</td></tr>
<tr><td>モンキー・D・ルフィ</td><td>新四皇SP</td><td class="price">約41万円(ソースにより20万〜50万円台)</td></tr>
<tr><td>モンキー・D・ルフィ</td><td>スーパーリーダーパラレル(L)</td><td class="price">約22万円</td></tr>
<tr><td>シャンクス</td><td>スーパーパラレル(SR)</td><td class="price">約20万円</td></tr>
<tr><td>シャンクス</td><td>SP</td><td class="price">約14万円</td></tr>
<tr><td>モンキー・D・ルフィ</td><td>L-SP(新レアリティ)</td><td class="price">約1.5万〜2.5万円</td></tr>
</tbody>
</table>

<p>目を引くのは、四皇の始祖ともいえる<strong>ロックス・D・ジーベック</strong>が最上位に予想されている点です。原作でも登場が限られる大物で、コレクター需要が集中しやすい題材です。加えて<strong>白ひげ(エドワード・ニューゲート)・シャンクス・カイドウ・ビッグマム</strong>という四皇のスーパーパラレルが揃うため、<strong>高額カードが1種に集中せず分散する</strong>構成が予想されています。</p>

<p>新レアリティの<strong>L-SP(スーパーリーダーパラレル)</strong>は、リーダーカードのさらに上位にあたる新枠です。従来のリーダーパラレルより封入が絞られると見られており、<strong>実際の封入率と初動相場が本弾のBOX価格を左右する最大の変数</strong>になります。</p>

<div class="callout"><strong>⚠️ 注意:</strong> 上記はすべて発売前のメディア予想であり、公式発表ではありません。過去にも発売前予想と実際の初動が大きくずれたケースは珍しくありません。発売後は当サイトの実データと各カードの実勢で確認してください。</div>

<h2>⑤ 封入率の予想(非公式)</h2>
<p>ONE PIECEカードゲームは公式が封入率を公表していないため、以下はメディアが過去弾の実績から推定した数値です。</p>

<table class="price-table">
<thead><tr><th>レアリティ</th><th>予想封入率</th><th>BOXあたりの目安</th></tr></thead>
<tbody>
<tr><td>上位スーパーパラレル</td><td>約0.22%</td><td class="price">約457BOXに1枚</td></tr>
<tr><td>スーパーパラレル(コミパラ)</td><td>約0.83%</td><td class="price">約121BOXに1枚</td></tr>
<tr><td>新四皇SP</td><td>約0.65%</td><td class="price">約154BOXに1枚</td></tr>
</tbody>
</table>

<p>最上位のカードは<strong>数百BOXに1枚</strong>という水準で、1BOX開封して当てられる確率は極めて低いのが実情です。別のメディアも新四皇SPのルフィについて「実質10カートン(約120BOX)に1枚程度」と推定しており、おおむね同じオーダーです。<strong>BOXを開けて元を取る前提での購入は現実的ではない</strong>ことは、あらかじめ押さえておくべき点です。開封の考え方は<a href="toushi.html">BOX投資の始め方</a>でも解説しています。</p>

<h2>⑥ BOX相場 3シナリオ予想</h2>
<p>ここまでの材料をもとに、<strong>発売後1〜2ヶ月時点</strong>のBOX買取相場を3シナリオで想定します。すべて<strong>定価¥5,760基準</strong>です。</p>

<h3>🔵 弱気シナリオ ¥11,000前後(定価の約1.9倍)｜確率感 20%</h3>
<p>再販が早期かつ大規模に行われ、供給が潤沢になるシナリオです。最新弾の<a href="op-16-atari-guide.html">決戦の刻(OP-16)</a>は発売から2ヶ月あまりで{{OP16_PRICE}}({{OP16_MULT}})まで落ち着いています。OP-17が<strong>この倍率をさらに下回り、定価の2倍を割る</strong>展開になると¥11,000前後です。1パック¥240への値上げで買い手の心理的な抵抗が強く出た場合や、L-SPの封入が予想より緩く目玉カードの相場が伸びなかった場合に、この帯へ収束します。ただし四皇テーマの注目度を考えると、確率は低めと見ています。</p>

<h3>🟣 中立シナリオ ¥16,000前後(定価の約2.8倍)｜確率感 45%(最有力)</h3>
<p>最も可能性が高いと考えるのがこの帯です。直前弾のOP-16は発売直後に1万3,000〜1万5,000円台(定価の約2.5倍)で取引が始まったと報じられており、<strong>4周年タイミングのプレミアムを少し上乗せした水準</strong>がここにあたります。<a href="op-14-atari-guide.html">蒼海の七傑(OP-14)</a>・<a href="op-15-atari-guide.html">神の島の冒険(OP-15)</a>の現在値{{OP14_PRICE}}・{{OP15_PRICE}}ともほぼ重なる帯で、発売直後に高値がつき、その後の再販でこの水準へ落ち着くという最も標準的な展開です。なお外部メディアはOP-17のBOX買取をシュリンクあり¥19,000程度と予想しており、この中立シナリオと次の強気シナリオの中間にあたります。</p>

<h3>🔴 強気シナリオ ¥24,000前後(定価の約4.2倍)｜確率感 35%</h3>
<p>8月弾のプレミアムが<strong>発売直後から</strong>効くシナリオです。金額としては、過去の8月弾であるOP-09({{OP09_PRICE}})・OP-13({{OP13_PRICE}})が<strong>1年以上かけて到達した現在の水準</strong>に、発売後1〜2ヶ月で並ぶイメージになります。条件は(1)L-SPの封入が想定以上に絞られる(2)ロックスや四皇スーパーパラレルの初動が予想の40万〜60万円を超える(3)再販が絞られ品薄が続く、の3点が重なることです。四皇という題材の強さと新レアリティの話題性を考えると、無視できない確率だと判断しています。</p>

<table class="price-table">
<thead><tr><th>シナリオ</th><th>想定BOX相場</th><th>定価比</th><th>確率感</th><th>参照した実績</th></tr></thead>
<tbody>
<tr><td>🔵 弱気</td><td class="price">¥11,000</td><td class="price">約1.9倍</td><td class="price">20%</td><td>OP-16の現在倍率を下回る展開</td></tr>
<tr class="best"><td>🟣 中立(最有力)</td><td class="price">¥16,000</td><td class="price">約2.8倍</td><td class="price">45%</td><td>OP-16初動+周年プレミアム</td></tr>
<tr><td>🔴 強気</td><td class="price">¥24,000</td><td class="price">約4.2倍</td><td class="price">35%</td><td>OP-09/OP-13の現在水準</td></tr>
</tbody>
</table>

<div class="callout"><strong>📌 確率配分の考え方:</strong> 当サイトはポケカ側でも同じ3シナリオ形式の予想を行っており、直近では「記念性・キャラクター人気が特に高い弾は、過去弾の倍率アンカーを大きく超えて初動が形成される」という結果を経験しました。その学びを反映し、本記事では<strong>強気シナリオの確率をやや厚めに置いています</strong>。逆にワンピBOXは発売から1〜2ヶ月で再販が入る前例が多く、発売直後の高値がそのまま定着しにくい点も踏まえて、中立を最有力としました。</div>

<h2>⑦ 買い方・売り方の3つの判断基準</h2>

<h3>基準1: 発売前(〜2026-08-22)｜定価で確保できるかがすべて</h3>
<p>抽選・予約で<strong>定価¥5,760で確保できた分</strong>は、中立シナリオでも大きな含み益になります。一方で発売前のフリマ・オークションでのプレ値購入は、どのシナリオでも利幅が小さくなり、弱気シナリオでは含み損になります。新弾は「定価で買えたかどうか」で損益がほぼ決まるため、<strong>抽選への複数エントリーが最も効率的</strong>です。</p>

<h3>基準2: 発売直後(8/22〜9月上旬)｜初動の1〜2週間で方向が見える</h3>
<p>発売直後は買取価格が最も動く時期です。売却を考えている場合、この時期の最高値が短期的な天井になるケースがあります。当サイトの<a href="/onepiece">比較トップ</a>と<a href="weekly.html">週間値動きランキング</a>で、OP-17の買取掲載が始まったあとの推移を追えます。<strong>店舗によって数千円の差が出る</strong>ため、売るなら必ず複数店を比較してください(<a href="kaitori-hikaku.html">高く売るコツはこちら</a>)。</p>

<h3>基準3: 再販後(9月〜10月)｜長期保有なら押し目を待つ</h3>
<p>ワンピカードは新弾の発売から1ヶ月前後で追加生産・再販が入るケースが多く報じられています。再販が本格化すると相場は一度落ち着く傾向があるため、<strong>長期保有を狙うならこの局面が買い場</strong>になり得ます。過去の8月弾がいずれも時間の経過とともに値を上げてきた事実は、この考え方を支持する材料です(ただし将来を保証するものではありません)。</p>

<h2>⑧ リスク要因</h2>
<ol>
<li><strong>大規模再販</strong> — 注目弾ほど生産数が多く組まれる傾向があり、再販が続けば初動の高値は維持されにくくなります。</li>
<li><strong>値上げによる需要減退</strong> — 1パック¥240への値上げは、開封需要そのものを冷やす可能性があります。値上げ後の最初の通常ブースターであるため、前例がない点はリスクです。</li>
<li><strong>L-SPの封入率が緩い場合</strong> — 新レアリティの供給が多ければ、目玉カードの相場が下がりBOX価格も連動して下がります。</li>
<li><strong>高額カードの分散</strong> — 四皇4種にスーパーパラレルが分散すると、1枚あたりの希少性が薄まり単価が伸びない可能性があります。</li>
<li><strong>大会環境での評価</strong> — 収録カードが対戦環境で強くない場合、プレイヤー需要が乗らず相場が伸び悩みます。</li>
</ol>

<h2>⑨ まとめ</h2>
<ul>
<li>OP-17「世界最強の戦士」は<strong>2026年8月22日(土)発売</strong>、1パック¥240・1BOX(24パック)¥5,760。この弾から値上げされました。</li>
<li>BOX相場は<strong>弱気¥11,000 / 中立¥16,000 / 強気¥24,000</strong>のレンジを想定し、<strong>中立¥16,000前後(定価の約2.8倍)を最有力</strong>と見ています。</li>
<li>過去の8月弾(OP-05・OP-09・OP-13)はいずれも現在<strong>定価の4.5倍以上</strong>を維持しており、4年目のOP-17も中長期での上昇余地は大きい構成です。</li>
<li>ただし直前弾のOP-16は現在{{OP16_PRICE}}({{OP16_MULT}})。<strong>発売直後から4倍台に乗るかどうかが強気シナリオの分岐</strong>になります。</li>
<li>最大の変数は<strong>新レアリティL-SPの封入率</strong>と、ロックス・四皇スーパーパラレルの初動相場です。</li>
<li>発売後の実際の買取価格は<a href="/onepiece">当サイトの最大9店舗比較</a>で毎日自動更新します。</li>
</ul>""",
        "faq": [
            {"q": "世界最強の戦士(OP-17)のBOX相場はいくらくらいになりますか？",
             "a": "発売前の予想として、当サイトでは3シナリオを想定しています。弱気¥11,000(定価の約1.9倍・直前弾OP-16の現在水準)、中立¥16,000(約2.8倍・最有力)、強気¥24,000(約4.2倍・過去の8月弾の現在水準)です。いずれも定価¥5,760を基準とした試算で、実際の相場は発売後の需給・再販で大きく変動します。発売後は当サイトの最大9店舗比較で実データを毎日更新します。"},
            {"q": "OP-17の発売日と定価はいくらですか？",
             "a": "2026年8月22日(土)発売で、定価は1パック¥240(税込)、1BOX(24パック)¥5,760(税込)です。この弾から1パック¥220→¥240へ値上げされ、BOXでは¥480の上昇となりました。エルバフ編と四皇をテーマにした弾で、シリーズ4周年の節目にあたる時期の新弾として注目されています。"},
            {"q": "新レアリティ「スーパーリーダーパラレル(L-SP)」とは何ですか？",
             "a": "OP-17で初登場する、リーダーカードのさらに上位にあたる新しいレアリティです。従来のリーダーパラレルより封入が絞られると見られており、メディアの予想買取価格はルフィのL-SPで約1.5万〜2.5万円とされています(非公式の予想)。実際の封入率と初動相場は発売後に判明し、BOX相場を左右する最大の変数になります。"},
            {"q": "OP-17は買いですか？売りですか？",
             "a": "定価¥5,760で抽選・予約できた分は、中立シナリオでも十分な含み益が見込めます。一方で発売前のプレ値購入は利幅が小さく、弱気シナリオでは含み損になり得ます。売却を考えている場合は発売直後1〜2週間の買取推移を、長期保有を狙う場合は再販後(9〜10月)の押し目を見るのが基本的な考え方です。相場は下落もあり得るため、最終判断はご自身の責任で行ってください。"},
            {"q": "過去の周年タイミングの弾と比べてどうですか？",
             "a": "8月に発売されてきた新時代の主役(OP-05)・新たなる皇帝(OP-09)・受け継がれる意志(OP-13)は、いずれも新レアリティや特別仕様を導入し、現在は定価の4.5倍以上を維持しています。OP-17も新レアリティL-SPを導入し四皇をテーマに据えているため、この系譜を継ぐ構成です。ただし過去3弾の高倍率は1年以上かけて形成されたもので、発売直後から同水準になるとは限りません。"},
        ],
    },
    {
        "slug": "shikou-treasure-get",
        "nav_label": "4周年！四皇トレジャーゲット全7種",
        "crumb": "4周年！四皇トレジャーゲットキャンペーンパック",
        "date": "2026-08-23",
        "date_jp": "2026年8月23日",
        "title": "4周年！四皇トレジャーゲットキャンペーンパック全7種まとめ｜当たりはルフィP-099・未開封で売るか開封するか期待値検証",
        "h1": "4周年！四皇トレジャーゲットキャンペーンパック全7種まとめ｜当たりはルフィP-099・未開封で売るか開封するか期待値を検証",
        "meta_desc": "OP-17「世界最強の戦士」発売に合わせて2026年8月22日から配布中の「4周年！四皇トレジャーゲットキャンペーンパック」全7種を解説。現四皇4人と元四皇3人=歴代四皇がそろうラインナップの収録内容と元カード対応、税込2,000円ごとに1パックの配布条件、発売直後の相場、未開封のまま売るか開封するかの期待値比較、混同しやすい4th Anniversary Set・カードステッカーvol.1との違いまで整理します。",
        "og_title": "4周年！四皇トレジャーゲットパック全7種｜当たりはルフィP-099・期待値検証",
        "og_desc": "OP-17発売に合わせて配布中の4周年プロモパック全7種を解説。収録カードと元カード対応、2,000円ごと1パックの配布条件、発売直後の相場、未開封で売るか開封するかの期待値比較。",
        "meta_line": "4周年プロモパック全7種・配布条件・相場・期待値検証",
        "hero_label": "🎁 4周年！四皇トレジャーゲットキャンペーン - 2026年8月22日(土)開始",
        "hero_big": "1パック1枚・全7種ランダム",
        "hero_sub": "ONE PIECEカードゲーム関連商品を税込2,000円購入ごとに1パックもらえる4周年記念のプロモパック。OP-17「世界最強の戦士」のBOX内に封入されているものではなく、購入額に応じて配布されるキャンペーン品です。7種は歴代四皇がそろう構成で、当たりは紫のモンキー・D・ルフィ【P-099】。",
        "disclaimer": "本記事は2026年8月23日時点で確認できる公開情報に基づく参考情報です。掲載するカード相場・パック相場は、発売直後(配布開始翌日)の<strong>ショップ販売価格やフリマアプリの初動実績を集計した目安</strong>であり、取引実績が乏しい段階の数値を含みます。プロモカードの配布はなくなり次第終了で、配布数の総量は公表されていません。<strong>封入率(7種の出現比率)は公式から発表されていない</strong>ため、本記事の期待値試算は「7種が均等に出る」と仮定した机上の計算です。実際の相場は今後の配布量・需給で大きく変動し、記載の水準を下回ることも十分あり得ます。投資助言を目的とするものではありません。売買の判断はご自身の責任で行ってください。BOX買取価格は当サイトが最大9店舗から自動取得した実データですが、実際の売却時は各店の公式ページで最終価格をご確認ください。",
        "related": '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較(毎日更新)</li>\n'
                   '<li><a href="op-17-forecast.html">【発売前予想】世界最強の戦士(OP-17) BOX相場3シナリオ</a> — 発売前に立てた3シナリオと、発売後の実データの答え合わせ</li>\n'
                   '<li><a href="box/op-17.html">世界最強の戦士(OP-17) BOX買取価格</a> — OP-17の店舗別買取価格を毎日更新</li>\n'
                   '<li><a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> — BOXを売る場合の店舗選びと高く売るコツ</li>\n'
                   '<li><a href="kougaku-ranking.html">高額BOXランキング・絶版ガイド</a> — 全弾の最高買取・定価比ランキング</li>\n'
                   '<li><a href="weekly.html">週間値動きランキング</a> — 直近7日間の値上がり・値下がりを毎日自動更新</li>',
        "body": """<p>ブースターパック<strong>「世界最強の戦士」(OP-17)</strong>の発売に合わせて、<strong>2026年8月22日(土)</strong>から<strong>「4周年！四皇トレジャーゲットキャンペーン」</strong>が始まりました。ONE PIECEカードゲーム関連商品を<strong>税込2,000円購入ごとに1パック</strong>もらえるプロモパックで、中身は<strong>1パック1枚・全7種ランダム</strong>です。</p>

<p>まず最初に押さえておきたいのは、<strong>このプロモパックはOP-17のBOX内に封入されているものではない</strong>ということ。あくまで購入額に応じて店頭で配られるキャンペーン品で、数量限定・なくなり次第終了、店舗によっては実施していない場合もあります。本記事では収録7種のリストと元カードの対応、発売直後の相場、そして<strong>「未開封のまま売るのと、開封してルフィを狙うのはどちらが得か」</strong>を実際の数字で検証します。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・配布条件は「ワンピカード関連商品を税込2,000円購入ごとに1パック」。BOX封入ではなくキャンペーン配布品<br>
・7種は<strong>現四皇4人＋元四皇3人=歴代四皇コンプリート</strong>の構成。<strong>明確な当たりは紫のモンキー・D・ルフィ【P-099】</strong>で、他6種とは相場が2倍以上離れている<br>
・未開封パックの相場と、開封して1枚ずつ売った場合の期待値は<strong>どの価格を基準にするかで結論が逆転する</strong>(後述)</div>

<h2>配布条件・開催期間</h2>
<table class="price-table">
<thead><tr><th>項目</th><th>内容</th></tr></thead>
<tbody>
<tr><td>キャンペーン名</td><td>4周年！四皇トレジャーゲットキャンペーン</td></tr>
<tr><td>開始日</td><td>2026年8月22日(土) ※OP-17「世界最強の戦士」発売日と同日</td></tr>
<tr><td>終了</td><td>なくなり次第終了(数量限定)</td></tr>
<tr><td>配布条件</td><td>ONE PIECEカードゲーム関連商品を<strong>税込2,000円購入ごとに1パック</strong></td></tr>
<tr><td>パック仕様</td><td>1パック1枚入り・全7種ランダム</td></tr>
<tr><td>注意</td><td>実施は各店舗の判断。<strong>キャンペーン非実施の店舗もある</strong></td></tr>
</tbody>
</table>

<p>「2,000円ごとに1パック」なので、<a href="box/op-17.html">OP-17のBOX(定価¥5,760)</a>を1つ買えば<strong>プロモパック2パック</strong>が付く計算になります。実際、楽天ブックスではOP-17の1BOXに「4周年！四皇トレジャーゲットキャンペーンパック×2パック」を特典として付けた商品が販売されていました。ただしこれは店舗ごとの運用であり、すべての販売店が同じ条件とは限りません。</p>

<h2>収録カード全7種リスト</h2>
<p>7種はすべて<strong>既存カードのプロモ版(4周年ロゴ入り)</strong>です。元となったカードの型番と合わせて整理します。ルフィとティーチの2枚のみ、プロモ専用のP-番号が割り当てられています。</p>

<table class="price-table">
<thead><tr><th>カード名</th><th>型番</th><th>色</th><th>四皇の区分</th><th>元カード / レアリティ</th></tr></thead>
<tbody>
<tr class="best"><td><strong>モンキー・D・ルフィ</strong></td><td>P-099</td><td>紫</td><td>現四皇</td><td>プロモ専用ナンバー(P)</td></tr>
<tr><td>マーシャル・D・ティーチ<br><span style="font-size:11px;color:#6b7280">黒ひげ</span></td><td>P-100</td><td>黒</td><td>現四皇</td><td>プロモ専用ナンバー(P)</td></tr>
<tr><td>シャンクス</td><td>OP14-027</td><td>緑</td><td>現四皇</td><td>OP-14収録 / R</td></tr>
<tr><td>バギー</td><td>OP12-049</td><td>青</td><td>現四皇</td><td>OP-12収録 / UC</td></tr>
<tr><td>エドワード・ニューゲート<br><span style="font-size:11px;color:#6b7280">白ひげ</span></td><td>ST15-002</td><td>赤</td><td>元四皇</td><td>スタートデッキ収録 / SR</td></tr>
<tr><td>シャーロット・リンリン<br><span style="font-size:11px;color:#6b7280">ビッグ・マム</span></td><td>ST20-005</td><td>黄</td><td>元四皇</td><td>スタートデッキ収録 / SR</td></tr>
<tr><td>カイドウ</td><td>EB04-030</td><td>紫</td><td>元四皇</td><td>EB-04収録 / R</td></tr>
</tbody>
</table>

<div class="callout"><strong>7種は「歴代四皇コンプリート」になっている:</strong> ラインナップをよく見ると、<strong>現在の四皇4人(ルフィ・シャンクス・黒ひげ・バギー)と、その座を退いた元四皇3人(白ひげ・ビッグ・マム・カイドウ)</strong>で、ちょうど歴代の四皇が全員そろう構成になっています。キャンペーン名の「四皇トレジャーゲット」はここから来ており、単なる人気キャラの寄せ集めではありません。色も赤・緑・青・紫・黒・黄と分散しており、7種すべて異なるキャラクター・異なる立ち位置で組まれています。</div>

<p>元カードの出自もばらけているのが特徴です。ルフィとティーチはプロモ専用のP-番号が新規に割り当てられた一方、シャンクスは<a href="op-14-atari-guide.html">OP-14</a>、バギーは<a href="op-12-atari-guide.html">OP-12</a>、カイドウは<a href="eb-04-atari-guide.html">EB-04</a>収録カードのプロモ版、ニューゲートとリンリンはスタートデッキ収録カードのプロモ版です。</p>

<h2>当たりカードは紫ルフィ【P-099】</h2>
<p>配布開始翌日(2026年8月23日)時点で、<strong>明確に頭ひとつ抜けているのは紫のモンキー・D・ルフィ【P-099】</strong>です。他の6種が1,000円前後〜1,500円前後のレンジに収まっているのに対し、ルフィだけが2,000円台後半で取引されています。</p>

<h3>フリマアプリの初動実売価格</h3>
<p>配布開始直後のフリマアプリ(メルカリ)における取引・出品状況をまとめたものです。プロモカードは配布から日が浅く<strong>取引実績が乏しいカードが多い</strong>ため、取引が成立していないものは出品価格の下限を記載しています。</p>

<table class="price-table">
<thead><tr><th>カード</th><th style="text-align:right">初動の目安</th><th>状況</th></tr></thead>
<tbody>
<tr class="best"><td><strong>ルフィ P-099</strong></td><td class="price">約¥2,600</td><td>取引成立(¥2,599〜¥2,666)</td></tr>
<tr><td>シャンクス OP14-027</td><td class="price">¥1,500〜</td><td>取引実績なし・出品下限</td></tr>
<tr><td>ティーチ P-100</td><td class="price">¥1,444〜</td><td>取引実績なし・出品下限</td></tr>
<tr><td>カイドウ EB04-030</td><td class="price">約¥1,222</td><td>取引成立</td></tr>
<tr><td>ニューゲート ST15-002</td><td class="price">約¥1,000</td><td>取引成立</td></tr>
<tr><td>バギー OP12-049</td><td class="price">約¥1,000</td><td>取引成立</td></tr>
<tr><td>リンリン ST20-005</td><td class="price">¥777〜¥1,111</td><td>取引成立(幅あり)</td></tr>
</tbody>
</table>

<h3>ショップ販売価格は大きく異なる</h3>
<p>注意が必要なのは、<strong>カードショップの販売価格とフリマ相場が大きく乖離している</strong>点です。ルフィP-099はカードショップの通販で<strong>¥1,980〜¥2,480</strong>あたりで並んでおり(店舗により差あり)、フリマの実売とおおむね近い水準です。一方、それ以外の6種はショップ側では<strong>¥180〜¥480程度</strong>で売られているケースが多く、フリマの1,000円台とは別物の価格帯になっています。</p>

<div class="callout"><strong>なぜ差が出るのか:</strong> フリマは「1枚だけ欲しい人が送料込みで買う」市場、ショップの販売価格は「在庫を並べて回転させる」価格です。プロモは配布数が多く、ショップには短期間で大量に集まるため、単価の安いカードほど早く値を下げる傾向があります。<strong>フリマの1,000円台は送料と手数料を含んだ価格</strong>である点も見落とせません(後述の期待値検証ではここを差し引いて計算します)。</div>

<h2>未開封パックの相場</h2>
<p>開封せずパックのまま売る場合の相場も確認しておきます。</p>
<ul>
<li><strong>スニーカーダンク(スニダン)</strong>: 1パックあたり<strong>¥1,000〜</strong>の出品が確認できます(2026年8月23日時点)。1パック・2パック・100パックといった単位で出品されています。</li>
<li><strong>フリマアプリ</strong>: 10パックセットで<strong>¥7,000〜¥7,999</strong>程度。1パックあたり<strong>¥700〜¥800</strong>の換算です。</li>
</ul>
<p>まとめ売りになるほど1パック単価が下がるのは、送料・手数料の負担割合が小さくなる分を価格に反映しているためです。</p>

<h2>【本題】未開封で売るか、開封してルフィを狙うか</h2>
<p>ここからが本題です。7種の相場が分かったので、<strong>「未開封のまま売る」と「開封して1枚ずつ売る」のどちらが期待値が高いか</strong>を計算します。</p>

<div class="callout"><strong>前提条件:</strong> 封入率は公式から発表されていないため、<strong>7種が均等(各1/7)に出ると仮定</strong>します。実際にはレアリティ差(ルフィ・ティーチのP-番号組が絞られている可能性)があり得るため、あくまで机上の試算です。また相場は配布開始翌日という<strong>取引実績が薄い段階の数値</strong>である点にもご注意ください。</div>

<h3>ケース1: 開封してフリマで1枚ずつ売る</h3>
<p>フリマの初動価格をそのまま合計すると、7種の合計は<strong>約¥9,743</strong>。7で割った<strong>1パックあたりの期待値は約¥1,392</strong>です。ただしフリマには手数料と送料がかかります。販売手数料10%・送料210円(ネコポス相当)を差し引くと、手取りベースの期待値は<strong>1パックあたり約¥1,043</strong>まで下がります。</p>

<table class="price-table">
<thead><tr><th>基準</th><th style="text-align:right">1パックあたり期待値</th></tr></thead>
<tbody>
<tr><td>フリマ表示価格の単純平均</td><td class="price">約¥1,392</td></tr>
<tr class="best"><td><strong>手数料10%・送料210円を差し引いた手取り</strong></td><td class="price"><strong>約¥1,043</strong></td></tr>
<tr><td>ショップ販売価格ベースの単純平均(参考)</td><td class="price">約¥609</td></tr>
</tbody>
</table>

<h3>ケース2: 未開封のまま売る</h3>
<p>未開封パックを1パック¥1,000で単品売りした場合、同じく手数料10%・送料210円を引くと手取りは<strong>約¥690</strong>。10パックまとめて¥7,500で売った場合は、手数料・送料を引いて<strong>1パックあたり約¥654</strong>です。</p>

<h3>結論: 数字上は開封が有利。ただし前提が弱い</h3>
<table class="price-table">
<thead><tr><th>戦略</th><th style="text-align:right">1パックあたり手取り</th><th>手間</th></tr></thead>
<tbody>
<tr class="best"><td><strong>開封して1枚ずつフリマ売り</strong></td><td class="price"><strong>約¥1,043</strong></td><td>1枚ずつ発送(手間大)</td></tr>
<tr><td>未開封を単品売り</td><td class="price">約¥690</td><td>1パックずつ発送</td></tr>
<tr><td>未開封をまとめ売り</td><td class="price">約¥654</td><td>1回の発送で完結(手間小)</td></tr>
</tbody>
</table>

<p>手取りベースでは<strong>開封して1枚ずつ売る方が1パックあたり約350〜390円有利</strong>という計算になります。ただし、この結論には次の弱点があります。</p>
<ul>
<li><strong>封入率が非公表</strong>: 均等前提が崩れると期待値は変わります。ルフィの出現率が1/7より低ければ、開封の優位はそのまま縮みます。</li>
<li><strong>取引実績が薄い</strong>: シャンクス・ティーチは配布翌日時点で<strong>取引成立が確認できず、出品価格のみ</strong>です。実際に売れる価格はこれを下回る可能性があります。</li>
<li><strong>ショップ基準では逆転する</strong>: カードショップの販売価格を基準にすると期待値は約¥609まで落ち、未開封まとめ売りとほぼ同等かそれ以下になります。<strong>どの市場で売るかで結論が変わる</strong>ということです。</li>
<li><strong>プロモは値を下げやすい</strong>: 配布は「なくなり次第終了」ですが、キャンペーン期間中は供給が増え続けます。配布終了までは下方向の圧力がかかりやすいと考えるのが自然です。</li>
<li><strong>手間が7倍</strong>: 1枚ずつの梱包・発送・取引対応を7回繰り返して差額が約350円/パックです。枚数が少ないうちは手間に見合わない可能性があります。</li>
</ul>

<div class="callout"><strong>実務的な落としどころ:</strong> ルフィP-099だけ抜いて単品で売り、残り6枚はまとめ売り(あるいは手元に残す)、という折衷が現実的です。ルフィと他6種の価格差が最も大きい今の局面では、<strong>当たり1枚を確実に現金化し、残りは手間をかけない</strong>のが手取りと労力のバランスが取りやすい選択になります。</div>

<h2>OP-17のBOXと合わせて考える</h2>
<p>転売・投資目線では、プロモパック単体ではなく<strong>OP-17のBOXとセットで見る</strong>のが実態に合います。定価¥5,760のBOXを1つ買えばプロモパック2パックが付き、そのBOX自体の買取価格は当サイトの実データで<strong>最高{{OP17_PRICE}}({{OP17_MULT}})</strong>です。</p>

<table class="price-table">
<thead><tr><th>内訳</th><th style="text-align:right">金額</th></tr></thead>
<tbody>
<tr><td><a href="box/op-17.html">OP-17 BOX</a> 買取最高(当サイト実データ)</td><td class="price">{{OP17_PRICE}}</td></tr>
<tr><td>プロモパック2パック分(未開封まとめ売り換算 約¥654×2)</td><td class="price">約¥1,308</td></tr>
<tr class="best"><td><strong>BOX定価</strong></td><td class="price"><strong>¥5,760</strong></td></tr>
</tbody>
</table>

<p>定価で入手できた場合、BOX単体でも定価の{{OP17_MULT}}の水準にあり、そこにプロモパック2パック分が上乗せされる形です。<strong>プロモは「おまけ」の域を出ませんが、BOXの利幅に対して数%を積み増す要素</strong>にはなります。逆に言えば、プロモパック欲しさに定価を大きく超えるプレ値でBOXを買う理由にはなりません。</p>

<p>発売前に当サイトが立てた3シナリオ(弱気¥11,000/中立¥16,000/強気¥24,000)との答え合わせは<a href="op-17-forecast.html">OP-17 BOX相場3シナリオ予想</a>で確認できます。BOXの店舗別買取価格は<a href="/onepiece">比較トップ</a>および<a href="box/op-17.html">OP-17個別ページ</a>で毎日更新しています。</p>

<h2>混同しやすい4周年関連の3つのキャンペーンの違い</h2>
<p>2026年8月は4周年関連の施策が複数同時に走っており、SNSでも混同が起きています。名前が似ているものを整理します。</p>

<table class="price-table">
<thead><tr><th>名称</th><th>入手方法</th><th>内容</th></tr></thead>
<tbody>
<tr class="best"><td><strong>4周年！四皇トレジャーゲットキャンペーンパック</strong><br><span style="font-size:11px;color:#6b7280">本記事の対象</span></td><td>関連商品 税込2,000円購入ごとに1パック</td><td>1パック1枚・全7種ランダムのプロモカード</td></tr>
<tr><td>カードステッカー vol.1</td><td>公認店で関連商品購入時にランダム1枚</td><td>OP-17収録キャラをデザインした<strong>ステッカー</strong>(カードではない)</td></tr>
<tr><td>4th Anniversary Set</td><td>プレミアムバンダイ等での<strong>抽選販売</strong>(有料商品)</td><td>特別デザインのプロモカード9枚入りの記念セット</td></tr>
</tbody>
</table>

<p>特に<strong>「4th Anniversary Set」は抽選販売の有料商品</strong>で、無料配布の四皇トレジャーゲットパックとはまったくの別物です。フリマで「4周年プロモ」と一括りにされた出品を買う際は、<strong>どのキャンペーンのカードなのかを必ず確認</strong>してください。</p>

<h2>購入・売却時の注意点</h2>
<h3>P-099には別バージョンが存在する</h3>
<p>最も注意すべき落とし穴です。<strong>「モンキー・D・ルフィ P-099」という型番のカードは、四皇トレジャーゲット版以外にも存在します</strong>(テーマプロモーションパック「新四皇」版など)。ショップの買取表や販売ページで<strong>型番だけを見て価格を判断すると、別バージョンの相場を見てしまう可能性</strong>があります。四皇トレジャーゲット版は<strong>4周年ロゴ入り</strong>が目印です。売買時は商品名の「四皇トレジャーゲットキャンペーンパック版」という表記まで確認しましょう。</p>

<h3>キャンペーン非実施の店舗がある</h3>
<p>配布は各店舗の判断で行われており、<strong>実施していない店舗、既に配布終了している店舗</strong>があります。プロモ目当てで購入する場合は、事前に店舗の告知(SNS等)を確認するのが確実です。</p>

<h3>プロモは「配布終了後」に値が動く</h3>
<p>プロモカードは配布期間中は供給が増え続けるため、相場が上がりにくい構造です。値動きを見るなら<strong>配布終了後、供給が止まってから</strong>が本番になります。急いで売る必要がなければ、配布終了のアナウンスを待ってから判断するのも一つの手です(ただし人気が続かず下がったまま、というケースもあります)。</p>

<h3>状態管理は通常のカードと同じ</h3>
<p>無料配布のプロモとはいえ、傷み・折れがあれば当然価値は下がります。開封する場合はスリーブに入れる、未開封で保管する場合はパックに折り目を付けないなど、通常のカードと同じ扱いを心がけてください。</p>""",
        "faq": [
            {"q": "4周年！四皇トレジャーゲットキャンペーンパックはどうすればもらえますか？",
             "a": "ONE PIECEカードゲーム関連商品を税込2,000円購入ごとに1パックもらえます。2026年8月22日(土)開始で、なくなり次第終了の数量限定です。ただし実施は各店舗の判断のため、キャンペーンを行っていない店舗や既に配布を終えている店舗もあります。事前に店舗の告知を確認するのが確実です。"},
            {"q": "OP-17のBOXを買うと何パックもらえますか？",
             "a": "「税込2,000円ごとに1パック」という条件のため、定価¥5,760のOP-17 BOXを1つ購入すると2パックもらえる計算になります。実際に楽天ブックスではOP-17 1BOXにキャンペーンパック×2を特典として付けた商品が販売されていました。ただし配布の運用は店舗ごとに異なるため、購入先の条件をご確認ください。"},
            {"q": "全7種のうち当たりはどれですか？",
             "a": "紫のモンキー・D・ルフィ【P-099】です。配布開始翌日(2026年8月23日)時点でフリマの実売が約¥2,600、カードショップの販売価格が¥1,980〜¥2,480あたりで、他6種(おおむね¥800〜¥1,500)から頭ひとつ抜けています。ただし配布直後の価格であり、今後の配布量次第で変動します。"},
            {"q": "未開封で売るのと開封して売るのはどちらが得ですか？",
             "a": "7種が均等に出ると仮定した試算では、開封して1枚ずつフリマで売った場合の手取り期待値が1パックあたり約¥1,043、未開封のまとめ売りが約¥654で、数字上は開封が有利です。ただし封入率は公式非公表で、シャンクス・ティーチは取引実績がまだ乏しく、カードショップの販売価格を基準にすると期待値は約¥609まで下がって逆転します。1枚ずつ発送する手間も7倍になるため、ルフィだけ単品で売り残りはまとめる折衷が現実的です。"},
            {"q": "このプロモパックはOP-17のBOXに入っていますか？",
             "a": "入っていません。OP-17「世界最強の戦士」のBOX内に封入されているものではなく、ONE PIECEカードゲーム関連商品の購入額(税込2,000円ごと)に応じて店頭で配布されるキャンペーン品です。BOXを開封してもこのプロモは出てきません。"},
            {"q": "「4th Anniversary Set」や「カードステッカーvol.1」とは違うものですか？",
             "a": "すべて別物です。4th Anniversary Setはプレミアムバンダイ等で抽選販売された有料の記念商品(特別デザインのプロモカード9枚入り)、カードステッカーvol.1は公認店で購入時にランダム配布されるステッカーでカードではありません。四皇トレジャーゲットキャンペーンパックは2,000円購入ごとに配布される全7種のプロモカードです。フリマで「4周年プロモ」とまとめられた出品を買う際は、どのキャンペーンのものか必ず確認してください。"},
            {"q": "ルフィP-099を売る時に気をつけることはありますか？",
             "a": "「P-099」という型番のルフィには四皇トレジャーゲット版以外のバージョン(テーマプロモーションパック新四皇版など)も存在します。型番だけで買取表の価格を見ると別バージョンの相場を参照してしまう可能性があるため、商品名に「四皇トレジャーゲットキャンペーンパック版」と明記されているかを確認してください。4周年ロゴ入りが目印です。"},
        ],
    },
    {
        "slug": "nika-luffy-comipara",
        "nav_label": "ニカルフィ コミパラ徹底解説",
        "crumb": "ニカルフィ コミパラ(OP05-119)",
        "date": "2026-08-24",
        "date_jp": "2026年8月24日",
        "title": "ニカルフィ コミパラ(OP05-119)徹底解説｜買取相場・PSA10・封入率288BOXに1枚の実態",
        "h1": "ニカルフィ コミパラ(OP05-119)徹底解説｜買取相場・PSA10相場・封入率288BOXに1枚の実態",
        "meta_desc": "ワンピースカード最高峰の1枚「モンキー・D・ルフィ コミックパラレル(ニカルフィ/OP05-119)」を単体で徹底解説。2026年8月24日時点の買取80万円・販売99.8万円・PSA10相場133万円という現在地、24カートン(288BOX)に約1枚という通常コミパラの4倍低い封入率、PSA10取得率71.7%が意味する状態難、直近3ヶ月で110万→80万に振れた価格推移、見分け方と売買の注意点までデータで整理します。",
        "og_title": "ニカルフィ コミパラ(OP05-119)徹底解説｜相場・PSA10・封入率",
        "og_desc": "ワンピカード最高峰の1枚ニカルフィ コミパラを単体解説。買取80万・PSA10相場133万、288BOXに1枚の封入率、PSA10取得率71.7%が示す状態難、価格推移と売買の注意点。",
        "meta_line": "ニカルフィ コミパラの相場・封入率・PSA10・売買の注意点",
        "hero_label": "モンキー・D・ルフィ コミックパラレル【OP05-119】",
        "hero_big": "買取 約¥800,000",
        "hero_sub": "新時代の主役(OP-05)収録。太陽の神ニカ(ギア5)を描いた、ワンピースカードでもっとも有名なコミックパラレル。封入率は24カートン(288BOX)に約1枚と通常のコミパラの4倍低く、PSA10取得率も71.7%と低め。相場・鑑定データは2026年8月24日時点。",
        "disclaimer": "本記事のカード相場は<strong>2026年8月24日時点</strong>にカード相場メディア altema が掲載する<strong>カードラッシュの買取・販売価格</strong>、およびPSA10相場(2026年8月19日更新)を基準にした目安です。1店舗の価格を基準にしているため、他店の買取額や実際の取引価格とは異なります。封入率は公式発表ではなく、開封報告等に基づく推定値です。高額カードは状態(センタリング・キズ・白かけ)により査定額が大きく変わり、記載の金額を保証するものではありません。BOX買取価格は当サイトが最大9店舗から自動取得した実データです。売買の判断はご自身の責任で行ってください。",
        "related": '<li><a href="op-05-atari-guide.html">新時代の主役(OP-05) 当たりカードガイド</a> — 収録弾の当たり全体と封入率</li>\n'
                   '<li><a href="box/op-05.html">新時代の主役(OP-05) BOX買取価格</a> — 店舗別のBOX買取価格を毎日更新</li>\n'
                   '<li><a href="roger-gold-comipara.html">ロジャー ゴールドコミパラ(OP09-118)徹底解説</a> — 2周年弾の最高峰カード</li>\n'
                   '<li><a href="red-comipara-guide.html">レッドコミパラ3種(OP-13)徹底解説</a> — 現在のワンピカード最高額帯</li>\n'
                   '<li><a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> — BOXを売るときの店舗選び</li>\n'
                   '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較</li>',
        "body": """<p><strong>モンキー・D・ルフィ コミックパラレル【OP05-119】</strong>、通称<strong>「ニカルフィ コミパラ」</strong>は、ワンピースカードゲームでもっとも知名度の高い高額カードの1枚です。<a href="op-05-atari-guide.html">新時代の主役(OP-05)</a>に収録され、太陽の神ニカ(ギア5)に覚醒したルフィを漫画のコマ風の全面イラストで描いています。</p>

<p>本記事では、このカード1枚に絞って<strong>現在の買取・販売・PSA10相場、封入率、鑑定データ、価格推移、売買の注意点</strong>を整理します。相場は<strong>2026年8月24日時点</strong>の実測値です。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・買取<strong>約80万円</strong>／販売約99.8万円／PSA10相場<strong>約133万円</strong>(2026年8月24日時点)<br>
・封入率は<strong>24カートン(288BOX)に約1枚</strong>。通常のコミパラ(6カートン=約72BOXに1枚)の<strong>4倍希少</strong><br>
・PSA10取得率<strong>71.7%</strong>は同格カードより明確に低い。<strong>状態難のカード</strong>で、素体で買うときほど状態確認が重要</div>

<h2>基本情報</h2>
<table class="price-table">
<thead><tr><th>項目</th><th>内容</th></tr></thead>
<tbody>
<tr><td>カード名</td><td>モンキー・D・ルフィ</td></tr>
<tr><td>型番</td><td><strong>OP05-119</strong></td></tr>
<tr><td>レアリティ</td><td>コミックパラレル(SEC-SP/スーパーパラレル)</td></tr>
<tr><td>収録</td><td><a href="op-05-atari-guide.html">ブースターパック「新時代の主役」(OP-05)</a></td></tr>
<tr><td>発売日</td><td>2023年8月26日</td></tr>
<tr><td>通称</td><td>ニカルフィ コミパラ／ギア5 コミパラ</td></tr>
</tbody>
</table>

<h2>現在の相場(2026年8月24日時点)</h2>
<table class="price-table">
<thead><tr><th>区分</th><th style="text-align:right">金額</th><th>備考</th></tr></thead>
<tbody>
<tr class="best"><td><strong>買取価格</strong></td><td class="price"><strong>約¥800,000</strong></td><td>素体(未鑑定)</td></tr>
<tr><td>販売価格</td><td class="price">約¥998,000</td><td>素体(未鑑定)</td></tr>
<tr><td>PSA10相場</td><td class="price">約¥1,330,000</td><td>2026年8月19日更新</td></tr>
</tbody>
</table>

<p>素体の買取80万円に対してPSA10が133万円と、<strong>鑑定で約1.7倍</strong>になる計算です。ただし後述のとおりこのカードはPSA10取得率が低く、鑑定に出して10が付かなければ差額は取れません。</p>

<h2>封入率｜288BOXに約1枚という現実</h2>
<p>ワンピースカードのコミックパラレル(スーパーパラレル)の封入率は、一般に<strong>6カートン(約72BOX)に約1枚</strong>とされています。ところがニカルフィ コミパラは、その中でもさらに絞られており、<strong>24カートン(約288BOX)に約1枚</strong>という水準です。<strong>通常のコミパラの約4倍低い封入率</strong>ということになります。</p>

<div class="callout"><strong>288BOXがどれくらいか:</strong> OP-05のBOX定価は¥5,280。288BOX買うと単純計算で<strong>約152万円</strong>です。買取80万円のカードを自引きで狙うのは、期待値でまったく見合いません。「BOXを買って当てる」より「カードを直接買う」ほうが安いという、高額コミパラに共通する構図です。BOX相場は<a href="box/op-05.html">OP-05個別ページ</a>で毎日更新しています。</div>

<h2>PSA10データ｜取得率71.7%は同格カードより低い</h2>
<table class="price-table">
<thead><tr><th>カード</th><th style="text-align:right">PSA10鑑定枚数</th><th style="text-align:right">PSA10取得率</th></tr></thead>
<tbody>
<tr class="best"><td><strong>ニカルフィ コミパラ(OP05-119)</strong></td><td class="price"><strong>2,822枚</strong></td><td class="price"><strong>71.7%</strong></td></tr>
<tr><td><a href="roger-gold-comipara.html">ロジャー ゴールドコミパラ(OP09-118)</a></td><td class="price">1,159枚</td><td class="price">89.6%</td></tr>
<tr><td><a href="red-comipara-guide.html">ルフィ レッドコミパラ(OP13-118)</a></td><td class="price">459枚</td><td class="price">87.3%</td></tr>
</tbody>
</table>

<p>ここが本カードの最大の特徴です。<strong>PSA10取得率71.7%</strong>は、ロジャー(89.6%)やレッドコミパラ(87.3%)と比べて明確に低く、<strong>10人が鑑定に出せば3人は9以下になる</strong>計算になります。</p>

<p>理由として考えられるのは、<strong>発売が2023年8月と古く、当時は現在ほど保管・美品意識が高くなかった</strong>こと、そして鑑定枚数2,822枚という<strong>母数の多さ</strong>です。長く流通してきた分、状態のばらつきが大きくなっています。</p>

<div class="callout"><strong>売買への影響:</strong> 素体で買う場合、<strong>「PSA10が狙える状態か」を前提にした値付けは危険</strong>です。逆に売る側から見れば、状態のよい素体は相対的に価値が高く、PSA10鑑定済みの個体はプレミアムが乗りやすい、ということでもあります。</div>

<h2>価格推移｜直近3ヶ月で110万→80万</h2>
<table class="price-table">
<thead><tr><th>時点</th><th style="text-align:right">買取価格</th><th>状況</th></tr></thead>
<tbody>
<tr><td>2026年5月5日</td><td class="price">約¥550,000</td><td>調整局面</td></tr>
<tr><td>2026年6月15日</td><td class="price">約¥1,100,000</td><td>直近ピーク</td></tr>
<tr><td>2026年7月15日</td><td class="price">約¥1,000,000</td><td>高値圏</td></tr>
<tr class="best"><td><strong>2026年8月24日</strong></td><td class="price"><strong>約¥800,000</strong></td><td>ピークから約27%下落</td></tr>
</tbody>
</table>

<p>5月の55万円から6月に110万円へ<strong>2倍に急騰</strong>し、その後8月にかけて80万円まで戻しています。<strong>3ヶ月で倍になり、2ヶ月で3割近く下げた</strong>ことになり、値動きの荒さがそのまま数字に出ています。</p>

<p>この規模の値幅は、売る側にとっては「いつ売るか」で数十万円変わることを意味します。<strong>売却を考えるなら、単日の買取表だけでなく数ヶ月の推移を見る</strong>ことをおすすめします。</p>

<h2>見分け方</h2>
<h3>コミックパラレルの識別</h3>
<p>コミックパラレル最大の目印は<strong>背景が漫画のコマになっている</strong>ことです。通常版やほかのパラレルはイラスト背景ですが、コミパラだけは原作の誌面がそのまま背景に使われています。</p>

<p>注意が必要なのは、<strong>カード右下のレアリティ表記だけでは通常のパラレルと区別がつかない</strong>点です。表記ではなく<strong>背景で判断</strong>してください。</p>

<h3>OP-05のほかのルフィとの混同</h3>
<p>OP-05には同じニカルフィのカードが複数あり、<strong>シークレットパラレル(SEC-P)</strong>との取り違えが起こりがちです。相場は桁が違い、SECパラレルの買取は約2万円台です。フリマの出品で「ニカルフィ パラレル」とだけ書かれている場合は、<strong>背景がコマかどうか</strong>と<strong>型番OP05-119</strong>の両方を必ず確認しましょう。</p>

<h3>偽物(レプリカ)対策</h3>
<p>高額カードには模造品が出回ります。一般的な判別点は<strong>レリーフ加工(表面の凹凸)の有無</strong>で、本物はキャラクターが浮き上がるような立体感があります。また裏面の青色が本物より<strong>紫がかっている</strong>個体は要注意とされています。高額帯では、<strong>鑑定済みを買う・実店舗で現物を見る</strong>のがもっとも確実です。</p>

<h2>売買の注意点</h2>
<ul>
<li><strong>買取表の「版」を確認する</strong> — 同じルフィでもコミパラ・SECパラ・リーダーパラレルで相場が桁違いです。型番(OP05-119)まで一致しているか確認しましょう。</li>
<li><strong>状態の影響が大きい</strong> — PSA10取得率71.7%が示すとおり、このカードは状態のばらつきが大きい部類です。センタリング・角のスレ・表面のキズは査定に直結します。鑑定に出すかの判断基準は <a href="psa-guide.html">ワンピースカードのPSA鑑定ガイド</a> で整理しています。</li>
<li><strong>複数店を比較する</strong> — 80万円クラスでは店舗間の差がそのまま数万円〜十数万円になります。1店舗の提示で決めないのが基本です。</li>
<li><strong>推移を見てから動く</strong> — 直近3ヶ月で55万→110万→80万と振れています。急ぎでなければ数週間の値動きを追ってから判断するほうが有利になりやすい局面です。</li>
<li><strong>BOX買いで狙わない</strong> — 288BOXに1枚の封入率では、自引きを狙う費用がカードの価格を大きく上回ります。</li>
</ul>""",
        "faq": [
            {"q": "ニカルフィ コミパラ(OP05-119)の買取価格はいくらですか？",
             "a": "2026年8月24日時点で買取約80万円、販売約99.8万円、PSA10相場は約133万円です(altema掲載のカードラッシュ価格基準)。ただし2026年6月には買取110万円をつけており、直近3ヶ月で大きく振れています。売却時は最新の買取表と数ヶ月の推移の両方を確認してください。"},
            {"q": "封入率はどのくらいですか？BOXを買えば当たりますか？",
             "a": "24カートン(約288BOX)に約1枚とされ、通常のコミックパラレル(6カートン=約72BOXに約1枚)の約4倍低い水準です。OP-05のBOX定価¥5,280で288BOX買うと約152万円になり、買取80万円のカードを自引きで狙うのは期待値的に見合いません。カードを直接買うほうが安く済みます。"},
            {"q": "PSA鑑定に出すべきですか？",
             "a": "素体買取80万円に対しPSA10相場が約133万円と差はありますが、このカードのPSA10取得率は71.7%と同格カード(ロジャー89.6%、レッドコミパラ87.3%)より明確に低く、約3割はPSA9以下になる計算です。鑑定料と返却までの期間、10が付かなかった場合のリスクを踏まえて判断してください。"},
            {"q": "ほかのニカルフィのカードとどう見分けますか？",
             "a": "コミックパラレルは背景が漫画のコマになっているのが最大の目印です。右下のレアリティ表記だけでは通常のパラレルと区別がつかないため、背景で判断してください。OP-05にはシークレットパラレル版のニカルフィもあり相場は桁違い(買取約2万円台)なので、型番がOP05-119かどうかも必ず確認しましょう。"},
            {"q": "偽物を避けるにはどうすればいいですか？",
             "a": "本物にはレリーフ加工による表面の凹凸があり、キャラクターが浮き上がって見えます。偽物はこの立体感がなく、裏面の青が紫がかっていることが多いとされています。この価格帯ではPSA等の鑑定済み品を選ぶか、実店舗で現物を確認して購入するのが確実です。"},
        ],
    },
    {
        "slug": "red-comipara-guide",
        "nav_label": "レッドコミパラ3種 徹底解説",
        "crumb": "レッドコミパラ3種(OP-13)",
        "date": "2026-08-24",
        "date_jp": "2026年8月24日",
        "title": "レッドコミパラ3種(OP-13)徹底解説｜ルフィ230万・エース80万・サボ60万の相場とPSA10・封入率631BOXに1枚",
        "h1": "レッドコミパラ3種(OP-13)徹底解説｜ルフィ230万・エース80万・サボ60万の相場とPSA10・封入率631BOXに1枚",
        "meta_desc": "ワンピースカードの現在最高額帯「レッドコミックパラレル(レッドスーパーパラレル)」3種を徹底解説。受け継がれる意志(OP-13)収録のルフィOP13-118・エースOP13-119・サボOP13-120について、2026年8月24日時点の買取230万/80万/60万、PSA10相場342万/130万/84万、鑑定枚数と取得率、狙いの1枚が約631BOXに1枚という封入率、発売から1年で9倍になった価格推移までデータで整理します。",
        "og_title": "レッドコミパラ3種(OP-13)徹底解説｜相場・PSA10・封入率",
        "og_desc": "ワンピカード最高額帯のレッドコミパラ3種を解説。ルフィ230万・エース80万・サボ60万の買取、PSA10相場と鑑定枚数、631BOXに1枚の封入率、1年で9倍の価格推移。",
        "meta_line": "レッドコミパラ3種の相場・封入率・PSA10・価格推移",
        "hero_label": "ASL3兄弟 レッドコミックパラレル【OP13-118/119/120】",
        "hero_big": "ルフィ 買取 約¥2,300,000",
        "hero_sub": "受け継がれる意志(OP-13)収録。3周年記念の特別仕様「レッドスーパーパラレル」で、ルフィ・エース・サボのASL3兄弟がそろって最高額帯を形成しています。狙いの1枚を自引きする確率は約631BOXに1枚。相場・鑑定データは2026年8月24日時点。",
        "disclaimer": "本記事のカード相場は<strong>2026年8月24日時点</strong>にカード相場メディア altema が掲載する<strong>カードラッシュの買取・販売価格</strong>、およびPSA10相場(2026年8月19日更新)を基準にした目安です。1店舗の価格を基準にしているため、他店の買取額や実際の取引価格とは異なります。封入率はバンダイの公式発表ではなく、開封報告等に基づく推定値で、ソースにより数値に幅があります。数百万円規模のカードは状態(センタリング・キズ・白かけ)により査定額が大きく変わり、記載の金額を保証するものではありません。BOX買取価格は当サイトが最大9店舗から自動取得した実データです。売買の判断はご自身の責任で行ってください。",
        "related": '<li><a href="op-13-atari-guide.html">受け継がれる意志(OP-13) 当たりカードガイド</a> — 収録弾の当たり全体・ゴッドパック・封入率</li>\n'
                   '<li><a href="box/op-13.html">受け継がれる意志(OP-13) BOX買取価格</a> — 店舗別のBOX買取価格を毎日更新</li>\n'
                   '<li><a href="nika-luffy-comipara.html">ニカルフィ コミパラ(OP05-119)徹底解説</a> — もっとも有名なコミックパラレル</li>\n'
                   '<li><a href="roger-gold-comipara.html">ロジャー ゴールドコミパラ(OP09-118)徹底解説</a> — 2周年弾の最高峰カード</li>\n'
                   '<li><a href="kougaku-ranking.html">高額BOXランキング・絶版ガイド</a> — 全弾の最高買取・定価比ランキング</li>\n'
                   '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較</li>',
        "body": """<p><strong>レッドコミックパラレル</strong>(正式名称<strong>「レッドスーパーパラレル」</strong>)は、<a href="op-13-atari-guide.html">受け継がれる意志(OP-13)</a>で登場した3周年記念の特別仕様です。通常のスーパーパラレル(コミックパラレル)を<strong>赤色に染めた特別版</strong>で、<strong>ルフィ・エース・サボのASL3兄弟</strong>の3種のみが存在します。</p>

<p>2026年8月現在、この3枚は<strong>ワンピースカードの最高額帯</strong>を形成しています。本記事では3枚を横並びで比較し、<strong>相場・PSA10データ・封入率・価格推移・売買の注意点</strong>を整理します。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・買取は<strong>ルフィ230万／エース80万／サボ60万</strong>。ルフィだけが他2枚の約3倍で突出<br>
・狙いの1枚を自引きする確率は<strong>約631BOXに1枚</strong>。BOX代に換算すると約333万円で、ルフィの買取額を上回る<br>
・ルフィは発売から1年で<strong>25万円→230万円(約9倍)</strong>。ただし直近ピーク250万からは調整局面</div>

<h2>3種の基本情報</h2>
<table class="price-table">
<thead><tr><th>カード</th><th>型番</th><th>キャラクター</th></tr></thead>
<tbody>
<tr class="best"><td><strong>モンキー・D・ルフィ</strong></td><td>OP13-118</td><td>ASL3兄弟の末弟・主人公</td></tr>
<tr><td>ポートガス・D・エース</td><td>OP13-119</td><td>ASL3兄弟の次兄</td></tr>
<tr><td>サボ</td><td>OP13-120</td><td>ASL3兄弟の義兄・革命軍</td></tr>
</tbody>
</table>
<p>収録は<a href="op-13-atari-guide.html">ブースターパック「受け継がれる意志」(OP-13)</a>、発売日は<strong>2025年8月23日</strong>、BOX定価は¥5,280です。</p>

<h2>現在の相場(2026年8月24日時点)</h2>
<table class="price-table">
<thead><tr><th>カード</th><th style="text-align:right">買取</th><th style="text-align:right">販売</th><th style="text-align:right">PSA10相場</th></tr></thead>
<tbody>
<tr class="best"><td><strong>ルフィ(OP13-118)</strong></td><td class="price"><strong>約¥2,300,000</strong></td><td class="price">約¥2,780,000</td><td class="price">約¥3,420,000</td></tr>
<tr><td>エース(OP13-119)</td><td class="price">約¥800,000</td><td class="price">約¥998,000</td><td class="price">約¥1,300,000</td></tr>
<tr><td>サボ(OP13-120)</td><td class="price">約¥600,000</td><td class="price">約¥698,000</td><td class="price">約¥840,000</td></tr>
</tbody>
</table>

<p>同じレアリティ・同じ弾・同じ3兄弟でありながら、<strong>ルフィだけがエースの約2.9倍、サボの約3.8倍</strong>という差がついています。封入率は3種でほぼ同等と考えられるため、この差は<strong>純粋にキャラクター人気と主人公補正</strong>によるものです。</p>

<h2>封入率｜狙いの1枚は約631BOXに1枚</h2>
<p>OP-13のスーパーパラレル全体の封入率は<strong>約0.48%(約210.5BOXに1枚)</strong>とされています。レッドスーパーパラレルはこの枠の中の3種なので、<strong>特定の1枚を狙う確率は約0.16%、BOX換算で約631BOXに1枚</strong>という計算になります。</p>

<table class="price-table">
<thead><tr><th>狙い方</th><th style="text-align:right">必要BOX数の目安</th><th style="text-align:right">BOX代(定価¥5,280換算)</th></tr></thead>
<tbody>
<tr><td>レッドSPどれか1枚</td><td class="price">約210BOX</td><td class="price">約¥1,110,000</td></tr>
<tr class="best"><td><strong>ルフィを狙い撃ち</strong></td><td class="price"><strong>約631BOX</strong></td><td class="price"><strong>約¥3,330,000</strong></td></tr>
</tbody>
</table>

<div class="callout"><strong>結論は明快:</strong> ルフィのレッドコミパラを自引きで狙うと、BOX代の期待値は<strong>約333万円</strong>。カードの買取額230万円・販売価格278万円を大きく上回ります。<strong>欲しいなら開封ではなくカードを直接買うほうが安い</strong>という、高額パラレルに共通する結論です。もちろん開封には当てる楽しみがありますが、収支だけで見れば不利です。BOX相場は<a href="box/op-13.html">OP-13個別ページ</a>で毎日更新しています。</div>

<h2>PSA10データ｜3種とも取得率は高め</h2>
<table class="price-table">
<thead><tr><th>カード</th><th style="text-align:right">PSA10鑑定枚数</th><th style="text-align:right">PSA10取得率</th><th style="text-align:right">素体買取→PSA10の倍率</th></tr></thead>
<tbody>
<tr class="best"><td><strong>ルフィ(OP13-118)</strong></td><td class="price">459枚</td><td class="price">87.3%</td><td class="price">約1.49倍</td></tr>
<tr><td>エース(OP13-119)</td><td class="price">404枚</td><td class="price">89.0%</td><td class="price">約1.63倍</td></tr>
<tr><td>サボ(OP13-120)</td><td class="price">424枚</td><td class="price">90.2%</td><td class="price">約1.40倍</td></tr>
</tbody>
</table>

<p>3種とも<strong>PSA10取得率は87〜90%</strong>と高水準です。発売が2025年8月と比較的新しく、高額カードとして最初から丁寧に扱われてきたことが背景にあると考えられます。参考までに、2023年発売の<a href="nika-luffy-comipara.html">ニカルフィ コミパラ</a>は取得率71.7%で、明確な差があります。</p>

<p>鑑定枚数はいずれも400枚台で、<strong>3種ほぼ同数</strong>です。これは封入率が3種で同等であることの傍証にもなっています。</p>

<h2>価格推移｜ルフィは1年で9倍</h2>
<h3>ルフィ(OP13-118)</h3>
<table class="price-table">
<thead><tr><th>時点</th><th style="text-align:right">買取価格</th><th>状況</th></tr></thead>
<tbody>
<tr><td>2025年8月23日(発売)</td><td class="price">約¥250,000</td><td>初動</td></tr>
<tr><td>2025年12月25日</td><td class="price">約¥450,000</td><td>じわ上げ</td></tr>
<tr><td>2026年1月15日</td><td class="price">約¥1,100,000</td><td>1ヶ月で2.4倍に急騰</td></tr>
<tr><td>2026年3月15日</td><td class="price">約¥850,000</td><td>反落</td></tr>
<tr><td>2026年5月15日</td><td class="price">約¥2,000,000</td><td>再騰</td></tr>
<tr><td>2026年8月15日</td><td class="price">約¥2,500,000</td><td>直近ピーク</td></tr>
<tr class="best"><td><strong>2026年8月24日</strong></td><td class="price"><strong>約¥2,300,000</strong></td><td>ピークから約8%調整</td></tr>
</tbody>
</table>

<p>初動25万円から1年で<strong>約9.2倍</strong>。ただし一本調子ではなく、<strong>110万→85万(-23%)</strong>のような大きな押し目を挟みながら切り上げてきました。</p>

<h3>エース・サボ</h3>
<p>エースは初動18万円から2026年1月に65万円、6月以降は80万円で横ばい。サボは初動15万円から2026年1月に50万円、6月に65万円をつけ、現在60万円です。<strong>両者ともルフィのような爆発的な上昇はなく、緩やかに水準を切り上げてから高値圏で安定</strong>という推移です。</p>

<div class="callout"><strong>3枚の性格の違い:</strong> ルフィは値幅が大きく<strong>投機的</strong>、エース・サボは値動きが穏やかで<strong>コレクション需要が支える</strong>タイプ、と整理できます。売買のタイミング管理が効くのはルフィ、腰を据えて持ちやすいのはエース・サボです。</div>

<h2>見分け方</h2>
<h3>レッドコミパラと通常コミパラの違い</h3>
<p>OP-13には<strong>通常のコミックパラレル版のルフィ・エース</strong>も収録されています(買取はルフィ約30万円、エース約13万円)。レッドコミパラとは<strong>相場が7倍以上違う</strong>ため、取り違えは致命的です。</p>
<p>見分けるポイントは<strong>全体の色味</strong>です。レッドスーパーパラレルは名前のとおりカード全体が<strong>赤く染まった特別仕様</strong>で、通常のコミパラは原作の誌面そのままの色調です。並べれば一目で分かりますが、フリマの写真だけでは判断しにくいこともあるため、<strong>型番(118/119/120がレッド)</strong>での確認が確実です。</p>

<h3>偽物(レプリカ)対策</h3>
<p>数百万円クラスのカードは模造品の標的になります。一般的な判別点は<strong>レリーフ加工(表面の凹凸)</strong>で、本物はキャラクターが浮き上がって見えます。裏面の青が<strong>紫がかっている</strong>個体も注意が必要です。この価格帯では<strong>PSA等の鑑定済みを買う</strong>のが実質的な必須条件と考えてよいでしょう。</p>

<h2>売買の注意点</h2>
<ul>
<li><strong>型番で確認する</strong> — OP13-118/119/120がレッドスーパーパラレルです。通常コミパラと相場が7倍以上違います。</li>
<li><strong>鑑定済みを選ぶ</strong> — 200万円超の取引で素体を個人間でやり取りするリスクは大きく、PSA10なら真贋と状態が担保されます。鑑定の料金・取得率・出すべきかの判断は <a href="psa-guide.html">ワンピースカードのPSA鑑定ガイド</a> を参照してください。</li>
<li><strong>複数店を比較する</strong> — この価格帯では店舗差がそのまま数十万円になります。1店舗の提示で決めないでください。</li>
<li><strong>ルフィは値動きが荒い</strong> — 直近1年で25万→110万→85万→250万→230万と推移しています。急ぎでなければ数週間の推移を見てから動くほうが有利です。</li>
<li><strong>開封で狙わない</strong> — 631BOX(約333万円相当)に1枚という封入率では、カードを直接買うほうが安く済みます。</li>
</ul>""",
        "faq": [
            {"q": "レッドコミパラ(レッドスーパーパラレル)とは何ですか？",
             "a": "受け継がれる意志(OP-13)で登場した3周年記念の特別仕様で、通常のスーパーパラレル(コミックパラレル)を赤色に染めた特別版です。ルフィ(OP13-118)・エース(OP13-119)・サボ(OP13-120)のASL3兄弟の3種のみが存在し、2026年8月現在ワンピースカードの最高額帯を形成しています。"},
            {"q": "3種の買取価格はいくらですか？",
             "a": "2026年8月24日時点で、ルフィ約230万円、エース約80万円、サボ約60万円です(altema掲載のカードラッシュ買取価格基準)。PSA10相場はそれぞれ約342万円・約130万円・約84万円。同じレアリティ・同じ弾でもルフィがエースの約2.9倍と突出しており、これはキャラクター人気と主人公補正によるものです。"},
            {"q": "封入率はどのくらいですか？BOXを買って狙えますか？",
             "a": "スーパーパラレル全体で約0.48%(約210.5BOXに1枚)、レッドは3種あるため狙いの1枚は約0.16%＝約631BOXに1枚とされています。BOX定価¥5,280で631BOX買うと約333万円になり、ルフィの買取230万円・販売278万円を上回ります。収支だけで見れば、開封で狙うよりカードを直接買うほうが安く済みます。"},
            {"q": "通常のコミックパラレルとどう見分けますか？",
             "a": "レッドスーパーパラレルはカード全体が赤く染まった特別仕様で、通常のコミパラは原作誌面そのままの色調です。OP-13には通常コミパラ版のルフィ(買取約30万円)・エース(約13万円)もあり相場が7倍以上違うため、型番がOP13-118/119/120かどうかで確認するのが確実です。"},
            {"q": "今が買い時ですか？売り時ですか？",
             "a": "ルフィは発売から1年で25万円→230万円と約9.2倍になっていますが、途中で110万→85万(-23%)のような押し目を何度も挟んでおり、直近も8月15日のピーク250万円から230万円へ調整しています。値動きが荒いため、売買どちらの場合も単日の買取表ではなく数週間〜数ヶ月の推移を確認してから判断することをおすすめします。エース・サボは値動きが穏やかで、高値圏での横ばいが続いています。"},
        ],
    },
    {
        "slug": "roger-gold-comipara",
        "nav_label": "ロジャー 金コミパラ徹底解説",
        "crumb": "ロジャー ゴールドコミパラ(OP09-118)",
        "date": "2026-08-24",
        "date_jp": "2026年8月24日",
        "title": "ロジャー ゴールドコミパラ(OP09-118)徹底解説｜買取70万・PSA10 109万と、初動割れから戻した価格推移",
        "h1": "ロジャー ゴールドコミパラ(OP09-118)徹底解説｜買取70万・PSA10 109万と、初動割れから2.8倍に戻した価格推移",
        "meta_desc": "ワンピースカード初のゴールド仕様「ゴール・D・ロジャー コミックパラレル(OP09-118)」を単体で徹底解説。2026年8月24日時点の買取70万・販売89.8万・PSA10相場109万、PSA10鑑定1,159枚と取得率89.6%、コミパラ5種構成ゆえロジャー単体は約360BOXに1枚という封入率、初動55万から25万へ半値以下に沈み再び70万へ戻した特異な価格推移、見分け方と売買の注意点をデータで整理します。",
        "og_title": "ロジャー 金コミパラ(OP09-118)徹底解説｜相場・PSA10・封入率",
        "og_desc": "ワンピカード初のゴールド仕様ロジャー コミパラを単体解説。買取70万・PSA10相場109万、360BOXに1枚の封入率、初動割れから2.8倍に戻した価格推移と売買の注意点。",
        "meta_line": "ロジャー金コミパラの相場・封入率・PSA10・価格推移",
        "hero_label": "ゴール・D・ロジャー コミックパラレル【OP09-118】",
        "hero_big": "買取 約¥700,000",
        "hero_sub": "新たなる皇帝(OP-09)収録、2周年記念の初ゴールド仕様コミックパラレル。発売初動55万円から2025年11月には25万円まで沈み、そこから約2.8倍に戻した特異な値動きが特徴です。相場・鑑定データは2026年8月24日時点。",
        "disclaimer": "本記事のカード相場は<strong>2026年8月24日時点</strong>にカード相場メディア altema が掲載する<strong>カードラッシュの買取・販売価格</strong>、およびPSA10相場(2026年8月19日更新)を基準にした目安です。1店舗の価格を基準にしているため、他店の買取額や実際の取引価格とは異なります。封入率は公式発表ではなく、開封報告等に基づく推定値です。高額カードは状態(センタリング・キズ・白かけ)により査定額が大きく変わり、記載の金額を保証するものではありません。BOX買取価格は当サイトが最大9店舗から自動取得した実データです。売買の判断はご自身の責任で行ってください。",
        "related": '<li><a href="op-09-atari-guide.html">新たなる皇帝(OP-09) 当たりカードガイド</a> — 収録弾の当たり全体と封入率</li>\n'
                   '<li><a href="box/op-09.html">新たなる皇帝(OP-09) BOX買取価格</a> — 店舗別のBOX買取価格を毎日更新</li>\n'
                   '<li><a href="nika-luffy-comipara.html">ニカルフィ コミパラ(OP05-119)徹底解説</a> — もっとも有名なコミックパラレル</li>\n'
                   '<li><a href="red-comipara-guide.html">レッドコミパラ3種(OP-13)徹底解説</a> — 現在のワンピカード最高額帯</li>\n'
                   '<li><a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> — BOXを売るときの店舗選び</li>\n'
                   '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較</li>',
        "body": """<p><strong>ゴール・D・ロジャー コミックパラレル【OP09-118】</strong>は、<a href="op-09-atari-guide.html">新たなる皇帝(OP-09)</a>に収録された2周年記念カードで、<strong>ワンピースカード初のゴールド仕様のコミックパラレル</strong>です。海賊王という別格のキャラクターと、記念弾の目玉という位置づけが重なった1枚です。</p>

<p>本記事では、このカード1枚に絞って<strong>現在の相場・封入率・PSA10データ・価格推移・売買の注意点</strong>を整理します。相場は<strong>2026年8月24日時点</strong>の実測値です。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・買取<strong>約70万円</strong>／販売約89.8万円／PSA10相場<strong>約109万円</strong>(2026年8月24日時点)<br>
・OP-09はコミパラが5種あるため、ロジャー単体は<strong>約360BOXに1枚</strong>と通常のコミパラより大幅に希少<br>
・発売初動55万→<strong>25万まで半値以下に沈み</strong>→70万に回復。<strong>初動割れから戻した</strong>数少ない高額カード</div>

<h2>基本情報</h2>
<table class="price-table">
<thead><tr><th>項目</th><th>内容</th></tr></thead>
<tbody>
<tr><td>カード名</td><td>ゴール・D・ロジャー</td></tr>
<tr><td>型番</td><td><strong>OP09-118</strong></td></tr>
<tr><td>レアリティ</td><td>コミックパラレル(ゴールド仕様/GSP)</td></tr>
<tr><td>収録</td><td><a href="op-09-atari-guide.html">ブースターパック「新たなる皇帝」(OP-09)</a></td></tr>
<tr><td>発売日</td><td>2024年8月31日(2周年記念弾)</td></tr>
<tr><td>通称</td><td>ロジャー金コミパラ／ゴールドスーパーパラレル</td></tr>
</tbody>
</table>

<h2>現在の相場(2026年8月24日時点)</h2>
<table class="price-table">
<thead><tr><th>区分</th><th style="text-align:right">金額</th><th>備考</th></tr></thead>
<tbody>
<tr class="best"><td><strong>買取価格</strong></td><td class="price"><strong>約¥700,000</strong></td><td>素体(未鑑定)</td></tr>
<tr><td>販売価格</td><td class="price">約¥898,000</td><td>素体(未鑑定)</td></tr>
<tr><td>PSA10相場</td><td class="price">約¥1,090,000</td><td>2026年8月19日更新</td></tr>
</tbody>
</table>

<h2>封入率｜コミパラ5種構成が希少性を押し上げている</h2>
<p>ワンピースカードのコミックパラレルは一般に<strong>6カートン(約72BOX)に約1枚</strong>とされています。ただしOP-09は<strong>コミックパラレルが5種類</strong>収録されている弾です。</p>

<table class="price-table">
<thead><tr><th>OP-09のコミパラ5種</th><th style="text-align:right">買取価格(2026年8月24日)</th></tr></thead>
<tbody>
<tr class="best"><td><strong>ゴール・D・ロジャー(ゴールド)</strong></td><td class="price"><strong>約¥700,000</strong></td></tr>
<tr><td>モンキー・D・ルフィ</td><td class="price">約¥300,000</td></tr>
<tr><td>シャンクス</td><td class="price">約¥160,000</td></tr>
<tr><td>マーシャル・D・ティーチ</td><td class="price">約¥150,000</td></tr>
<tr><td>バギー</td><td class="price">約¥120,000</td></tr>
</tbody>
</table>

<p>コミパラ枠を5種で分け合うため、<strong>ロジャー1種を狙う確率は本来の約5分の1</strong>、BOX換算で<strong>約360BOXに約1枚</strong>という水準になります。</p>

<div class="callout"><strong>BOX代に換算すると:</strong> OP-09のBOX定価は¥5,280。360BOX買えば<strong>約190万円</strong>です。買取70万円・販売89.8万円のカードを自引きで狙うには、まったく見合いません。<strong>欲しいならカードを直接買う</strong>ほうが安く済みます。BOX相場は<a href="box/op-09.html">OP-09個別ページ</a>で毎日更新しています。</div>

<p>なお、四皇(シャンクス・黒ひげ・バギー)とルフィのコミパラが同時に収録されているのは、OP-09が<strong>「新たなる皇帝」＝新四皇をテーマにした2周年記念弾</strong>だからです。ロジャーはそのテーマの頂点に立つ特別枠として、1枚だけゴールド仕様が与えられています。</p>

<h2>PSA10データ</h2>
<table class="price-table">
<thead><tr><th>項目</th><th style="text-align:right">数値</th></tr></thead>
<tbody>
<tr><td>PSA10鑑定枚数</td><td class="price">1,159枚</td></tr>
<tr><td>PSA10取得率</td><td class="price">89.6%</td></tr>
<tr class="best"><td><strong>素体買取→PSA10相場の倍率</strong></td><td class="price"><strong>約1.56倍</strong></td></tr>
</tbody>
</table>

<p>取得率<strong>89.6%</strong>は高水準で、<strong>10枚出せば9枚がPSA10になる</strong>計算です。2023年発売の<a href="nika-luffy-comipara.html">ニカルフィ コミパラ(71.7%)</a>と比べると明確に高く、発売時期の新しさと高額カードとしての扱われ方の差が出ています。</p>

<h2>価格推移｜初動割れから2.8倍に戻した特異な動き</h2>
<table class="price-table">
<thead><tr><th>時点</th><th style="text-align:right">買取価格</th><th>状況</th></tr></thead>
<tbody>
<tr><td>2024年8月31日(発売)</td><td class="price">約¥550,000</td><td>初動</td></tr>
<tr><td>2025年11月</td><td class="price">約¥250,000</td><td><strong>初動から約55%下落</strong>(底)</td></tr>
<tr><td>2026年1月</td><td class="price">約¥380,000〜¥520,000</td><td>回復局面</td></tr>
<tr><td>2026年6月</td><td class="price">約¥700,000〜¥900,000</td><td>初動を上抜け</td></tr>
<tr class="best"><td><strong>2026年8月24日</strong></td><td class="price"><strong>約¥700,000</strong></td><td>底値から約2.8倍</td></tr>
</tbody>
</table>

<p>このカードの値動きは、ほかの高額コミパラと明確に違います。<strong>発売から1年2ヶ月かけて初動の半値以下(25万円)まで沈み、そこから9ヶ月で2.8倍に戻した</strong>という推移です。</p>

<div class="callout"><strong>この推移が示すもの:</strong> 記念弾のトップレアでも、<strong>発売直後に買うと1年以上含み損を抱える可能性がある</strong>ということです。一方で、25万円の底値圏で拾えていれば現在70万円。<strong>高額カードでも「発売直後が高値」とは限らない</strong>という、実データに基づく典型例といえます。<a href="red-comipara-guide.html">レッドコミパラ</a>のような右肩上がり型とは対照的です。</div>

<h2>見分け方</h2>
<h3>ゴールド仕様の識別</h3>
<p>コミックパラレルは<strong>背景が漫画のコマ</strong>になっているのが共通の目印です。そのうえでロジャーのカードは<strong>ゴールド(金色)の箔仕様</strong>が施されており、OP-09のほかの4種(ルフィ・シャンクス・ティーチ・バギー)とは見た目で明確に区別できます。</p>

<h3>OP-09のほかのロジャーとの混同</h3>
<p>OP-09にはロジャーの<strong>シークレットパラレル(SEC-P)</strong>も収録されています。こちらはコミパラより相場がかなり下がるため、購入時は<strong>背景がコマかどうか</strong>と<strong>型番OP09-118</strong>の両方を必ず確認してください。「ロジャー パラレル」という曖昧な表記の出品は特に要注意です。</p>

<h3>偽物(レプリカ)対策</h3>
<p>本物にはレリーフ加工による表面の凹凸があり、キャラクターが浮き上がって見えます。偽物は立体感が乏しく、裏面の青が<strong>紫がかっている</strong>ことが多いとされています。70万円クラスでは<strong>鑑定済みを買う・実店舗で現物を確認する</strong>のが安全です。</p>

<h2>売買の注意点</h2>
<ul>
<li><strong>型番で確認する</strong> — OP09-118がゴールドコミパラです。同じロジャーでもSECパラレルとは相場が大きく異なります。</li>
<li><strong>推移の位置を意識する</strong> — 底値25万円から2.8倍に戻した現在70万円という位置にあります。過去に初動割れを経験しているカードなので、高値掴みには注意が必要です。</li>
<li><strong>鑑定は比較的通りやすい</strong> — PSA10取得率89.6%で、素体買取70万に対しPSA10相場は約109万(約1.56倍)。鑑定料・期間を踏まえたうえで検討する価値はあります(詳しい判断基準は <a href="psa-guide.html">PSA鑑定ガイド</a>)。</li>
<li><strong>複数店を比較する</strong> — 70万円クラスでは店舗差が数万円〜十数万円になります。</li>
<li><strong>開封で狙わない</strong> — 360BOX(約190万円相当)に1枚では、カードを直接買うほうが安く済みます。</li>
</ul>""",
        "faq": [
            {"q": "ロジャー ゴールドコミパラ(OP09-118)の買取価格はいくらですか？",
             "a": "2026年8月24日時点で買取約70万円、販売約89.8万円、PSA10相場は約109万円です(altema掲載のカードラッシュ価格基準)。2025年11月には約25万円まで下落した時期があり、そこから約2.8倍に戻した水準にあります。"},
            {"q": "封入率はどのくらいですか？",
             "a": "コミックパラレルの一般的な封入率は6カートン(約72BOX)に約1枚ですが、OP-09はコミパラが5種類(ロジャー・ルフィ・シャンクス・ティーチ・バギー)収録されているため、ロジャー単体を狙う確率は約5分の1、BOX換算で約360BOXに約1枚となります。BOX定価¥5,280で360BOXは約190万円になり、買取70万円のカードを自引きで狙うのは見合いません。"},
            {"q": "なぜ一度25万円まで下がったのですか？",
             "a": "本記事は当サイトが確認できた価格データの推移を示すもので、下落の理由を断定できる情報は確認できていません。事実として、2024年8月の発売初動55万円から2025年11月に約25万円(初動比-55%)まで下げ、その後2026年6月に初動を上抜けて現在70万円という推移をたどっています。記念弾のトップレアでも発売直後が高値とは限らない実例として参考になります。"},
            {"q": "PSA鑑定に出すべきですか？",
             "a": "PSA10取得率は89.6%と高く、10枚出せば9枚が10になる計算です。素体買取70万円に対しPSA10相場は約109万円(約1.56倍)なので、鑑定料と返却までの期間、その間の相場変動リスクを踏まえて判断する価値はあります。鑑定枚数はすでに1,159枚あり、PSA10自体は市場に一定数流通しています。"},
            {"q": "OP-09のほかのロジャーと見分けるには？",
             "a": "コミックパラレルは背景が漫画のコマになっており、さらにロジャーのゴールドコミパラは金色の箔仕様が施されています。OP-09にはロジャーのシークレットパラレル(SEC-P)もあり相場が異なるため、背景がコマかどうかと型番OP09-118の両方を確認してください。「ロジャー パラレル」とだけ書かれた出品は特に注意が必要です。"},
        ],
    },
    {
        "slug": "comipara-ranking",
        "nav_label": "歴代コミパラ相場ランキング",
        "crumb": "歴代コミックパラレル相場ランキング",
        "date": "2026-08-24",
        "date_jp": "2026年8月24日",
        "title": "歴代コミックパラレル相場ランキング全22弾｜最高はルフィ レッドコミパラ230万・BOX買取と連動しない理由",
        "h1": "歴代コミックパラレル相場ランキング全22弾｜最高はルフィ レッドコミパラ230万円・トップレアとBOX買取が連動しない理由",
        "meta_desc": "ワンピースカードのコミックパラレル(スーパーパラレル)を全22弾横断でランキング。2026年8月24日時点の買取価格で弾別最高額とカード単体TOP12を一覧化し、上位12枚のうち6枚をルフィが占める主人公補正、コミパラが複数種ある弾ほど1種あたりが希少になる構造、そして当サイトが最大9店舗から毎日自動取得しているBOX買取実データと突き合わせて「トップレアが高い弾＝BOXも高い」が成立しない理由まで解説します。",
        "og_title": "歴代コミパラ相場ランキング全22弾｜最高は230万・BOXと連動しない理由",
        "og_desc": "ワンピカードのコミックパラレルを全22弾横断でランキング。弾別最高額とカード単体TOP12、ルフィ補正、そしてBOX買取実データと連動しない理由をデータで解説。",
        "meta_line": "全22弾のコミパラ相場ランキング・分析・BOX実データとの比較",
        "hero_label": "歴代コミックパラレル 相場ランキング(全22弾)",
        "hero_big": "最高額は¥2,300,000",
        "hero_sub": "ワンピースカードの実質的な最高レアリティ「コミックパラレル(スーパーパラレル)」を全22弾横断で比較。首位はルフィのレッドコミパラ(OP-13)。カード相場は2026年8月24日時点、BOX買取価格は当サイトが最大9店舗から毎日自動取得している実データです。",
        "disclaimer": "本記事のカード相場は<strong>2026年8月24日時点</strong>にカード相場メディア altema が掲載する<strong>カードラッシュの買取価格</strong>を基準にした目安です。1店舗の買取価格のため、他店の査定額や販売価格とは異なります。掲載順位は各弾の当たりカード上位に入っているコミックパラレルを対象にしたもので、下位のコミパラや掲載外のカードは含まれない場合があります。封入率は公式発表ではなく開封報告等に基づく推定値で、ソースにより幅があります。BOX買取価格は当サイトが最大9店舗から自動取得した実データで毎日変動するため、記事内のランキング表は表示時点の最新値に自動更新されます。売買の判断はご自身の責任で行ってください。",
        "related": '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較(毎日更新)</li>\n'
                   '<li><a href="red-comipara-guide.html">レッドコミパラ3種(OP-13)徹底解説</a> — ランキング1位・2位・5位の3枚を深掘り</li>\n'
                   '<li><a href="nika-luffy-comipara.html">ニカルフィ コミパラ(OP05-119)徹底解説</a> — ランキング3位の1枚を深掘り</li>\n'
                   '<li><a href="roger-gold-comipara.html">ロジャー ゴールドコミパラ(OP09-118)徹底解説</a> — ランキング4位の1枚を深掘り</li>\n'
                   '<li><a href="kougaku-ranking.html">高額BOXランキング・絶版ガイド</a> — BOX側の最高買取・定価比ランキング</li>\n'
                   '<li><a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> — BOXを売るときの店舗選びと高く売るコツ</li>',
        "body": """<p><strong>コミックパラレル</strong>(公式名称<strong>「スーパーパラレル」</strong>、通称コミパラ)は、ワンピースカードゲームの実質的な最高レアリティです。原作漫画のコマをそのまま背景に使った全面イラストが特徴で、各弾の相場を牽引しているのはほぼ例外なくこの枠のカードです。</p>

<p>本記事では、<strong>全22弾のコミパラを横断でランキング</strong>し、そのうえで<strong>当サイトが最大9店舗から毎日自動取得しているBOX買取実データと突き合わせて</strong>、「トップレアが高い弾はBOXも高いのか」を検証します。カード相場は<strong>2026年8月24日時点</strong>の実測値です。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・首位は<strong>ルフィ レッドコミパラ(OP-13)の230万円</strong>。2位以下を3倍近く引き離して独走<br>
・カード単体TOP12のうち<strong>6枚がルフィ</strong>。主人公補正がそのまま相場に出ている<br>
・<strong>コミパラ最高額とBOX買取価格は連動しない</strong>。トップレア230万円のOP-13よりBOXが高い弾がいくつもある</div>

<h2>コミックパラレルとは</h2>
<p>コミックパラレルは、原作漫画のコマを背景に使った特別仕様のカードです。公式のレアリティ名は<strong>「スーパーパラレル」</strong>で、ファンの間ではコミパラ・漫画パラレルと呼ばれています。</p>

<h3>見分け方</h3>
<p>最大の目印は<strong>背景が漫画のコマになっている</strong>ことです。注意すべきは、<strong>カード右下のレアリティ表記だけでは通常のパラレルと区別がつかない</strong>点です。表記ではなく背景で判断してください。</p>

<h3>封入率の目安</h3>
<p>コミパラの封入率は一般に<strong>6カートン(約72BOX)に約1枚</strong>とされています。ただしこれは「コミパラ枠が引ける確率」であり、<strong>1つの弾に複数種のコミパラがある場合、狙いの1枚を引く確率はその分だけ下がります</strong>。後述のとおり、この構造が相場に大きく影響しています。</p>

<h2>弾別コミパラ最高額ランキング(全22弾)</h2>
<p>各弾のコミックパラレルのうち、もっとも買取価格が高い1枚を並べたランキングです。弾名から各弾の当たりカードガイドに移動できます。</p>

<table class="price-table">
<thead><tr><th>順位</th><th>弾</th><th>カード</th><th style="text-align:right">買取価格</th></tr></thead>
<tbody>
<tr class="best"><td>1位</td><td><a href="op-13-atari-guide.html">受け継がれる意志(OP-13)</a></td><td><strong>モンキー・D・ルフィ</strong><br><span style="font-size:11px;color:#6b7280">レッドコミパラ</span></td><td class="price"><strong>¥2,300,000</strong></td></tr>
<tr><td>2位</td><td><a href="op-05-atari-guide.html">新時代の主役(OP-05)</a></td><td>モンキー・D・ルフィ(ニカ)</td><td class="price">¥800,000</td></tr>
<tr><td>3位</td><td><a href="op-09-atari-guide.html">新たなる皇帝(OP-09)</a></td><td>ゴール・D・ロジャー<br><span style="font-size:11px;color:#6b7280">ゴールド仕様</span></td><td class="price">¥700,000</td></tr>
<tr><td>4位</td><td><a href="eb-02-atari-guide.html">Anime 25th collection(EB-02)</a></td><td>モンキー・D・ルフィ</td><td class="price">¥500,000</td></tr>
<tr><td>5位</td><td><a href="op-06-atari-guide.html">双璧の覇者(OP-06)</a></td><td>ロロノア・ゾロ</td><td class="price">¥270,000</td></tr>
<tr><td>6位</td><td><a href="eb-01-atari-guide.html">メモリアルコレクション(EB-01)</a></td><td>トニートニー・チョッパー</td><td class="price">¥240,000</td></tr>
<tr><td>7位</td><td><a href="op-16-atari-guide.html">決戦の刻(OP-16)</a></td><td>サカズキ／クザン<br><span style="font-size:11px;color:#6b7280">同額で並走</span></td><td class="price">¥230,000</td></tr>
<tr><td>8位</td><td><a href="op-07-atari-guide.html">500年後の未来(OP-07)</a></td><td>ボア・ハンコック</td><td class="price">¥200,000</td></tr>
<tr><td>9位</td><td><a href="op-01-atari-guide.html">ROMANCE DAWN(OP-01)</a></td><td>シャンクス</td><td class="price">¥170,000</td></tr>
<tr><td>10位</td><td><a href="prb-02-atari-guide.html">THE BEST vol.2(PRB-02)</a></td><td>サンジ</td><td class="price">¥160,000</td></tr>
<tr><td>11位</td><td><a href="op-02-atari-guide.html">頂上決戦(OP-02)</a></td><td>ポートガス・D・エース</td><td class="price">¥140,000</td></tr>
<tr><td>11位</td><td><a href="op-11-atari-guide.html">神速の拳(OP-11)</a></td><td>モンキー・D・ルフィ</td><td class="price">¥140,000</td></tr>
<tr><td>13位</td><td><a href="eb-03-atari-guide.html">Heroines Edition(EB-03)</a></td><td>ウタ</td><td class="price">¥120,000</td></tr>
<tr><td>14位</td><td><a href="op-12-atari-guide.html">師弟の絆(OP-12)</a></td><td>ジュエリー・ボニー</td><td class="price">¥100,000</td></tr>
<tr><td>14位</td><td><a href="op-14-atari-guide.html">蒼海の七傑(OP-14)</a></td><td>ジュラキュール・ミホーク</td><td class="price">¥100,000</td></tr>
<tr><td>14位</td><td><a href="eb-04-atari-guide.html">EGGHEAD CRISIS(EB-04)</a></td><td>コビー</td><td class="price">¥100,000</td></tr>
<tr><td>17位</td><td><a href="op-03-atari-guide.html">強大な敵(OP-03)</a></td><td>そげキング</td><td class="price">¥90,000</td></tr>
<tr><td>17位</td><td><a href="op-04-atari-guide.html">謀略の王国(OP-04)</a></td><td>サボ</td><td class="price">¥90,000</td></tr>
<tr><td>17位</td><td><a href="op-10-atari-guide.html">王族の血統(OP-10)</a></td><td>トラファルガー・ロー</td><td class="price">¥90,000</td></tr>
<tr><td>17位</td><td><a href="prb-01-atari-guide.html">THE BEST(PRB-01)</a></td><td>ナミ</td><td class="price">¥90,000</td></tr>
<tr><td>21位</td><td><a href="op-15-atari-guide.html">神の島の冒険(OP-15)</a></td><td>エネル</td><td class="price">¥80,000</td></tr>
<tr><td>22位</td><td><a href="op-08-atari-guide.html">二つの伝説(OP-08)</a></td><td>シルバーズ・レイリー</td><td class="price">¥60,000</td></tr>
</tbody>
</table>

<p>最高額のOP-13(230万円)と最下位のOP-08(6万円)では<strong>約38倍</strong>の開きがあります。同じ最高レアリティ枠でも、弾によってここまで差が出るのがワンピースカードの特徴です。</p>

<p>なお<a href="op-17-atari-guide.html">世界最強の戦士(OP-17)</a>は新レアリティ「海賊団スーパーパラレル」を採用しており従来のコミパラ枠とは別系統のため、本ランキングには含めていません。スタートデッキEX(ST-30)にはコミパラの収録がありません。</p>

<h2>カード単体TOP12</h2>
<p>弾をまたいでカード単体で並べたランキングです。</p>

<table class="price-table">
<thead><tr><th>順位</th><th>カード</th><th>収録</th><th style="text-align:right">買取価格</th></tr></thead>
<tbody>
<tr class="best"><td>1位</td><td><strong>モンキー・D・ルフィ</strong> レッドコミパラ</td><td>OP-13</td><td class="price"><strong>¥2,300,000</strong></td></tr>
<tr><td>2位</td><td>ポートガス・D・エース レッドコミパラ</td><td>OP-13</td><td class="price">¥800,000</td></tr>
<tr><td>2位</td><td><strong>モンキー・D・ルフィ(ニカ)</strong></td><td>OP-05</td><td class="price">¥800,000</td></tr>
<tr><td>4位</td><td>ゴール・D・ロジャー(ゴールド)</td><td>OP-09</td><td class="price">¥700,000</td></tr>
<tr><td>5位</td><td>サボ レッドコミパラ</td><td>OP-13</td><td class="price">¥600,000</td></tr>
<tr><td>6位</td><td><strong>モンキー・D・ルフィ</strong></td><td>EB-02</td><td class="price">¥500,000</td></tr>
<tr><td>7位</td><td><strong>モンキー・D・ルフィ</strong></td><td>OP-13</td><td class="price">¥300,000</td></tr>
<tr><td>7位</td><td><strong>モンキー・D・ルフィ</strong></td><td>OP-09</td><td class="price">¥300,000</td></tr>
<tr><td>9位</td><td>ロロノア・ゾロ</td><td>OP-06</td><td class="price">¥270,000</td></tr>
<tr><td>10位</td><td>トニートニー・チョッパー</td><td>EB-01</td><td class="price">¥240,000</td></tr>
<tr><td>11位</td><td>サカズキ</td><td>OP-16</td><td class="price">¥230,000</td></tr>
<tr><td>11位</td><td>クザン</td><td>OP-16</td><td class="price">¥230,000</td></tr>
</tbody>
</table>

<h2>分析①｜TOP12のうち6枚がルフィ</h2>
<p>上のランキングを見ると、<strong>12枠のうち6枠をモンキー・D・ルフィが占めています</strong>(1位・2位・6位・7位×2、ニカ版を含む)。2位グループのエース、5位のサボを加えると、<strong>ASL3兄弟だけで9枠</strong>です。</p>

<div class="callout"><strong>何を意味するか:</strong> コミパラの相場は<strong>封入率よりキャラクター人気で決まる</strong>ということです。封入率は基本的にどのコミパラも同じ枠から出るため、価格差の説明にはなりません。実際、同じ弾・同じレアリティのレッドコミパラ3種でも、ルフィ230万・エース80万・サボ60万と<strong>3.8倍の差</strong>がついています(詳細は<a href="red-comipara-guide.html">レッドコミパラ3種徹底解説</a>)。</div>

<p>逆に言えば、<strong>ルフィのコミパラは高値になりやすい</strong>という経験則が成り立ちます。新弾でルフィのコミパラが収録された場合、相場の上限が高くなる傾向を頭に入れておくとよいでしょう。</p>

<h2>分析②｜コミパラの種類数が希少性を左右する</h2>
<p>封入率は「6カートン(約72BOX)に約1枚」が目安ですが、これは<strong>コミパラ枠に当たる確率</strong>です。1つの弾に何種類のコミパラがあるかで、狙いの1枚を引く難易度は大きく変わります。</p>

<table class="price-table">
<thead><tr><th>弾</th><th style="text-align:right">コミパラ種類数(目安)</th><th style="text-align:right">狙いの1枚の目安</th></tr></thead>
<tbody>
<tr><td><a href="op-15-atari-guide.html">神の島の冒険(OP-15)</a></td><td class="price">1種(エネルのみ)</td><td class="price">約72BOXに1枚</td></tr>
<tr><td><a href="eb-04-atari-guide.html">EGGHEAD CRISIS(EB-04)</a></td><td class="price">1種(コビーのみ)</td><td class="price">約72BOXに1枚</td></tr>
<tr class="best"><td><a href="op-09-atari-guide.html">新たなる皇帝(OP-09)</a></td><td class="price"><strong>5種</strong></td><td class="price"><strong>約360BOXに1枚</strong></td></tr>
<tr><td><a href="op-13-atari-guide.html">受け継がれる意志(OP-13)</a></td><td class="price">レッド3種＋通常</td><td class="price">レッド1枚は約631BOXに1枚</td></tr>
</tbody>
</table>

<p>コミパラが1種しかない弾(OP-15・EB-04)は「コミパラを引けば必ず当たり」ですが、5種あるOP-09では<strong>狙いのロジャーを引く確率は約5分の1</strong>になります。OP-13のレッドコミパラに至っては<strong>約631BOXに1枚</strong>です。</p>

<div class="callout"><strong>BOX代に換算すると:</strong> 631BOX×定価¥5,280＝<strong>約333万円</strong>。ルフィ レッドコミパラの買取230万円・販売278万円を上回ります。<strong>高額コミパラは「自引きより買うほうが安い」</strong>のが基本構造です。同じ計算はOP-09のロジャー(約360BOX＝約190万円に対し買取70万円)、OP-05のニカルフィ(約288BOX＝約152万円に対し買取80万円)でも成立します。</div>

<h2>分析③｜コミパラ最高額とBOX買取は連動しない</h2>
<p>ここからが当サイト独自の検証です。当サイトは<strong>最大9店舗のBOX買取価格を毎日自動取得</strong>しています。「トップレアが高い弾はBOXも高いはず」という直感が正しいかを、実データで確かめてみます。</p>

<p>以下は現在のBOX買取ランキングです(毎日自動更新)。</p>

{{BOX_RANKING}}

<p>コミパラ最高額ランキングと見比べると、<strong>順位が大きく食い違っている</strong>ことが分かります。代表的なズレは次のとおりです。</p>

<ul>
<li><strong>OP-13</strong> — コミパラ最高額は<strong>1位(230万円)</strong>だが、BOX買取は上位ではない。トップレアが飛び抜けていてもBOXは連動していません。</li>
<li><strong>OP-16</strong> — コミパラは7位(23万円)だが、BOX買取は下位。海軍大将トリオという強力な看板を持ちながらBOXは伸びていません。</li>
<li><strong>OP-01・OP-11</strong> — コミパラ最高額は中位(17万円・14万円)ながら、BOX買取は上位に入ります。</li>
</ul>

<h3>なぜ連動しないのか</h3>
<p>理由は大きく3つあります。</p>

<h4>1. BOX価格は「供給量」で決まる</h4>
<p>カード相場が需要で動くのに対し、BOX相場は<strong>市場に残っている未開封BOXの量</strong>に強く影響されます。古い弾ほど開封が進んで未開封在庫が減り、再販がかかりにくくなるため、トップレアの価格とは別の理屈で値が上がります。OP-01が好例で、2026年4月にブロック①としてスタンダード使用不可になった後もBOX買取は上位を維持しています。</p>

<h4>2. トップレア以外の高額枠がある</h4>
<p><a href="op-11-atari-guide.html">神速の拳(OP-11)</a>のコミパラ最高額は14万円ですが、この弾には<strong>3周年スペシャル(金)のルフィが買取140万円</strong>で存在します。コミパラではないため本ランキングには出てきませんが、BOXの開封需要はこちらが牽引しています。<strong>コミパラだけを見ると弾の実力を見誤る</strong>典型例です。金銀6枚の相場・封入率・BOX代換算は <a href="anniversary-sp-guide.html">3周年スペシャルカード(金/銀)徹底解説</a> にまとめました。</p>

<h4>3. 発売からの経過時間が違う</h4>
<p>OP-13は2025年8月発売で、この1年で再販と開封が進みました。一方でコミパラ相場は同じ期間に25万円→230万円へ上昇しています。<strong>カードは減らないが、BOXは開けられて減る</strong>——この非対称性が、時間の経過とともに両者の順位を乖離させます。</p>

<div class="callout"><strong>実務的な結論:</strong> 「このカードが高いからBOXも買い」という判断は成立しません。<strong>カードを狙うならカード相場を、BOXを狙うならBOX相場を、それぞれ別に見る</strong>のが正解です。BOX側の最新価格は<a href="/onepiece">比較トップ</a>で毎日更新しており、定価比のランキングは<a href="kougaku-ranking.html">高額BOXランキング</a>でまとめています。</div>

<h2>もっと詳しく｜上位カードの個別解説</h2>
<p>ランキング上位の3枚については、封入率・PSA10鑑定データ・価格推移まで掘り下げた個別記事を用意しています。</p>
<ul>
<li><strong><a href="red-comipara-guide.html">レッドコミパラ3種(OP-13)徹底解説</a></strong> — ランキング1位・2位・5位。ルフィ230万/エース80万/サボ60万の比較、631BOXに1枚の封入率、1年で9.2倍になった価格推移</li>
<li><strong><a href="nika-luffy-comipara.html">ニカルフィ コミパラ(OP05-119)徹底解説</a></strong> — ランキング2位。288BOXに1枚の封入率と、PSA10取得率71.7%が示す状態難</li>
<li><strong><a href="roger-gold-comipara.html">ロジャー ゴールドコミパラ(OP09-118)徹底解説</a></strong> — ランキング4位。初動55万から25万に沈み70万へ戻した特異な価格推移</li>
</ul>""",
        "faq": [
            {"q": "コミックパラレル(コミパラ)とは何ですか？",
             "a": "原作漫画のコマを背景に使った全面イラスト仕様のカードで、公式のレアリティ名は「スーパーパラレル」です。ワンピースカードの実質的な最高レアリティで、各弾の相場を牽引しているのはほぼこの枠のカードです。封入率は一般に6カートン(約72BOX)に約1枚とされています。"},
            {"q": "歴代でもっとも高いコミパラはどれですか？",
             "a": "2026年8月24日時点では、受け継がれる意志(OP-13)のモンキー・D・ルフィ レッドコミパラで買取約230万円です。2位グループのエース レッドコミパラ(OP-13)とニカルフィ(OP-05)がともに約80万円なので、1位が2位以下を約2.9倍引き離しています。最下位のOP-08レイリー(約6万円)とは約38倍の差があります。"},
            {"q": "なぜルフィのコミパラは高いのですか？",
             "a": "カード単体TOP12のうち6枠をルフィが占めています。コミパラは基本的にどれも同じ枠から出るため封入率では価格差を説明できず、差はキャラクター人気によるものです。実際、同じ弾・同じレアリティのレッドコミパラ3種でもルフィ230万・エース80万・サボ60万と3.8倍の開きがあります。"},
            {"q": "BOXを買ってコミパラを狙うのは得ですか？",
             "a": "高額なコミパラほど不利になります。OP-13のレッドコミパラは狙いの1枚が約631BOXに1枚で、BOX代に換算すると約333万円。カードの買取230万円・販売278万円を上回ります。OP-09のロジャー(約360BOX＝約190万円に対し買取70万円)、OP-05のニカルフィ(約288BOX＝約152万円に対し買取80万円)でも同じ結論です。開封は当てる楽しみのために行うもので、収支だけで見れば直接買うほうが安く済みます。"},
            {"q": "コミパラが高い弾はBOXも高いですか？",
             "a": "連動しません。当サイトが最大9店舗から毎日取得しているBOX買取実データと突き合わせると、コミパラ最高額1位のOP-13よりBOX買取が高い弾がいくつもあります。理由は、BOX価格が市場に残る未開封在庫の量に強く左右されること、OP-11の3周年スペシャル(金)のようにコミパラ以外の高額枠が開封需要を牽引する弾があること、そしてカードは減らないがBOXは開封で減るという非対称性の3点です。カードを狙うならカード相場を、BOXを狙うならBOX相場を別々に確認してください。"},
        ],
    },
    {
        "slug": "psa-guide",
        "nav_label": "ワンピカードPSA鑑定ガイド",
        "crumb": "ワンピースカード PSA鑑定ガイド",
        "date": "2026-08-24",
        "date_jp": "2026年8月24日",
        "title": "ワンピースカードのPSA鑑定ガイド｜実データで見る「出すべきカード」の判断基準と取得率71.7〜93.2%の現実",
        "h1": "ワンピースカードのPSA鑑定ガイド｜実データで見る「出すべきカード」の判断基準とPSA10取得率71.7〜93.2%の現実",
        "meta_desc": "ワンピースカードをPSA鑑定に出すべきか、実データで判断するためのガイド。素体買取とPSA10相場の倍率(1.40〜1.66倍)、カードごとに大きく違うPSA10取得率(ニカルフィ71.7%〜フラシウタ93.2%)、鑑定料と返却待ちを織り込んだ期待値の考え方、センタリング55/45などの提出前セルフチェック、そして「PSA10相場は販売価格であって買取価格ではない」という最大の落とし穴まで、2026年8月24日時点の実測値で整理します。",
        "og_title": "ワンピカードPSA鑑定ガイド｜出すべきカードの判断基準を実データで",
        "og_desc": "素体買取とPSA10相場の倍率、カード別のPSA10取得率71.7〜93.2%、期待値の考え方、提出前セルフチェック、PSA10相場が販売価格である落とし穴まで実データで解説。",
        "meta_line": "PSA鑑定の料金・取得率実データ・出すべきカードの判断基準",
        "hero_label": "ワンピースカード PSA鑑定ガイド",
        "hero_big": "PSA10取得率は71.7〜93.2%",
        "hero_sub": "「PSA10にすれば高く売れる」は半分正解です。素体買取に対するPSA10相場の倍率は1.40〜1.66倍ある一方、PSA10が付く確率はカードによって20ポイント以上の差があります。当サイトが確認できた実測データで、出すべきカードの判断基準を整理します。データは2026年8月24日時点。",
        "disclaimer": "本記事のカード相場・PSA10相場・鑑定枚数・取得率は<strong>2026年8月24日時点</strong>(PSA10相場は2026年8月19日更新)にカード相場メディア altema が掲載する数値で、素体の買取価格は<strong>カードラッシュの買取価格</strong>を基準にした目安です。<strong>PSA10相場は販売価格ベース</strong>であり、鑑定品を売却する際の買取価格はこれより低くなります。鑑定料金・納期は2026年8月時点に複数の公開情報で確認した目安で、PSAの料金体系・申告価値の区分・混雑状況により変動します。<strong>提出前に必ずPSA公式サイトで最新の料金と納期をご確認ください</strong>。鑑定結果を保証するものではなく、本記事の期待値試算は一定の仮定を置いた机上の計算です。売買・鑑定の判断はご自身の責任で行ってください。",
        "related": '<li><a href="nika-luffy-comipara.html">ニカルフィ コミパラ(OP05-119)徹底解説</a> — 取得率71.7%と最も低いカードの詳細</li>\n'
                   '<li><a href="red-comipara-guide.html">レッドコミパラ3種(OP-13)徹底解説</a> — PSA10相場342万円の最高額帯</li>\n'
                   '<li><a href="roger-gold-comipara.html">ロジャー ゴールドコミパラ(OP09-118)徹底解説</a> — 取得率89.6%の高額カード</li>\n'
                   '<li><a href="comipara-ranking.html">歴代コミックパラレル相場ランキング全22弾</a> — 鑑定候補になる高額カードの一覧</li>\n'
                   '<li><a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> — BOXを売るときの店舗選び</li>\n'
                   '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較</li>',
        "body": """<p>ワンピースカードの高額カードを持っていると、必ず一度は考えるのが<strong>「PSA鑑定に出すべきか」</strong>です。PSA10が付けば相場が上がるのは事実ですが、<strong>鑑定料と数ヶ月の待ち時間を払ってでも得なのか</strong>は、カードによって答えが変わります。</p>

<p>本記事では、精神論ではなく<strong>実際の数値</strong>で判断できるように整理します。素体の買取価格・PSA10相場・鑑定枚数・PSA10取得率は、いずれも<strong>2026年8月24日時点</strong>の実測値です。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・素体買取に対するPSA10相場の倍率は<strong>1.40〜1.66倍</strong>。思ったほど大きくない<br>
・PSA10取得率は<strong>カードによって71.7%〜93.2%</strong>と20ポイント以上の差がある。古い弾ほど低い<br>
・最大の落とし穴は<strong>「PSA10相場は販売価格」</strong>であること。売るときの買取価格はここからさらに下がる</div>

<h2>PSA鑑定とは</h2>
<p>PSA(Professional Sports Authenticator)は、カードの<strong>真贋と状態を10段階で判定</strong>する第三者鑑定機関です。鑑定されたカードは専用のケース(スラブ)に封入され、グレードが刻印されたラベルが付きます。最高評価が<strong>PSA10(GEM MT)</strong>で、これが付くと相場が大きく上がります。</p>

<p>ワンピースカードのように<strong>数十万〜数百万円のカードが存在するタイトル</strong>では、真贋の担保という意味でも鑑定の価値があります。個人間で200万円のカードを素体でやり取りするリスクを考えれば、スラブ入りであること自体が取引の前提になる価格帯です。</p>

<h2>料金と納期の目安(2026年8月時点)</h2>
<p>PSA JAPANの主なプランは以下のとおりです。<strong>料金体系・納期は改定されることがあり、混雑状況でも変動します。提出前に必ず公式サイトで最新情報を確認してください。</strong></p>

<table class="price-table">
<thead><tr><th>プラン</th><th style="text-align:right">1枚あたり</th><th>納期の目安</th></tr></thead>
<tbody>
<tr><td>バリュー・バルク(20枚以上)</td><td class="price">約¥3,980</td><td>約120営業日</td></tr>
<tr><td>バリュー</td><td class="price">約¥4,980</td><td>約90営業日</td></tr>
<tr><td>バリュー・プラス</td><td class="price">約¥7,980</td><td>約60営業日</td></tr>
<tr><td>バリュー・マックス</td><td class="price">約¥8,980</td><td>約40営業日</td></tr>
<tr><td>レギュラー</td><td class="price">約¥11,980</td><td>約30〜60営業日</td></tr>
</tbody>
</table>

<div class="callout"><strong>高額カードほど料金は上がる:</strong> PSAのプランは<strong>申告価値(そのカードの想定価値)によって使えるプランが決まります</strong>。レギュラーの申告価値上限は25万円程度とされており、<a href="red-comipara-guide.html">ルフィのレッドコミパラ(素体買取230万円)</a>のようなカードは、より上位の高額プランを使う必要があります。「4,980円で出せる」と考えていると計算が狂うので、<strong>自分のカードの価格帯でいくらかかるかを事前に確認</strong>してください。</div>

<h2>【実データ】素体買取とPSA10相場の倍率</h2>
<p>ここからが本題です。ワンピースカードの主要な高額カードについて、<strong>素体(未鑑定)の買取価格とPSA10相場</strong>を並べます。</p>

<table class="price-table">
<thead><tr><th>カード</th><th>収録</th><th style="text-align:right">素体買取</th><th style="text-align:right">PSA10相場</th><th style="text-align:right">倍率</th></tr></thead>
<tbody>
<tr class="best"><td><a href="nika-luffy-comipara.html">ニカルフィ コミパラ</a></td><td>OP-05</td><td class="price">¥800,000</td><td class="price">¥1,330,000</td><td class="price"><strong>1.66倍</strong></td></tr>
<tr><td><a href="red-comipara-guide.html">エース レッドコミパラ</a></td><td>OP-13</td><td class="price">¥800,000</td><td class="price">¥1,300,000</td><td class="price">1.63倍</td></tr>
<tr><td><a href="roger-gold-comipara.html">ロジャー 金コミパラ</a></td><td>OP-09</td><td class="price">¥700,000</td><td class="price">¥1,090,000</td><td class="price">1.56倍</td></tr>
<tr><td>サインルフィ(SRパラレル)</td><td>OP-05</td><td class="price">¥800,000</td><td class="price">¥1,240,000</td><td class="price">1.55倍</td></tr>
<tr><td><a href="red-comipara-guide.html">ルフィ レッドコミパラ</a></td><td>OP-13</td><td class="price">¥2,300,000</td><td class="price">¥3,420,000</td><td class="price">1.49倍</td></tr>
<tr><td><a href="red-comipara-guide.html">サボ レッドコミパラ</a></td><td>OP-13</td><td class="price">¥600,000</td><td class="price">¥840,000</td><td class="price">1.40倍</td></tr>
</tbody>
</table>

<p>倍率は<strong>1.40〜1.66倍のレンジ</strong>に収まっています。「PSA10なら倍以上」というイメージを持たれがちですが、<strong>実データではおおむね1.5倍前後</strong>です。</p>

<h2>【実データ】PSA10取得率はカードで20ポイント以上違う</h2>
<p>倍率と同じくらい重要なのが、<strong>そもそもPSA10が付くのか</strong>です。すでに鑑定された枚数と、そのうちPSA10になった割合を見てみます。</p>

<table class="price-table">
<thead><tr><th>カード</th><th>収録/発売</th><th style="text-align:right">鑑定枚数(PSA10)</th><th style="text-align:right">PSA10取得率</th></tr></thead>
<tbody>
<tr><td>フラシウタ(優勝プロモ)</td><td>プロモ</td><td class="price">726枚</td><td class="price">93.2%</td></tr>
<tr><td>ナミ パラレル</td><td>OP-01</td><td class="price">7,824枚</td><td class="price">92.9%</td></tr>
<tr><td>サインルフィ</td><td>OP-05</td><td class="price">3,331枚</td><td class="price">91.4%</td></tr>
<tr><td><a href="red-comipara-guide.html">サボ レッドコミパラ</a></td><td>OP-13 / 2025年8月</td><td class="price">424枚</td><td class="price">90.2%</td></tr>
<tr><td><a href="roger-gold-comipara.html">ロジャー 金コミパラ</a></td><td>OP-09 / 2024年8月</td><td class="price">1,159枚</td><td class="price">89.6%</td></tr>
<tr><td><a href="red-comipara-guide.html">エース レッドコミパラ</a></td><td>OP-13 / 2025年8月</td><td class="price">404枚</td><td class="price">89.0%</td></tr>
<tr><td><a href="red-comipara-guide.html">ルフィ レッドコミパラ</a></td><td>OP-13 / 2025年8月</td><td class="price">459枚</td><td class="price">87.3%</td></tr>
<tr class="best"><td><a href="nika-luffy-comipara.html">ニカルフィ コミパラ</a></td><td>OP-05 / <strong>2023年8月</strong></td><td class="price">2,822枚</td><td class="price"><strong>71.7%</strong></td></tr>
</tbody>
</table>

<p>最高93.2%から最低71.7%まで、<strong>20ポイント以上の開き</strong>があります。93%なら10枚出して9枚以上が10になりますが、<strong>71.7%は10枚出して3枚が9以下</strong>ということです。</p>

<h3>なぜニカルフィだけ低いのか</h3>
<p>表を発売時期で並べると傾向が見えます。<strong>2023年8月発売のニカルフィだけが突出して低く</strong>、2024年以降のカードは軒並み87%以上です。</p>

<p>考えられる要因は2つあります。ひとつは<strong>当時の保管意識</strong>で、ワンピースカードがここまで高額化する前に開封・保管された個体が多く、状態のばらつきが大きいこと。もうひとつは<strong>鑑定枚数の母数</strong>で、2,822枚という多さは「とりあえず出してみた」個体を多く含むことを意味します。</p>

<div class="callout"><strong>実務的な読み方:</strong> <strong>古い弾のカードほど「PSA10が付く前提」で計算してはいけません</strong>。逆に新しい弾のカード(取得率87〜90%)は、状態がよければ比較的高い確率でPSA10が期待できます。</div>

<h2>出すべきか｜期待値の考え方</h2>
<p>倍率と取得率が分かれば、おおよその期待値が計算できます。ここでは分かりやすさのため、<strong>PSA10にならなかった場合は素体と同程度の価値に戻る</strong>と仮定します(実際にはPSA9も素体よりやや高く売れることが多いため、やや保守的な計算です)。</p>

<h3>ケース1: サボ レッドコミパラ(取得率90.2%・倍率1.40)</h3>
<p>期待値＝0.902×84万円＋0.098×60万円＝<strong>約81.6万円</strong>。素体売却の60万円に対して<strong>約21万円のプラス</strong>で、鑑定料を引いても十分に見合う計算です。</p>

<h3>ケース2: ニカルフィ コミパラ(取得率71.7%・倍率1.66)</h3>
<p>期待値＝0.717×133万円＋0.283×80万円＝<strong>約118.0万円</strong>。素体売却の80万円に対して<strong>約38万円のプラス</strong>。倍率が高いぶん、取得率が低くても数字上はプラスに出ます。</p>

<div class="callout"><strong>ただし、この計算には重大な前提の穴があります。</strong> 次の章で説明する「PSA10相場＝販売価格」という点を織り込むと、結論は変わり得ます。</div>

<h2>最大の落とし穴｜PSA10相場は販売価格であって買取価格ではない</h2>
<p>ここが本記事でもっとも伝えたい点です。</p>

<p>一般に公開されている<strong>「PSA10相場」は、ショップやフリマでの販売価格</strong>です。一方、上の表の<strong>素体買取は買取価格</strong>です。<strong>この2つを直接比べると、鑑定のメリットを過大評価します。</strong></p>

<table class="price-table">
<thead><tr><th>比較する数字</th><th>意味</th></tr></thead>
<tbody>
<tr><td>素体 買取 ¥800,000</td><td>あなたが<strong>店に売る</strong>ときに受け取る額</td></tr>
<tr class="best"><td>PSA10 相場 ¥1,330,000</td><td>店が<strong>売る</strong>ときの値段(あなたの受取額ではない)</td></tr>
</tbody>
</table>

<p>PSA10を店に売る場合、買取価格は販売価格から相応に引かれます。ワンピースカードの素体では、販売価格に対して買取が<strong>7〜8割程度</strong>という水準が一般的です(たとえばニカルフィは販売99.8万円に対し買取80万円で約80%、ロジャーは販売89.8万円に対し買取70万円で約78%)。</p>

<p>同じ比率がPSA10にも当てはまると仮定すると、ニカルフィのPSA10買取は<strong>133万円×0.8＝約106万円</strong>。ここから鑑定料を引き、取得率71.7%を掛け直すと、素体売却80万円との差はかなり縮みます。</p>

<div class="callout"><strong>正しい比較のしかた:</strong> 鑑定を検討するなら、<strong>「PSA10の買取価格」と「素体の買取価格」を比べる</strong>のが正解です。あるいは<strong>自分で販売する前提</strong>なら、PSA10相場をそのまま使ってよいことになります。<strong>売り方によって答えが変わる</strong>と理解してください。</div>

<h2>提出前のセルフチェック</h2>
<p>費用倒れを避ける最大のコツは、<strong>PSA10が狙える個体だけ出す</strong>ことです。提出前に自分で確認できるポイントを挙げます。</p>

<h3>1. センタリング</h3>
<p>カードの絵柄が枠の中央にあるかです。PSAの基準では、表面でおおむね<strong>55/45程度までが許容範囲</strong>、<strong>60/40を超えると10は難しい</strong>とされています。明らかに片寄っている個体は、ほかが完璧でも10は取れません。</p>

<h3>2. 傷・白かけ</h3>
<p>角や縁の<strong>白かけ(白い欠け)</strong>、表面のスレ、指紋、へこみは減点対象です。<strong>一目で分かる傷がある個体はPSA10はほぼ不可能</strong>と考えてください。明るい照明の下で、角度を変えながら表裏を確認します。</p>

<h3>3. 印刷ズレ・汚れ</h3>
<p>製造段階の印刷ズレや、パック開封時に付いた汚れ・シミも評価に影響します。<strong>自分で「ほぼ完璧」と思える個体だけを候補にする</strong>のが、費用倒れを防ぐ現実的な線引きです。</p>

<h2>そのほかの注意点</h2>
<ul>
<li><strong>返却まで数ヶ月かかる</strong> — バリューなら約90営業日。その間に相場が動くリスクがあります。<a href="nika-luffy-comipara.html">ニカルフィは3ヶ月で55万→110万→80万</a>と振れており、返却時に相場が下がっている可能性は現実的に考えるべきです。</li>
<li><strong>高額カードは上位プランが必要</strong> — 申告価値によって使えるプランが決まり、料金が上がります。事前に確認してください。</li>
<li><strong>安いカードは費用倒れになりやすい</strong> — 倍率が1.5倍前後である以上、素体で数万円のカードは鑑定料と手間に見合わないことが多くなります。</li>
<li><strong>真贋の担保という価値もある</strong> — 数十万〜数百万円のカードでは、スラブ入りであること自体が売りやすさにつながります。金額だけで判断しない考え方もあります。</li>
<li><strong>すでにPSA10が多いカードもある</strong> — ナミ パラレル(OP-01)は7,824枚、サインルフィは3,331枚がPSA10になっています。希少性そのものが薄れている枠もあると理解しておきましょう。</li>
</ul>""",
        "faq": [
            {"q": "ワンピースカードをPSA10にすると、どのくらい価値が上がりますか？",
             "a": "2026年8月24日時点の実データでは、素体の買取価格に対してPSA10相場は1.40〜1.66倍です(ニカルフィ1.66倍、エース レッドコミパラ1.63倍、ロジャー金1.56倍、ルフィ レッドコミパラ1.49倍、サボ レッドコミパラ1.40倍)。「倍以上になる」というイメージより控えめで、おおむね1.5倍前後と考えるのが実態に近い水準です。"},
            {"q": "PSA10はどのくらいの確率で付きますか？",
             "a": "カードによって大きく異なり、当サイトが確認できた範囲では71.7%〜93.2%と20ポイント以上の開きがあります。特に2023年8月発売のニカルフィ コミパラは71.7%と低く、10枚出せば3枚は9以下になる計算です。一方2024年以降発売のカードは87〜90%台が中心で、状態がよければ比較的高い確率でPSA10が期待できます。"},
            {"q": "鑑定料はいくらかかりますか？",
             "a": "2026年8月時点の目安で、バリューが約4,980円(納期約90営業日)、バリュー・プラスが約7,980円(約60営業日)、レギュラーが約11,980円(約30〜60営業日)などです。ただしPSAのプランは申告価値によって使えるものが決まり、レギュラーの上限は25万円程度とされています。数十万〜数百万円のカードはより上位の高額プランが必要になるため、提出前に必ず公式サイトで最新の料金と条件を確認してください。"},
            {"q": "PSA10相場と素体買取を比べれば、出すべきか判断できますか？",
             "a": "できません。これが最大の落とし穴です。公開されている「PSA10相場」は販売価格であり、素体買取は買取価格だからです。PSA10を店に売る場合の買取価格は販売価格から引かれます(ワンピカードの素体では販売価格の7〜8割程度が一般的)。鑑定を検討するなら「PSA10の買取価格」と「素体の買取価格」を比べてください。自分で販売するつもりならPSA10相場をそのまま使って構いません。"},
            {"q": "出す前に自分で確認できることはありますか？",
             "a": "センタリング(絵柄の片寄り)、角や縁の白かけ、表面のスレや指紋、印刷ズレや汚れの4点です。センタリングはおおむね55/45程度までが許容範囲で、60/40を超えるとPSA10は難しいとされています。一目で分かる傷がある個体はPSA10はほぼ不可能なので、自分で「ほぼ完璧」と思える個体だけを候補にするのが費用倒れを防ぐ線引きです。"},
        ],
    },
    {
        "slug": "box-price-pattern",
        "nav_label": "BOX相場の値動きパターン",
        "crumb": "ワンピBOX相場の値動きパターン",
        "date": "2026-08-24",
        "date_jp": "2026年8月24日",
        "title": "ワンピBOX相場の値動きパターン｜実データで見えた「新しい弾ほど下がる」傾向と、カード相場と連動しない理由",
        "h1": "ワンピBOX相場の値動きパターン｜実データで見えた「新しい弾ほど下がる」傾向と、カード相場と連動しない理由",
        "meta_desc": "当サイトが最大9店舗から毎日自動取得しているワンピースカードのBOX買取実データで、全弾の値動きを横断分析。同じ期間にカード相場は全弾が下落したにもかかわらず、BOX相場は上昇と下落がほぼ拮抗しました。下落が直近弾に集中し古い弾ほど堅いという傾向、そこから読み取れる供給量の構造、買い時・売り時の考え方までを実測値で整理します。",
        "og_title": "ワンピBOX相場の値動きパターン｜新しい弾ほど下がる傾向を実データで",
        "og_desc": "最大9店舗のBOX買取実データで全弾の値動きを横断分析。カード相場が全弾下落した期間もBOXは拮抗。下落が直近弾に集中する傾向と、買い時・売り時の考え方。",
        "meta_line": "全弾のBOX買取値動き実測・パターン分析・売買タイミング",
        "hero_label": "ワンピBOX相場 値動きレポート",
        "hero_big": "上昇{{CHG_UP}} / 下落{{CHG_DOWN}} / 横ばい{{CHG_FLAT}}",
        "hero_sub": "当サイトが最大9店舗から毎日自動取得しているBOX買取実データで、全{{CHG_N}}弾の値動きを横断集計しました({{CHG_PERIOD}}時点)。平均変化率は{{CHG_AVG}}。同じ期間にカード相場は全弾が下落しており、BOXとカードが別の動きをしていることが実測で確認できます。",
        "disclaimer": "本記事のBOX買取価格は、当サイトが最大9店舗から自動取得した実データです。各弾の「最高買取価格」(掲載店舗のうち最も高い店の価格)を用いており、店舗ごとの価格差や、掲載店舗の増減による変動を含みます。集計期間は当サイトのワンピ価格履歴が蓄積されている範囲に限られ、長期のトレンドを断定できるだけの期間ではありません。値動きの<strong>理由</strong>については、再販や出荷の実施状況を公開情報で確認できた範囲を超えて断定していません(バンダイは個別弾の再販を網羅的に公表していないため)。カード相場に関する記述は altema 掲載のカードラッシュ買取価格(2026年8月24日時点)を基準にした比較です。相場は今後も変動し、本記事の傾向が継続することを保証するものではありません。売買の判断はご自身の責任で行ってください。",
        "related": '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較(毎日更新)</li>\n'
                   '<li><a href="weekly.html">週間値動きランキング</a> — 直近7日間の値上がり・値下がりを毎日自動更新</li>\n'
                   '<li><a href="kougaku-ranking.html">高額BOXランキング・絶版ガイド</a> — 全弾の最高買取・定価比ランキング</li>\n'
                   '<li><a href="comipara-ranking.html">歴代コミックパラレル相場ランキング全22弾</a> — カード側の相場ランキング</li>\n'
                   '<li><a href="toushi.html">ワンピカードBOX投資の始め方</a> — 値上がりしやすいBOXの特徴と保管・リスク</li>\n'
                   '<li><a href="kaitori-hikaku.html">ワンピBOX買取比較ガイド</a> — 売るときの店舗選びと高く売るコツ</li>',
        "body": """<p>「ワンピースカードのBOXは今、上がっているのか下がっているのか」——この問いに、<strong>当サイトが最大9店舗から毎日自動取得しているBOX買取の実データ</strong>で答えます。</p>

<p>集計期間は<strong>{{CHG_PERIOD}}</strong>。全{{CHG_N}}弾を横断すると、上昇{{CHG_UP}}弾・下落{{CHG_DOWN}}弾・横ばい{{CHG_FLAT}}弾、平均変化率は<strong>{{CHG_AVG}}</strong>でした。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・同じ期間に<strong>カード相場は全弾が下落</strong>したが、<strong>BOX相場は上昇{{CHG_UP}}・下落{{CHG_DOWN}}でほぼ拮抗</strong><br>
・<strong>下落は発売の新しい弾に集中</strong>。古い弾は横ばいか上昇で、明確な差が出た<br>
・BOXとカードは<strong>別の力学で動く</strong>。片方の相場からもう片方を推測すると外す</div>

<h2>全弾のBOX買取 値動き一覧</h2>
<p>期間はじめと最新の最高買取価格、その変化率です(集計は{{CHG_PERIOD}}時点)。<strong>直近7日間の動きは<a href="weekly.html">週間値動きランキング</a>で毎日自動更新</strong>しているので、売買直前の判断はそちらもあわせてご確認ください。弾名から各弾の当たりカードガイドに移動できます。</p>

{{PRICE_CHANGE_TABLE}}

<p>最大の上昇は<strong>{{CHG_TOP_NAME}}({{CHG_TOP_PCT}})</strong>、最大の下落は<strong>{{CHG_BOTTOM_NAME}}({{CHG_BOTTOM_PCT}})</strong>でした。</p>

<div class="callout"><strong>表の読み方の注意:</strong> スタートデッキEX(ST-30)は定価¥1,980の構築済みデッキで、定価¥5,280前後のブースターパックとは商品性が異なります。値動きの幅も大きく出やすいため、ブースター同士の比較とは分けて見てください。</div>

<h2>発見①｜カードは全弾下落、BOXは拮抗</h2>
<p>この期間、<strong>カード相場は極めて厳しい動きをしていました</strong>。当サイトが弾別の当たりカード相場を更新した際、コミックパラレルを収録する全22弾のトップレアが、そろって下落していたことが確認できています。下落幅は最大で40%を超える弾もありました。</p>

<p>ところが同じ期間、<strong>BOX買取は上昇{{CHG_UP}}弾・下落{{CHG_DOWN}}弾・横ばい{{CHG_FLAT}}弾</strong>で、平均でも{{CHG_AVG}}にとどまっています。</p>

<div class="callout"><strong>これが意味すること:</strong> 「看板カードが下がったからBOXも下がるはず」という推測は、<strong>実データでは成立していません</strong>。カードとBOXは連動しているように見えて、実際には別々の力学で動いています。この構造は静的な順位比較でも確認しており、<a href="comipara-ranking.html">歴代コミックパラレル相場ランキング</a>でカード相場1位の弾がBOX買取では上位ではない、といったズレが起きています。</div>

<h2>発見②｜下落は「新しい弾」に集中している</h2>
<p>下落した弾を発売時期で並べ直すと、はっきりした偏りが出ます。<strong>大きく下げているのは直近に発売された弾</strong>で、それ以外の弾は横ばいか小幅な動きに収まっています。</p>

<p>本記事の執筆時点では、<a href="op-15-atari-guide.html">神の島の冒険(OP-15)</a>と<a href="op-16-atari-guide.html">決戦の刻(OP-16)</a>——いずれも2026年に発売された比較的新しい弾——が下落幅の上位を占めていました。一方で<a href="op-01-atari-guide.html">ROMANCE DAWN(OP-01)</a>や<a href="op-05-atari-guide.html">新時代の主役(OP-05)</a>のような古い弾は、ほぼ横ばいを維持しています。</p>

<h3>考えられる構造</h3>
<p>理由を断定できる公開情報は確認できていませんが、BOX相場の一般的な構造からは次のように整理できます。</p>
<ul>
<li><strong>新しい弾は供給が続いている</strong> — 発売から間もない弾は追加出荷や再販がかかりやすく、市場の未開封在庫が増えます。実際、OP-15については2026年4月中旬の追加出荷が販売店から案内されていました(それ以降の再販状況は当サイトでは確認できていません)。</li>
<li><strong>古い弾は供給が止まっている</strong> — 時間が経つほど開封が進んで未開封BOXが減り、再販も新弾に集中するため、価格が下支えされます。</li>
<li><strong>新弾の発売が直前弾の需要を吸う</strong> — 新しい弾が出ると開封需要がそちらに移り、直前弾の相場が緩みやすくなります。</li>
</ul>

<div class="callout"><strong>注意:</strong> ONE PIECEカードゲームには「絶版」「生産終了」の公式アナウンス制度がなく、バンダイは個別弾の再販を網羅的に公表していません。そのため上記はあくまで<strong>BOX相場の一般的な構造からの整理</strong>であり、特定の弾の値動きの原因を断定するものではありません。</div>

<h2>発見③｜古い弾ほど堅い</h2>
<p>この期間に上昇した弾・横ばいだった弾を見ると、<strong>2023〜2024年に発売された弾が中心</strong>です。発売から1年以上が経過し、未開封BOXの流通量が絞られてきた弾ほど、値動きが安定しています。</p>

<p>これは<a href="kougaku-ranking.html">高額BOXランキング</a>で見られる「古い弾ほど定価比が高い」という構造とも整合します。2026年4月にブロック①としてスタンダード使用不可になったOP-01が、それでもBOX買取で上位を維持していることが象徴的です。<strong>競技での使用可否よりも、未開封BOXがどれだけ市場に残っているかのほうが、BOX相場への影響が大きい</strong>と読み取れます。</p>

<h2>実務的な示唆</h2>
<h3>買う場合</h3>
<ul>
<li><strong>新しい弾は焦らない</strong> — 発売直後から数ヶ月は供給が続き、相場が緩みやすい局面です。直前弾が下げているうちは、押し目を待つ判断がしやすくなります。</li>
<li><strong>古い弾は下がりにくいが、その分すでに高い</strong> — 値動きが安定している弾は参入コストも高くなっています。定価比は<a href="kougaku-ranking.html">高額BOXランキング</a>で確認できます。</li>
</ul>

<h3>売る場合</h3>
<ul>
<li><strong>新弾発売前に動く</strong> — 新しい弾が出ると直前弾の需要が移りやすいため、発売スケジュールを意識した売却が有利になりやすい局面があります。</li>
<li><strong>短期の値動きは<a href="weekly.html">週間値動きランキング</a>で</strong> — 本記事は長めの期間の傾向を見るものです。売る直前の判断は直近7日の動きも合わせて確認してください。</li>
<li><strong>必ず複数店を比較する</strong> — 本記事の数値は「最高買取価格」です。同じ弾でも店舗差があるため、<a href="/onepiece">比較トップ</a>で最高値の店を確認してから売却してください。</li>
</ul>

<h2>この分析の限界</h2>
<ul>
<li><strong>期間が短い</strong> — 集計期間は{{CHG_DAYS}}日間です。季節性や年単位のトレンドを判断できる長さではありません。</li>
<li><strong>理由は断定していない</strong> — 再販の実施状況が網羅的に公表されないため、個別弾の値動きの原因は特定できません。本記事は「何が起きたか」の記録であり、「なぜ起きたか」の証明ではありません。</li>
<li><strong>最高買取価格ベース</strong> — 掲載店舗の増減や、特定店の値付け変更が数値に影響します。</li>
<li><strong>傾向は変わり得る</strong> — 本記事の数値は{{CHG_PERIOD}}時点の集計です。相場は日々動くため、最新の順位は<a href="/onepiece">比較トップ</a>、直近の値動きは<a href="weekly.html">週間値動きランキング</a>でご確認ください。</li>
</ul>""",
        "faq": [
            {"q": "ワンピースカードのBOX相場は今、上がっていますか？下がっていますか？",
             "a": "集計期間{{CHG_PERIOD}}では、上昇{{CHG_UP}}弾・下落{{CHG_DOWN}}弾・横ばい{{CHG_FLAT}}弾で、平均変化率は{{CHG_AVG}}でした。全体としてどちらか一方に傾いているというより、弾ごとに動きが分かれている状況です。これは{{CHG_PERIOD}}時点の集計です。直近7日間の値動きは週間値動きランキングで毎日自動更新しています。"},
            {"q": "カードの相場が下がったら、BOXも下がりますか？",
             "a": "実データでは連動していません。この集計期間、コミックパラレルを収録する全22弾のトップレアがそろって下落した一方で、BOX買取は上昇{{CHG_UP}}弾・下落{{CHG_DOWN}}弾とほぼ拮抗していました。BOX価格は市場に残る未開封在庫の量に強く影響されるため、看板カードの相場とは別の力学で動きます。"},
            {"q": "どんな弾が下がりやすいですか？",
             "a": "本記事の集計では、下落は発売から間もない弾に集中していました。新しい弾は追加出荷や再販がかかりやすく市場の未開封在庫が増えること、新弾が出ると開封需要がそちらに移ることが、BOX相場の一般的な構造として考えられます。ただしバンダイは個別弾の再販を網羅的に公表していないため、特定の弾の値動きの原因を断定することはできません。"},
            {"q": "スタンダードで使えなくなった弾は暴落しますか？",
             "a": "実データではそうなっていません。2026年4月にブロック①としてスタンダード使用不可になったOP-01は、その後もBOX買取で上位を維持しています。競技での使用可否よりも、未開封BOXがどれだけ市場に残っているかのほうがBOX相場への影響が大きいと読み取れます。"},
            {"q": "買い時・売り時はどう判断すればいいですか？",
             "a": "買う場合は、新しい弾は供給が続いて相場が緩みやすいため焦らず押し目を待つ、古い弾は下がりにくい反面すでに高いという前提で考えます。売る場合は、新弾発売で直前弾の需要が移りやすいことを意識しつつ、直前の判断は週間値動きランキングで直近7日の動きも確認してください。いずれの場合も、実際の売却時は比較トップで最高値の店舗を確認することをおすすめします。"},
        ],
    },
    {
        "slug": "anniversary-sp-guide",
        "nav_label": "3周年スペシャル(金/銀)徹底解説",
        "crumb": "3周年スペシャルカード(金/銀)",
        "date": "2026-08-25",
        "date_jp": "2026年8月25日",
        "title": "ワンピ3周年スペシャル(金/銀)徹底解説｜ルフィ金140万・ティーチ25万・バギー18万と、唯一BOX代を上回るカード",
        "h1": "ワンピ3周年スペシャルカード(金/銀)徹底解説｜ルフィ金140万・ティーチ25万・バギー18万の相場と封入率",
        "meta_desc": "ワンピースカードの3周年スペシャルカード(金/銀)全6枚を横断解説。神速の拳(OP-11)のルフィ、師弟の絆(OP-12)のティーチ、蒼海の七傑(OP-14)のバギーが金銀2種ずつ収録され、2026年8月24日時点の買取はルフィ金140万・銀80万、ティーチ金25万・銀13万、バギー金18万・銀9万。金は銀の約1.75〜2.00倍という規則性、キャラ間で最大7.8倍の差、コミックパラレルより低い封入率、そしてルフィ金だけがBOX代換算を上回る唯一のカードである点までデータで整理します。",
        "og_title": "ワンピ3周年スペシャル(金/銀)徹底解説｜相場・封入率・BOX代換算",
        "og_desc": "3周年SP全6枚を横断解説。ルフィ金140万・ティーチ25万・バギー18万の相場、金は銀の約2倍という規則性、コミパラより低い封入率、ルフィ金だけBOX代を上回る理由。",
        "meta_line": "3周年スペシャル6枚の相場・封入率・BOX代換算",
        "hero_label": "3周年スペシャルカード(金/銀) 全6枚",
        "hero_big": "ルフィ(金) 買取 約¥1,400,000",
        "hero_sub": "神速の拳(OP-11)・師弟の絆(OP-12)・蒼海の七傑(OP-14)の3弾に、金と銀の2種ずつ収録された3周年記念の特別仕様。コミックパラレルより封入率が低いにもかかわらず、レアリティが別枠のためコミパラのランキングには登場しません。相場は2026年8月24日時点。",
        "disclaimer": "本記事のカード買取価格は<strong>2026年8月24日時点</strong>にカード相場メディア altema が掲載する<strong>カードラッシュの買取価格</strong>を基準にした目安です。1店舗の買取価格のため、他店の査定額や販売価格とは異なります(別ソースでは同じカードに±10%程度の差が出ています)。<strong>封入率はバンダイの公式発表ではなく</strong>、開封報告等をもとにトレカ系メディアが公開している推定値で、ソースにより数値に幅があります。本記事のBOX代換算は、その推定封入率に定価を掛けた<strong>机上の計算</strong>であり、実際の開封結果を保証するものではありません。この確率帯では分散が極めて大きく、目安の倍のBOXを開けても出ないことは普通に起こります。BOX買取価格は当サイトが最大9店舗から自動取得した実データです。売買・開封の判断はご自身の責任で行ってください。",
        "related": '<li><a href="comipara-ranking.html">歴代コミックパラレル相場ランキング全22弾</a> — コミパラ側の相場ランキング(3周年SPは別枠のため未収録)</li>\n'
                   '<li><a href="op-11-atari-guide.html">神速の拳(OP-11) 当たりカードガイド</a> — ルフィ3周年SPを収録する弾</li>\n'
                   '<li><a href="op-12-atari-guide.html">師弟の絆(OP-12) 当たりカードガイド</a> — ティーチ3周年SPを収録する弾</li>\n'
                   '<li><a href="op-14-atari-guide.html">蒼海の七傑(OP-14) 当たりカードガイド</a> — バギー3周年SPを収録する弾</li>\n'
                   '<li><a href="psa-guide.html">ワンピースカードのPSA鑑定ガイド</a> — 高額カードを鑑定に出すべきかの判断基準</li>\n'
                   '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較</li>',
        "body": """<p><strong>3周年スペシャルカード</strong>は、ONE PIECEカードゲーム3周年を記念して<strong>金と銀の2種類</strong>で作られた特別仕様のカードです。<a href="op-11-atari-guide.html">神速の拳(OP-11)</a>のルフィ、<a href="op-12-atari-guide.html">師弟の絆(OP-12)</a>のティーチ、<a href="op-14-atari-guide.html">蒼海の七傑(OP-14)</a>のバギーと、<strong>3弾にわたって計6枚</strong>が存在します。</p>

<p>この6枚には見落とされがちな特徴があります。<strong>コミックパラレルより封入率が低いにもかかわらず、レアリティが別枠のため<a href="comipara-ranking.html">コミパラのランキング</a>には一切登場しない</strong>のです。ルフィの金は買取140万円で、実質的にワンピースカードで2番目に高い部類にあたります。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・<strong>金は銀の約1.75〜2.00倍</strong>。3枚とも例外なくこのレンジに収まる規則性がある<br>
・キャラ間の差は最大<strong>7.8倍</strong>(ルフィ金140万 vs バギー金18万)。封入率はほぼ同等なので純粋な人気差<br>
・<strong>ルフィ金だけがBOX代換算を上回る</strong>。他の高額カードと違い、自引きが理論上プラスになる稀なケース</div>

<h2>3周年スペシャルカードとは</h2>
<p>2025年から2026年にかけて発売された3弾に、それぞれ1キャラずつ、金と銀の2バージョンで収録されました。通常のパックにごく低確率で封入される特別仕様で、公式のレアリティ表記は<strong>SP(スペシャルカード)</strong>です。</p>

<table class="price-table">
<thead><tr><th>収録弾</th><th>キャラクター</th><th>種類</th><th style="text-align:right">BOX定価</th></tr></thead>
<tbody>
<tr><td><a href="op-11-atari-guide.html">神速の拳(OP-11)</a></td><td><strong>モンキー・D・ルフィ</strong></td><td>金・銀の2種</td><td class="price">¥5,280</td></tr>
<tr><td><a href="op-12-atari-guide.html">師弟の絆(OP-12)</a></td><td>マーシャル・D・ティーチ</td><td>金・銀の2種</td><td class="price">¥5,280</td></tr>
<tr><td><a href="op-14-atari-guide.html">蒼海の七傑(OP-14)</a></td><td>バギー</td><td>金・銀の2種</td><td class="price">¥5,280</td></tr>
</tbody>
</table>

<h2>全6枚の買取相場(2026年8月24日時点)</h2>
<table class="price-table">
<thead><tr><th>カード</th><th>収録</th><th style="text-align:right">金</th><th style="text-align:right">銀</th><th style="text-align:right">金/銀の倍率</th></tr></thead>
<tbody>
<tr class="best"><td><strong>モンキー・D・ルフィ</strong></td><td>OP-11</td><td class="price"><strong>¥1,400,000</strong></td><td class="price">¥800,000</td><td class="price">1.75倍</td></tr>
<tr><td>マーシャル・D・ティーチ</td><td>OP-12</td><td class="price">¥250,000</td><td class="price">¥130,000</td><td class="price">1.92倍</td></tr>
<tr><td>バギー</td><td>OP-14</td><td class="price">¥180,000</td><td class="price">¥90,000</td><td class="price">2.00倍</td></tr>
</tbody>
</table>

<h2>発見①｜金は銀の約2倍という規則性</h2>
<p>3枚とも、金は銀の<strong>1.75〜2.00倍</strong>に収まっています。キャラクターの人気も相場の絶対額もまったく違うのに、<strong>金銀の比率だけは揃っている</strong>のが興味深い点です。</p>

<div class="callout"><strong>実務的な使い方:</strong> この規則性は<strong>価格の妥当性チェック</strong>に使えます。フリマなどで金銀どちらかの出品を見たとき、もう一方の相場から「おおむね2倍(または半分)か」を確認すれば、相場から外れた値付けに気づけます。金銀の差が3倍以上あるような出品は、状態や版に何か違いがないか確認したほうがよいでしょう。</div>

<h2>発見②｜キャラ間で最大7.8倍の差</h2>
<p>一方で、キャラクター間の差は極端です。</p>
<ul>
<li>ルフィ金は<strong>ティーチ金の5.6倍</strong></li>
<li>ルフィ金は<strong>バギー金の7.8倍</strong></li>
</ul>
<p>後述するとおり<strong>封入率は3弾でほぼ同水準</strong>です。つまりこの差は希少性ではなく、<strong>純粋にキャラクター人気と主人公補正</strong>によるものです。これは<a href="comipara-ranking.html">コミックパラレルのランキング</a>で見られた傾向(カード単体TOP12のうち6枚がルフィ)とも一致します。</p>

<h2>封入率｜コミパラより低い</h2>
<p>3周年スペシャルの封入率は、トレカ系メディアが公開している推定値では次のとおりです。<strong>いずれも公式発表ではなく、ソースにより幅があります。</strong></p>

<table class="price-table">
<thead><tr><th>弾</th><th style="text-align:right">3周年SP枠</th><th style="text-align:right">狙いの1枚(金または銀)</th></tr></thead>
<tbody>
<tr><td><a href="op-11-atari-guide.html">神速の拳(OP-11)</a></td><td class="price">約0.95%(約105BOXに1枚)</td><td class="price">約0.47%(<strong>約211.5BOX</strong>に1枚)</td></tr>
<tr><td><a href="op-12-atari-guide.html">師弟の絆(OP-12)</a></td><td class="price">約0.64%(約157.4BOXに1枚)</td><td class="price">約0.32%(<strong>約314.8BOX</strong>に1枚)</td></tr>
<tr><td><a href="op-14-atari-guide.html">蒼海の七傑(OP-14)</a></td><td class="price">約0.73%(約137.3BOXに1枚)</td><td class="price">約0.36%(<strong>約274.6BOX</strong>に1枚)</td></tr>
</tbody>
</table>

<p>参考までに、コミックパラレルの一般的な封入率は<strong>6カートン(約72BOX)に約1枚</strong>とされています。3周年SPは枠自体が105〜157BOXに1枚で、<strong>コミパラよりも明確に低い</strong>水準です。それでもコミパラのランキングに載らないのは、単に<strong>レアリティの区分が別</strong>だからにすぎません。</p>

<h2>発見③｜ルフィ金だけがBOX代を上回る</h2>
<p>ここが本記事でもっとも重要な点です。上の封入率をBOX定価(¥5,280)で金額に換算し、カードの買取価格と比べます。</p>

<table class="price-table">
<thead><tr><th>狙うカード</th><th style="text-align:right">必要BOX数</th><th style="text-align:right">BOX代換算</th><th style="text-align:right">カード買取</th><th style="text-align:right">差</th></tr></thead>
<tbody>
<tr class="best"><td><strong>ルフィ(金)</strong></td><td class="price">約211.5BOX</td><td class="price">約¥1,117,000</td><td class="price"><strong>¥1,400,000</strong></td><td class="price" style="color:#15803d;font-weight:700">+約28万円</td></tr>
<tr><td>ティーチ(金)</td><td class="price">約314.8BOX</td><td class="price">約¥1,662,000</td><td class="price">¥250,000</td><td class="price" style="color:#b91c1c;font-weight:700">-約141万円</td></tr>
<tr><td>バギー(金)</td><td class="price">約274.6BOX</td><td class="price">約¥1,450,000</td><td class="price">¥180,000</td><td class="price" style="color:#b91c1c;font-weight:700">-約127万円</td></tr>
</tbody>
</table>

<p><strong>ルフィ金だけが、BOX代換算をカードの買取価格が上回っています。</strong>しかも実際に211BOXを開ければ、ルフィ金以外にも銀・コミックパラレル・SP・パラレルが大量に出るため、実際の回収額はさらに上振れします。</p>

<p>これは当サイトが扱ってきた他の高額カードとは対照的です。<a href="red-comipara-guide.html">レッドコミパラのルフィ</a>は約631BOX(約333万円)に1枚で買取230万円、<a href="nika-luffy-comipara.html">ニカルフィ</a>は約288BOX(約152万円)に1枚で買取80万円と、<strong>いずれも自引きが大きく不利</strong>でした。3周年SPのルフィ金は、当サイトが確認した範囲で<strong>唯一の例外</strong>です。</p>

<div class="callout"><strong>ただし、鵜呑みにしないでください:</strong><br>
・<strong>封入率は公式非公表の推定値</strong>です。ソースにより数値に幅があり、この計算の前提が揺らげば結論も変わります<br>
・<strong>分散が極めて大きい</strong>確率帯です。211BOXは「平均して1枚出る」という意味であり、その倍を開けても出ないことは普通に起こります<br>
・<strong>211BOX＝約112万円の資金</strong>が先に必要です。資金効率と在庫リスクを考えれば、素直にカードを買うほうが確実です<br>
・買取価格は変動します。別ソースでは同じルフィ金を約125万円としており、その水準でもプラスではありますが差は縮みます</div>

<p>結論としては「<strong>理論上はプラスだが、実行する合理性は薄い</strong>」というのが正確なところです。むしろこの計算が示しているのは、<strong>ルフィ金の相場が封入率に対して割高</strong>——言い換えれば<strong>人気が希少性を大きく上回って評価されている</strong>という事実です。</p>

<h2>なぜコミパラのランキングに載らないのか</h2>
<p>3周年スペシャルは、レアリティ表記が<strong>SP(スペシャルカード)</strong>で、コミックパラレル(スーパーパラレル)とは別の区分です。そのため各メディアの「コミパラランキング」や、当サイトの<a href="comipara-ranking.html">歴代コミックパラレル相場ランキング</a>にも登場しません。</p>

<div class="callout"><strong>見落としに注意:</strong> コミパラのランキングだけを見て弾の実力を判断すると、OP-11を読み違えます。OP-11のコミパラ最高額は約14万円で全22弾中11位ですが、同じ弾に<strong>買取140万円のルフィ金</strong>が存在します。BOX買取でOP-11が上位に入っているのは、このSP枠が開封需要を牽引しているためと考えられます。</div>

<h2>売買の注意点</h2>
<ul>
<li><strong>金か銀かを必ず確認する</strong> — 名称が似ており、相場は約2倍違います。背景の箔の色が金か銀かで判別できます。</li>
<li><strong>通常のSPと混同しない</strong> — 各弾には3周年SP以外にも通常のスペシャルカードが収録されています。相場は桁が違うため、3周年仕様かどうかを確認してください。</li>
<li><strong>ソースによる価格差が大きい</strong> — 本記事はaltema掲載のカードラッシュ買取を基準にしていますが、別ソースではルフィ金を約125万円としています。売却時は必ず複数店を比較してください。</li>
<li><strong>状態の影響が大きい</strong> — 100万円超の価格帯では、センタリングや白かけが査定に直結します。鑑定に出すかの判断は<a href="psa-guide.html">PSA鑑定ガイド</a>を参照してください。</li>
<li><strong>BOX買いで狙うなら分散を理解する</strong> — 理論上プラスなのはルフィ金のみで、それも「平均すれば」の話です。ティーチ金・バギー金は大幅なマイナスになります。</li>
</ul>""",
        "faq": [
            {"q": "3周年スペシャルカードは何種類ありますか？",
             "a": "神速の拳(OP-11)のルフィ、師弟の絆(OP-12)のティーチ、蒼海の七傑(OP-14)のバギーが、それぞれ金と銀の2種ずつ収録されており、計6枚です。通常のパックにごく低確率で封入される特別仕様で、公式のレアリティ表記はSP(スペシャルカード)です。"},
            {"q": "3周年スペシャルの買取価格はいくらですか？",
             "a": "2026年8月24日時点で、ルフィ金140万円・銀80万円、ティーチ金25万円・銀13万円、バギー金18万円・銀9万円です(altema掲載のカードラッシュ買取価格基準)。金は銀の約1.75〜2.00倍という規則性があり、3枚とも例外なくこのレンジに収まっています。"},
            {"q": "なぜルフィだけこんなに高いのですか？",
             "a": "封入率は3弾でほぼ同水準(105〜157BOXに1枚)なので、希少性の差ではありません。ルフィ金はティーチ金の5.6倍、バギー金の7.8倍で、これは純粋にキャラクター人気と主人公補正によるものです。コミックパラレルでも同じ傾向があり、カード単体のTOP12のうち6枚をルフィが占めています。"},
            {"q": "BOXを買って3周年スペシャルを狙うのは得ですか？",
             "a": "ルフィ金のみ、理論上はプラスです。狙いの1枚は約211.5BOXに1枚とされ、BOX代換算で約111.7万円。買取140万円を下回るため計算上は上回ります。一方ティーチ金は約314.8BOX(約166万円)に対し買取25万円、バギー金は約274.6BOX(約145万円)に対し買取18万円と大幅なマイナスです。ただしルフィ金についても封入率は公式非公表の推定値で、分散が極めて大きく、211BOXの倍を開けても出ないことは普通に起こります。約112万円の資金が先に必要な点も含め、実行する合理性は薄いと考えてください。"},
            {"q": "コミパラのランキングに3周年スペシャルが載っていないのはなぜですか？",
             "a": "レアリティ表記がSP(スペシャルカード)で、コミックパラレル(スーパーパラレル)とは別の区分だからです。封入率はコミパラ(6カートン=約72BOXに1枚)より低いにもかかわらず、区分が違うためランキングには登場しません。コミパラのランキングだけで弾の実力を判断すると、買取140万円のルフィ金を擁するOP-11を読み違えることになります。"},
        ],
    },
]


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


def _box_ranking_rows(box: dict) -> list:
    """ONEPIECE_PRODUCTS と実データを突合し、最高買取の降順で行を返す。"""
    import re
    from scraper.products_onepiece import ONEPIECE_PRODUCTS

    rows = []
    for p in ONEPIECE_PRODUCTS:
        m = re.search(r"(OP|EB|PRB|ST)-?(\d+)", p.name)
        if not m:
            continue
        slug = f"{m.group(1).lower()}-{int(m.group(2)):02d}"
        if slug not in box:
            continue
        price, _stores = box[slug]
        label = p.name.split("【")[0].replace("ブースターパック", "").replace(
            "エクストラブースター", "").replace("プレミアムブースター", "").strip()
        rows.append({
            "slug": slug, "code": m.group(0).upper().replace("-", "-"),
            "label": label or p.name, "release": p.release_date,
            "retail": p.retail_price, "price": price,
            "mult": price / p.retail_price if p.retail_price else 0,
        })
    rows.sort(key=lambda r: r["price"], reverse=True)
    return rows


def _box_ranking_table(box: dict) -> str:
    body = ""
    for i, r in enumerate(_box_ranking_rows(box), 1):
        cls = ' class="best"' if i == 1 else ""
        y, mth, _d = r["release"].split("-")
        body += (f'<tr{cls}><td>{i}位</td>'
                 f'<td><a href="{r["slug"]}-atari-guide.html">{_esc(r["label"])}</a>'
                 f'<br><span style="font-size:11px;color:#6b7280">{_esc(r["code"])}</span></td>'
                 f'<td>{int(y)}年{int(mth)}月</td>'
                 f'<td class="price">¥{r["retail"]:,}</td>'
                 f'<td class="price">¥{r["price"]:,}</td>'
                 f'<td class="price">約{r["mult"]:.1f}倍</td></tr>')
    return ('<table class="price-table"><thead><tr><th>順位</th><th>弾</th>'
            '<th>発売</th><th style="text-align:right">定価</th>'
            '<th style="text-align:right">最高買取</th>'
            '<th style="text-align:right">定価比</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


# 値動きレポート記事で使う期間(日)。history_op がこれより短ければ全期間を使う。
PRICE_CHANGE_WINDOW_DAYS = 60


def _history_op_at(days_ago: int):
    """days_ago 日前に最も近い history_op を (日付文字列, {slug: max_price}) で返す。"""
    import re
    from datetime import date, timedelta
    files = sorted(HISTORY_OP_DIR.glob("*.json"))
    if not files:
        return None, {}
    latest = date.fromisoformat(files[-1].stem)
    target = latest - timedelta(days=days_ago)
    pick = files[0]
    for f in files:
        try:
            if date.fromisoformat(f.stem) <= target:
                pick = f
        except ValueError:
            continue
    data = json.loads(pick.read_text(encoding="utf-8"))
    out = {}
    for r in data:
        m = re.search(r"(OP|EB|PRB|ST)-?(\d+)", r["name"])
        if not m:
            continue
        out[f"{m.group(1).lower()}-{int(m.group(2)):02d}"] = r.get("max_price", 0)
    return pick.stem, out


def _price_change_rows() -> tuple:
    """(期間ラベル, [行], 集計) を返す。行は変化率の降順。"""
    from datetime import date
    files = sorted(HISTORY_OP_DIR.glob("*.json"))
    if len(files) < 2:
        return "", [], {}
    old_day, old = _history_op_at(PRICE_CHANGE_WINDOW_DAYS)
    new_day, new = _history_op_at(0)
    if not old or not new:
        return "", [], {}
    labels = {a["slug"]: a["short_name"] for a in _all_articles()}
    rows = []
    for slug in sorted(set(old) & set(new)):
        o, n = old.get(slug, 0), new.get(slug, 0)
        if o <= 0 or n <= 0:
            continue
        rows.append({"slug": slug, "label": labels.get(slug, slug.upper()),
                     "old": o, "new": n, "pct": (n - o) / o * 100})
    rows.sort(key=lambda r: -r["pct"])
    up = sum(1 for r in rows if r["pct"] > 1)
    down = sum(1 for r in rows if r["pct"] < -1)
    flat = len(rows) - up - down
    avg = sum(r["pct"] for r in rows) / len(rows) if rows else 0
    d0, d1 = date.fromisoformat(old_day), date.fromisoformat(new_day)
    period = (f"{d0.year}年{d0.month}月{d0.day}日〜{d1.month}月{d1.day}日"
              f"({(d1 - d0).days}日間)")
    agg = {"up": up, "down": down, "flat": flat, "avg": avg, "n": len(rows),
           "days": (d1 - d0).days}
    return period, rows, agg


def _all_articles() -> list:
    from scraper.article_data_onepiece import ARTICLES
    return ARTICLES


def _price_change_table(rows: list) -> str:
    body = ""
    for r in rows:
        cls = ""
        if r["pct"] > 1:
            cls = ' style="color:#15803d;font-weight:700"'
        elif r["pct"] < -1:
            cls = ' style="color:#b91c1c;font-weight:700"'
        body += (f'<tr><td><a href="{r["slug"]}-atari-guide.html">{_esc(r["label"])}</a>'
                 f'<br><span style="font-size:11px;color:#6b7280">{r["slug"].upper()}</span></td>'
                 f'<td class="price">¥{r["old"]:,}</td>'
                 f'<td class="price">¥{r["new"]:,}</td>'
                 f'<td class="price"{cls}>{r["pct"]:+.1f}%</td></tr>')
    return ('<table class="price-table"><thead><tr><th>弾</th>'
            '<th style="text-align:right">期間はじめ</th>'
            '<th style="text-align:right">最新</th>'
            '<th style="text-align:right">変化率</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def _howto_placeholders(body: str, box: dict) -> str:
    rows = _box_ranking_rows(box)
    body = body.replace("{{BOX_RANKING}}", _box_ranking_table(box))
    by_slug = {r["slug"]: r for r in rows}
    for i, r in enumerate(rows[:5], 1):
        body = body.replace(f"{{{{TOP{i}_NAME}}}}", r["label"])
        body = body.replace(f"{{{{TOP{i}_PRICE}}}}", f"¥{r['price']:,}")
        body = body.replace(f"{{{{TOP{i}_MULT}}}}", f"約{r['mult']:.1f}倍")
    for slug, r in by_slug.items():
        key = slug.upper().replace("-", "")
        body = body.replace(f"{{{{{key}_PRICE}}}}", f"¥{r['price']:,}")
        body = body.replace(f"{{{{{key}_MULT}}}}", f"約{r['mult']:.1f}倍")
    body = body.replace("{{BOX_COUNT}}", str(len(rows)))

    if "{{PRICE_CHANGE" in body or "{{CHG_" in body:
        period, chg, agg = _price_change_rows()
        body = body.replace("{{PRICE_CHANGE_TABLE}}", _price_change_table(chg))
        body = body.replace("{{CHG_PERIOD}}", period)
        body = body.replace("{{CHG_DAYS}}", str(agg.get("days", 0)))
        body = body.replace("{{CHG_UP}}", str(agg.get("up", 0)))
        body = body.replace("{{CHG_DOWN}}", str(agg.get("down", 0)))
        body = body.replace("{{CHG_FLAT}}", str(agg.get("flat", 0)))
        body = body.replace("{{CHG_N}}", str(agg.get("n", 0)))
        body = body.replace("{{CHG_AVG}}", f"{agg.get('avg', 0):+.1f}%")
        if chg:
            body = body.replace("{{CHG_TOP_NAME}}", chg[0]["label"])
            body = body.replace("{{CHG_TOP_PCT}}", f"{chg[0]['pct']:+.1f}%")
            body = body.replace("{{CHG_BOTTOM_NAME}}", chg[-1]["label"])
            body = body.replace("{{CHG_BOTTOM_PCT}}", f"{chg[-1]['pct']:+.1f}%")
    return body


def _howto_subst(h: dict, box: dict) -> dict:
    """howto記事の全テキスト項目に実データのプレースホルダを差し込む。"""
    out = {}
    for k, v in h.items():
        if isinstance(v, str):
            out[k] = _howto_placeholders(v, box)
        elif k == "faq":
            out[k] = [{"q": _howto_placeholders(f["q"], box),
                       "a": _howto_placeholders(f["a"], box)} for f in v]
        else:
            out[k] = v
    return out


def _howto_nav_links(current_slug: str) -> str:
    return "".join(
        f'<a href="{h["slug"]}.html"'
        + (' class="current"' if h["slug"] == current_slug else "")
        + f'>{_esc(h["nav_label"])}</a>\n'
        for h in HOWTO_ARTICLES)


def _nav(current_slug: str, articles: list) -> str:
    links = ""
    for a in articles:
        cur = ' class="current"' if a["slug"] == current_slug else ""
        links += f'<a href="{a["slug"]}-atari-guide.html"{cur}>{_esc(a["nav_label"])}</a>\n'
    howto = _howto_nav_links(current_slug)
    howto_section = (f'<div class="article-nav-sub">📰 買取ガイド</div>\n{howto}'
                     if howto else "")
    return (f'<nav class="article-nav">\n'
            f'<div class="article-nav-title">ワンピ買取</div>\n'
            f'<a href="/onepiece">買取価格比較トップ</a>\n'
            f'<a href="weekly.html">📊 週間値動きランキング</a>\n'
            f'<a href="weekly/index.html">📚 週間値動き記事アーカイブ</a>\n'
            f'{howto_section}'
            f'<div class="article-nav-sub">📘 BOX掘り下げガイド</div>\n{links}</nav>')


def _card_rank_map(articles: list) -> tuple:
    """各弾のコミックパラレル最高額から弾別順位を作る(コミパラ非収録弾は除外)。"""
    import re
    vals = {}
    for a in articles:
        best = 0
        for _name, rarity, price in a.get("ranking", []):
            if "コミックパラレル" in rarity:
                best = max(best, int(re.sub(r"[^0-9]", "", price) or 0))
        if best:
            vals[a["slug"]] = best
    ranked = sorted(vals.items(), key=lambda x: -x[1])
    out, prev, rank = {}, None, 0
    for i, (slug, price) in enumerate(ranked, 1):
        if price != prev:
            rank, prev = i, price
        out[slug] = (rank, price)
    return out, len(ranked)


def _positioning_section(a: dict, articles: list, box: dict) -> str:
    """全弾の中での本弾の位置づけ(カード相場順位 vs BOX買取順位)を自動生成する。"""
    slug = a["slug"]
    card_ranks, card_n = _card_rank_map(articles)
    rows = _box_ranking_rows(box)
    box_rank = next((i for i, r in enumerate(rows, 1) if r["slug"] == slug), 0)
    box_n = len(rows)
    if not box_rank:
        return ""

    cr = card_ranks.get(slug)
    if cr:
        c_rank, c_price = cr
        card_line = (f'<tr><td>コミックパラレル最高額</td>'
                     f'<td class="price">¥{c_price:,}</td>'
                     f'<td class="price"><strong>{card_n}弾中 {c_rank}位</strong></td></tr>')
    else:
        card_line = ('<tr><td>コミックパラレル最高額</td><td class="price">—</td>'
                     '<td class="price">対象外(本弾はコミパラ非収録)</td></tr>')

    box_price = rows[box_rank - 1]["price"]
    box_mult = rows[box_rank - 1]["mult"]
    box_line = (f'<tr><td>BOX買取(当サイト実データ・最高値)</td>'
                f'<td class="price">¥{box_price:,}</td>'
                f'<td class="price"><strong>{box_n}弾中 {box_rank}位</strong></td></tr>')

    if cr:
        gap = box_rank - c_rank
        if abs(gap) <= 3:
            comment = ("カード相場とBOX買取の評価が<strong>おおむね一致</strong>している弾です。"
                       "トップレアの強さがそのままBOX需要につながっていると考えられます。")
        elif gap > 0:
            comment = ("トップレアの高さに対して、<strong>BOX買取は相対的に控えめ</strong>な弾です。"
                       "カードが高くてもBOXが連動しない主な要因は、未開封BOXの供給量(再販・開封の進み方)にあります。"
                       "カードを狙うのとBOXを持つのは別の判断になります。")
        else:
            comment = ("コミパラ最高額は上位ではないものの、<strong>BOX買取は相対的に高い</strong>弾です。"
                       "コミックパラレル以外の高額枠が開封需要を支えているか、"
                       "未開封BOXの流通量が少ないことが背景として考えられます。")
    else:
        comment = ("本弾はコミックパラレル枠を収録していないため(新レアリティを採用した弾や"
                   "スタートデッキが該当します)、カード相場のランキングは対象外です。"
                   "BOX買取の位置づけのみ参考にしてください。")

    return f"""
<h2>全弾で見た本弾の位置づけ</h2>
<p>ワンピースカードの全弾を横断して、本弾がどの位置にあるかを整理します。カード相場は当たりカードのコミックパラレル最高額、BOX買取は当サイトが最大9店舗から毎日自動取得している実データです。</p>
<table class="price-table">
<thead><tr><th>指標</th><th style="text-align:right">本弾の値</th><th style="text-align:right">全弾での順位</th></tr></thead>
<tbody>
{card_line}
{box_line}
</tbody>
</table>
<p>{comment}</p>
<p>全弾のコミックパラレル相場ランキングは <a href="comipara-ranking.html">歴代コミックパラレル相場ランキング全22弾</a>、BOX買取の全弾ランキングは <a href="kougaku-ranking.html">高額BOXランキング・絶版ガイド</a> でまとめています。なお本弾のBOX買取は<strong>定価比{box_mult:.1f}倍</strong>の水準です。</p>
"""


def _asof(a: dict) -> str:
    return CARD_ASOF_OVERRIDE.get(a["slug"], CARD_ASOF)


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
        "datePublished": "2026-07-14", "dateModified": CARD_ASOF_ISO,
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
    body += _positioning_section(a, articles, box)

    # 公式BOX/パック画像がある弾のみ hero 左に画像(無い弾はテキストheroのまま)
    _stats = (
        f'<div class="stat-label">看板当たり {_esc(a["hero_card"])} 買取相場({_asof(a)}時点)</div>'
        f'<div class="stat-big">{_esc(a["hero_big"])}</div>'
        f'<div class="stat-sub">{a["hero_sub"]} / '
        f'<a href="box/{slug}.html" style="color:#b91c1c;font-weight:700">{box_line}</a></div>')
    if (ROOT / "images" / "boxes" / f"{slug}.webp").exists():
        _img = (
            f'<picture><source srcset="/images/boxes/{slug}.webp" type="image/webp">'
            f'<img src="/images/boxes/{slug}.jpg" alt="{_esc(a["box_name"])} パッケージ画像" '
            'width="150" height="150" loading="eager" decoding="async" '
            'style="width:130px;height:auto;border-radius:8px;flex-shrink:0"></picture>')
        hero_html = (f'<div class="hero" style="display:flex;gap:18px;align-items:center">'
                     f'{_img}<div>{_stats}</div></div>')
    else:
        hero_html = f'<div class="hero">{_stats}</div>'

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
<div class="meta">公開: 2026年7月14日 / 相場更新: {_asof(a)} / {_esc(a['meta_line'])} / ワンピ買取チェッカー編集部</div>

{hero_html}

{body}

<a href="box/{slug}.html" class="cta">{_esc(a['box_name'])}の最新買取価格を最大9店舗で比較する &rarr;</a>

<div class="disclaimer">
<strong>ご注意:</strong> 本記事の当たりカード・収録種類・封入率は、複数の公開情報(カードショップの買取相場・大量開封報告等)と当サイトが自動収集した買取価格データに基づく参考情報です。封入率は公式発表ではなく推定値を含みます。買取相場は需給で日々変動し、本記事のカード金額は<strong>{_asof(a)}時点</strong>にカード相場メディア altema が掲載する<strong>カードラッシュの買取価格</strong>を基準にした目安です(1店舗の買取価格のため、他店や販売価格とは異なります)。BOX買取価格は当サイトが最大9店舗から自動取得した実データを基準にしています。売買・開封の判断はご自身の責任で行ってください。
</div>

<h2>関連BOX・記事もチェック</h2>
<ul>
<li><a href="box/{slug}.html">{_esc(a['box_name'])}</a> — 本商品の店舗別最新買取価格(毎日更新)</li>
<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全23種のBOX買取価格を最大9店舗で横断比較</li>
<li><a href="weekly.html">週間値動きランキング</a> — 全ワンピBOXの急上昇・急落ランキング(毎日更新)</li>
</ul>

<a href="box/{slug}.html" class="back">&larr; {_esc(a['short_name'])} 個別ページへ</a>
<a href="/onepiece" class="back">&larr; ワンピ買取比較トップ</a>
</article>
</div><!-- /content-layout -->

</div>

{AFFILIATE}

<div class="ft">
  <a href="/onepiece">ワンピ買取チェッカー</a> / <a href="/privacy.html">プライバシーポリシー</a>
</div>
</body>
</html>
"""


def _render_howto(h: dict, atari_articles: list, box: dict | None = None) -> str:
    if box:
        h = _howto_subst(h, box)
    slug = h["slug"]
    body_html = h["body"]
    url = f"{BASE}/onepiece/{slug}.html"

    blog_ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": h["title"], "description": h["meta_desc"],
        "datePublished": h.get("date", "2026-07-18"),
        "dateModified": h.get("date", "2026-07-18"),
        "image": f"{BASE}/ogp.jpg",
        "author": {"@type": "Organization", "name": "ワンピ買取チェッカー編集部", "url": f"{BASE}/onepiece"},
        "publisher": {"@type": "Organization", "name": "ワンピ買取チェッカー",
                      "logo": {"@type": "ImageObject", "url": f"{BASE}/ogp.png"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "articleSection": "買取ガイド", "inLanguage": "ja",
    }
    crumb_ld = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{BASE}/"},
            {"@type": "ListItem", "position": 2, "name": "ワンピ買取チェッカー", "item": f"{BASE}/onepiece"},
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

    hero_html = (f'<div class="hero">'
                 f'<div class="stat-label">{_esc(h["hero_label"])}</div>'
                 f'<div class="stat-big">{_esc(h["hero_big"])}</div>'
                 f'<div class="stat-sub">{h["hero_sub"]}</div></div>')

    faq_html = "".join(
        f'<h3>{_esc(f["q"])}</h3>\n<p>{f["a"]}</p>\n' for f in h["faq"])
    faq_section = f'<h2>よくある質問(FAQ)</h2>\n{faq_html}'

    disclaimer_html = h.get(
        "disclaimer",
        "本記事は、ワンピースカードの未開封BOXを売却する際の一般的な考え方・比較の手順をまとめた参考情報です。"
        "買取価格・相場は需給や各店の在庫状況により日々変動し、店舗ごとに査定基準(シュリンク・外箱状態の減額幅等)も異なります。"
        "掲載・紹介する金額はあくまで目安であり、特定の買取価格を保証するものではありません。"
        "BOX買取価格は当サイトが最大9店舗から自動取得した実データを基準にしていますが、"
        "実際の売却時は各店の公式ページで最終価格をご確認ください。売買の判断はご自身の責任で行ってください。")
    related_html = h.get(
        "related",
        '<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大9店舗で横断比較(毎日更新)</li>\n'
        '<li><a href="weekly.html">週間値動きランキング</a> — 直近7日間で値上がり・値下がりしたBOXを毎日自動更新</li>\n'
        '<li><a href="op-13-atari-guide.html">受け継がれる意志(OP-13) 当たりカードガイド</a> — レッドコミパラを擁する高額弾の詳細</li>\n'
        '<li><a href="op-15-atari-guide.html">神の島の冒険(OP-15) 当たりカードガイド</a> — エネル コミパラが看板の人気弾</li>')

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://h.accesstrade.net">
<meta name="description" content="{_esc(h['meta_desc'])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{_esc(h['og_title'])}">
<meta property="og:description" content="{_esc(h['og_desc'])}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/ogp.jpg">
<meta property="og:site_name" content="ワンピ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_esc(h['og_title'])}">
<meta name="twitter:description" content="{_esc(h['og_desc'])}">
<meta name="twitter:image" content="{BASE}/ogp.jpg">
<title>{_esc(h['title'])}｜ワンピ買取チェッカー</title>
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
<script type="application/ld+json">
{json.dumps(faq_ld, ensure_ascii=False, indent=0)}
</script>
{STYLE}
</head>
<body>
<a class="gswitch" href="/"><span class="ar">◀</span> ポケモンカードの買取比較はこちら</a>
<div class="header"><a href="/onepiece"><h1>ワンピ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="/">ホーム</a> &gt; <a href="/onepiece">ワンピ買取チェッカー</a> &gt; {_esc(h['crumb'])}</div>

<div class="content-layout">
{_nav(slug, atari_articles)}

<article>
<h1>{h['h1']}</h1>
<div class="meta">公開: {_esc(h.get('date_jp', '2026年7月18日'))} / {_esc(h['meta_line'])} / ワンピ買取チェッカー編集部</div>

{hero_html}

{body_html}

{faq_section}

<a href="/onepiece" class="cta">ワンピBOXの最新買取価格を最大9店舗で比較する &rarr;</a>

<div class="disclaimer">
<strong>ご注意:</strong> {disclaimer_html}
</div>

<h2>関連ページもチェック</h2>
<ul>
{related_html}
</ul>

<a href="/onepiece" class="back">&larr; ワンピ買取比較トップ</a>
</article>
</div><!-- /content-layout -->

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
    for h in HOWTO_ARTICLES:
        html = _render_howto(h, ARTICLES, box)
        (ART_DIR / f"{h['slug']}.html").write_text(html, encoding="utf-8")
        print(f"wrote onepiece/{h['slug']}.html")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build()
