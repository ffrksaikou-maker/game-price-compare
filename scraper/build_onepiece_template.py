"""template.html -> onepiece-template.html 変換スクリプト(冪等)。

ポケカ版テンプレを流用し、ブランディング/カテゴリ(op/eb/prb/st)/配色/既定フィルタ/
ページ切替バナー をワンピ用に置換する。各構造置換は必ず1回以上ヒットすることを assert。
切替は全幅のカラーバナー(.gswitch)で強調表示する。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ===== 切替バナー(全幅・カラーCTA) =====
UPD_CSS = '.header .upd{position:absolute;right:20px;font-size:11px;color:var(--text-sub)}'
BANNER_CSS = (
    '\n.gswitch{display:flex;align-items:center;justify-content:center;gap:8px;'
    'padding:13px 16px;font-size:15px;font-weight:800;text-decoration:none;color:#fff;'
    'box-shadow:inset 0 -2px 0 rgba(0,0,0,.12)}'
    '\n.gswitch .ar{font-size:19px;line-height:1}'
    '\n.gs-op{background:linear-gradient(135deg,#ff6b6b,#e53935)}'
    '\n.gs-pk{background:linear-gradient(135deg,#4aa3ff,#1e88e5)}'
    '\n.gswitch:active{filter:brightness(.94)}'
    '\n@media(hover:hover){.gswitch:hover{filter:brightness(1.08)}}'
)
# ワンピ版 → ポケカへ戻る(href="/" はNetlify/http.server共に index.html)
OP_BANNER = ('<a class="gswitch gs-pk" href="/">'
             '<span class="ar">◀</span> ポケモンカードの買取比較はこちら</a>\n')
# ポケカ版 → ワンピへ(本番のクリーンURL)
PK_BANNER = ('<a class="gswitch gs-op" href="/onepiece">'
             'ONE PIECEカードの買取比較はこちら <span class="ar">▶</span></a>\n')

# 旧・隅ボタン方式(過去パッチ)を掃除するための文字列
_OLD_SWITCH_CSS = ('\n.header .switch{position:absolute;left:12px;font-size:12px;font-weight:700;'
                   'color:#ef4444;text-decoration:none;border:1px solid #ef4444;border-radius:6px;padding:3px 8px}')


def normalize_src(s: str) -> str:
    """過去にパッチ済みのtemplate.htmlでも素の状態に戻す(冪等化)。"""
    s = s.replace(UPD_CSS + BANNER_CSS, UPD_CSS)
    s = s.replace(UPD_CSS + _OLD_SWITCH_CSS, UPD_CSS)
    s = s.replace(PK_BANNER, "")
    s = s.replace('<div class="header">\n  <a class="switch" href="/onepiece">ワンピ版 ▶</a>\n  <h1>',
                  '<div class="header">\n  <h1>')
    return s


def rep(text, old, new, *, count=None):
    n = text.count(old)
    assert n > 0, f"NOT FOUND: {old[:60]!r}"
    if count is not None:
        assert n == count, f"expected {count} of {old[:40]!r}, got {n}"
    return text.replace(old, new)


src = normalize_src((ROOT / "template.html").read_text(encoding="utf-8"))
t = src

# 1) 構造置換(グローバル置換より先に、原文のまま当てる) ---------------------------

# メタ description / og / twitter
t = rep(t, 'content="ポケモンカード未開封BOXの買取価格をラントゥ・ホムラ・一丁目・森森買取等10店舗横断で比較。最高値が一目でわかるポケカ買取チェッカー。"',
        'content="ONE PIECEカードゲーム未開封BOXの買取価格をラントゥ・ホムラ・一丁目・森森買取等11店舗横断で比較。最高値が一目でわかるワンピ買取チェッカー。"')
t = rep(t, 'content="ポケモンカード未開封BOXの買取価格をラントゥ・ホムラ・一丁目・森森買取等10店舗横断で比較。最高値が一目でわかる。"',
        'content="ONE PIECEカードゲーム未開封BOXの買取価格をラントゥ・ホムラ・一丁目・森森買取等11店舗横断で比較。最高値が一目でわかる。"', count=2)

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

# 切替バナー用CSS
t = rep(t, UPD_CSS, UPD_CSS + BANNER_CSS, count=1)

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

# 商品名を非リンク(span)化
t = rep(t,
        '''    const aName=document.createElement("a");
    aName.href="box/"+x.s+".html";
    aName.textContent=x.n;
    aName.style.cssText="color:inherit;text-decoration:none;border-bottom:1px dashed #c4b5fd";
    tdN.appendChild(aName);''',
        '''    const aName=document.createElement("span");
    aName.textContent=x.n;
    aName.style.cssText="color:inherit";
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
        'ONE PIECEカード未開封BOX 23商品×11店舗')

# 2) グローバル文言置換(ブランディング) --------------------------------------
t = t.replace("ポケモンカードゲーム", "ONE PIECEカードゲーム")
t = t.replace("ポケモンカード", "ONE PIECEカード")
t = t.replace("ポケカ買取チェッカー", "ワンピ買取チェッカー")
t = t.replace("ポケカ", "ワンピ")

# 3) 切替バナー挿入(グローバル置換の後。バナー文言"ポケモンカード"を保護するため) ----
t = rep(t, '<div class="header">', OP_BANNER + '<div class="header">', count=1)

out = ROOT / "onepiece-template.html"
out.write_text(t, encoding="utf-8")
print(f"wrote {out} ({len(t)} bytes)")

# ===== ポケカ側テンプレにも切替バナーを追加(冪等) =====
pk = normalize_src((ROOT / "template.html").read_text(encoding="utf-8"))
pk = pk.replace(UPD_CSS, UPD_CSS + BANNER_CSS, 1)
pk = pk.replace('<div class="header">', PK_BANNER + '<div class="header">', 1)
(ROOT / "template.html").write_text(pk, encoding="utf-8")
print("patched template.html with ワンピ版 banner")
