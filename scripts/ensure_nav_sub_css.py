"""Ensure .article-nav-sub CSS rule exists in every file that uses the class.

Articles with TOC have a different @media rule, so the earlier scripts couldn't
replace the CSS block cleanly. This adds the missing .article-nav-sub rule
inline after .article-nav a rules.

Idempotent.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CSS_RULE = '.article-nav-sub{font-size:12px;font-weight:700;margin:14px 0 6px;color:#b91c1c;padding-top:10px;border-top:1px solid var(--border)}\n'

# Insert the rule AFTER the .article-nav a:hover rule line (keeps CSS localized)
MARKER = '.article-nav a:hover{color:var(--accent);border-left-color:var(--accent)}'


def process(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    if 'article-nav-sub' not in content:
        return False  # not using the class
    if '.article-nav-sub{' in content:
        return False  # CSS already present
    if MARKER not in content:
        return False  # can't find insert point
    new = content.replace(MARKER, MARKER + '\n' + CSS_RULE.rstrip(), 1)
    path.write_text(new, encoding="utf-8")
    return True


def main():
    ok = 0
    targets = []
    for p in ROOT.glob("*.html"):
        targets.append(p)
    for p in (ROOT / "box").glob("*.html"):
        targets.append(p)
    for p in (ROOT / "weekly").glob("*.html"):
        targets.append(p)
    targets.append(ROOT / "box-template.html")

    seen = set()
    for p in targets:
        if p in seen: continue
        seen.add(p)
        if process(p):
            ok += 1
            print(f"OK: {p.relative_to(ROOT)}")
    print(f"\n=== {ok} files patched ===")


if __name__ == "__main__":
    main()
