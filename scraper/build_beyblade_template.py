"""template.html -> beyblade-template.html 変換スクリプト(冪等)。

ポケカ版テンプレを流用し、ブランディング/カテゴリ(bx/ux/cx/limited)/配色/店舗列/
切替バナー をベイブレード用に置換する。各構造置換は必ず1回以上ヒットすることを assert。

ポケカ・ワンピとの差分:
  - 買取店は4店のみ(森森/ルデヤ/ホムラ/一丁目)
  - 「フリマ相場」「フリマ差」列を追加(メルカリ売却済みの中央値。買取より高いことが多い)
  - 記事・個別商品ページは作らないので商品名はリンクにしない
"""
import re
from pathlib import Path

from . import switch_banner as sb

ROOT = Path(__file__).resolve().parent.parent

TITLE = "ベイブレード買取チェッカー｜ベイブレードXの買取価格を4店舗+メルカリ相場で比較"
DESC = ("ベイブレードX 44商品の買取価格を森森・ルデヤ・ホムラ・一丁目の4店舗から自動収集して比較。"
        "メルカリの売却相場も並べて表示するので、買取とフリマどちらが高いか一目でわかります。登録不要・無料。")
DESC_SHORT = ("ベイブレードXの買取価格を4店舗で比較。メルカリ売却相場との差も表示。"
              "買取とフリマどちらが高いか一目でわかります。")


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
t = set_content(t, '<meta property="og:site_name"', "ベイブレード買取チェッカー")
t = set_content(t, '<meta name="twitter:title"', TITLE)
t = set_content(t, '<meta name="twitter:description"', DESC_SHORT)
t = re.sub(r"<title>[^<]*</title>", f"<title>{TITLE}</title>", t, count=1)

t = rep(t, '<meta property="og:url" content="https://pokeca-box-hikaku.com/">',
        '<meta property="og:url" content="https://pokeca-box-hikaku.com/beyblade">')
t = rep(t, '<link rel="canonical" href="https://pokeca-box-hikaku.com/">',
        '<link rel="canonical" href="https://pokeca-box-hikaku.com/beyblade">')

# 2) カテゴリ配色 -----------------------------------------------------------
t = rep(t, "  --special: #e3f2fd;\n}",
        "  --special: #e3f2fd;\n  --bx: #e3f2fd;\n  --ux: #ede7f6;\n  --cx: #e8f5e9;\n  --limited: #fff3e0;\n}")
t = rep(t, 'tr.cat-ss td{background:#fce4ec}',
        'tr.cat-ss td{background:#fce4ec}tr.cat-bx td{background:var(--bx)}tr.cat-ux td{background:var(--ux)}tr.cat-cx td{background:var(--cx)}tr.cat-limited td{background:var(--limited)}',
        count=1)
t = rep(t, 'tr.cat-ss:hover td{background:#f8bbd0 !important}',
        'tr.cat-ss:hover td{background:#f8bbd0 !important}tr.cat-bx:hover td{background:#bbdefb !important}tr.cat-ux:hover td{background:#d1c4e9 !important}tr.cat-cx:hover td{background:#c8e6c9 !important}tr.cat-limited:hover td{background:#ffe0b2 !important}',
        count=1)
t = rep(t, '  tr.cat-ss td.pn{background:#fce4ec}',
        '  tr.cat-ss td.pn{background:#fce4ec}\n  tr.cat-bx td.pn{background:var(--bx)}\n  tr.cat-ux td.pn{background:var(--ux)}\n  tr.cat-cx td.pn{background:var(--cx)}\n  tr.cat-limited td.pn{background:var(--limited)}',
        count=1)
t = rep(t, '  tr.cat-ss:hover td.pn{background:#f8bbd0 !important}',
        '  tr.cat-ss:hover td.pn{background:#f8bbd0 !important}\n  tr.cat-bx:hover td.pn{background:#bbdefb !important}\n  tr.cat-ux:hover td.pn{background:#d1c4e9 !important}\n  tr.cat-cx:hover td.pn{background:#c8e6c9 !important}\n  tr.cat-limited:hover td.pn{background:#ffe0b2 !important}',
        count=1)

# 3) モバイルで商品名(型番+長い商品名)が見切れるので折り返す ----------------
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
    <button class="fb" data-f="cat" data-v="ux">UX</button>
    <button class="fb" data-f="cat" data-v="cx">CX</button>
    <button class="fb" data-f="cat" data-v="bx">BX</button>
    <button class="fb" data-f="cat" data-v="limited">限定品</button>''')

t = rep(t,
        '''  <div class="li"><span class="ls" style="background:var(--mega)"></span>MEGA</div>
  <div class="li"><span class="ls" style="background:var(--sv)"></span>SV</div>
  <div class="li"><span class="ls" style="background:var(--special)"></span>スペシャルBOX</div>
  <div class="li"><span class="ls" style="background:#fce4ec"></span>S&amp;S</div>''',
        '''  <div class="li"><span class="ls" style="background:var(--ux)"></span>UX</div>
  <div class="li"><span class="ls" style="background:var(--cx)"></span>CX</div>
  <div class="li"><span class="ls" style="background:var(--bx)"></span>BX</div>
  <div class="li"><span class="ls" style="background:var(--limited)"></span>限定品</div>''')

# 5) 店舗フィルタ(10店 -> 4店) ----------------------------------------------
t = rep(t,
        '''    <button class="fb st active" data-s="morimori">森森</button>
    <button class="fb st active" data-s="homura">ホムラ</button>
    <button class="fb st active" data-s="icchome">一丁目</button>
    <button class="fb st active" data-s="runto">ラントゥ</button>
    <button class="fb st active" data-s="collect_tendo">コレクト</button>
    <button class="fb st active" data-s="shinsoku">シンソク</button>
    <button class="fb st active" data-s="oku">オク</button>
    <button class="fb st active" data-s="sommelier">ソムリエ</button>
    <button class="fb st active" data-s="rudeya">ルデヤ</button>
    <button class="fb st active" data-s="kaikyo">海峡</button>''',
        '''    <button class="fb st active" data-s="icchome">一丁目</button>
    <button class="fb st active" data-s="morimori">森森</button>
    <button class="fb st active" data-s="rudeya">ルデヤ</button>
    <button class="fb st active" data-s="homura">ホムラ</button>''')

# 6) テーブルヘッダ(店舗列を4店に + フリマ2列を追加) -------------------------
_TH_OLD_START = '''        <th class="sc" data-s="morimori"><a href="https://www.morimori-kaitori.jp/category/0112"'''
assert _TH_OLD_START in t
_th_begin = t.index(_TH_OLD_START)
_th_end = t.index("      </tr>", _th_begin)
t = t[:_th_begin] + '''        <th class="sc" data-s="icchome"><a href="https://www.1-chome.com/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'icchome',shop_name:'一丁目'})">一丁目</a></th>
        <th class="sc" data-s="morimori"><a href="https://www.morimori-kaitori.jp/category/1904001" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'morimori',shop_name:'森森'})">森森</a></th>
        <th class="sc" data-s="rudeya"><a href="https://kaitori-rudeya.com/category/detail/240" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'rudeya',shop_name:'ルデヤ'})">ルデヤ</a></th>
        <th class="sc" data-s="homura"><a href="https://kaitori-homura.com/products?q%5Bproduct_sub_category_id_eq%5D=188" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'homura',shop_name:'ホムラ'})">ホムラ</a></th>
''' + t[_th_end:]

# 発売日を商品名の直後に足す(再販が狙えるかの判断材料として需要が高い)
t = rep(t, '        <th style="min-width:200px">商品名</th>\n',
        '        <th style="min-width:200px">商品名</th>\n'
        '        <th style="min-width:84px">発売日</th>\n',
        count=1)

# フリマ列のヘッダを「差益」の直後に足す。
# 差益(定価との差)は dcol クラスを付けてモバイルでは隠す。狭い画面で
# 「フリマ相場/フリマ差」が横スクロールの外に出てしまうと、このページの
# 主目的(買取とフリマの比較)が初期表示で見えなくなるため。
# フリマ高値は買取店の列より右(一番右)に置く。まとめ売りを拾いきれておらず
# 値の信頼度が買取価格より低いため、主役の位置には置かない。
# thead の店舗列は render() が並べ替えで末尾に append し直すので、
# ここでの記述位置に関わらず render() 側で fmcol を最後に送っている。
t = rep(t, '        <th style="min-width:50px">差益</th>\n',
        '        <th class="dcol" style="min-width:50px">差益</th>\n'
        '        <th class="fmcol" style="min-width:92px">フリマ高値</th>\n',
        count=1)

# 6.5) 表の直前にフリマ価格の注意書き --------------------------------------
# フッターの注記だけだと表から遠く読まれないため、表の直上にも置く。
t = rep(t, '<div class="tw">',
        '<div class="fmnote">⚠ <b>フリマ高値は値ブレが大きい参考値です</b>。'
        'メルカリで直近30日に売れた最高額を載せていますが、出品時期・付属品・'
        '出品者の値付けで大きく変動します。同じ価格で売れることを保証するものでは'
        'なく、手数料(販売価格の10%)と送料も差し引かれます。'
        '確実性を重視する場合は買取価格をご確認ください。</div>\n<div class="tw">',
        count=1)
t = rep(t, '\n.cb{max-width:var(--table-width);',
        '\n.fmnote{max-width:var(--table-width);margin:10px auto 0;padding:9px 13px;'
        'background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;'
        'font-size:12px;line-height:1.6;color:#9a3412}'
        '\n.fmnote b{color:#c2410c}'
        '\n@media(max-width:768px){.fmnote{margin:10px 12px 0;font-size:11px}}'
        '\n.cb{max-width:var(--table-width);',
        count=1)

# 7) フッターの出典(4店のみ) -------------------------------------------------
_FT_OLD = '''  <a href="https://www.morimori-kaitori.jp/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'morimori',shop_name:'森森'})">森森買取</a> /'''
assert _FT_OLD in t
_ft_begin = t.index(_FT_OLD)
_ft_end = t.index("<br>\n  <a href=\"privacy.html\"", _ft_begin)
t = t[:_ft_begin] + '''  <a href="https://www.morimori-kaitori.jp/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'morimori',shop_name:'森森'})">森森買取</a> /
  <a href="https://kaitori-rudeya.com/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'rudeya',shop_name:'ルデヤ'})">買取ルデヤ</a> /
  <a href="https://kaitori-homura.com/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'homura',shop_name:'ホムラ'})">買取ホムラ</a> /
  <a href="https://www.1-chome.com/" target="_blank" rel="noopener noreferrer" onclick="gtag('event','shop_click',{shop:'icchome',shop_name:'一丁目'})">買取一丁目</a> /
  <a href="https://jp.mercari.com/" target="_blank" rel="noopener noreferrer">メルカリ</a>''' + t[_ft_end:]

t = rep(t, '  ※ 各店舗公式サイトより取得した未開封シュリンク付BOXの新品買取価格<br>\n',
        '  ※ 各店舗公式サイトより取得した新品未開封品の買取価格<br>\n'
        '  ※ フリマ高値はメルカリで直近30日に売却された中の最高額(パーツ単体・バラ売り・まとめ売りは除外)。'
        '括弧内は高値上位2割の平均<br>\n'
        '  ※ フリマ価格は値ブレが大きく、同額で売れることを保証するものではありません。'
        '手数料・送料は含みません。あくまで参考値としてご利用ください<br>\n',
        count=1)

# 店舗の並びは固定にする。ポケカは「最高買取になった回数の多い順」で動的に
# 並べ替えるが、ベイは4店しかなく、カテゴリを切り替えるたびに列が入れ替わると
# 読みにくい。掲載数の多い一丁目を左、最も少ないホムラを右に固定する。
t = replace_section(
    t, "function computeShopOrder(cat) {", "function computeS_SS() {",
    """function computeShopOrder(cat) {
  return [...S];
}
function computeS_SS() {""")

# 8) JS: 店舗配列 / カテゴリラベル / 既定表示 --------------------------------
t = rep(t, 'const S=["morimori","homura","icchome","runto","collect_tendo","shinsoku","oku","sommelier","rudeya","kaikyo"];',
        'const S=["icchome","morimori","rudeya","homura"];')
t = rep(t, 'let S_SS = ["homura","runto","morimori","icchome","oku","sommelier","rudeya","kaikyo","collect_tendo","shinsoku"];',
        'let S_SS = ["icchome","morimori","rudeya","homura"];')
t = rep(t, 'const CL={"mega":"MEGA","sv":"SV","special":"スペシャルBOX","ss":"S&S ソード&シールド"};',
        'const CL={"ux":"UX (アルティメット)","cx":"CX (カスタム)","bx":"BX (ベーシック)","limited":"限定品"};')
t = rep(t, 'cc===""?P.filter(x=>x.c!=="ss")', 'cc===""?P.slice()')
t = rep(t, 'const INV_KEY="pokeca_inventory";', 'const INV_KEY="beyblade_inventory";')

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
    if(x.j){
      const jn=document.createElement("div");
      jn.style.cssText="font-size:10px;color:#9ca3af;font-weight:400;line-height:1.3;letter-spacing:.02em";
      jn.textContent="JAN "+x.j;
      tdN.appendChild(jn);
    }
    tr.appendChild(tdN);

    // Release date
    const tdRel=document.createElement("td");
    tdRel.className="rp";
    tdRel.style.cssText="font-size:11px;color:#6b7280;white-space:nowrap";
    tdRel.textContent=x.d?x.d.replace(/-/g,"/"):"-";
    tr.appendChild(tdRel);''',
        count=1)

# 10) フリマ列の描画(差益セルの直後) -----------------------------------------
t = rep(t,
        '''    tr.appendChild(tdD);

    // Shop prices''',
        '''    tr.appendChild(tdD);

    tdD.classList.add("dcol");

    // Shop prices''',
        count=1)

# フリマ高値のセルは店舗列の後(行の末尾)に追加する
t = rep(t,
        '''      tr.appendChild(td);
    });

    frag.appendChild(tr);''',
        '''      tr.appendChild(td);
    });

    // Mercari: 直近30日の最高売却額 + 高値上位の平均
    const tdF=document.createElement("td");
    tdF.classList.add("fmcol");
    if(x.f>0){
      tdF.className="p fmcol";
      const hi=document.createElement("div");
      hi.style.cssText="font-weight:700;color:#f57c00";
      hi.textContent=fp(x.f);
      tdF.appendChild(hi);
      if(x.fa>0&&x.fn>1){
        const av=document.createElement("div");
        av.style.cssText="font-size:10px;color:#9ca3af;line-height:1.25;white-space:nowrap";
        av.textContent=x.fn+"件平均 "+fp(x.fa);
        tdF.appendChild(av);
      }
    }
    else{tdF.className="nd fmcol";tdF.textContent="-"}
    tr.appendChild(tdF);

    frag.appendChild(tr);''',
        count=1)

# thead: 店舗列を並べ替えた後、フリマ高値を最後尾へ送る
t = rep(t,
        '  SO.forEach(function(s){if(scThs[s])thr.appendChild(scThs[s])});',
        '  SO.forEach(function(s){if(scThs[s])thr.appendChild(scThs[s])});\n'
        '  var fmTh=thr.querySelector("th.fmcol");if(fmTh)thr.appendChild(fmTh);',
        count=1)

# カテゴリ見出し行のcolspan
# (商品名/発売日/定価/最高買取/差益 の5列 + フリマ高値1列)
t = rep(t, 'let cs=4+SO.filter(s=>vs.has(s)).length;',
        'let cs=6+SO.filter(s=>vs.has(s)).length;', count=1)

# 11) 記事枠・ランキング枠は使わない(記事を作らないため空にする) --------------
t = rep(t, "<!-- {{BLOG_LINKS}} -->\n\n", "")
t = rep(t, "<!-- {{RANKING_SUMMARY}} -->\n\n", "")

# 12) サイト説明セクション(ポケカ固有の機能紹介ごと差し替える) ---------------
t = replace_section(t, '<section class="site-intro"', "</section>", '''<section class="site-intro" aria-label="サイトについて">
  <details class="si-card">
    <summary class="si-summary">📖 ベイブレード買取チェッカーについて(タップで開く)</summary>
    <div class="si-body">
      <p class="si-lead">ベイブレードX 44商品×4店舗の買取価格を毎日3回(11:00/15:00/18:00 JST)自動収集し、メルカリの売却相場と並べて比較できる個人運営の情報サイトです。</p>
      <div class="si-grid">
        <div class="si-item"><h3>📊 4店舗を一括比較</h3><p>森森買取・買取ルデヤ・買取ホムラ・買取一丁目の公式買取表を自動収集。最高値は黄色ハイライトで明示します。</p></div>
        <div class="si-item"><h3>🛒 フリマ高値も並べて表示</h3><p>表の一番右に、メルカリで直近30日に売れた最高額と高値上位の平均を掲載。買取価格と見比べる参考値としてご利用ください。</p></div>
        <div class="si-item"><h3>💰 資産モード</h3><p>右上「資産モード」で保有個数を入力すると合計資産額をリアルタイム計算します。</p></div>
        <div class="si-item"><h3>🏷️ 定価は公式表記</h3><p>定価はタカラトミー公式の製品情報ページに掲載された希望小売価格(税込)をそのまま使用しています。</p></div>
      </div>
      <div class="si-howto"><strong>使い方</strong>: 上部のシリーズ(UX/CX/BX/限定品)・買取屋ボタンで絞り込み → 一番右の「フリマ高値」はメルカリの実売参考値です。買取価格と見比べる際は、フリマは手数料と送料が引かれる点にご注意ください。</div>
      <div class="si-meta">
        <a href="about.html">運営者情報</a> ・ <a href="privacy.html">プライバシーポリシー</a> ・ <a href="contact.html">お問い合わせ</a>
      </div>
    </div>
  </details>
</section>''')

# 13) ブランディング文言(残りの表記ゆれ) -------------------------------------
t = t.replace("ポケモンカードゲーム", "ベイブレードX")
t = t.replace("ポケモンカード", "ベイブレードX")
t = t.replace("ポケカ買取チェッカー", "ベイブレード買取チェッカー")
t = t.replace("ポケカ", "ベイブレード")
t = t.replace("未開封BOX", "商品")

# 14) 切替バナー -------------------------------------------------------------
t = sb.apply(t, "beyblade")

out = ROOT / "beyblade-template.html"
out.write_text(t, encoding="utf-8")
print(f"wrote {out} ({len(t)} bytes)")

# ===== ポケカ/ワンピのテンプレにもベイへの導線を入れて3択にする(冪等) =====
for filename, page in [("template.html", "pokemon"),
                       ("onepiece-template.html", "onepiece")]:
    path = ROOT / filename
    if not path.exists():
        print(f"skip {filename} (not found)")
        continue
    text = sb.strip(path.read_text(encoding="utf-8"))
    path.write_text(sb.apply(text, page), encoding="utf-8")
    print(f"patched {filename} with 3-way switch banner")
