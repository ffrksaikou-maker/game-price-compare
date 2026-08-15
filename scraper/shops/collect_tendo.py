"""Scraper for 買取コレクト @collect_tendo on X.

買取コレクトはHPがなくXに不定期で買取価格表の画像を投稿する形式。
このスクレイパーは:
1. Playwright で占い垢のCookieを使ってX(Twitter)にログイン状態でアクセス
2. https://x.com/collect_tendo の最新ツイートから画像URLを抽出
3. 過去にOCRした画像URLとの差分を data/x_state/collect_tendo.json で管理
4. 新規画像のみ Claude API (Vision) でOCR&構造化抽出
5. {商品名: 価格} を ScrapedItem として返す

必要なシークレット:
- X_AUTH_TOKEN: 占い垢のauth_token Cookie (Read-onlyで使用)
- X_CT0: 占い垢のct0 Cookie (CSRF用)
- ANTHROPIC_API_KEY: Claude API Key (画像OCR用)
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

TARGET_USERNAME = "collect_tendo"
PROFILE_URL = f"https://x.com/{TARGET_USERNAME}"
STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "x_state" / "collect_tendo.json"
MAX_IMAGES_TO_OCR = 4  # 最新ツイートの画像のみOCR(コスト/負荷抑制)
MAX_OCR_RETRIES = 3  # OCRが空を返した画像を再挑戦する回数
ANTHROPIC_MODEL = "claude-sonnet-4-6"

# OCR後の名前正規化辞書(コレクト固有の表記揺れをmatcher側のキーワードに寄せる)
NAME_NORMALIZE = {
    "ニンジャスビナー": "ニンジャスピナー",
    "ポケモンセンタートウホク": "スペシャルBOX トウホク",
    "ポケモンセンターヒロシマ": "スペシャルBOX ヒロシマ",
    "ポケモンセンターフクオカ": "スペシャルBOX フクオカ",
    "ポケセントウホク": "スペシャルBOX トウホク",
    "ポケセンヒロシマ": "スペシャルBOX ヒロシマ",
    "ポケセンフクオカ": "スペシャルBOX フクオカ",
}


class CollectTendoScraper(BaseScraper):
    shop_id = "collect_tendo"
    shop_name = "買取コレクト"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        auth_token = os.environ.get("X_AUTH_TOKEN")
        ct0 = os.environ.get("X_CT0")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not auth_token or not ct0:
            logger.warning("CollectTendo: X_AUTH_TOKEN/X_CT0 missing, skipping")
            return []
        if not anthropic_key:
            logger.warning("CollectTendo: ANTHROPIC_API_KEY missing, skipping")
            return []

        state = self._load_state()
        seen_urls = set(state.get("processed_urls", []))

        # Step 1: Playwrightで画像URL取得
        image_urls = self._fetch_recent_image_urls(auth_token, ct0)
        if not image_urls:
            logger.warning("CollectTendo: no images found, returning cached items")
            return self._items_from_state(state)

        # Step 2: 新規画像だけOCR
        new_urls = [u for u in image_urls if u not in seen_urls]
        logger.info(
            "CollectTendo: %d image URLs found (%d new)",
            len(image_urls), len(new_urls),
        )

        fail_counts: dict[str, int] = state.get("ocr_fail_counts", {})
        new_items: dict[str, int] = {}
        for url in new_urls:
            logger.info("CollectTendo: OCR %s", url[:80])
            extracted = self._ocr_image(anthropic_key, url)
            if extracted is None:
                # API/通信エラー(残高切れ・レート制限等)。復旧すれば読めるので
                # 既読にもせず失敗回数にも数えない。
                logger.warning("CollectTendo: OCR unavailable, will retry next run")
                continue
            if not extracted:
                # 価格表でない画像(宣伝画像等)。既読にすると古い価格が
                # 永久に残るため、MAX_OCR_RETRIES 回までは次回に再挑戦する。
                fail_counts[url] = fail_counts.get(url, 0) + 1
                if fail_counts[url] < MAX_OCR_RETRIES:
                    logger.warning(
                        "CollectTendo: OCR empty (%d/%d), will retry next run",
                        fail_counts[url], MAX_OCR_RETRIES,
                    )
                    continue
                logger.warning("CollectTendo: OCR empty %d times, giving up", MAX_OCR_RETRIES)
                seen_urls.add(url)
                continue
            fail_counts.pop(url, None)
            for name, price in extracted.items():
                if price > 0 and price > new_items.get(name, 0):
                    new_items[name] = price
            seen_urls.add(url)

        # Step 3: state更新 — 新OCR結果は既存をオーバーライト
        cached_items = state.get("items", {})
        cached_items.update(new_items)
        state["items"] = cached_items
        # processed_urls は最新50件まで保持(古いのは破棄)
        state["processed_urls"] = list(seen_urls)[-50:]
        state["ocr_fail_counts"] = {
            u: c for u, c in fail_counts.items() if u in image_urls
        }
        state["last_check"] = int(time.time())
        self._save_state(state)

        return [ScrapedItem(name=n, price=p) for n, p in cached_items.items() if p > 0]

    # ----- helpers -----

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_state(self, state: dict) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _items_from_state(self, state: dict) -> list[ScrapedItem]:
        return [ScrapedItem(name=n, price=p) for n, p in state.get("items", {}).items() if p > 0]

    def _fetch_recent_image_urls(self, auth_token: str, ct0: str) -> list[str]:
        """Playwrightで@collect_tendoの最新ツイートから画像URLを収集"""
        from playwright.sync_api import sync_playwright

        urls: list[str] = []
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
            # Cookieセット (両方 .x.com スコープで)
            context.add_cookies([
                {
                    "name": "auth_token",
                    "value": auth_token,
                    "domain": ".x.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax",
                },
                {
                    "name": "ct0",
                    "value": ct0,
                    "domain": ".x.com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax",
                },
            ])
            page = context.new_page()
            try:
                page.goto(PROFILE_URL, wait_until="domcontentloaded", timeout=30000)
                # ツイート要素が出るまで待つ
                try:
                    page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
                except Exception:
                    logger.warning("CollectTendo: timeline not loaded (login expired?)")
                    browser.close()
                    return []

                # 最新ツイートだけ見るのでスクロール不要(初期描画分のみ取得)
                page.wait_for_timeout(1500)

                # 画像URL抽出: src のクエリパラメータを保持しつつ name=large に上書き
                raw = page.evaluate(
                    """() => {
                        const articles = Array.from(document.querySelectorAll('article[data-testid=\"tweet\"]'));
                        const out = [];
                        for (const a of articles) {
                            const imgs = Array.from(a.querySelectorAll('img'));
                            for (const i of imgs) {
                                const s = i.src;
                                if (s && s.includes('pbs.twimg.com/media/')) {
                                    try {
                                        const u = new URL(s);
                                        if (!u.searchParams.has('format')) u.searchParams.set('format', 'jpg');
                                        u.searchParams.set('name', 'large');
                                        out.push(u.toString());
                                    } catch(e) {}
                                }
                            }
                        }
                        return Array.from(new Set(out));
                    }"""
                )
                urls = list(raw)[:MAX_IMAGES_TO_OCR]
            finally:
                browser.close()

        return urls

    def _ocr_image(self, anthropic_key: str, image_url: str) -> dict[str, int] | None:
        """画像をClaude APIに渡して {商品名: 価格} を抽出

        None = API/通信エラーで判定不能(再試行すべき)、{} = 価格表でない画像。
        """
        try:
            img_resp = requests.get(image_url, timeout=20, headers={"User-Agent": self.HEADERS["User-Agent"]})
            img_resp.raise_for_status()
            image_b64 = base64.standard_b64encode(img_resp.content).decode("utf-8")
            content_type = img_resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        except requests.RequestException as e:
            logger.error("CollectTendo: image download failed: %s", e)
            return None

        prompt = (
            "この画像はトレーディングカードの買取価格表です。"
            "**ポケモンカードゲーム(ポケカ)の未開封BOX** と **ONE PIECEカードゲーム(ワンピ)の未開封BOX** を抽出してください。"
            "遊戯王/ガンダムカード/ドラゴンボール/MTG/その他TCGは絶対に除外してください。\n\n"
            "出力は以下のJSON形式のみ、説明文や前置きは一切不要:\n"
            '{"items": [{"name": "商品名", "price": 価格(整数、円)}, ...]}\n\n'
            "★最重要ルール: シュリンクの判別 ★\n"
            "- 表に『シュリンク有り(シュリンク付き/シュリンク有/シュリンクあり)』と『シュリンク無し(シュリンクなし/シュリンク無)』の**2つの価格列**がある場合、"
            "  **必ず『シュリンク有り』列の価格を採用すること**。シュリンク無し列の価格は絶対に採用しない。\n"
            "- 列ヘッダ(『シュリンク有り』『シュリンク無し』など)を画像の上部から必ず確認し、"
            "  各商品行のうち**シュリンク有り列のセル**の数値だけを読み取る。\n"
            "- シュリンク有り列が『-』『—』『×』『空欄』『取り消し線』の場合、その商品は採用しない(シュリンク無しの値で代替してはいけない)。\n"
            "- シュリンク有り>シュリンク無し が原則。同一商品で2つ価格が見えて区別が付かない場合は **必ず大きい方の値** を採用。\n"
            "- 列が1つしかない(シュリンク区別なし)表の場合のみ、その単一価格を採用してOK。\n\n"
            "その他のルール:\n"
            "- **価格は商品名と同じ行に書かれた金額のみを採用**(隣の商品の価格と混同しない)\n"
            "- 桁を慎重に読み取る(¥24,000 と ¥70,000 を間違えない、千円単位の区切りに注意)\n"
            "- ポケカ: 未開封BOX(拡張/強化拡張/ハイクラスパック/スタートデッキ100/地域別スペシャルBOX等)。"
            "例: 「ロケット団の栄光」「メガブレイブ」「151」「黒炎の支配者」「ニンジャスピナー」\n"
            "- ワンピ: 未開封BOX。弾番号を必ず商品名に含める(例: 「OP-16 決戦の刻」「EB-04 EGGHEAD CRISIS」"
            "「PRB-02 ONE PIECE CARD THE BEST vol.2」)。弾番号が読み取れる場合は必ず併記する\n"
            "- 商品名は表記そのまま、ただしOCR誤認は文脈から修正(例: 「初天」→「仰天」、「ゲーファンタズマ」→「ダークファンタズマ」)\n"
            "- 価格は半角整数、単位や¥は含めない\n"
            "- 価格不明・取り消し線・空欄のものは含めない\n"
            "- シングルカード/デッキ/単パック1袋/カートン売りは除外\n"
            "- 価格が読み取りにくい/自信がない場合はその商品をスキップ(誤った値を出すよりスキップ優先)\n"
        )

        api_url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
        try:
            r = requests.post(api_url, headers=headers, json=body, timeout=60)
            if r.status_code >= 400:
                logger.error("CollectTendo: claude API %d: %s", r.status_code, r.text[:500])
                return None
            payload = r.json()
        except (requests.RequestException, ValueError) as e:
            logger.error("CollectTendo: claude API failed: %s", e)
            return None

        text = ""
        for block in payload.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            logger.warning("CollectTendo: no JSON in response: %s", text[:200])
            return {}
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            logger.warning("CollectTendo: JSON parse failed: %s", e)
            return {}

        result: dict[str, int] = {}
        for it in obj.get("items", []):
            name = (it.get("name") or "").strip()
            price = it.get("price")
            if isinstance(price, str):
                price = int(re.sub(r"[^\d]", "", price)) if re.search(r"\d", price) else 0
            # 正規化: コレクト固有の表記揺れを既存matcherのキーワードに寄せる
            name = NAME_NORMALIZE.get(name, name)
            if name and isinstance(price, int) and price > 0:
                result[name] = max(result.get(name, 0), price)
        logger.info("CollectTendo: OCR extracted %d items from image", len(result))
        return result
