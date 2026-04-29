"""Add a mobile-only footer navigation block to all pages.

Desktop users have the sidebar article-nav. But on mobile (<=1023px) many pages
hide the nav entirely, cutting off flow between articles/spotlights. This adds
a .mobile-footer-nav block that appears only on mobile, placed after the
content-layout close marker.

Idempotent.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ROOT_ARTICLES = [
    "kaitori-tips.html", "shop-hikaku.html", "single-card-tips.html",
    "psa-guide.html", "mercari-hikaku.html", "shrink-nashi.html",
    "monthly-ranking-2026-03.html", "box-toushi.html", "restock-guide.html",
    "ranking.html", "151-spotlight.html", "inferno-x-spotlight.html",
]

CSS_RULE = (
    '.mobile-footer-nav{display:none;margin:24px 0;padding:18px 16px;background:#f9fafb;border:1px solid var(--border);border-radius:12px}\n'
    '.mfn-title{font-size:14px;font-weight:700;margin-bottom:10px;color:var(--text)}\n'
    '.mfn-section{margin-top:14px}\n'
    '.mfn-section-title{font-size:12px;font-weight:700;color:#b91c1c;margin-bottom:8px;letter-spacing:.5px}\n'
    '.mobile-footer-nav a{display:block;font-size:13px;padding:10px 12px;border-radius:8px;color:var(--text);text-decoration:none;background:#fff;margin-bottom:6px;border:1px solid var(--border);transition:all .2s}\n'
    '.mobile-footer-nav a:hover,.mobile-footer-nav a:active{color:var(--accent);border-color:var(--accent);background:#f5f3ff}\n'
    '.mobile-footer-nav a.spot{border-left:3px solid #b91c1c;font-weight:600}\n'
    '@media(max-width:1023px){.mobile-footer-nav{display:block}}\n'
)

CSS_INSERT_MARKER = '@media(max-width:1023px){.content-layout{display:block}'


def build_block(prefix: str) -> str:
    return f'''
<nav class="mobile-footer-nav">
  <div class="mfn-title">📚 他の記事を読む</div>
  <div class="mfn-section">
    <div class="mfn-section-title">🔥 BOX深掘り特集</div>
    <a class="spot" href="{prefix}151-spotlight.html">【特集】ポケモンカード151がなぜ高い？12倍超え解説</a>
    <a class="spot" href="{prefix}inferno-x-spotlight.html">【特集】インフェルノXが定価の5倍に高騰</a>
  </div>
  <div class="mfn-section">
    <div class="mfn-section-title">📰 一般記事</div>
    <a href="{prefix}index.html">買取価格比較トップ</a>
    <a href="{prefix}weekly/">🔥 今週の急上昇記事</a>
    <a href="{prefix}ranking.html">上昇ランキング</a>
    <a href="{prefix}kaitori-tips.html">BOX買取のコツ</a>
    <a href="{prefix}shop-hikaku.html">10店舗比較</a>
    <a href="{prefix}box-toushi.html">BOX投資の始め方</a>
    <a href="{prefix}restock-guide.html">再販情報の見つけ方</a>
    <a href="{prefix}shrink-nashi.html">シュリンクなしBOX</a>
    <a href="{prefix}psa-guide.html">PSA鑑定ガイド</a>
    <a href="{prefix}mercari-hikaku.html">メルカリ・スニダン比較</a>
    <a href="{prefix}single-card-tips.html">シングル売り</a>
  </div>
</nav>
'''


INSERT_POINT = '</div><!-- /content-layout -->'


def process(path: Path, prefix: str) -> bool:
    content = path.read_text(encoding="utf-8")
    orig = content

    # 1) Add CSS if not present
    if '.mobile-footer-nav{' not in content:
        # Find the first 1023px media query line and insert CSS before it
        idx = content.find(CSS_INSERT_MARKER)
        if idx != -1:
            content = content[:idx] + CSS_RULE + content[idx:]

    # 2) Insert the HTML block after </div><!-- /content-layout -->
    if 'class="mobile-footer-nav"' not in content and INSERT_POINT in content:
        block = build_block(prefix)
        content = content.replace(INSERT_POINT, INSERT_POINT + block, 1)

    if content != orig:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    ok = 0
    for fname in ROOT_ARTICLES:
        p = ROOT / fname
        if p.exists() and process(p, prefix=''):
            ok += 1
            print(f"OK: {fname}")
    for p in [ROOT / "box-template.html", *sorted((ROOT / "box").glob("*.html"))]:
        if p.exists() and process(p, prefix='../'):
            ok += 1
            print(f"OK: {p.relative_to(ROOT)}")
    for p in sorted((ROOT / "weekly").glob("*.html")):
        if process(p, prefix='../'):
            ok += 1
            print(f"OK: {p.relative_to(ROOT)}")
    print(f"\n=== {ok} files patched ===")


if __name__ == "__main__":
    main()
