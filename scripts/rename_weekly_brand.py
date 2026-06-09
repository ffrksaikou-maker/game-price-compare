"""Rename the weekly timeline brand from '急上昇' wording to '値動き/価格変化'
so it reflects both gainers and decliners.

Only touches brand/section LABEL strings — leaves factual body prose such as
'〜が急上昇した' / '台へ急上昇' / '週間急上昇1位' untouched.
Applied to all html + generator.py + weekly_article_template.py. Idempotent.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Order: more specific compounds first.
REPLACEMENTS = [
    ("BOX急上昇ランキング", "BOX値動きランキング"),
    ("今週の急上昇記事", "今週の値動き記事"),
    ("今週の急上昇ランキング", "今週の値動きランキング"),
    ("週間急上昇記事", "週間値動き記事"),
    ("週間急上昇ランキング", "週間値動きランキング"),
    ("週間急上昇アーカイブ", "週間値動きアーカイブ"),
    ("買取急上昇ランキング", "買取値動きランキング"),
    ("急上昇レポート", "値動きレポート"),
    ("急上昇情報", "値動き情報"),
    ("🔥 急上昇ランキング", "🔥 値動きランキング"),
    ("TOP急上昇:", "値動きTOP:"),
    ("急上昇TOP10", "価格変化ランキング"),
    ("準急上昇", "値上がり次点"),
]


def process(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    orig = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    if content != orig:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    ok = 0
    targets = (
        list(ROOT.glob("*.html"))
        + list((ROOT / "box").glob("*.html"))
        + list((ROOT / "weekly").glob("*.html"))
        + [ROOT / "scraper" / "generator.py", ROOT / "scripts" / "weekly_article_template.py"]
    )
    for p in targets:
        if p.exists() and process(p):
            ok += 1
    print(f"=== renamed in {ok} files ===")


if __name__ == "__main__":
    main()
