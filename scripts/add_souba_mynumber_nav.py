"""Insert the souba-mynumber-2026 article link into article-nav and mobile-footer-nav
across all pages. Idempotent: skips files that already contain the link.

Inserts right after the '上昇ランキング' (ranking.html) entry in both the left
article-nav and the mobile-footer-nav '一般記事' section.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK_SLUG = "souba-mynumber-2026.html"
LABEL = "📰 相場下落・膠着とマイナンバー"


def process(path: Path, prefix: str) -> bool:
    content = path.read_text(encoding="utf-8")
    if LINK_SLUG in content:
        return False
    anchor = f'{prefix}ranking.html">上昇ランキング</a>'
    if anchor not in content:
        return False
    new = anchor + f'\n<a href="{prefix}{LINK_SLUG}">{LABEL}</a>'
    content = content.replace(anchor, new)
    path.write_text(content, encoding="utf-8")
    return True


def main():
    ok = skip = 0
    targets = []
    # root articles
    for p in sorted(ROOT.glob("*.html")):
        targets.append((p, ""))
    # box-template + box/*.html
    targets.append((ROOT / "box-template.html", "../"))
    for p in sorted((ROOT / "box").glob("*.html")):
        targets.append((p, "../"))
    # weekly/*.html
    for p in sorted((ROOT / "weekly").glob("*.html")):
        targets.append((p, "../"))

    for p, prefix in targets:
        if not p.exists():
            continue
        if process(p, prefix):
            ok += 1
        else:
            skip += 1
    print(f"=== updated {ok}, skipped {skip} ===")


if __name__ == "__main__":
    main()
