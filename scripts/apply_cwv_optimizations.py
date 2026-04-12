"""Apply CWV optimizations to existing article HTML files.

Adds: preconnect/dns-prefetch hints, img loading="lazy" + decoding="async".
Idempotent - can be re-run safely.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ARTICLES = [
    "kaitori-tips.html",
    "shop-hikaku.html",
    "single-card-tips.html",
    "psa-guide.html",
    "mercari-hikaku.html",
    "shrink-nashi.html",
    "monthly-ranking-2026-03.html",
    "box-toushi.html",
    "restock-guide.html",
    "privacy.html",  # also add to privacy page for consistency
]

PRECONNECT_BLOCK = """<!-- Preconnect hints for Core Web Vitals -->
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://h.accesstrade.net">
<link rel="dns-prefetch" href="https://m.media-amazon.com">
"""

PRECONNECT_MARKER = "Preconnect hints for Core Web Vitals"


def apply_preconnect(content: str) -> tuple[str, bool]:
    """Insert preconnect hints right after the viewport meta tag. Idempotent."""
    if PRECONNECT_MARKER in content:
        return content, False
    # Insert after <meta name="viewport" ...>
    m = re.search(r'(<meta\s+name="viewport"[^>]*>)', content)
    if not m:
        return content, False
    insert_pos = m.end()
    new_content = content[:insert_pos] + "\n" + PRECONNECT_BLOCK + content[insert_pos:]
    return new_content, True


def apply_img_lazy(content: str) -> tuple[str, int]:
    """Add loading='lazy' + decoding='async' to img tags that don't have them.
    Specifically targets affiliate and external images (accesstrade etc.)
    Skips inline SVGs and dynamically generated imgs.
    """
    count = 0
    # Match img tags with src containing accesstrade or other external URLs,
    # that don't already have loading attribute
    def replace_img(match: re.Match) -> str:
        nonlocal count
        tag = match.group(0)
        if 'loading=' in tag:
            return tag  # already has loading attr
        # Insert loading="lazy" and decoding="async" before the closing >
        new_tag = tag[:-1] + ' loading="lazy" decoding="async">'
        count += 1
        return new_tag

    new_content = re.sub(
        r'<img\s+[^>]*src="https://h\.accesstrade\.net/[^"]+"[^>]*>',
        replace_img,
        content,
    )
    return new_content, count


def main():
    for fname in ARTICLES:
        path = ROOT / fname
        if not path.exists():
            print(f"SKIP: {fname} (not found)")
            continue

        content = path.read_text(encoding="utf-8")

        content, preconnect_added = apply_preconnect(content)
        content, img_count = apply_img_lazy(content)

        if preconnect_added or img_count > 0:
            path.write_text(content, encoding="utf-8")
            changes = []
            if preconnect_added:
                changes.append("preconnect")
            if img_count:
                changes.append(f"img×{img_count}")
            print(f"OK: {fname} ({', '.join(changes)})")
        else:
            print(f"SKIP: {fname} (no changes needed)")


if __name__ == "__main__":
    main()
