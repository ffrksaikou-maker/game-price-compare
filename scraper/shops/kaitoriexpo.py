"""Scraper for 買取EXPO @kaitoriexpo on X.

買取EXPOはXに買取価格を**テキストで**投稿する。コレクト(@collect_tendo)と違い
画像ではないので、OCR(Claude Vision)は不要で本文をそのままパースできる。
ポケカ・ワンピース・ドラゴンボールを別々のツイートで出しており、
match_all_games が4マスターに通すので1スクレイパーで3ジャンルまかなえる。

1. Playwright で占い垢のCookieを使ってXにログイン状態でアクセス
2. https://x.com/kaitoriexpo の最新ツイート本文を収集
3. 本文をパースして {商品名: 価格} を作る
4. data/x_state/kaitoriexpo.json に保持(ツイートが流れても直近の値を保つ)

必要なシークレット:
- X_AUTH_TOKEN / X_CT0: 占い垢のCookie (Read-onlyで使用)
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

TARGET_USERNAME = "kaitoriexpo"
PROFILE_URL = f"https://x.com/{TARGET_USERNAME}"
STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "x_state" / "kaitoriexpo.json"

PRICE_RE = re.compile(r"^(.*?)\s*(?:box|BOX)?\s*([0-9][0-9,]*)\s*円\s*$")
# 「シュリ無」はシュリンクなし。当サイトはシュリンク付きBOXを扱うため除外する。
# 「〆切」は買取停止、「カートン」はBOX単価ではない。
EXCLUDE_WORDS = ("シュリ無", "シュリなし", "シュリンクなし", "〆切", "カートン", "シングル")
# 告知文から金額らしき数字を拾わないための除外
NOISE_WORDS = ("以上は着払い", "持ち込み", "記載商品", "現金可能", "件の表示",
               "買取価格", "リポスト", "いいね", "返信")
MIN_PRICE = 500
MAX_PRICE = 900000


def parse_tweet_text(text: str) -> dict[str, int]:
    """ツイート本文から {商品名: 価格} を取り出す。"""
    out: dict[str, int] = {}
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if any(w in line for w in EXCLUDE_WORDS) or any(w in line for w in NOISE_WORDS):
            continue
        m = PRICE_RE.match(line)
        if not m:
            continue
        name = re.sub(r"^[\W_]+", "", m.group(1), flags=re.UNICODE).strip()
        try:
            price = int(m.group(2).replace(",", ""))
        except ValueError:
            continue
        if not name or not (MIN_PRICE <= price <= MAX_PRICE):
            continue
        if price > out.get(name, 0):
            out[name] = price
    return out


class KaitoriExpoScraper(BaseScraper):
    shop_id = "kaitoriexpo"
    shop_name = "買取EXPO"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        import os

        auth_token = os.environ.get("X_AUTH_TOKEN")
        ct0 = os.environ.get("X_CT0")
        if not auth_token or not ct0:
            logger.warning("KaitoriExpo: X_AUTH_TOKEN/X_CT0 missing, using cache")
            return self._items_from_state(self._load_state())

        texts = self._fetch_recent_tweet_texts(auth_token, ct0)
        if not texts:
            logger.warning("KaitoriExpo: no tweets found, using cache")
            return self._items_from_state(self._load_state())

        found: dict[str, int] = {}
        for t in texts:
            for name, price in parse_tweet_text(t).items():
                if price > found.get(name, 0):
                    found[name] = price

        state = self._load_state()
        cached: dict = state.get("items", {})
        # ツイートが流れて見えなくなった商品も直近の値を保つ。
        # 同じ商品が再掲されたら新しい値で上書きする。
        cached.update(found)
        state["items"] = cached
        state["last_check"] = int(time.time())
        state["last_found"] = len(found)
        self._save_state(state)

        logger.info("KaitoriExpo: %d tweets, %d items parsed (%d cached total)",
                    len(texts), len(found), len(cached))
        return [ScrapedItem(name=n, price=p) for n, p in cached.items() if p > 0]

    # ----- helpers -----

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("KaitoriExpo: state file broken, starting fresh")
        return {}

    def _save_state(self, state: dict) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                              encoding="utf-8")

    def _items_from_state(self, state: dict) -> list[ScrapedItem]:
        return [ScrapedItem(name=n, price=p)
                for n, p in state.get("items", {}).items() if p > 0]

    def _fetch_recent_tweet_texts(self, auth_token: str, ct0: str) -> list[str]:
        """Playwrightで@kaitoriexpoの最新ツイート本文を収集する。"""
        from playwright.sync_api import sync_playwright

        texts: list[str] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=self.HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 1800},
                locale="ja-JP",
            )
            context.add_cookies([
                {"name": "auth_token", "value": auth_token, "domain": ".x.com",
                 "path": "/", "httpOnly": True, "secure": True, "sameSite": "Lax"},
                {"name": "ct0", "value": ct0, "domain": ".x.com",
                 "path": "/", "httpOnly": False, "secure": True, "sameSite": "Lax"},
            ])
            page = context.new_page()
            try:
                page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=30000)
                try:
                    page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
                except Exception:
                    logger.warning("KaitoriExpo: timeline not loaded (login expired?)")
                    browser.close()
                    return []
                page.wait_for_timeout(1500)
                # 価格表は長文で複数ツイートに分かれるため、少しスクロールして
                # ポケカ/ワンピ/DBの3種が揃うところまで読む。
                for _ in range(3):
                    page.mouse.wheel(0, 2400)
                    page.wait_for_timeout(1200)
                texts = page.evaluate(
                    """() => Array.from(
                        document.querySelectorAll('article[data-testid="tweet"]')
                    ).map(a => a.innerText).slice(0, 25)"""
                ) or []
            except Exception as e:
                logger.warning("KaitoriExpo: fetch failed: %s", e)
            finally:
                browser.close()
        return texts
