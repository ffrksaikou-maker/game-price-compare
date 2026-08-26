"""template.html -> dragonball-template.html 変換スクリプト(冪等)。

ポケカ版テンプレを流用し、ブランディング/カテゴリ(fb/sb/st/dv)/配色/店舗列/
切替バナー をドラゴンボール用に置換する。各構造置換は必ず1回以上ヒットすることを assert。

ポケカ・ワンピ・ベイとの差分:
  - 買取店は4店のみ(森森/ルデヤ/ホムラ/ラントゥ)
  - 記事・個別商品ページは作らないので商品名はリンクにしない
  - 発売日列を商品名の直後に追加(ベイ版と同じ。再販判断に使うため)
"""
import re
from pathlib import Path

from . import switch_banner as sb

ROOT = Path(__file__).resolve().parent.parent

TITLE = "ドラゴンボール買取チェッカー｜フュージョンワールドBOXの買取価格を4店舗比較"
DESC = ("ドラゴンボールカード(フュージョンワールド・スーパーダイバーズ)未開封BOXの買取価格を"
        "森森・ルデヤ・ホムラ・ラントゥの4店舗から自動収集して比較。"
        "FB-01〜の各弾やMANGA BOOSTER・STORY BOOSTERの最高買取店が一目でわかります。登録不要・無料。")
DESC_SHORT = ("ドラゴンボールカード未開封BOXの買取価格を4店舗で自動比較。"
              "フュージョンワールド各弾の最高買取店が一目でわかります。")


def rep(text, old, new, *, count=None):
    n = text.count(old)
    assert n > 0, f"NOT FOUND: {old[:70]!r}"
    if count is not None:
        assert n == count, f"expected {count} of {old[:40]!r}, got {n}"
    return text.replace(old, new)


def set_content(text, marker, new):
    """<meta ...> の content 属性を差し替える(元の文言に依存しない)。"""
    i = text.index(marker)
    j = text.index('content="', i) + len('content="')
    k = text.index('"', j)
    return text[:j] + new + text[k:]


def replace_section(text, start_marker, end_marker, new):
    i = text.index(start_marker)
    j = text.index(end_marker, i) + len(end_marker)
    return text[:i] + new + text[j:]


src = sb.strip((ROOT / "template.html").read_text(encoding="utf-8"))
t = src

# 1) メタ情報(文言が更新されても壊れないよう content を属性位置で差し替える) --
t = set_content(t, '<meta name="description"', DESC)
t = set_content(t, '<meta property="og:title"', TITLE)
t = set_content(t, '<meta property="og:description"', DESC_SHORT)
t = set_content(t, '<meta property="og:site_name"', "ドラゴンボール買取チェッカー")
t = set_content(t, '<meta name="twitter:title"', TITLE)
t = set_content(t, '<meta name="twitter:description"', DESC_SHORT)
t = re.sub(r"<title>[^<]*</title>", f"<title>{TITLE}</title>", t, count=1)

t = rep(t, '<meta property="og:url" content="https://pokeca-box-hikaku.com/">',
        '<meta property="og:url" content="https://pokeca-box-hikaku.com/dragonball">')
t = rep(t, '<link rel="canonical" href="https://pokeca-box-hikaku.com/">',
        '<link rel="canonical" href="https://pokeca-box-hikaku.com/dragonball">')

# 2) カテゴリ配色 -----------------------------------------------------------
t = rep(t, "  --special: #e3f2fd;\n}",
        "  --special: #e3f2fd;\n  --fb: #fff8e1;\n  --sb: #ffebee;\n  --st: #e8f5e9;\n  --dv: #ede7f6;\n}")
t = rep(t, 'tr.cat-ss td{background:#fce4ec}',
        'tr.cat-ss td{background:#fce4ec}tr.cat-fb td{background:var(--fb)}tr.cat-sb td{background:var(--sb)}tr.cat-st td{background:var(--st)}tr.cat-dv td{background:var(--dv)}',
        count=1)
t = rep(t, 'tr.cat-ss:hover td{background:#f8bbd0 !important}',
        'tr.cat-ss:hover td{background:#f8bbd0 !important}tr.cat-fb:hover td{background:#ffecb3 !important}tr.cat-sb:hover td{background:#ffcdd2 !important}tr.cat-st:hover td{background:#c8e6c9 !important}tr.cat-dv:hover td{background:#d1c4e9 !important}',
        count=1)
t = rep(t, '  tr.cat-ss td.pn{background:#fce4ec}',
        '  tr.cat-ss td.pn{background:#fce4ec}\n  tr.cat-fb td.pn{background:var(--fb)}\n  tr.cat-sb td.pn{background:var(--sb)}\n  tr.cat-st td.pn{background:var(--st)}\n  tr.cat-dv td.pn{background:var(--dv)}',
        count=1)
t = rep(t, '  tr.cat-ss:hover td.pn{background:#f8bbd0 !important}',
        '  tr.cat-ss:hover td.pn{background:#f8bbd0 !important}\n  tr.cat-fb:hover td.pn{background:#ffecb3 !important}\n  tr.cat-sb:hover td.pn{background:#ffcdd2 !important}\n  tr.cat-st:hover td.pn{background:#c8e6c9 !important}\n  tr.cat-dv:hover td.pn{background:#d1c4e9 !important}',
        count=1)

# 3) モバイルで商品名(弾名+弾番号)が見切れるので折り返す --------------------
t = rep(t,
        '  td.pn{position:sticky;left:0;z-index:10;min-width:140px;max-width:180px;overflow:hidden;text-overflow:ellipsis;font-size:11px;padding-left:8px}',
        '  td.pn{position:sticky;left:0;z-index:10;min-width:150px;max-width:210px;white-space:normal;word-break:break-word;line-height:1.3;font-size:11px;padding-left:8px}\n'
        '  th.dcol,td.dcol{display:none}',
        count=1)
t = rep(t,
        '  td.pn{min-width:120px;max-width:150px;font-size:10px}',
        '  td.pn{min-width:130px;max-width:170px;font-size:10px;white-space:normal;word-break:break-word;line-height:1.3}',
        count=1)

# 4) 絞り込みボタン / 凡例 ---------------------------------------------------
t = rep(t,
        '''    <button class="fb" data-f="cat" data-v="all">ALL</button>
    <button class="fb" data-f="cat" data-v="mega">MEGA</button>
    <button class="fb" data-f="cat" data-v="sv">SV</button>

    <button class="fb" data-f="cat" data-v="special">スペシャルBOX</button>
    <button class="fb" data-f="cat" data-v="ss">S&amp;S</button>''',
        '''    <button class="fb" data-f="cat" data-v="all">ALL</button>
    <button class="fb" data-f="cat" data-v="fb">ブースター</button>
    <button class="fb" data-f="cat" data-v="sb">MANGA</button>
    <button class="fb" data-f="cat" data-v="st">STORY</button>
    <button class="fb" data-f="cat" data-v="dv">ダイバーズ</button>''')

t = rep(t,
        '''  <div class="li"><span class="ls" style="background:var(--mega)"></span>MEGA</div>
  <div class="li"><span class="ls" style="background:var(--sv)"></span>SV</div>
  <div class="li"><span class="ls" style="background:var(--special)"></span>スペシャルBOX</div>
  <div class="li"><span class="ls" style="background:#fce4ec"></span>S&amp;S</div>''',
        '''  <div class="li"><span class="ls" style="background:var(--fb)"></span>ブースターパック</div>
  <div class="li"><span class="ls" style="background:var(--sb)"></span>MANGA BOOSTER</div>
  <div class="li"><span class="ls" style="background:var(--st)"></span>STORY BOOSTER</div>
  <div class="li"><span class="ls" style="background:var(--dv)"></span>スーパーダイバーズ</div>''')

# 5) 店舗フィルタ(9店 -> 4店) ------------------------------------------------
t = rep(t,
        '''    <button class="fb st active" data-s="morimori">森森</button>
    <button class="fb st active" data-s="homura">ホムラ</button>
    <button class="fb st active" data-s="icchome">一丁目</button>
    <button class="fb st active" data-s="runto">ラントゥ</button>
    <button class="fb st active" data-s="collect_tendo">コレクト</button>
    <button class="fb st active" data-s="shinsoku">シンソク</button>
    <button class="fb st active" data-s="oku">オク</button>
    <button class="fb st active" data-s="rudeya">ルデヤ</button>
    <button class="fb st active" data-s="kaikyo">海峡</button>''',
        '''    <button class="fb st active" data-s="homura">ホムラ</button>
    <button class="fb st active" data-s="rudeya">ルデヤ</button>
    <button class="fb st active" data-s="runto">ラントゥ</button>
    <button class="fb st active" data-s="morimori">森森</button>''')

# 6) テーブルヘッダ(店舗列を4店に) -------------------------------------------
_TH_OLD_START = '''        <th class="sc" data-s="morimori"><a href="https://www.morimori-kaitori.jp/category/0112"'''
assert _TH_OLD_START in t
_th_begin = t.index(_TH_OLD_START)
_th_end = t.index("      </tr>", _th_begin)
t = t[:_th_begin] + '''        <th class="sc" data-s="homura"><a href="https://kaitori-homura.com/products?q%5Bproduct_sub_category_id_eq%5D=171" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'homura',shop_name:'ホムラ'})">ホムラ</a></th>
        <th class="sc" data-s="rudeya"><a href="https://kaitori-rudeya.com/category/detail/225" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'rudeya',shop_name:'ルデヤ'})">ルデヤ</a></th>
        <th class="sc" data-s="runto"><a href="https://runto666.com/product-category/dg/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'runto',shop_name:'ラントゥ'})">ラントゥ</a></th>
        <th class="sc" data-s="morimori"><a href="https://www.morimori-kaitori.jp/category/2404" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'morimori',shop_name:'森森'})">森森</a></th>
''' + t[_th_end:]

# 発売日を商品名の直後に足す(再販が狙えるかの判断材料として需要が高い)
t = rep(t, '        <th style="min-width:200px">商品名</th>\n',
        '        <th style="min-width:200px">商品名</th>\n'
        '        <th style="min-width:84px">発売日</th>\n',
        count=1)

# 7) フッターの出典(4店のみ) -------------------------------------------------
_FT_OLD = '''  <a href="https://www.morimori-kaitori.jp/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'morimori',shop_name:'森森'})">森森買取</a> /'''
assert _FT_OLD in t
_ft_begin = t.index(_FT_OLD)
_ft_end = t.index("<br>\n  <a href=\"privacy.html\"", _ft_begin)
t = t[:_ft_begin] + '''  <a href="https://www.morimori-kaitori.jp/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'morimori',shop_name:'森森'})">森森買取</a> /
  <a href="https://kaitori-rudeya.com/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'rudeya',shop_name:'ルデヤ'})">買取ルデヤ</a> /
  <a href="https://kaitori-homura.com/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'homura',shop_name:'ホムラ'})">買取ホムラ</a> /
  <a href="https://runto666.com/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'runto',shop_name:'ラントゥ'})">ラントゥ買取</a>''' + t[_ft_end:]

t = rep(t, '  ※ 各店舗公式サイトより取得した未開封シュリンク付BOXの新品買取価格<br>\n',
        '  ※ 各店舗公式サイトより取得した未開封BOXの新品買取価格<br>\n',
        count=1)

# 店舗の並びは固定にする。ポケカは「最高買取になった回数の多い順」で動的に
# 並べ替えるが、DBは4店しかなく、カテゴリを切り替えるたびに列が入れ替わると
# 読みにくい。掲載数の多いホムラを左、最も少ない森森を右に固定する。
t = replace_section(
    t, "function computeShopOrder(cat) {", "function computeS_SS() {",
    """function computeShopOrder(cat) {
  return [...S];
}
function computeS_SS() {""")

# 8) JS: 店舗配列 / カテゴリラベル / 既定表示 --------------------------------
t = rep(t, 'const S=["morimori","homura","icchome","runto","collect_tendo","shinsoku","oku","rudeya","kaikyo"];',
        'const S=["homura","rudeya","runto","morimori"];')
t = rep(t, 'let S_SS = ["homura","runto","morimori","icchome","oku","rudeya","kaikyo","collect_tendo","shinsoku"];',
        'let S_SS = ["homura","rudeya","runto","morimori"];')
t = rep(t, 'const CL={"mega":"MEGA","sv":"SV","special":"スペシャルBOX","ss":"S&S ソード&シールド"};',
        'const CL={"fb":"ブースターパック (FB)","sb":"MANGA BOOSTER (SB)","st":"STORY BOOSTER (ST)","dv":"スーパーダイバーズ"};')
t = rep(t, 'cc===""?P.filter(x=>x.c!=="ss")', 'cc===""?P.slice()')
t = rep(t, 'const INV_KEY="pokeca_inventory";', 'const INV_KEY="dragonball_inventory";')

# 9) 商品名はリンクにしない(個別ページを作らないため) ------------------------
t = rep(t,
        '''    const aName=document.createElement("a");
    aName.href="box/"+x.s+".html";
    aName.textContent=x.n;
    aName.style.cssText="color:inherit;text-decoration:none;border-bottom:1px dashed #c4b5fd";
    tdN.appendChild(aName);''',
        '''    tdN.textContent=x.n;''')

# 発売日セル(商品名の直後。モバイルでも隠さない)
t = rep(t,
        '''    tdN.textContent=x.n;
    tr.appendChild(tdN);''',
        '''    tdN.textContent=x.n;
    tr.appendChild(tdN);

    // Release date
    const tdRel=document.createElement("td");
    tdRel.className="rp";
    tdRel.style.cssText="font-size:11px;color:#6b7280;white-space:nowrap";
    tdRel.textContent=x.d?x.d.replace(/-/g,"/"):"-";
    tr.appendChild(tdRel);''',
        count=1)

# 10) 差益列は狭い画面では隠す(店舗列を優先して見せる) -----------------------
t = rep(t,
        '''    tr.appendChild(tdD);

    // Shop prices''',
        '''    tr.appendChild(tdD);

    tdD.classList.add("dcol");

    // Shop prices''',
        count=1)
t = rep(t, '        <th style="min-width:50px">差益</th>\n',
        '        <th class="dcol" style="min-width:50px">差益</th>\n', count=1)

# カテゴリ見出し行のcolspan (商品名/発売日/定価/最高買取/差益 の5列)
t = rep(t, 'let cs=4+SO.filter(s=>vs.has(s)).length;',
        'let cs=5+SO.filter(s=>vs.has(s)).length;', count=1)

# 11) 記事枠・ランキング枠は使わない(記事を作らないため空にする) --------------
t = rep(t, "<!-- {{BLOG_LINKS}} -->\n\n", "")
t = rep(t, "<!-- {{RANKING_SUMMARY}} -->\n\n", "")

# 12) サイト説明セクション(ポケカ固有の機能紹介ごと差し替える) ---------------
t = replace_section(t, '<section class="site-intro"', "</section>", '''<section class="site-intro" aria-label="サイトについて">
  <details class="si-card">
    <summary class="si-summary">📖 ドラゴンボール買取チェッカーについて(タップで開く)</summary>
    <div class="si-body">
      <p class="si-lead">ドラゴンボールカード(フュージョンワールド・スーパーダイバーズ)の未開封BOX買取価格を、毎日3回(11:00/15:00/18:00 JST)4店舗から自動収集して比較できる個人運営の情報サイトです。</p>
      <div class="si-grid">
        <div class="si-item"><h3>📊 4店舗を一括比較</h3><p>買取ホムラ・買取ルデヤ・ラントゥ買取・森森買取の公式買取表を自動収集。最高値は黄色ハイライトで明示します。</p></div>
        <div class="si-item"><h3>🎴 対象はBOX単位</h3><p>ブースターパック(FB-01〜)、MANGA BOOSTER(SB)、STORY BOOSTER(ST)、スーパーダイバーズのアドバンスパックを掲載しています。シングルカードは扱っていません。</p></div>
        <div class="si-item"><h3>💰 資産モード</h3><p>右上「資産モード」で保有個数を入力すると合計資産額をリアルタイム計算します。</p></div>
      </div>
      <div class="si-howto"><strong>使い方</strong>: 上部のシリーズ(ブースター/MANGA/STORY/ダイバーズ)・買取屋ボタンで絞り込み → 最高買取欄で一番高い店を確認 → 店舗名リンクから各店の公式ページへ移動できます。</div>
      <div class="si-meta">
        <a href="about.html">運営者情報</a> ・ <a href="privacy.html">プライバシーポリシー</a> ・ <a href="contact.html">お問い合わせ</a>
      </div>
    </div>
  </details>
</section>''')

# 13) ブランディング文言(残りの表記ゆれ) -------------------------------------
t = t.replace("ポケモンカードゲーム", "ドラゴンボールカード")
t = t.replace("ポケモンカード", "ドラゴンボールカード")
t = t.replace("ポケカ買取チェッカー", "ドラゴンボール買取チェッカー")
t = t.replace("ポケカ", "ドラゴンボール")

# 14) 買取ガイド記事へのリンク枠(中身は generator が {{ARTICLE_LINKS}} に差し込む)
_article_block = (
    '<div class="blog-links" id="blogLinks">{{ARTICLE_LINKS}}</div>\n'
    '<section class="site-intro"'
)
t = t.replace('<section class="site-intro"', _article_block, 1)

# 15) 切替バナー -------------------------------------------------------------
t = sb.apply(t, "dragonball")

out = ROOT / "dragonball-template.html"
out.write_text(t, encoding="utf-8")
print(f"wrote {out} ({len(t)} bytes)")

# ===== 既存3ページのテンプレにもDBへの導線を入れて4択にする(冪等) =====
for filename, page in [("template.html", "pokemon"),
                       ("onepiece-template.html", "onepiece"),
                       ("beyblade-template.html", "beyblade")]:
    path = ROOT / filename
    if not path.exists():
        print(f"skip {filename} (not found)")
        continue
    text = sb.strip(path.read_text(encoding="utf-8"))
    path.write_text(sb.apply(text, page), encoding="utf-8")
    print(f"patched {filename} with 4-way switch banner")
