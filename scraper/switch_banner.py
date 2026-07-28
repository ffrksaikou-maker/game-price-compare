"""ポケカ / ワンピ / ベイブレードの3ページを行き来する切替バナー。

ページが2枚のうちは全幅1本のバナーで足りていたが、ベイブレード版の追加で3枚に
なったため「自分以外の2つ」を横並びで出すバーに拡張した。生成スクリプト
(build_onepiece_template.py / build_beyblade_template.py)から共用する。

strip() は旧形式(全幅1本の <a class="gswitch">)と新形式(.gsbar)の両方を落とすので、
どの状態のテンプレから再生成しても結果が同じになる(冪等)。
"""

from __future__ import annotations

import re

# 挿入位置の目印にしている既存CSS(template.html 内に1箇所)
UPD_CSS = '.header .upd{position:absolute;right:20px;font-size:11px;color:var(--text-sub)}'

BANNER_CSS = (
    '\n.gsbar{display:flex}'
    '\n.gsbar .gswitch{flex:1;min-width:0}'
    '\n.gswitch{display:flex;align-items:center;justify-content:center;gap:6px;'
    'padding:13px 10px;font-size:14px;font-weight:800;text-decoration:none;color:#fff;'
    'box-shadow:inset 0 -2px 0 rgba(0,0,0,.12);white-space:nowrap;overflow:hidden;'
    'text-overflow:ellipsis}'
    '\n.gswitch .ar{font-size:17px;line-height:1}'
    '\n.gs-op{background:linear-gradient(135deg,#ff6b6b,#e53935)}'
    '\n.gs-pk{background:linear-gradient(135deg,#4aa3ff,#1e88e5)}'
    '\n.gs-by{background:linear-gradient(135deg,#ffa726,#f57c00)}'
    '\n.gswitch:active{filter:brightness(.94)}'
    '\n@media(hover:hover){.gswitch:hover{filter:brightness(1.08)}}'
    '\n@media(max-width:480px){.gswitch{font-size:12px;padding:11px 6px;gap:4px}'
    '.gswitch .ar{font-size:14px}}'
)

# ページ定義: key -> (CSSクラス, リンク先, ラベル)
# href="/" はNetlify/http.server共に index.html を指す。
_PAGES = {
    "pokemon": ("gs-pk", "/", "ポケモンカード"),
    "onepiece": ("gs-op", "/onepiece", "ONE PIECEカード"),
    "beyblade": ("gs-by", "/beyblade", "ベイブレード"),
}
# 並び順は固定(ページによって左右が入れ替わると迷子になるため)
_ORDER = ["pokemon", "onepiece", "beyblade"]

_OLD_SWITCH_CSS = (
    '\n.header .switch{position:absolute;left:12px;font-size:12px;font-weight:700;'
    'color:#ef4444;text-decoration:none;border:1px solid #ef4444;border-radius:6px;padding:3px 8px}'
)
_BANNER_RE = re.compile(
    r'(?:<div class="gsbar">.*?</div>|<a class="gswitch[^>]*>.*?</a>)\n?',
    re.S,
)
_CSS_RE = re.compile(
    r'\n\.gsbar\{.*?@media\(max-width:480px\)\{\.gswitch\{[^}]*\}[^}]*\}\}'
    r'|\n\.gswitch\{.*?@media\(hover:hover\)\{\.gswitch:hover\{filter:brightness\(1\.08\)\}\}',
    re.S,
)


def bar(current: str) -> str:
    """current 以外の2ページへのリンクを横並びで返す。"""
    assert current in _PAGES, current
    parts = []
    for key in _ORDER:
        if key == current:
            continue
        cls, href, label = _PAGES[key]
        # 自分より前のページは「◀ 戻る」、後ろのページは「進む ▶」の向きにする
        if _ORDER.index(key) < _ORDER.index(current):
            inner = f'<span class="ar">◀</span> {label}の買取比較'
        else:
            inner = f'{label}の買取比較 <span class="ar">▶</span>'
        parts.append(f'<a class="gswitch {cls}" href="{href}">{inner}</a>')
    return '<div class="gsbar">' + "".join(parts) + "</div>\n"


def strip(text: str) -> str:
    """既存の切替バナー(旧形式含む)とそのCSSを除去して素の状態に戻す。"""
    text = _CSS_RE.sub("", text)
    text = text.replace(UPD_CSS + _OLD_SWITCH_CSS, UPD_CSS)
    text = _BANNER_RE.sub("", text)
    text = text.replace(
        '<div class="header">\n  <a class="switch" href="/onepiece">ワンピ版 ▶</a>\n  <h1>',
        '<div class="header">\n  <h1>',
    )
    return text


def apply(text: str, current: str) -> str:
    """素のテンプレにCSSとバナーを入れる。strip 済みの文字列を渡すこと。"""
    assert UPD_CSS in text, "UPD_CSS marker not found"
    text = text.replace(UPD_CSS, UPD_CSS + BANNER_CSS, 1)
    return text.replace('<div class="header">', bar(current) + '<div class="header">', 1)
