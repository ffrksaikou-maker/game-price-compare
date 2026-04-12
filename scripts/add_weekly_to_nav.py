"""Add weekly hot-boxes article + inferno-x-spotlight links to article-nav.

Each article HTML has a hardcoded <nav class="article-nav"> sidebar.
This script inserts new links idempotently.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Articles in root /
ROOT_ARTICLES = [
    "kaitori-tips.html", "shop-hikaku.html", "single-card-tips.html",
    "psa-guide.html", "mercari-hikaku.html", "shrink-nashi.html",
    "monthly-ranking-2026-03.html", "box-toushi.html", "restock-guide.html",
    "inferno-x-spotlight.html",  # also include the spotlight article itself
    "ranking.html",
]

# (link path, label) for nav entries to insert at the top of article-nav
# These prefixes are for root-level pages; box-template uses ../ prefix
ROOT_NEW_LINKS = [
    ('weekly/', '🔥 今週の急上昇記事'),
    ('inferno-x-spotlight.html', '【特集】インフェルノX高騰'),
]

BOX_NEW_LINKS = [
    ('../weekly/', '🔥 今週の急上昇記事'),
    ('../inferno-x-spotlight.html', '【特集】インフェルノX高騰'),
]

MARKER_FIRST_LINK_INDEX_HTML = '<a href="index.html">買取価格比較</a>'
MARKER_FIRST_LINK_BOX_TPL = '<a href="../index.html">買取価格比較</a>'


def insert_after(content: str, marker: str, additions: list[str]) -> tuple[str, bool]:
    """Insert each new <a> right after the marker line, idempotent.
    Returns (new_content, changed).
    """
    if marker not in content:
        return content, False

    # Skip if already present
    already_has = all(href in content for href, _ in [(a.split('"')[1], None) for a in additions])
    # We track by full anchor markup to be safer
    addition_html = []
    for line in additions:
        if line in content:
            continue
        addition_html.append(line)
    if not addition_html:
        return content, False

    new_content = content.replace(
        marker,
        marker + "\n" + "\n".join(addition_html),
        1,
    )
    return new_content, True


def main():
    # Build the addition lines for ROOT articles
    root_additions = [
        f'<a href="{href}">{label}</a>'
        for href, label in ROOT_NEW_LINKS
    ]

    for fname in ROOT_ARTICLES:
        path = ROOT / fname
        if not path.exists():
            print(f"SKIP: {fname} (not found)")
            continue
        content = path.read_text(encoding="utf-8")
        new_content, changed = insert_after(content, MARKER_FIRST_LINK_INDEX_HTML, root_additions)
        if changed:
            path.write_text(new_content, encoding="utf-8")
            print(f"OK: {fname}")
        else:
            print(f"SKIP: {fname} (no marker or already present)")

    # box-template.html
    box_template = ROOT / "box-template.html"
    if box_template.exists():
        box_additions = [
            f'<a href="{href}">{label}</a>'
            for href, label in BOX_NEW_LINKS
        ]
        content = box_template.read_text(encoding="utf-8")
        new_content, changed = insert_after(content, MARKER_FIRST_LINK_BOX_TPL, box_additions)
        if changed:
            box_template.write_text(new_content, encoding="utf-8")
            print(f"OK: box-template.html")
        else:
            print(f"SKIP: box-template.html (no marker or already present)")


if __name__ == "__main__":
    main()
