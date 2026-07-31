"""template.html -> onepiece-template.html 変換スクリプト(冪等)。

ポケカ版テンプレを流用し、ブランディング/カテゴリ(op/eb/prb/st)/配色/既定フィルタ/
ページ切替バナー をワンピ用に置換する。各構造置換は必ず1回以上ヒットすることを assert。
切替バナーは3ページ(ポケカ/ワンピ/ベイブレード)共通の switch_banner が生成する。

メタ情報は content を属性位置で差し替える。以前は原文を固定文字列で置換していたが、
template.html 側の文言が更新されるたびに assert で落ちて再生成できなくなるため。
"""
import re
from pathlib import Path

from . import switch_banner as sb

ROOT = Path(__file__).resolve().parent.parent

# 現行 onepiece-template.html に入っている文言をそのまま維持する
# (ここを変えるとタイトル/descriptionが差し替わるので、変更は意図的に行うこと)
TITLE = "ワンピ買取チェッカー｜未開封BOX買取価格比較"
DESC = ("ONE PIECEカードゲーム未開封BOXの買取価格をラントゥ・ホムラ・一丁目・森森買取等"
        "11店舗横断で比較。最高値が一目でわかるワンピ買取チェッカー。")
DESC_SHORT = ("ONE PIECEカードゲーム未開封BOXの買取価格をラントゥ・ホムラ・一丁目・森森買取等"
              "11店舗横断で比較。最高値が一目でわかる。")


def rep(text, old, new, *, count=None):
    n = text.count(old)
    assert n > 0, f"NOT FOUND: {old[:60]!r}"
    if count is not None:
        assert n == count, f"expected {count} of {old[:40]!r}, got {n}"
    return text.replace(old, new)


def set_content(text, marker, new):
    """<meta ...> の content 属性を差し替える(元の文言に依存しない)。"""
    i = text.index(marker)
    j = text.index('content="', i) + len('content="')
    k = text.index('"', j)
    return text[:j] + new + text[k:]


src = sb.strip((ROOT / "template.html").read_text(encoding="utf-8"))
t = src

# 1) 構造置換(グローバル置換より先に、原文のまま当てる) ---------------------------

# メタ description / og / twitter
t = set_content(t, '<meta name="description"', DESC)
t = set_content(t, '<meta property="og:title"', TITLE)
t = set_content(t, '<meta property="og:description"', DESC_SHORT)
t = set_content(t, '<meta property="og:site_name"', "ワンピ買取チェッカー")
t = set_content(t, '<meta name="twitter:title"', TITLE)
t = set_content(t, '<meta name="twitter:description"', DESC_SHORT)
t = re.sub(r"<title>[^<]*</title>", f"<title>{TITLE}</title>", t, count=1)

# og:url / canonical → /onepiece
t = rep(t, '<meta property="og:url" content="https://pokeca-box-hikaku.com/">',
        '<meta property="og:url" content="https://pokeca-box-hikaku.com/onepiece">')
t = rep(t, '<link rel="canonical" href="https://pokeca-box-hikaku.com/">',
        '<link rel="canonical" href="https://pokeca-box-hikaku.com/onepiece">')

# CSSカテゴリ変数(op/eb/prb/st)
t = rep(t, "  --special: #e3f2fd;\n}",
        "  --special: #e3f2fd;\n  --op: #ffebee;\n  --eb: #e8f5e9;\n  --prb: #fff3e0;\n  --st: #e3f2fd;\n}")

# カテゴリ行の背景色(PC)
t = rep(t, 'tr.cat-ss td{background:#fce4ec}',
        'tr.cat-ss td{background:#fce4ec}tr.cat-op td{background:var(--op)}tr.cat-eb td{background:var(--eb)}tr.cat-prb td{background:var(--prb)}tr.cat-st td{background:var(--st)}',
        count=1)
t = rep(t, 'tr.cat-ss:hover td{background:#f8bbd0 !important}',
        'tr.cat-ss:hover td{background:#f8bbd0 !important}tr.cat-op:hover td{background:#ffcdd2 !important}tr.cat-eb:hover td{background:#c8e6c9 !important}tr.cat-prb:hover td{background:#ffe0b2 !important}tr.cat-st:hover td{background:#bbdefb !important}',
        count=1)
# モバイル商品名セル(pn)
t = rep(t, '  tr.cat-ss td.pn{background:#fce4ec}',
        '  tr.cat-ss td.pn{background:#fce4ec}\n  tr.cat-op td.pn{background:var(--op)}\n  tr.cat-eb td.pn{background:var(--eb)}\n  tr.cat-prb td.pn{background:var(--prb)}\n  tr.cat-st td.pn{background:var(--st)}',
        count=1)
t = rep(t, '  tr.cat-ss:hover td.pn{background:#f8bbd0 !important}',
        '  tr.cat-ss:hover td.pn{background:#f8bbd0 !important}\n  tr.cat-op:hover td.pn{background:#ffcdd2 !important}\n  tr.cat-eb:hover td.pn{background:#c8e6c9 !important}\n  tr.cat-prb:hover td.pn{background:#ffe0b2 !important}\n  tr.cat-st:hover td.pn{background:#bbdefb !important}',
        count=1)

# モバイルで商品名の弾番号【OP-XX】が省略(…)で見切れるので折り返し表示にする。
# 768px と 480px の td.pn ルールを white-space:normal に置換。
t = rep(t,
        '  td.pn{position:sticky;left:0;z-index:10;min-width:140px;max-width:180px;overflow:hidden;text-overflow:ellipsis;font-size:11px;padding-left:8px}',
        '  td.pn{position:sticky;left:0;z-index:10;min-width:150px;max-width:210px;white-space:normal;word-break:break-word;line-height:1.3;font-size:11px;padding-left:8px}',
        count=1)
t = rep(t,
        '  td.pn{min-width:120px;max-width:150px;font-size:10px}',
        '  td.pn{min-width:130px;max-width:170px;font-size:10px;white-space:normal;word-break:break-word;line-height:1.3}',
        count=1)

# シリーズ絞り込みボタン
t = rep(t,
        '''    <button class="fb" data-f="cat" data-v="all">ALL</button>
    <button class="fb" data-f="cat" data-v="mega">MEGA</button>
    <button class="fb" data-f="cat" data-v="sv">SV</button>

    <button class="fb" data-f="cat" data-v="special">スペシャルBOX</button>
    <button class="fb" data-f="cat" data-v="ss">S&amp;S</button>''',
        '''    <button class="fb" data-f="cat" data-v="all">ALL</button>
    <button class="fb" data-f="cat" data-v="op">ブースター</button>
    <button class="fb" data-f="cat" data-v="eb">エクストラ</button>
    <button class="fb" data-f="cat" data-v="prb">プレミアム</button>
    <button class="fb" data-f="cat" data-v="st">デッキ</button>''')

# 凡例
t = rep(t,
        '''  <div class="li"><span class="ls" style="background:var(--mega)"></span>MEGA</div>
  <div class="li"><span class="ls" style="background:var(--sv)"></span>SV</div>
  <div class="li"><span class="ls" style="background:var(--special)"></span>スペシャルBOX</div>
  <div class="li"><span class="ls" style="background:#fce4ec"></span>S&amp;S</div>''',
        '''  <div class="li"><span class="ls" style="background:var(--op)"></span>ブースター</div>
  <div class="li"><span class="ls" style="background:var(--eb)"></span>エクストラ</div>
  <div class="li"><span class="ls" style="background:var(--prb)"></span>プレミアム</div>
  <div class="li"><span class="ls" style="background:var(--st)"></span>デッキ</div>''')

# JSカテゴリラベル
t = rep(t, 'const CL={"mega":"MEGA","sv":"SV","special":"スペシャルBOX","ss":"S&S ソード&シールド"};',
        'const CL={"op":"通常ブースター","eb":"エクストラブースター","prb":"プレミアムブースター","st":"スタートデッキ"};')

# 既定表示は全カテゴリ
t = rep(t, 'cc===""?P.filter(x=>x.c!=="ss")', 'cc===""?P.slice()')

# 商品名を個別BOXページ(onepiece/box/{slug}.html)へのリンクにする。
# /onepiece(ルートのonepiece.html)からの相対解決で /onepiece/box/... になる。
t = rep(t,
        '''    const aName=document.createElement("a");
    aName.href="box/"+x.s+".html";
    aName.textContent=x.n;
    aName.style.cssText="color:inherit;text-decoration:none;border-bottom:1px dashed #c4b5fd";
    tdN.appendChild(aName);''',
        '''    const aName=document.createElement("a");
    aName.href="onepiece/box/"+x.s+".html";
    aName.textContent=x.n;
    aName.style.cssText="color:inherit;text-decoration:none;border-bottom:1px dashed #ffabab";
    tdN.appendChild(aName);''')

# 在庫キー分離
t = rep(t, 'const INV_KEY="pokeca_inventory";', 'const INV_KEY="onepiece_inventory";')

# 店舗別カラムの外部リンクをワンピカテゴリへ(判明分)
t = rep(t, 'href="https://kaitori-oku.jp/category.html?cat1=340&cat2=363"',
        'href="https://kaitori-oku.jp/category.html?cat1=340&cat2=364"')
t = rep(t, 'href="https://kaitori-rudeya.com/category/detail/114"',
        'href="https://kaitori-rudeya.com/category/detail/224"')
t = rep(t, 'href="https://runto666.com/product-category/card/"',
        'href="https://runto666.com/product-category/onepiece/"')

# 「について」セクションの数値
t = rep(t, 'ポケモンカード未開封BOX 67商品×10店舗',
        'ONE PIECEカード未開封BOX 24商品×11店舗')

# 2) グローバル文言置換(ブランディング) --------------------------------------
t = t.replace("ポケモンカードゲーム", "ONE PIECEカードゲーム")
t = t.replace("ポケモンカード", "ONE PIECEカード")
t = t.replace("ポケカ買取チェッカー", "ワンピ買取チェッカー")
t = t.replace("ポケカ", "ワンピ")

# 3) 切替バナー挿入(グローバル置換の後。バナー文言"ポケモンカード"を保護するため) ----
t = sb.apply(t, "onepiece")

out = ROOT / "onepiece-template.html"
out.write_text(t, encoding="utf-8")
print(f"wrote {out} ({len(t)} bytes)")

# ===== ポケカ側テンプレにも切替バナーを追加(冪等) =====
pk_path = ROOT / "template.html"
pk = sb.apply(sb.strip(pk_path.read_text(encoding="utf-8")), "pokemon")
pk_path.write_text(pk, encoding="utf-8")
print("patched template.html with 3-way switch banner")
