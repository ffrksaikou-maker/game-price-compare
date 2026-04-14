"""Add kokuen-spotlight link to all files' spotlight navigation sections.

Applies to:
- Root articles (prefix '')
- box-template.html + box/*.html (prefix '../')
- weekly/*.html (prefix '../')
- New 11 articles themselves (they have it already)

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

# Left sidebar article-nav has "🔥 BOX深掘り特集" subsection
# Currently ends with inferno-x-spotlight. Need to add kokuen-spotlight after.
LEFT_NAV_MARKER_ROOT = '<a href="inferno-x-spotlight.html">【特集】インフェルノX高騰</a>'
LEFT_NAV_MARKER_BOX = '<a href="../inferno-x-spotlight.html">【特集】インフェルノX高騰</a>'
LEFT_NAV_ADD_ROOT = '<a href="kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>'
LEFT_NAV_ADD_BOX = '<a href="../kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>'

# Mobile footer nav has 🔥 BOX深掘り特集 section ending with inferno-x-spotlight
MOBILE_MARKER_ROOT = '<a class="spot" href="inferno-x-spotlight.html">【特集】インフェルノXが定価の5倍に高騰</a>'
MOBILE_MARKER_BOX = '<a class="spot" href="../inferno-x-spotlight.html">【特集】インフェルノXが定価の5倍に高騰</a>'
MOBILE_ADD_ROOT = '<a class="spot" href="kokuen-spotlight.html">【特集】黒炎の支配者がなぜ高い？定価の約4倍</a>'
MOBILE_ADD_BOX = '<a class="spot" href="../kokuen-spotlight.html">【特集】黒炎の支配者がなぜ高い？定価の約4倍</a>'


def process(path: Path, prefix: str) -> bool:
    content = path.read_text(encoding="utf-8")
    orig = content

    left_marker = LEFT_NAV_MARKER_BOX if prefix == '../' else LEFT_NAV_MARKER_ROOT
    left_add = LEFT_NAV_ADD_BOX if prefix == '../' else LEFT_NAV_ADD_ROOT
    mobile_marker = MOBILE_MARKER_BOX if prefix == '../' else MOBILE_MARKER_ROOT
    mobile_add = MOBILE_ADD_BOX if prefix == '../' else MOBILE_ADD_ROOT

    # Left nav: add after inferno-x-spotlight entry (if not already present)
    if left_add not in content and left_marker in content:
        content = content.replace(left_marker, left_marker + '\n' + left_add, 1)

    # Mobile footer nav: add after inferno-x-spotlight entry (if not already present)
    if mobile_add not in content and mobile_marker in content:
        content = content.replace(mobile_marker, mobile_marker + '\n    ' + mobile_add, 1)

    if content != orig:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    ok = 0
    # Root articles
    for fname in ROOT_ARTICLES:
        p = ROOT / fname
        if not p.exists(): continue
        if process(p, prefix=''):
            ok += 1; print(f"OK: {fname}")

    # box-template + box/*
    for p in [ROOT / "box-template.html", *sorted((ROOT / "box").glob("*.html"))]:
        if p.exists() and process(p, prefix='../'):
            ok += 1; print(f"OK: {p.relative_to(ROOT)}")

    # weekly/*
    for p in sorted((ROOT / "weekly").glob("*.html")):
        if process(p, prefix='../'):
            ok += 1; print(f"OK: {p.relative_to(ROOT)}")

    # New 11 articles — they already have the nav section correctly
    # But ensure consistency by processing them too
    new_articles = [
        "kokuen-spotlight.html", "erika-sar-guide.html",
        "lizardon-sar-kokuen-guide.html", "mega-lizardon-x-guide.html",
        "lizardon-box-guide.html", "zeppan-ranking-2026-03.html",
        "mega-pack-compare.html", "masterball-mirror-guide.html",
        "pigeot-sar-guide.html", "kokuen-atari-guide.html",
        "kokuen-vs-rocket.html",
    ]
    for fname in new_articles:
        p = ROOT / fname
        if p.exists() and process(p, prefix=''):
            ok += 1; print(f"OK: {fname}")

    print(f"\n=== {ok} files patched ===")


if __name__ == "__main__":
    main()
