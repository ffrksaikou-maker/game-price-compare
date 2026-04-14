"""Restructure nav: move 【特集】spotlight links from left article-nav to new right spotlight-nav.

Applies to:
- Root articles (prefix '')
- box-template.html + box/*.html (prefix '../')
- weekly/*.html (prefix '../')

Idempotent: safe to re-run.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ROOT_ARTICLES = [
    "kaitori-tips.html", "shop-hikaku.html", "single-card-tips.html",
    "psa-guide.html", "mercari-hikaku.html", "shrink-nashi.html",
    "monthly-ranking-2026-03.html", "box-toushi.html", "restock-guide.html",
    "ranking.html",
]

NEW_CSS = (
    '.content-layout{display:flex;gap:20px;align-items:flex-start}\n'
    '.content-layout article,.content-layout .main-card{flex:1;min-width:0}\n'
    '.article-nav,.spotlight-nav{width:180px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}\n'
    '.article-nav-title,.spotlight-nav-title{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}\n'
    '.article-nav a,.spotlight-nav a{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4;transition:all .2s}\n'
    '.article-nav a:hover,.spotlight-nav a:hover{color:var(--accent);border-left-color:var(--accent)}\n'
    '.article-nav a.current,.spotlight-nav a.current{color:var(--accent);border-left-color:var(--accent);font-weight:600}\n'
    '.spotlight-nav a{font-weight:500}\n'
    '.spotlight-nav-title{color:#b91c1c}\n'
    '@media(max-width:1200px){.spotlight-nav{display:none}}\n'
    '@media(max-width:1023px){.content-layout{display:block}.article-nav{display:none}}'
)

CSS_END_MARKER = '@media(max-width:1023px){.content-layout{display:block}.article-nav{display:none}}'
CLOSE_MARKER = '</div><!-- /content-layout -->'


def process(path: Path, prefix: str) -> bool:
    content = path.read_text(encoding="utf-8")
    orig = content

    # 1) Replace CSS block (idempotent: skip if spotlight-nav already present)
    if 'spotlight-nav' not in content:
        css_start = content.find('.content-layout{display:flex')
        css_end = content.find(CSS_END_MARKER, css_start) if css_start != -1 else -1
        if css_start != -1 and css_end != -1:
            content = content[:css_start] + NEW_CSS + content[css_end + len(CSS_END_MARKER):]

    # 2) Remove spotlight links from left article-nav
    for target in ("inferno-x-spotlight.html", "151-spotlight.html"):
        label_map = {
            "inferno-x-spotlight.html": "【特集】インフェルノX高騰",
            "151-spotlight.html": "【特集】ポケモンカード151高騰",
        }
        label = label_map[target]
        for cls in ('', ' class="current"'):
            line = f'<a href="{prefix}{target}"{cls}>{label}</a>\n'
            content = content.replace(line, '')

    # 3) Rename 記事一覧 → 一般記事
    content = content.replace(
        '<div class="article-nav-title">記事一覧</div>',
        '<div class="article-nav-title">一般記事</div>'
    )

    # 4) Insert spotlight-nav before </div><!-- /content-layout -->
    if 'spotlight-nav-title' not in content and CLOSE_MARKER in content:
        spotlight_block = (
            '\n<nav class="spotlight-nav">\n'
            '<div class="spotlight-nav-title">🔥 BOX深掘り特集</div>\n'
            f'<a href="{prefix}151-spotlight.html">【特集】ポケモンカード151高騰</a>\n'
            f'<a href="{prefix}inferno-x-spotlight.html">【特集】インフェルノX高騰</a>\n'
            '</nav>\n'
        )
        content = content.replace(CLOSE_MARKER, spotlight_block + CLOSE_MARKER, 1)

    if content != orig:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    count_ok = 0
    count_skip = 0

    # Root articles
    for fname in ROOT_ARTICLES:
        p = ROOT / fname
        if not p.exists():
            print(f"MISS: {fname}")
            continue
        if process(p, prefix=''):
            count_ok += 1
            print(f"OK: {fname}")
        else:
            count_skip += 1
            print(f"SKIP: {fname}")

    # box-template.html
    p = ROOT / "box-template.html"
    if p.exists():
        if process(p, prefix='../'):
            count_ok += 1
            print(f"OK: box-template.html")
        else:
            count_skip += 1
            print(f"SKIP: box-template.html")

    # box/*.html
    for p in sorted((ROOT / "box").glob("*.html")):
        if process(p, prefix='../'):
            count_ok += 1
            print(f"OK: box/{p.name}")
        else:
            count_skip += 1
            print(f"SKIP: box/{p.name}")

    # weekly/*.html
    for p in sorted((ROOT / "weekly").glob("*.html")):
        if process(p, prefix='../'):
            count_ok += 1
            print(f"OK: weekly/{p.name}")
        else:
            count_skip += 1
            print(f"SKIP: weekly/{p.name}")

    print(f"\n=== TOTAL: {count_ok} updated, {count_skip} skipped ===")


if __name__ == "__main__":
    main()
