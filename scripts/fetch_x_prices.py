#!/usr/bin/env python3
"""XからBOX買取価格を取り、data/x_state/*.json を更新する(ローカル実行用)。

なぜCIでやらないか:
    GitHub Actions からヘッドレスChromeでXを開くと Cloudflare のボット検証
    (「x.com セキュリティ検証の実行」)で止まり、タイムラインに到達できない。
    2026-09-09のCIログで確認済み。Cookieの失効ではない。
    家庭回線の実ブラウザなら通るので、X取得だけローカルに寄せる。

仕組み:
    専用のChromeプロファイル(X_PROFILE_DIR)を使う。初回だけ手でXにログインすれば、
    以後はそのプロファイルにセッションが残るのでCookieの受け渡しが要らない。
    取得結果は各スクレイパーが使うのと同じ data/x_state/<shop>.json に書くので、
    CI側は「取得に失敗したらキャッシュを返す」既存の挙動のまま最新値を拾える。

使い方:
    python -m scripts.fetch_x_prices --login    # 初回: ブラウザが開くのでXにログイン
    python -m scripts.fetch_x_prices            # 取得してstateを更新
    python -m scripts.fetch_x_prices --push     # 取得してgitにcommit/pushまで
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Windowsのコンソールは既定がcp932で日本語が化けるため、UTF-8に寄せる
for _s in (sys.stdout, sys.stderr):
    try:
        if _s.encoding and _s.encoding.lower() not in ("utf-8", "utf8"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

X_PROFILE_DIR = ROOT.parent / "x-scraper-profile"
STATE_DIR = ROOT / "data" / "x_state"

# (アカウント, state名, 検索キーワード)
# プロフィールを流し読みすると価格表ツイートが下に流れて届かない。
# ジャンルごとに from: 検索で狙い撃ちするほうが確実に最新の表を拾える。
ACCOUNTS = [
    ("kaitoriexpo", "kaitoriexpo", ["ドラゴンボール", "ポケカ", "ワンピース"]),
]


def _launch(p, headless: bool):
    """実プロファイルでChromeを起動する。Cloudflare対策で実ブラウザを使う。

    表示して使うとき(ログイン時)に縦1800pxを指定すると画面からはみ出して
    入力欄に届かなくなるため、そのときはウィンドウ任せにする。
    """
    kwargs = dict(
        user_data_dir=str(X_PROFILE_DIR),
        channel="chrome",
        headless=headless,
        locale="ja-JP",
        args=["--disable-blink-features=AutomationControlled",
              "--window-size=1280,900"],
    )
    if headless:
        # ヘッドレスなら縦を長く取って一度に多くのツイートを読む
        kwargs["viewport"] = {"width": 1280, "height": 1800}
    else:
        kwargs["no_viewport"] = True
    return p.chromium.launch_persistent_context(**kwargs)


def do_login() -> int:
    """初回セットアップ: ブラウザを開いたままにするので手でログインする。"""
    from playwright.sync_api import sync_playwright

    X_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"プロファイル: {X_PROFILE_DIR}", flush=True)
    print("開いたブラウザでXにログインしてください。完了したらEnterを押します。")
    with sync_playwright() as p:
        ctx = _launch(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=60000)
        print("ログインの完了を自動で検知します(最大5分)。ブラウザは閉じないでください。", flush=True)
        # URLでの判定は、別タブで操作されたりリダイレクトの形が変わると外す。
        # ログインすれば auth_token Cookie が必ず入るので、それを見る。
        ok = False
        for i in range(60):
            time.sleep(5)
            try:
                names = {c["name"] for c in ctx.cookies("https://x.com")}
                if "auth_token" in names:
                    ok = True
                    break
            except Exception:
                break
            if i % 6 == 5:
                print(f"  待機中... {(i + 1) * 5}秒", flush=True)
        if not ok:
            print("ログインを検知できませんでした。もう一度実行してください。")
            ctx.close()
            return 1
        print("ログインを検知。タイムラインを確認します。")
        page.goto("https://x.com/kaitoriexpo", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        n = len(page.query_selector_all('article[data-testid="tweet"]'))
        print(f"タイムライン取得テスト: article {n} 件")
        if n:
            print("セットアップ完了。次は `python -m scripts.fetch_x_prices` で取得できます。")
        ctx.close()
    return 0 if n else 1


def fetch_texts(username: str, headless: bool, url: str | None = None) -> list[str]:
    from playwright.sync_api import sync_playwright

    texts: list[str] = []
    with sync_playwright() as p:
        ctx = _launch(p, headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(url or f"https://x.com/{username}",
                      wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_selector('article[data-testid="tweet"]', timeout=25000)
            except Exception:
                title = page.title()[:60]
                body = page.inner_text("body")[:150].replace("\n", " ")
                print(f"  タイムライン未取得 title={title} body={body}")
                ctx.close()
                return []
            page.wait_for_timeout(1500)
            # Xのタイムラインは仮想スクロールで、下へ進むと上のツイートがDOMから
            # 消える。まとめて取ると取りこぼすので、スクロールしながら毎回集める。
            seen: dict[str, str] = {}
            # f=live は新しい順。深追いすると古い価格表まで拾うので浅くする。
            for _ in range(2):
                chunk = page.evaluate(
                    """() => Array.from(
                        document.querySelectorAll('article[data-testid="tweet"]')
                    ).map(a => a.innerText)"""
                ) or []
                for t in chunk:
                    if t and t not in seen:
                        seen[t] = t
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(1100)
            texts = list(seen.values())
        finally:
            ctx.close()
    return texts


def update_state(name: str, items: dict) -> int:
    path = STATE_DIR / f"{name}.json"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {}
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state = {}
    cached = state.get("items", {})
    before = len(cached)
    cached.update(items)
    state["items"] = cached
    state["last_check"] = int(time.time())
    state["last_found"] = len(items)
    state["source"] = "local"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(cached) - before


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", action="store_true", help="初回セットアップ(手動ログイン)")
    ap.add_argument("--show", action="store_true", help="ブラウザを表示して実行")
    ap.add_argument("--push", action="store_true", help="更新をgitにcommit/pushする")
    args = ap.parse_args()

    if args.login:
        return do_login()

    if not X_PROFILE_DIR.exists():
        print("プロファイルが無い。先に --login を実行してください。", file=sys.stderr)
        return 1

    from scraper.shops.kaitoriexpo import parse_tweet_text

    total_new = 0
    from urllib.parse import quote

    for username, state_name, keywords in ACCOUNTS:
        print(f"--- @{username} ---", flush=True)
        texts: list[str] = []
        for kw in keywords:
            q = quote(f"from:{username} {kw}")
            got = fetch_texts(username, headless=not args.show,
                              url=f"https://x.com/search?q={q}&f=live")
            print(f"  [{kw}] {len(got)}ツイート", flush=True)
            texts.extend(got)
        if not texts:
            print("  ツイートを取得できなかった")
            continue
        # texts は新しい順。最初に出た値を採用する(先勝ち)。max だと
        # 過去の高かった頃の価格表が残り続けてしまう。
        found: dict = {}
        for t in texts:
            for n, v in parse_tweet_text(t).items():
                found.setdefault(n, v)
        added = update_state(state_name, found)
        total_new += len(found)
        print(f"  ツイート{len(texts)}件 / 価格{len(found)}件 (新規{added})")
        for n, v in list(found.items())[:8]:
            print(f"     {n[:40]:42} {v:>7,}")

    if args.push and total_new:
        subprocess.run(["git", "add", "data/x_state"], cwd=ROOT, check=False)
        r = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=ROOT)
        if r.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m",
                 f"X価格を更新(ローカル取得 {time.strftime('%Y-%m-%d %H:%M')})"],
                cwd=ROOT, check=False)
            subprocess.run(["git", "pull", "--rebase", "-q"], cwd=ROOT, check=False)
            subprocess.run(["git", "push", "-q"], cwd=ROOT, check=False)
            print("git push 済み")
        else:
            print("差分なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
