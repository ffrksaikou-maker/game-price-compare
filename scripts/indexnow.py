"""Submit URLs to IndexNow (Bing / Yahoo / Seznam / Naver).

The API key is auto-detected from the 32-char hex .txt file in the project root,
which is also the public key file IndexNow verifies against.

Usage:
    python scripts/indexnow.py storm-emeralda-spotlight.html index.html
    python scripts/indexnow.py --new       # sitemapのlastmodが前回送信時から変わったURLのみ (CI用)
    python scripts/indexnow.py --sitemap   # 全件
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "pokeca-box-hikaku.com"
BASE = f"https://{HOST}"
ENDPOINT = "https://api.indexnow.org/indexnow"
STATE_FILE = ROOT / "data" / "indexnow_sent.json"
# 1回の送信で送る上限。lastmodを一斉に書き換えたときに全件を投げないためのブレーキ
MAX_PER_RUN = 200


def find_key() -> str:
    for path in ROOT.glob("*.txt"):
        if re.fullmatch(r"[0-9a-f]{32}", path.stem):
            return path.stem
    raise SystemExit("IndexNow key file not found in project root")


def sitemap_entries() -> list[tuple[str, str]]:
    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>", text)


def load_state() -> dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )


def to_url(arg: str) -> str:
    if arg.startswith("http"):
        return arg
    return f"{BASE}/{arg.lstrip('/')}"


def submit(urls: list[str], key: str) -> int:
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{BASE}/{key}.txt",
        "urlList": urls,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.status


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)

    mode = args[0]
    entries = sitemap_entries() if mode in ("--new", "--sitemap") else []
    state: dict[str, str] = {}

    if mode == "--new":
        state = load_state()
        urls = [url for url, mod in entries if state.get(url) != mod]
        if not urls:
            print("no updated URLs since last submission")
            return
        if len(urls) > MAX_PER_RUN:
            print(f"{len(urls)} updated URLs, capping at {MAX_PER_RUN} this run")
            urls = urls[:MAX_PER_RUN]
    elif mode == "--sitemap":
        urls = [url for url, _ in entries]
    else:
        urls = [to_url(a) for a in args]

    key = find_key()
    print(f"key={key}")
    print(f"submitting {len(urls)} URLs")
    for url in urls[:10]:
        print(f"  {url}")
    if len(urls) > 10:
        print(f"  ... and {len(urls) - 10} more")

    try:
        status = submit(urls, key)
    except urllib.error.URLError as exc:
        raise SystemExit(f"submission failed: {exc}")

    print(f"HTTP {status}")
    if status not in (200, 202):
        raise SystemExit(f"unexpected status: {status}")
    print("accepted")

    if mode == "--new":
        sent = set(urls)
        state.update({url: mod for url, mod in entries if url in sent})
        save_state(state)
        print(f"state saved: {len(state)} URLs tracked")


if __name__ == "__main__":
    main()
