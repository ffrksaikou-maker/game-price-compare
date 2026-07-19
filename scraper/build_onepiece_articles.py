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
        "title": "ワンピBOX買取比較ガイド｜最大11店舗の実データで高く売るコツと店舗の選び方",
        "h1": "ワンピBOX買取比較ガイド｜未開封BOXを最大11店舗の実データで高く売るコツと店舗の選び方",
        "meta_desc": "ワンピースカードの未開封BOXを高く売るための店舗比較・売り方ガイド。シュリンクや外箱状態などの査定ポイント、最大11店舗を毎日自動比較する当サイトの使い方、高く売る5つのコツ、今買取が高い傾向のBOXまで実データ視点で解説。",
        "og_title": "ワンピBOX買取比較ガイド｜最大11店舗の実データで高く売るコツ",
        "og_desc": "ワンピースカードの未開封BOXを高く売る店舗比較・売り方ガイド。シュリンク・外箱の査定ポイント、最大11店舗比較の使い方、高く売る5つのコツを実データ視点で解説。",
        "meta_line": "ワンピBOX買取の基礎知識・店舗比較・高く売るコツ",
        "hero_label": "ワンピBOX買取比較ガイド",
        "hero_big": "最大11店舗を毎日自動比較",
        "hero_sub": "シュリンク維持・複数店比較・売却タイミングの見極めで、ワンピースカードの未開封BOXをできるだけ高く売るための実践ガイド。相場は当サイトの実データで毎日チェックできます。",
        "body": """<p>ワンピースカードゲームの未開封BOXは、弾(タイトル)によって買取価格が大きく異なり、<strong>同じ弾でも店舗ごとに数百円〜数千円の差</strong>が出ることが珍しくありません。せっかく売るなら、少しでも高い店で・良いタイミングで手放したいところです。本記事では、<strong>ワンピBOXをできるだけ高く売るための店舗比較・売り方のコツ</strong>を、当サイトが最大11店舗から毎日自動収集している買取価格データの視点で整理します。「どこで売れば一番高いのか」「今売るべきか」を判断する材料としてご活用ください。最新の店舗別買取価格は <a href="/onepiece">ワンピBOX買取価格比較トップ</a> で毎日更新しています。</p>

<h2>ワンピBOX買取の基礎｜査定で見られるポイント</h2>
<p>未開封BOXの買取価格は「弾ごとの相場」だけでなく、<strong>個々のBOXの状態</strong>によっても上下します。まずは査定でチェックされる基本ポイントを押さえましょう。</p>
<h3>シュリンク(外装フィルム)の有無</h3>
<p>最も重要なのが<strong>シュリンク(BOX全体を包む透明フィルム)</strong>の有無です。シュリンク付きは「未開封・すり替えなしの証明」として扱われ、多くの店で買取価格が最も高くなります。シュリンクを剥がしてしまうと、たとえパックを開けていなくても「シュリンクなし」区分となり、査定額が下がるのが一般的です。売却を視野に入れているなら、シュリンクは剥がさないでおくのが鉄則です。</p>
<h3>外箱(BOX)の状態</h3>
<p>外箱の<strong>潰れ・角のつぶれ・スレ・日焼け</strong>なども査定に影響します。特に高額弾ほど状態の影響が出やすいため、保管時は重い物を上に置かない・直射日光を避けるなどの配慮が有効です。輸送中の潰れを防ぐため、発送買取では緩衝材でしっかり梱包しましょう。</p>
<h3>付属品・封入形態</h3>
<p>カートン(BOXが複数入った輸送箱)単位で売る場合は<strong>カートン未開封</strong>がより高評価になることがあります。また、店舗によっては「初回生産版」「再販版」などの区別や、同梱プロモの有無を見る場合もあります。基本的には<strong>買った状態のまま手を加えず保管する</strong>のが最も無難です。</p>

<h2>当サイトの強み｜最大11店舗を毎日自動比較</h2>
<p>当サイト「ワンピ買取チェッカー」は、ワンピースカードのBOX買取に対応した<strong>最大11店舗</strong>の買取価格を毎日自動で収集し、弾ごとに横断比較できるようにしています。1店舗ずつ公式サイトを見て回る必要がなく、<strong>「今どの店が一番高いか」を一目で確認</strong>できるのが最大の強みです。</p>
<ul>
<li><strong>毎日自動更新</strong>: 各店の買取ページから最新価格を自動取得し、日々の値動きを反映します。</li>
<li><strong>弾別に横断比較</strong>: OP-01〜最新弾・EB・PRB・スタートデッキまで、弾ごとに全店の価格を並べて比較できます。</li>
<li><strong>値動きも追える</strong>: <a href="weekly.html">週間値動きランキング</a>で、直近7日間で値上がり・値下がりしたBOXを毎日チェックできます。</li>
</ul>
<p>相場は日々変動するため、売る直前に最新の比較データを確認するのが失敗しないコツです。具体的な金額は断定せず、<strong>当サイトの最大11店舗比較の実データで最新値を確認</strong>してから判断してください。</p>

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
<p>ワンピースカードの中でも、特に高額で取引されやすい傾向のある弾を紹介します。金額は需給で日々変動するため、必ず<strong>当サイトの最大11店舗比較の実データで最新値を確認</strong>してください(下記は各弾の看板カードや傾向であり、BOX買取価格の断定ではありません)。</p>
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
             "a": "弾やタイミングによって最高値の店舗は変わります。当サイトはワンピBOX買取に対応した最大11店舗の価格を毎日自動比較しているため、<a href=\"/onepiece\">比較トップ</a>で売りたい弾の最新価格を並べて、その時点で最も高い店を選ぶのが確実です。"},
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
{_mobile_nav(slug, articles)}

</div>

{AFFILIATE}

<div class="ft">
  <a href="/onepiece">ワンピ買取チェッカー</a> / <a href="/privacy.html">プライバシーポリシー</a>
</div>
</body>
</html>
"""


def _render_howto(h: dict, atari_articles: list) -> str:
    slug = h["slug"]
    url = f"{BASE}/onepiece/{slug}.html"

    blog_ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": h["title"], "description": h["meta_desc"],
        "datePublished": "2026-07-18", "dateModified": "2026-07-18",
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
<div class="meta">公開: 2026年7月18日 / {_esc(h['meta_line'])} / ワンピ買取チェッカー編集部</div>

{hero_html}

{h['body']}

{faq_section}

<a href="/onepiece" class="cta">ワンピBOXの最新買取価格を最大11店舗で比較する &rarr;</a>

<div class="disclaimer">
<strong>ご注意:</strong> 本記事は、ワンピースカードの未開封BOXを売却する際の一般的な考え方・比較の手順をまとめた参考情報です。買取価格・相場は需給や各店の在庫状況により日々変動し、店舗ごとに査定基準(シュリンク・外箱状態の減額幅等)も異なります。掲載・紹介する金額はあくまで目安であり、特定の買取価格を保証するものではありません。BOX買取価格は当サイトが最大11店舗から自動取得した実データを基準にしていますが、実際の売却時は各店の公式ページで最終価格をご確認ください。売買の判断はご自身の責任で行ってください。
</div>

<h2>関連ページもチェック</h2>
<ul>
<li><a href="/onepiece">ワンピBOX買取価格比較トップ</a> — 全弾のBOX買取価格を最大11店舗で横断比較(毎日更新)</li>
<li><a href="weekly.html">週間値動きランキング</a> — 直近7日間で値上がり・値下がりしたBOXを毎日自動更新</li>
<li><a href="op-13-atari-guide.html">受け継がれる意志(OP-13) 当たりカードガイド</a> — レッドコミパラを擁する高額弾の詳細</li>
<li><a href="op-15-atari-guide.html">神の島の冒険(OP-15) 当たりカードガイド</a> — エネル コミパラが看板の人気弾</li>
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
        html = _render_howto(h, ARTICLES)
        (ART_DIR / f"{h['slug']}.html").write_text(html, encoding="utf-8")
        print(f"wrote onepiece/{h['slug']}.html")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build()
