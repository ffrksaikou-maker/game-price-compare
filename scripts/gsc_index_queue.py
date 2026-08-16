"""Track which URLs still need a manual Search Console indexing request.

The requests themselves are made through the browser (claude-in-chrome); Google
blocks scripted sessions. This only decides what to submit next and remembers
what already went out.

Usage:
    python scripts/gsc_index_queue.py                     # 次に撃つ13件
    python scripts/gsc_index_queue.py --next 5
    python scripts/gsc_index_queue.py --status
    python scripts/gsc_index_queue.py --done kaitori-tips.html mega-pack-compare.html
    python scripts/gsc_index_queue.py --indexed kokuen-spotlight.html
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://pokeca-box-hikaku.com"
PENDING_FILE = ROOT / "data" / "gsc_pending.csv"
STATE_FILE = ROOT / "data" / "gsc_requested.json"

# 14件目で「割り当て量を超えています」が出るため実測上限は13件/日
DAILY_LIMIT = 13
# 申請しても入らなかったURLを再申請するまでの日数
REQUEUE_DAYS = 60
JST = timezone(timedelta(hours=9))


def to_url(arg: str) -> str:
    if arg.startswith("http"):
        return arg
    return f"{BASE}/{arg.lstrip('/')}"


def load_pending() -> list[tuple[str, int]]:
    if not PENDING_FILE.exists():
        raise SystemExit(f"pending list not found: {PENDING_FILE}")
    rows: list[tuple[str, int]] = []
    with PENDING_FILE.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("url") or "").strip()
            if not url:
                continue
            try:
                priority = int((row.get("priority") or "9").strip())
            except ValueError:
                priority = 9
            rows.append((url, priority))
    return rows


def load_state() -> dict[str, dict]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict[str, dict]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )


def sent_today(state: dict[str, dict]) -> int:
    today = datetime.now(JST).date().isoformat()
    return sum(
        1
        for entry in state.values()
        if entry.get("requested_at", "")[:10] == today
        and entry.get("result") == "requested"
    )


def remaining(pending: list[tuple[str, int]], state: dict[str, dict]) -> list[str]:
    fresh_after = datetime.now(JST) - timedelta(days=REQUEUE_DAYS)
    targets: list[tuple[int, str]] = []
    for url, priority in pending:
        entry = state.get(url)
        if entry:
            if entry.get("result") == "indexed":
                continue
            try:
                stamp = datetime.fromisoformat(entry["requested_at"])
            except (KeyError, ValueError):
                stamp = None
            if stamp and stamp > fresh_after:
                continue
        targets.append((priority, url))
    targets.sort(key=lambda item: item[0])
    return [url for _, url in targets]


def record(urls: list[str], result: str) -> None:
    state = load_state()
    stamp = datetime.now(JST).isoformat(timespec="seconds")
    for arg in urls:
        state[to_url(arg)] = {"requested_at": stamp, "result": result}
    save_state(state)
    print(f"recorded {len(urls)} URL(s) as {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--next", type=int, nargs="?", const=DAILY_LIMIT, default=None)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--done", nargs="+", metavar="URL")
    parser.add_argument("--indexed", nargs="+", metavar="URL")
    args = parser.parse_args()

    if args.done:
        record(args.done, "requested")
        return
    if args.indexed:
        record(args.indexed, "indexed")
        return

    pending = load_pending()
    state = load_state()
    left = remaining(pending, state)
    today = sent_today(state)

    if args.status:
        indexed = sum(1 for e in state.values() if e.get("result") == "indexed")
        requested = sum(1 for e in state.values() if e.get("result") == "requested")
        print(f"total     {len(pending)}")
        print(f"requested {requested}")
        print(f"indexed   {indexed}")
        print(f"remaining {len(left)}")
        print(f"today     {today}/{DAILY_LIMIT}")
        return

    room = max(0, min(args.next or DAILY_LIMIT, DAILY_LIMIT - today))
    if room == 0:
        print(f"daily limit reached ({today}/{DAILY_LIMIT})")
        return
    print(f"# {len(left)} remaining, {today}/{DAILY_LIMIT} sent today")
    for url in left[:room]:
        print(url)


if __name__ == "__main__":
    main()
