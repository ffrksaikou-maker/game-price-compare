"""Fix: move spotlight-nav into article-nav as a bottom subsection (single left column).

Previous script created a separate right-side column, which conflicted with
existing TOC columns on article pages (4-column layout was too cramped).
This script reverts that structure and puts spotlight links inline at the
bottom of article-nav with a styled subtitle divider.

Idempotent.
"""
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent

ROOT_ARTICLES = [
    "kaitori-tips.html", "shop-hikaku.html", "single-card-tips.html",
    "psa-guide.html", "mercari-hikaku.html", "shrink-nashi.html",
    "monthly-ranking-2026-03.html", "box-toushi.html", "restock-guide.html",
    "ranking.html", "151-spotlight.html", "inferno-x-spotlight.html",
]

# Original CSS to restore (single-column layout, no spotlight-nav rules)
ORIG_CSS = (
    '.content-layout{display:flex;gap:24px;align-items:flex-start}\n'
    '.content-layout article,.content-layout .main-card{flex:1;min-width:0}\n'
    '.article-nav{width:180px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}\n'
    '.article-nav-title{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}\n'
    '.article-nav a{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4;transition:all .2s}\n'
    '.article-nav a:hover{color:var(--accent);border-left-color:var(--accent)}\n'
    '.article-nav a.current{color:var(--accent);border-left-color:var(--accent);font-weight:600}\n'
    '.article-nav-sub{font-size:12px;font-weight:700;margin:14px 0 6px;color:#b91c1c;padding-top:10px;border-top:1px solid var(--border)}\n'
    '@media(max-width:1023px){.content-layout{display:block}.article-nav{display:none}}'
)

CSS_START_MARKER = '.content-layout{display:flex;'
# End of the new CSS block we previously inserted ends with the 1023px media query
CSS_END_MARKER = '@media(max-width:1023px){.content-layout{display:block}.article-nav{display:none}}'


def process(path: Path, prefix: str, current_key: str | None) -> bool:
    """current_key: 'inferno'|'151'|None — which entry gets class='current'"""
    content = path.read_text(encoding="utf-8")
    orig = content

    # 1) Replace the CSS block back to single-column + add .article-nav-sub rule
    start = content.find(CSS_START_MARKER)
    end = content.find(CSS_END_MARKER, start) if start != -1 else -1
    if start != -1 and end != -1:
        content = content[:start] + ORIG_CSS + content[end + len(CSS_END_MARKER):]

    # 2) Remove the separate right-side spotlight-nav block
    # It was inserted as:
    #   \n<nav class="spotlight-nav">\n<div class="spotlight-nav-title">🔥 BOX深掘り特集</div>\n<a href="...151-spotlight.html">...</a>\n<a href="...inferno-x-spotlight.html">...</a>\n</nav>\n
    content = re.sub(
        r'\n<nav class="spotlight-nav">\n<div class="spotlight-nav-title">🔥 BOX深掘り特集</div>\n'
        r'<a href="[^"]*151-spotlight\.html"[^>]*>【特集】ポケモンカード151高騰</a>\n'
        r'<a href="[^"]*inferno-x-spotlight\.html"[^>]*>【特集】インフェルノX高騰</a>\n'
        r'</nav>\n',
        '',
        content,
    )

    # 3) Inject spotlight subsection at bottom of article-nav (before </nav>)
    # Find article-nav block and replace </nav> with subsection + </nav>
    # Only if the subsection isn't already present
    if 'article-nav-sub' not in content:
        # Build the 2 anchor lines with optional current class
        def anchor(target: str, label: str) -> str:
            cls = ' class="current"' if current_key == target.replace('-spotlight.html', '') else ''
            return f'<a href="{prefix}{target}"{cls}>{label}</a>'

        sub_block = (
            '<div class="article-nav-sub">🔥 BOX深掘り特集</div>\n'
            + anchor("151-spotlight.html", "【特集】ポケモンカード151高騰") + '\n'
            + anchor("inferno-x-spotlight.html", "【特集】インフェルノX高騰") + '\n'
        )
        # Replace the first </nav> after <nav class="article-nav">
        nav_open = content.find('<nav class="article-nav">')
        if nav_open != -1:
            nav_close = content.find('</nav>', nav_open)
            if nav_close != -1:
                content = content[:nav_close] + sub_block + content[nav_close:]

    if content != orig:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    ok = skip = 0

    # Root articles
    for fname in ROOT_ARTICLES:
        p = ROOT / fname
        if not p.exists():
            print(f"MISS: {fname}")
            continue
        key = None
        if fname == "151-spotlight.html":
            key = "151"
        elif fname == "inferno-x-spotlight.html":
            key = "inferno"
        changed = process(p, prefix='', current_key=key)
        ok += int(changed); skip += int(not changed)
        print(f"{'OK' if changed else 'SKIP'}: {fname}")

    # box-template + box/*
    for p in [ROOT / "box-template.html", *sorted((ROOT / "box").glob("*.html"))]:
        if not p.exists(): continue
        changed = process(p, prefix='../', current_key=None)
        ok += int(changed); skip += int(not changed)
        print(f"{'OK' if changed else 'SKIP'}: {p.relative_to(ROOT)}")

    # weekly/*
    for p in sorted((ROOT / "weekly").glob("*.html")):
        changed = process(p, prefix='../', current_key=None)
        ok += int(changed); skip += int(not changed)
        print(f"{'OK' if changed else 'SKIP'}: {p.relative_to(ROOT)}")

    print(f"\n=== TOTAL: {ok} updated, {skip} skipped ===")


if __name__ == "__main__":
    main()
