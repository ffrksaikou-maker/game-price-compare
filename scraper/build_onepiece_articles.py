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


# ===== ハウツー記事(onepiece/{slug}.html・atari接尾辞なし) =====
# 弾別 atari-guide とは別枠の「買取ガイド」記事。body は .format() せず直接埋め込む
# ため、リテラルの波括弧を自由に使ってよい。faq から可視FAQ+FAQPage JSON-LDを生成。
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
        "body": """<p>ワンピースカードゲームの未開封BOXは、弾によって買取価格に<strong>数倍の開き</strong>があります。定価¥5,280前後の同じブースターパックでも、1万円台で落ち着くものから<strong>6万円を超える</strong>ものまで存在するのが実情です。本記事では、当サイトが最大9店舗から毎日自動収集している買取データをもとに、<strong>全{{BOX_COUNT}}弾を最高買取価格の高い順にランキング</strong>し、あわせて「ワンピカードに絶版はあるのか」「2026年4月に導入されたブロックアイコン制度はBOX相場にどう影響するのか」を整理します。</p>

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


def _mobile_nav(current_slug: str, articles: list) -> str:
    links = "".join(
        f'<a href="{a["slug"]}-atari-guide.html">{_esc(a["nav_label"])}</a>\n'
        for a in articles)
    howto = _howto_nav_links(current_slug)
    howto_section = (f'<div class="mfn-section"><div class="mfn-section-title">📰 買取ガイド</div>\n'
                     f'{howto}</div>\n' if howto else "")
    return (f'<nav class="mobile-footer-nav">\n<div class="mfn-title">📚 他のページを見る</div>\n'
            f'{howto_section}'
            f'<div class="mfn-section"><div class="mfn-section-title">📘 BOX掘り下げガイド</div>\n{links}</div>\n'
            f'<div class="mfn-section"><div class="mfn-section-title">📰 ワンピ買取</div>\n'
            f'<a href="/onepiece">買取価格比較トップ</a>\n<a href="weekly.html">📊 週間値動きランキング</a>\n'
            f'<a href="weekly/index.html">📚 週間値動き記事アーカイブ</a>\n</div>\n</nav>')


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

    # 公式BOX/パック画像がある弾のみ hero 左に画像(無い弾はテキストheroのまま)
    _stats = (
        f'<div class="stat-label">看板当たり {_esc(a["hero_card"])} 買取相場(2026年7月時点)</div>'
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
<div class="meta">公開: 2026年7月14日 / {_esc(a['meta_line'])} / ワンピ買取チェッカー編集部</div>

{hero_html}

{body}

<a href="box/{slug}.html" class="cta">{_esc(a['box_name'])}の最新買取価格を最大9店舗で比較する &rarr;</a>

<div class="disclaimer">
<strong>ご注意:</strong> 本記事の当たりカード・収録種類・封入率は、複数の公開情報(カードショップの買取相場・大量開封報告等)と当サイトが自動収集した買取価格データに基づく参考情報です。封入率は公式発表ではなく推定値を含みます。買取相場は需給で日々変動し、本記事のカード金額は2026年7月時点の目安です。BOX買取価格は当サイトが最大9店舗から自動取得した実データを基準にしています。売買・開封の判断はご自身の責任で行ってください。
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
{_mobile_nav(slug, articles)}

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
{_mobile_nav(slug, atari_articles)}

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
