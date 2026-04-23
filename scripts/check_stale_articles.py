"""Report articles whose lastmod is >= N days old (default 30).

Reads sitemap.xml and prints a prioritized update list.

Usage:
  python scripts/check_stale_articles.py              # 30 days threshold
  python scripts/check_stale_articles.py --days 60    # custom threshold
  python scripts/check_stale_articles.py --warn 14    # warn tier (14-30d)
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Force UTF-8 stdout on Windows so emoji/Japanese print correctly
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(__file__).resolve().parent.parent
SITEMAP = ROOT / "sitemap.xml"

# Evergreen pages (更新不要) — ignore
EVERGREEN = {
    "/privacy.html",
    "/",  # index is auto-regenerated
    "/ranking.html",  # auto-regenerated
    "/weekly/",
    "/sv-box-list.html",
    "/mega-box-list.html",
    "/ss-box-list.html",
}

# Auto-managed prefixes (box/, weekly/, etc.) — also ignore
AUTO_PREFIXES = ("/box/", "/weekly/")


def parse_sitemap() -> list[tuple[str, date]]:
    """Return [(path, lastmod_date), ...]."""
    if not SITEMAP.exists():
        print("ERROR: sitemap.xml not found", file=sys.stderr)
        sys.exit(1)
    text = SITEMAP.read_text(encoding="utf-8")
    entries: list[tuple[str, date]] = []
    url_blocks = re.findall(r"<url>(.*?)</url>", text, re.DOTALL)
    base = "https://pokeca-box-hikaku.com"
    for blk in url_blocks:
        loc_m = re.search(r"<loc>([^<]+)</loc>", blk)
        mod_m = re.search(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", blk)
        if not loc_m or not mod_m:
            continue
        path = loc_m.group(1).removeprefix(base)
        try:
            d = datetime.strptime(mod_m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        entries.append((path, d))
    return entries


def classify(entries: list[tuple[str, date]], stale_days: int, warn_days: int) -> dict:
    today = date.today()
    groups = {"stale": [], "warn": [], "ok": [], "skip": []}
    for path, d in entries:
        if path in EVERGREEN or any(path.startswith(p) for p in AUTO_PREFIXES):
            groups["skip"].append((path, d, (today - d).days))
            continue
        age = (today - d).days
        if age >= stale_days:
            groups["stale"].append((path, d, age))
        elif age >= warn_days:
            groups["warn"].append((path, d, age))
        else:
            groups["ok"].append((path, d, age))
    for k in groups:
        groups[k].sort(key=lambda x: x[2], reverse=True)
    return groups


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30, help="stale threshold (days)")
    ap.add_argument("--warn", type=int, default=14, help="warn threshold (days)")
    args = ap.parse_args()

    entries = parse_sitemap()
    groups = classify(entries, args.days, args.warn)

    print(f"=== 古記事レポート (today={date.today()}) ===")
    print(f"stale >= {args.days}日: {len(groups['stale'])}件")
    print(f"warn  >= {args.warn}日: {len(groups['warn'])}件")
    print(f"ok    <  {args.warn}日: {len(groups['ok'])}件")
    print(f"(skip 自動更新): {len(groups['skip'])}件")
    print()

    if groups["stale"]:
        print("🔴 要更新 (>= {}日)".format(args.days))
        for path, d, age in groups["stale"]:
            print(f"  {age:3d}日  {d}  {path}")
        print()
    if groups["warn"]:
        print("🟡 警告 ({}〜{}日)".format(args.warn, args.days - 1))
        for path, d, age in groups["warn"]:
            print(f"  {age:3d}日  {d}  {path}")
        print()
    if not groups["stale"] and not groups["warn"]:
        print("✅ 全記事OK")


if __name__ == "__main__":
    main()
