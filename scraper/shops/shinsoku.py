"""Scraper for 買取シンソク (shinsoku-tcg.com).

ポケカBOXは /yuso-kaitori ページにあり、JSで動的ロード+lazy scroll。
1. BOXフィルタを選択
2. 最下部まで繰り返しスクロール
3. .product-card のうち .badge-box を持つものから商品名+価格を抽出
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from pathlib import Path

import requests

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

URL = "https://shinsoku-tcg.com/yuso-kaitori"

# ドラゴンボールはWebの買取表に無く、X(@shinsoku_price)に価格表の画像で出る。
# サイト内検索でも0件なので、画像をOCRして拾うしか経路がない。
X_USERNAME = "shinsoku_price"
X_PROFILE_URL = f"https://x.com/{X_USERNAME}"
X_STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "x_state" / "shinsoku.json"
X_MAX_IMAGES = 6          # 直近ツイートの画像のみ見る(コスト/負荷を抑える)
X_MAX_OCR_RETRIES = 3     # 価格表でない画像を諦めるまでの回数
X_STALE_DAYS = 14         # 価格表に出てこなくなった商品を落とすまでの日数
ANTHROPIC_MODEL = "claude-sonnet-4-6"
# ワンピBOXは既定のBOXフィルタ一覧に含まれないため、title検索で別取得する。
# ポケカ側matcherはワンピを弾き、ワンピ側matcherが拾う。
ONEPIECE_URL = "https://shinsoku-tcg.com/yuso-kaitori?title=%E3%83%AF%E3%83%B3%E3%83%94%E3%83%BC%E3%82%B9"


class ShinsokuScraper(BaseScraper):
    shop_id = "shinsoku"
    shop_name = "買取シンソク"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        from playwright.sync_api import sync_playwright

        items: list[ScrapedItem] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=self.HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 1800},
                locale="ja-JP",
            )
            page = ctx.new_page()
            try:
                # --- ポケカ等: 既定一覧をBOXフィルタで取得 ---
                page.goto(URL, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                try:
                    page.select_option("select", label="BOX")
                    page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning("Shinsoku: BOX filter select failed: %s", e)
                self._scroll_and_extract(page, items, "BOX filter")

                # --- ワンピ: title検索でワンピBOXを取得 ---
                try:
                    page.goto(ONEPIECE_URL, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)
                    self._scroll_and_extract(page, items, "ONE PIECE title")
                except Exception as e:
                    logger.warning("Shinsoku: ONE PIECE pass failed: %s", e)
            finally:
                browser.close()

        # --- ドラゴンボール: Xの価格表画像からOCRで取得 ---
        try:
            items.extend(self._scrape_x_dragonball())
        except Exception as e:
            logger.warning("Shinsoku: X(DB) pass failed: %s", e)

        return items

    def _scroll_and_extract(self, page, items: list[ScrapedItem], label: str) -> None:
        """最下部までスクロールして .badge-box 付き商品を抽出し items に追加。"""
        last_h = 0
        for i in range(80):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(700)
            h = page.evaluate("() => document.body.scrollHeight")
            if h == last_h:
                break
            last_h = h

        raw = page.evaluate(
            """() => {
                const cards = Array.from(document.querySelectorAll('.product-card'));
                const boxes = cards.filter(c => c.querySelector('.badge-box'));
                return boxes.map(c => {
                    const h3 = c.querySelector('h3');
                    const m = c.innerText.match(/¥[\\d,]+/);
                    return {
                        name: h3 ? h3.innerText.trim() : '',
                        price: m ? m[0] : '',
                    };
                });
            }"""
        )
        before = len(items)
        for r in raw:
            name = r.get("name", "").strip()
            price = self.parse_price(r.get("price", ""))
            if name and price > 0:
                items.append(ScrapedItem(name=name, price=price))
        logger.info("Shinsoku[%s]: %d BOX cards -> %d items",
                    label, len(raw), len(items) - before)

    # ----- X(@shinsoku_price)のドラゴンボール価格表 -----

    def _scrape_x_dragonball(self) -> list[ScrapedItem]:
        """Xの画像をOCRしてドラゴンボールBOXの買取価格を取る。"""
        auth_token = os.environ.get("X_AUTH_TOKEN")
        ct0 = os.environ.get("X_CT0")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        state = self._load_x_state()
        if not anthropic_key:
            logger.warning("Shinsoku: ANTHROPIC_API_KEY missing, using cached DB prices")
            return self._items_from_x_state(state)

        image_urls = (self._fetch_x_image_urls(auth_token, ct0)
                      if auth_token and ct0 else [])
        if not image_urls:
            # CIからXを開くとCloudflareで止まるため、ローカルが集めた分を使う。
            image_urls = state.get("pending_images", [])
            if image_urls:
                logger.info("Shinsoku: using %d image URLs collected locally",
                            len(image_urls))
        if not image_urls:
            logger.warning("Shinsoku: no X images found, using cached DB prices")
            return self._items_from_x_state(state)

        seen = set(state.get("processed_urls", []))
        fails: dict = state.get("ocr_fail_counts", {})
        new_items: dict = {}
        for url in [u for u in image_urls if u not in seen]:
            logger.info("Shinsoku: OCR %s", url[:80])
            got = self._ocr_dragonball_image(anthropic_key, url)
            if got is None:
                # API/通信エラー。復旧すれば読めるので既読にしない。
                logger.warning("Shinsoku: OCR unavailable, will retry next run")
                continue
            if not got:
                fails[url] = fails.get(url, 0) + 1
                if fails[url] < X_MAX_OCR_RETRIES:
                    continue
                seen.add(url)
                continue
            fails.pop(url, None)
            for name, price in got.items():
                if price > 0 and price > new_items.get(name, 0):
                    new_items[name] = price
            seen.add(url)

        cached = state.get("items", {})
        cached.update(new_items)
        state["items"] = cached
        now = int(time.time())
        seen_at = state.get("seen_at", {})
        for _n in new_items:
            seen_at[_n] = now
        for _n in cached:
            seen_at.setdefault(_n, now)
        state["seen_at"] = {k: v for k, v in seen_at.items() if k in cached}
        state["processed_urls"] = list(seen)[-50:]
        state["ocr_fail_counts"] = {u: c for u, c in fails.items() if u in image_urls}
        state["last_check"] = int(time.time())
        state["pending_images"] = [u for u in state.get("pending_images", [])
                                   if u not in seen]
        self._save_x_state(state)
        logger.info("Shinsoku: X DB prices %d new / %d total", len(new_items), len(cached))
        return self._items_from_x_state(state)

    def _load_x_state(self) -> dict:
        if X_STATE_FILE.exists():
            try:
                return json.loads(X_STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Shinsoku: X state broken, starting fresh")
        return {}

    def _save_x_state(self, state: dict) -> None:
        X_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        X_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    def _items_from_x_state(self, state: dict) -> list[ScrapedItem]:
        """X_STALE_DAYS を過ぎても価格表に出てこない商品は掲載しない。"""
        cutoff = int(time.time()) - X_STALE_DAYS * 86400
        seen_at = state.get("seen_at", {})
        # 取得側が壊れて価格表がまったく取れなくなった場合、期限切れ判定を
        # 続けると全商品が消える。直近の更新自体が無いときは何も落とさない。
        if not seen_at or max(seen_at.values(), default=0) < cutoff:
            return [ScrapedItem(name=n, price=p)
                    for n, p in state.get("items", {}).items() if p > 0]
        out = []
        for n, p in state.get("items", {}).items():
            if p <= 0:
                continue
            if seen_at and seen_at.get(n, 0) < cutoff:
                continue
            out.append(ScrapedItem(name=n, price=p))
        return out

    def _fetch_x_image_urls(self, auth_token: str, ct0: str) -> list[str]:
        from playwright.sync_api import sync_playwright

        urls: list[str] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                user_agent=self.HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 1800},
                locale="ja-JP",
            )
            ctx.add_cookies([
                {"name": "auth_token", "value": auth_token, "domain": ".x.com",
                 "path": "/", "httpOnly": True, "secure": True, "sameSite": "Lax"},
                {"name": "ct0", "value": ct0, "domain": ".x.com",
                 "path": "/", "httpOnly": False, "secure": True, "sameSite": "Lax"},
            ])
            page = ctx.new_page()
            try:
                page.goto(X_PROFILE_URL, wait_until="domcontentloaded", timeout=30000)
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
                    logger.warning("Shinsoku(X): timeline not loaded. url=%s title=%s body=%s",
                                   _url, _title, _body)
                    browser.close()
                    return []
                page.wait_for_timeout(1500)
                # 画像は遅延読み込みなので少しスクロールして読み込ませる
                for _ in range(3):
                    page.mouse.wheel(0, 2200)
                    page.wait_for_timeout(1200)
                raw = page.evaluate(
                    """() => Array.from(document.querySelectorAll('article[data-testid="tweet"] img'))
                        .map(i => i.src)
                        .filter(s => s.includes('pbs.twimg.com/media'))"""
                ) or []
            except Exception as e:
                logger.warning("Shinsoku: X fetch failed: %s", e)
                raw = []
            finally:
                browser.close()
        for u in raw:
            # サムネイルではなく大きい画像を取る
            u = re.sub(r"name=[a-z0-9]+", "name=large", u)
            if u not in urls:
                urls.append(u)
        return urls[:X_MAX_IMAGES]

    def _ocr_dragonball_image(self, anthropic_key: str, image_url: str) -> dict | None:
        """画像から {商品名: 価格} を抽出。None=通信/APIエラー、{}=価格表でない画像。"""
        try:
            r = requests.get(image_url, timeout=20,
                             headers={"User-Agent": self.HEADERS["User-Agent"]})
            r.raise_for_status()
            image_b64 = base64.standard_b64encode(r.content).decode("utf-8")
            content_type = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        except requests.RequestException as e:
            logger.error("Shinsoku: image download failed: %s", e)
            return None

        prompt = (
            "この画像はトレーディングカードの買取価格表です。"
            "**ドラゴンボールスーパーカードゲーム フュージョンワールド(および スーパーダイバーズ)の未開封BOX** "
            "だけを抽出してください。"
            "ポケモンカード/ONE PIECE/遊戯王/ヴァイスシュヴァルツ/その他TCGは絶対に除外してください。"
            "ドラゴンボールの価格表でない画像なら、items を空配列で返してください。\n\n"
            "出力は以下のJSON形式のみ、説明文や前置きは一切不要:\n"
            '{"items": [{"name": "商品名", "price": 価格(整数、円)}, ...]}\n\n'
            "ルール:\n"
            "- 弾番号を必ず商品名に含める(例: 「FB-07 神龍への願い」「SB-01 MANGA BOOSTER 01」"
            "「ST-01 STORY BOOSTER 01」)。弾番号が読み取れるなら必ず併記する\n"
            "- **シュリンク有りと無しの2列がある場合は必ずシュリンク有りの価格を採用**する。"
            "シュリンク無しの値は使わない\n"
            "- 価格は商品名と同じ行の金額のみを採用し、隣の行と混同しない\n"
            "- 桁を慎重に読む(11,500 と 115,000 を間違えない)\n"
            "- カートン売り/シングルカード/デッキ/バラパックは除外\n"
            "- 価格が空欄・取り消し線・『〆切』『買取停止』などのものは含めない\n"
            "- 価格は半角整数、単位や¥は含めない\n"
            "- 読み取りに自信がない商品はスキップ(誤った値を出すよりスキップ優先)\n"
        )
        body = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 2000,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": content_type, "data": image_b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        }
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": anthropic_key,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json=body, timeout=60)
            if resp.status_code >= 400:
                logger.error("Shinsoku: claude API %d: %s", resp.status_code, resp.text[:300])
                return None
            payload = resp.json()
        except (requests.RequestException, ValueError) as e:
            logger.error("Shinsoku: claude API failed: %s", e)
            return None

        try:
            text = "".join(b.get("text", "") for b in payload.get("content", []))
            m = re.search(r"\{.*\}", text, re.S)
            if not m:
                return {}
            data = json.loads(m.group(0))
        except (ValueError, KeyError) as e:
            logger.warning("Shinsoku: OCR parse failed: %s", e)
            return {}

        out = {}
        for it in data.get("items", []):
            name = str(it.get("name", "")).strip()
            try:
                price = int(it.get("price", 0))
            except (TypeError, ValueError):
                continue
            if name and 500 <= price <= 900000:
                out[name] = max(price, out.get(name, 0))
        return out
