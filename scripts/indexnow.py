"""Submit URLs to IndexNow (Bing / Yahoo / Seznam / Naver).

The API key is auto-detected from the 32-char hex .txt file in the project root,
which is also the public key file IndexNow verifies against.

Usage:
    python scripts/indexnow.py storm-emeralda-spotlight.html index.html
    python scripts/indexnow.py --sitemap
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "pokeca-box-hikaku.com"
BASE = f"https://{HOST}"
ENDPOINT = "https://api.indexnow.org/indexnow"


def find_key() -> str:
    for path in ROOT.glob("*.txt"):
        if re.fullmatch(r"[0-9a-f]{32}", path.stem):
            return path.stem
    raise SystemExit("IndexNow key file not found in project root")


def sitemap_urls() -> list[str]:
    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>(.*?)</loc>", text)


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

    key = find_key()
    urls = sitemap_urls() if args[0] == "--sitemap" else [to_url(a) for a in args]

    print(f"key={key}")
    print(f"submitting {len(urls)} URLs")
    for u in urls[:10]:
        print(f"  {u}")
    if len(urls) > 10:
        print(f"  ... and {len(urls) - 10} more")

    status = submit(urls, key)
    print(f"HTTP {status}")
    if status in (200, 202):
        print("accepted")
    else:
        raise SystemExit(f"unexpected status: {status}")


if __name__ == "__main__":
    main()
