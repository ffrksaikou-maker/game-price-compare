#!/usr/bin/env python3
"""サイト内の「N店舗」表記を、実際の掲載店舗数に合わせる。

店舗を足すたびに記事中の「最大9店舗から自動取得」のような表記が置き去りになり、
実態と食い違う。テンプレートの店舗配列(const S=[...])を唯一の基準にして、
決まった言い回しだけを機械的に直す。

**数字だけを見て置換しない。** 次のような紛らわしい表記があるため、
置換するフレーズをホワイトリストで限定している:
  - 「1店舗(カードラッシュ)が提示する買取価格」… カード相場のソース説明。触らない
  - 「10店舗以上の平均値を掲載している他サイト」… 他サイトの話。触らない
  - 「当サイトでは7店舗で買取掲載が確認できており」… 商品ごとの実数。generatorが毎回入れる

使い方:
    python -m scripts.sync_shop_counts --check   # 差分を表示するだけ
    python -m scripts.sync_shop_counts           # 実際に書き換える
"""
from __future__ import annotations

import argparse
import glob
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ジャンルごとの「店舗数の基準になるテンプレート」
TEMPLATES = {
    "pokeca": "template.html",
    "onepiece": "onepiece-template.html",
    "dragonball": "dragonball-template.html",
    "beyblade": "beyblade-template.html",
}

# 置換してよい言い回しだけを列挙する。{n} が店舗数に置き換わる。
# (正規表現, 置換後) — 正規表現の (\d+) が数字部分。
PHRASES = [
    (r"最大(\d+)店舗", "最大{n}店舗"),
    (r"(\d+)店舗比較", "{n}店舗比較"),
    (r"(\d+)店舗の最高値", "{n}店舗の最高値"),
    (r"(\d+)店舗の最高買取価格", "{n}店舗の最高買取価格"),
    (r"(\d+)店舗の実データ", "{n}店舗の実データ"),
    (r"(\d+)店舗データ", "{n}店舗データ"),
    (r"(\d+)店舗の買取価格データ", "{n}店舗の買取価格データ"),
    (r"(\d+)店舗横断", "{n}店舗横断"),
    (r"(\d+)店舗の公式サイトから", "{n}店舗の公式サイトから"),
    (r"(\d+)店舗から自動取得", "{n}店舗から自動取得"),
    (r"(\d+)店舗から毎日自動取得", "{n}店舗から毎日自動取得"),
    (r"(\d+)店舗から収集", "{n}店舗から収集"),
    (r"(\d+)店舗から毎日自動収集", "{n}店舗から毎日自動収集"),
    (r"(\d+)店舗で横断比較", "{n}店舗で横断比較"),
    (r"(\d+)店舗で比較", "{n}店舗で比較"),
    (r"(\d+)店舗最新比較", "{n}店舗最新比較"),
]

# この文字列を含む行は触らない(他サイトの話・カード相場のソース説明など)
SKIP_LINE_MARKERS = (
    "カードラッシュ",
    "他サイト",
    "平均値を掲載",
    "買取掲載が確認",
    'class="value"',
)


def shop_count(genre: str) -> int:
    """テンプレートの const S=[...] から実際の掲載店舗数を数える。"""
    path = ROOT / TEMPLATES[genre]
    if not path.exists():
        return 0
    m = re.search(r"const S=\[(.*?)\];", path.read_text(encoding="utf-8"))
    if not m:
        return 0
    return len([x for x in m.group(1).split(",") if x.strip()])


def genre_of(rel: str) -> str:
    """パスからジャンルを決める。テンプレート類は名前で判定する。"""
    name = rel.rsplit("/", 1)[-1]
    if rel.startswith("onepiece/") or name.startswith("onepiece") or "onepiece" in name:
        return "onepiece"
    if rel.startswith("dragonball/") or name.startswith("dragonball") or "dragonball" in name:
        return "dragonball"
    if name.startswith("beyblade") or "beyblade" in name:
        return "beyblade"
    return "pokeca"


# 記事はビルダー(Pythonソース)から生成されるため、HTMLだけ直しても次のビルドで戻る。
# ただしCIにソースコードを書き換えさせるのは事故のもとなので、既定はHTMLのみ。
# 店舗を増減したときは開発側で --include-source を付けて一度流す。
HTML_PATTERNS = ("*.html", "onepiece/*.html", "dragonball/*.html",
                 "box/*.html", "onepiece/box/*.html", "dragonball/box/*.html",
                 "shop/*.html", "weekly/*.html")
SOURCE_PATTERNS = ("scraper/build_*.py", "scraper/generator*.py",
                   "scraper/article_data_onepiece.py")


def target_files(include_source: bool = False) -> list[str]:
    out: list[str] = []
    for pat in HTML_PATTERNS + (SOURCE_PATTERNS if include_source else ()):
        out.extend(sorted(glob.glob(str(ROOT / pat))))
    return [str(Path(p).relative_to(ROOT)).replace("\\", "/") for p in out]


def fix_text(text: str, n: int) -> tuple[str, int]:
    changed = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if any(mk in line for mk in SKIP_LINE_MARKERS):
            continue
        new = line
        for pat, rep in PHRASES:
            new = re.sub(pat, lambda m, r=rep: r.format(n=n), new)
        if new != line:
            changed += len(re.findall(r"\d+店舗", line))
            lines[i] = new
    return "\n".join(lines), changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="書き換えずに差分だけ出す")
    ap.add_argument("--include-source", action="store_true",
                    help="scraper/ のビルダーソースも対象にする(店舗を増減したとき)")
    args = ap.parse_args()

    counts = {g: shop_count(g) for g in TEMPLATES}
    print("店舗数:", ", ".join(f"{g}={c}" for g, c in counts.items()))
    if not all(counts[g] for g in ("pokeca", "onepiece")):
        print("テンプレートから店舗数を取得できないため中止", file=sys.stderr)
        return 1

    total_files = total_hits = 0
    for rel in target_files(args.include_source):
        n = counts[genre_of(rel)]
        if not n:
            continue
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        new, hits = fix_text(text, n)
        if new == text:
            continue
        total_files += 1
        total_hits += hits
        if args.check:
            print(f"  {rel}: {hits}箇所 -> {n}店舗")
        else:
            io.open(path, "w", encoding="utf-8", newline="").write(new)
    verb = "要修正" if args.check else "修正"
    print(f"{verb}: {total_files}ファイル / {total_hits}箇所")
    return 0


if __name__ == "__main__":
    sys.exit(main())
