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
EXCLUDE_WORDS = ("シュリ無", "シュリなし", "シュリンクなし", "カートン", "シングル")
# 「ブラックボルトDX 〆切」のような行は買取停止。価格0として返し、古い価格表の
# 値が残り続けないようにする(0は掲載しない扱い)。
STOP_RE = re.compile(r"^(.*?)\s*(?:〆切|締切|締め切り|受付終了|買取終了|買取停止)\s*[!！]*$")
# 「ハドウシーカー\n買取上限に達したため、7000円に価格を変更させていただきます！」
# のような単発の価格変更告知。直前の行を商品名とみなす。
CHANGE_RE = re.compile(r"([0-9][0-9,]*)\s*円に(?:価格を|買取価格を)?変更")
# 告知文から金額らしき数字を拾わないための除外
# 「30th Celecration 20500円→18500円」のような値下げ告知は価格表ではない。
# 矢印つきの行を商品として拾うと、商品名に価格が混ざったゴミが state に残る。
NOISE_WORDS = ("以上は着払い", "持ち込み", "記載商品", "現金可能", "件の表示",
               "買取価格", "リポスト", "いいね", "返信", "→", "⇒", "->")
MIN_PRICE = 500
MAX_PRICE = 900000
# 価格表に出てこなくなった商品を落とすまでの日数。買取をやめた商品の価格が
# 残り続けるのを防ぐ。EXPOはジャンルごとに投稿が分かれ、日によって出ない
# ジャンルがあるため短くしすぎない。
STALE_DAYS = 14
# 公式サイトの買取カタログ(会員登録不要で見られる公開API)
CATALOG_URL = "https://kaitori-expo.com/expo-build/cms/buyback/api.php?action=catalog"
CATALOG_KINDS = ("box", "other")
# kind=other には同名の派生商品が混ざる(例: 「ステラミラクルデッキビルド」¥3,600 が
# BOX ¥11,000 を上書きした)。BOXと取り違えやすい語を除く。
CATALOG_EXCLUDE = ("デッキビルド", "パック", "スターターセット", "ファイル")


def parse_tweet_text(text: str) -> dict[str, int]:
    """ツイート本文から {商品名: 価格} を取り出す。"""
    out: dict[str, int] = {}
    lines = [ln.strip() for ln in text.split("\n")]
    prev = ""
    for line in lines:
        if not line:
            continue
        cm = CHANGE_RE.search(line)
        if cm and prev and "円" not in prev and len(prev) <= 40 \
                and not any(w in prev for w in EXCLUDE_WORDS):
            name = re.sub(r"^[\W_]+", "", prev, flags=re.UNICODE).strip()
            try:
                price = int(cm.group(1).replace(",", ""))
            except ValueError:
                price = 0
            if name and MIN_PRICE <= price <= MAX_PRICE:
                out[name] = price
            prev = line
            continue
        prev = line
        if any(w in line for w in EXCLUDE_WORDS):
            continue
        sm = STOP_RE.match(line)
        if sm:
            name = re.sub(r"^[\W_]+", "", sm.group(1), flags=re.UNICODE).strip()
            if name and name not in out:
                out[name] = 0
            continue
        if any(w in line for w in NOISE_WORDS):
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

        # 公式サイトの買取カタログAPIを最優先で使う(2026-11-28〜)。
        # Xの投稿は複数ジャンルに分かれ、上限到達による値下げも別投稿で
        # 出るため、拾い方次第で古い価格が残った。APIは店の現在値そのもの。
        api_items = self._fetch_catalog()
        if api_items:
            return api_items
        logger.warning("KaitoriExpo: catalog API unavailable, falling back to X")

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
        # 商品ごとの最終確認日。今回の価格表に出た商品だけ更新する。
        now = int(time.time())
        seen_at = state.get("seen_at", {})
        for _n in found:
            seen_at[_n] = now
        # 導入前からある商品は起点が無いので、今回を起点にして猶予を与える
        for _n in cached:
            seen_at.setdefault(_n, now)
        state["seen_at"] = {k: v for k, v in seen_at.items() if k in cached}
        state["last_check"] = now
        state["last_found"] = len(found)
        self._save_state(state)

        logger.info("KaitoriExpo: %d tweets, %d items parsed (%d cached total)",
                    len(texts), len(found), len(cached))
        return self._items_from_state(state)

    # ----- helpers -----

    def _fetch_catalog(self) -> list[ScrapedItem]:
        """公式サイト(kaitori-expo.com)の買取カタログAPIから現在の買取価格を取る。

        kind: box/other/pack を対象にし、carton(カートン)・unsealed(シュリ無)・
        single・psa は除外。available=False(買取上限到達・停止)は掲載しない。
        """
        try:
            resp = self.session.get(CATALOG_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("KaitoriExpo: catalog API failed: %s", e)
            return []
        products = data.get("products") or []
        if not data.get("ok") or not products:
            logger.warning("KaitoriExpo: catalog API returned no products")
            return []
        items: list[ScrapedItem] = []
        best: dict[str, int] = {}
        for p in products:
            if p.get("kind") not in CATALOG_KINDS:
                continue
            if p.get("category") in ("psa",):
                continue
            if not p.get("available"):
                continue
            name = (p.get("name") or "").strip()
            try:
                price = int(p.get("price") or 0)
            except (TypeError, ValueError):
                continue
            if not name or price <= 0:
                continue
            if any(w in name for w in EXCLUDE_WORDS):
                continue
            if p.get("kind") == "other" and any(w in name for w in CATALOG_EXCLUDE):
                continue
            if price > best.get(name, 0):
                best[name] = price
        items = [ScrapedItem(name=n, price=v) for n, v in best.items()]
        logger.info("KaitoriExpo: catalog API %d items (updated %s)",
                    len(items), data.get("updated", "?"))
        return items

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
        """STALE_DAYS を過ぎても価格表に出てこない商品は掲載しない。"""
        cutoff = int(time.time()) - STALE_DAYS * 86400
        seen_at = state.get("seen_at", {})
        # 取得側が壊れて価格表がまったく取れなくなった場合、期限切れ判定を
        # 続けると全商品が消える。直近の更新自体が無いときは何も落とさない。
        if not seen_at or max(seen_at.values(), default=0) < cutoff:
            return [ScrapedItem(name=n, price=p)
                    for n, p in state.get("items", {}).items() if p > 0]
        return [ScrapedItem(name=n, price=p)
                for n, p in state.get("items", {}).items()
                if p > 0 and seen_at.get(n, 0) >= cutoff]

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
                    # ログイン切れか、Xのセレクタ変更かを切り分けられるように
                    # 実際に何が表示されているかを残す。
                    try:
                        _url = page.url
                        _title = page.title()[:80]
                        _body = page.inner_text("body")[:200].replace("\n", " ")
                    except Exception:
                        _url = _title = _body = "?"
                    logger.warning("KaitoriExpo: timeline not loaded. url=%s title=%s body=%s",
                                   _url, _title, _body)
                    browser.close()
                    return []
                page.wait_for_timeout(1500)
                # 価格表は長文で複数ツイートに分かれるため、少しスクロールして
                # ポケカ/ワンピ/DBの3種が揃うところまで読む。
                for _ in range(3):
                    page.mouse.wheel(0, 2400)
                    page.wait_for_timeout(1200)
                # 長いツイートは「さらに表示」で折りたたまれ、innerText に本文の
                # 後半が入らない。実際 30th CELEBRATION 20500円 がこれで落ちていた。
                # 展開ボタンを押してから読む。
                for _ in range(3):
                    clicked = page.evaluate(
                        """() => {
                            const btns = Array.from(document.querySelectorAll(
                                'button[data-testid="tweet-text-show-more-link"], ' +
                                'div[data-testid="tweet-text-show-more-link"]'
                            ));
                            btns.forEach(b => b.click());
                            return btns.length;
                        }"""
                    ) or 0
                    if not clicked:
                        break
                    page.wait_for_timeout(800)
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
