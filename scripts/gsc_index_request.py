"""Request Google indexing for URLs that Search Console reports as not indexed.

Google blocks Playwright's own browser launch, so a real chrome.exe is started
with a remote debugging port and attached over CDP (see cart-bot/sites/edion.py).
The Google session lives in a dedicated profile that must be logged in once by
hand via --login.

Usage:
    python scripts/gsc_index_request.py             # 上限まで送信
    python scripts/gsc_index_request.py --dry-run   # 対象URLを出すだけ
    python scripts/gsc_index_request.py --login     # 初回ログイン用にChromeだけ起動
    python scripts/gsc_index_request.py --limit 3   # 件数を絞って試す
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PROPERTY = "https://pokeca-box-hikaku.com/"
PENDING_FILE = ROOT / "data" / "gsc_pending.csv"
STATE_FILE = ROOT / "data" / "gsc_requested.json"
PROFILE_DIR = ROOT / "sessions" / "gsc_chrome"
LOG_FILE = ROOT / "data" / "gsc_index_request.log"

# 14件目で「割り当て量を超えています」が出るため実測上限は13件/日
DAILY_LIMIT = 13
# 一度通したURLを再申請するまでの日数
REQUEUE_DAYS = 60
CDP_PORT = int(os.environ.get("GSC_CDP_PORT", "9223"))
WEBHOOK = os.environ.get("GSC_DISCORD_WEBHOOK", "")
JST = timezone(timedelta(hours=9))

CONSOLE_URL = (
    "https://search.google.com/search-console"
    f"?resource_id={urllib.parse.quote(PROPERTY, safe='')}"
)
REQUEST_LABEL = "インデックス登録をリクエスト"
QUOTA_TEXT = "割り当て量を超えています"
ALREADY_TEXT = "URL は Google に登録されています"


def log(message: str) -> None:
    stamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def notify(message: str) -> None:
    if not WEBHOOK:
        return
    payload = json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=15).close()
    except OSError as exc:
        log(f"discord notify failed: {exc}")


def find_chrome_exe() -> str:
    for path in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if os.path.exists(path):
            return path
    raise SystemExit("chrome.exe not found")


def wait_for_port(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def launch_chrome(port: int) -> subprocess.Popen:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    args = [
        find_chrome_exe(),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--disable-popup-blocking",
        "--lang=ja-JP",
        "--window-size=1400,900",
    ]
    return subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def close_chrome(proc: subprocess.Popen) -> None:
    # terminate()はTerminateProcess相当でCookieが書き戻されないため、まずWM_CLOSEを送る
    subprocess.run(
        ["taskkill", "/PID", str(proc.pid), "/T"], capture_output=True, check=False
    )
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.terminate()


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
    return sum(1 for entry in state.values() if entry.get("requested_at", "")[:10] == today)


def pick_targets(
    pending: list[tuple[str, int]], state: dict[str, dict], limit: int
) -> list[str]:
    fresh_after = datetime.now(JST) - timedelta(days=REQUEUE_DAYS)
    targets: list[tuple[int, str]] = []
    for url, priority in pending:
        entry = state.get(url)
        if entry:
            try:
                stamp = datetime.fromisoformat(entry["requested_at"])
            except (KeyError, ValueError):
                stamp = None
            if stamp and stamp > fresh_after and entry.get("result") != "failed":
                continue
        targets.append((priority, url))
    targets.sort(key=lambda item: item[0])
    return [url for _, url in targets[:limit]]


def open_console(page: Page) -> None:
    page.goto(CONSOLE_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(6_000)
    if "accounts.google.com" in page.url:
        raise SystemExit("not signed in — run with --login first")


def search_box(page: Page):
    for selector in (
        "input[aria-label*='検査']",
        "input[placeholder*='検査']",
        "input[type='text']",
    ):
        box = page.locator(selector).first
        if box.count() and box.is_visible():
            return box
    raise RuntimeError("URL inspection box not found")


def inspect_and_request(page: Page, url: str) -> str:
    box = search_box(page)
    box.click()
    page.keyboard.press("Delete")
    page.keyboard.type(url, delay=25)
    page.keyboard.press("Enter")
    page.wait_for_timeout(12_000)

    body = page.inner_text("body")
    if QUOTA_TEXT in body:
        return "quota"

    button = page.get_by_text(REQUEST_LABEL, exact=False).first
    try:
        button.wait_for(state="visible", timeout=20_000)
    except PlaywrightTimeout:
        return "already" if ALREADY_TEXT in body else "failed"

    button.click()
    page.wait_for_timeout(30_000)
    body = page.inner_text("body")
    page.keyboard.press("Escape")
    page.wait_for_timeout(3_000)

    if QUOTA_TEXT in body:
        return "quota"
    return "requested"


def run(limit: int, dry_run: bool) -> int:
    pending = load_pending()
    state = load_state()
    already = sent_today(state)
    room = max(0, min(limit, DAILY_LIMIT - already))
    if room == 0:
        log(f"daily limit reached ({already}/{DAILY_LIMIT})")
        return 0

    targets = pick_targets(pending, state, room)
    if not targets:
        log("nothing left to request")
        return 0

    log(f"{len(targets)} target(s), {already} already sent today")
    for url in targets:
        log(f"  {url}")
    if dry_run:
        return 0

    chrome = launch_chrome(CDP_PORT)
    if not wait_for_port(CDP_PORT):
        close_chrome(chrome)
        raise SystemExit("chrome debug port did not open")

    requested = 0
    stopped = ""
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            open_console(page)

            for url in targets:
                try:
                    result = inspect_and_request(page, url)
                except (PlaywrightTimeout, RuntimeError) as exc:
                    result = "failed"
                    log(f"{url} -> error: {exc}")
                log(f"{url} -> {result}")
                state[url] = {
                    "requested_at": datetime.now(JST).isoformat(timespec="seconds"),
                    "result": result,
                }
                save_state(state)
                if result == "quota":
                    stopped = "quota exceeded"
                    break
                if result == "requested":
                    requested += 1
                page.wait_for_timeout(5_000)
            browser.close()
    finally:
        close_chrome(chrome)

    remaining = len(pick_targets(pending, state, 999))
    summary = (
        f"GSC索引リクエスト: {requested}件送信 / 残り{remaining}件"
        + (f" ({stopped})" if stopped else "")
    )
    log(summary)
    notify(summary)
    return requested


def login_mode(timeout: int = 900) -> None:
    chrome = launch_chrome(CDP_PORT)
    if not wait_for_port(CDP_PORT):
        close_chrome(chrome)
        raise SystemExit("chrome debug port did not open")

    log(f"profile: {PROFILE_DIR}")
    log("開いたChromeでGoogleにログインしてください（完了を自動検出します）")
    deadline = time.time() + timeout
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(CONSOLE_URL, wait_until="domcontentloaded", timeout=60_000)
            while time.time() < deadline:
                page.wait_for_timeout(5_000)
                if "accounts.google.com" in page.url:
                    continue
                if "search-console" in page.url:
                    log("ログインを確認しました")
                    break
            else:
                log("タイムアウト: ログインを確認できませんでした")
            browser.close()
    finally:
        close_chrome(chrome)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--login", action="store_true")
    parser.add_argument("--limit", type=int, default=DAILY_LIMIT)
    args = parser.parse_args()

    if args.login:
        login_mode()
        return
    run(args.limit, args.dry_run)


if __name__ == "__main__":
    main()
