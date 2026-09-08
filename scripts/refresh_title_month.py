"""タイトルの【YYYY年M月最新】を現在の年月に更新する。

検索結果に古い月が出ているとクリック率が落ちる。実測では同じ
「スタートデッキ100 当たり」需要で、日付なしの記事がCTR11.3%なのに対し
「【2026年8月最新】」付き(9月時点)は4.1%まで落ちていた。

CIから --stage 付きで呼ぶと、書き換えたファイルを git add まで行う。
月が変わらなければ書き換えは発生しないので、実質は月1回だけ差分が出る。
"""
import argparse
import io
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

PATTERN = re.compile(r"【(20\d{2})年(\d{1,2})月最新】")
SKIP_DIRS = {".git", "node_modules", "scripts", ".github", "assets", "img"}
# 生成元。ここを直さないと次のビルドで古い月に戻る
EXTRA_FILES = ["scraper/article_data_onepiece.py"]


def _targets(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".html"):
                yield os.path.join(dirpath, name)
    for rel in EXTRA_FILES:
        path = os.path.join(root, rel)
        if os.path.exists(path):
            yield path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="store_true", help="書き換えたファイルを git add する")
    ap.add_argument("--dry-run", action="store_true", help="書き換えずに対象だけ出す")
    args = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    now = datetime.now(JST)
    replacement = f"【{now.year}年{now.month}月最新】"

    changed = []
    total = 0
    for path in _targets(root):
        try:
            text = io.open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if PATTERN.search(text) is None:
            continue
        new_text, n = PATTERN.subn(replacement, text)
        if new_text == text:
            continue
        total += n
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        changed.append(rel)
        if not args.dry_run:
            io.open(path, "w", encoding="utf-8", newline="").write(new_text)

    if not changed:
        print(f"タイトルの月は最新です ({replacement})")
        return 0

    print(f"{replacement} に更新: {len(changed)} ファイル / {total} 箇所")
    for rel in changed[:10]:
        print(f"  {rel}")
    if len(changed) > 10:
        print(f"  ... 他 {len(changed) - 10} ファイル")

    if args.stage and not args.dry_run:
        subprocess.run(["git", "add", "--"] + changed, cwd=root, check=True)
        print(f"git add: {len(changed)} ファイル")
    return 0


if __name__ == "__main__":
    sys.exit(main())
