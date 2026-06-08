"""Rename the ranking link/labels site-wide from '上昇ランキング' to
'(週間)価格変化ランキング' so the section reflects both gainers and decliners.

Only touches anchor labels / headings that point to the ranking concept.
Leaves '急上昇'(weekly hot article) wording untouched.
Idempotent.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Ordered: specific compounds first, bare label last.
REPLACEMENTS = [
    ("週間上昇ランキング", "週間価格変化ランキング"),
    ("週間 上昇ランキング", "週間 価格変化ランキング"),
    ("日次の上昇ランキング", "日次の価格変化ランキング"),
    ("上昇ランキングに戻る", "価格変化ランキングに戻る"),
    (">📈 上昇ランキング</a>", ">📊 週間価格変化ランキング</a>"),
    (">上昇ランキング</a>", ">📊 週間価格変化ランキング</a>"),
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
    files = (
        list(ROOT.glob("*.html"))
        + list((ROOT / "box").glob("*.html"))
        + list((ROOT / "weekly").glob("*.html"))
    )
    for p in files:
        if process(p):
            ok += 1
    print(f"=== renamed in {ok} files ===")


if __name__ == "__main__":
    main()
