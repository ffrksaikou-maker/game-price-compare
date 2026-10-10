"""Scraper for 森森買取 (morimori-kaitori.jp).

2026-10 のリニューアル後は商品が div.mm1551-prow の行で並び、通常買取価格は
data-cond-new-price 属性に入る(data-price-disp-flg="1" は価格非表示)。
ページ送りは ?page=N。商品リンクは /category/<サブカテゴリ>/product/<id>。
"""

from __future__ import annotations

import logging
import os
import re
import time
from urllib.parse import quote

from .base import BaseScraper, ScrapedItem

logger = logging.getLogger(__name__)

BASE = "https://www.morimori-kaitori.jp"
# ポケカ=キーワード検索, ワンピ=専用カテゴリ(検索は取りこぼすため category を直に見る)。
# ワンピは2カテゴリに跨る: 2403=OP-01〜15/EB/PRB-02, 0112003=OP-16以降の新弾/PRB-01。
# 検索sk=ワンピースにも category/2403 にも新弾(OP-16 決戦の刻等)は出ないため両方見る。
# ポケカ側matcherはワンピを弾き、ワンピ側が拾う。(ラベル, URL)
# ベイブレードは 1904001。/category/price-list/1904001 だと div.product-item が
# 描画されずタイムアウトするため price-list を挟まない形を使う。
# ポケカは 2026-10 からシングルカード(PSA鑑定品など)も扱い始め、検索にも
# カテゴリにも混ざる。シングルはサブカテゴリ 2401009 に入るので除外する
# (SINGLE_CATEGORIES / SINGLE_NAME_RE)。BOXは 2401001/2401002/2401010 と 2401 直下。
TARGETS = [
    ("ポケモン", f"{BASE}/category/2401"),
    ("ワンピ", f"{BASE}/category/2403"),
    ("ワンピ新弾", f"{BASE}/category/0112003"),
    ("ベイブレード", f"{BASE}/category/1904001"),
    # ドラゴンボールは category/2404 に2件しか無く、MANGA BOOSTER は
    # category/24 側にあるため、両方をまとめて拾える検索を使う。
    ("ドラゴンボール", f"{BASE}/search?sk={quote('ドラゴンボール')}"),
]
SEARCH_URL = TARGETS[0][1]  # 後方互換(_open_with_retry のデフォルト値)

# ページを開く試行回数。1回あたり goto 60s + selector 30s かかるため、
# 森森が完全に応答しない障害時はこの回数がそのままジョブの所要時間になる。
# 2026-08-24 に GitHub Actions から全カテゴリ goto タイムアウトが続き、
# 5回×全カテゴリで約29分を消費してジョブごと落ちたため既定を 2 に下げた。
# 一時的な H2 リセットを拾いたいときは環境変数で戻せる。
OPEN_ATTEMPTS = int(os.environ.get("MORIMORI_OPEN_ATTEMPTS", "2") or 2)

ROW_SELECTOR = "div.mm1551-prow"
# シングルカードのサブカテゴリ。BOXの買取価格と誤マッチさせないため丸ごと捨てる。
SINGLE_CATEGORIES = {"2401009"}
# カテゴリ外に紛れたシングル用の保険(鑑定品・カード番号・レアリティ表記)
SINGLE_NAME_RE = re.compile(
    r"PSA|BGS|ARS|CGC|鑑定|\d{1,3}/[\w-]+|\d+-SV-P|(?:^|\s)(?:AR|SAR|SR|UR|HR|CHR|CSR)(?:\s|$)"
)


class MorimoriScraper(BaseScraper):
    shop_id = "morimori"
    shop_name = "森森"
    use_playwright = True

    def scrape(self) -> list[ScrapedItem]:
        items: list[ScrapedItem] = []
        seen_names: set[str] = set()

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # headless だと morimori-kaitori.jp に BOT 検出され
            # ERR_HTTP2_PROTOCOL_ERROR で全リクエストが弾かれる。
            # headful なら通るため、CI(Linux)では Xvfb 上で実行する
            # (.github/workflows/update.yml で xvfb-run でラップ済み)。
            # ローカルで窓を出したくない時は SCRAPER_HEADLESS=1 でヘッドレス化
            # (ただしBOT検出で失敗しキャッシュにフォールバックする可能性が高い)。
            headless = os.environ.get("SCRAPER_HEADLESS") == "1"
            browser = p.chromium.launch(headless=headless)
            try:
                for label, target_url in TARGETS:
                    try:
                        page = self._open_with_retry(browser, target_url)
                        prev_hrefs: list[str] = []
                        for page_num in range(1, 30):
                            if page_num > 1:
                                sep = "&" if "?" in target_url else "?"
                                url = f"{target_url}{sep}page={page_num}"
                                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                                try:
                                    page.wait_for_selector(ROW_SELECTOR, timeout=20000)
                                except Exception:
                                    break  # 最終ページの次は行が無い

                            before = len(items)
                            hrefs = self._extract_from_page(page, items, seen_names)
                            if not hrefs or hrefs == prev_hrefs:
                                break  # 行なし / page指定が効かず同じページ
                            prev_hrefs = hrefs
                            logger.info(
                                "%s: %s page %d: %d new items (total %d)",
                                self.shop_name, label, page_num,
                                len(items) - before, len(items),
                            )
                        page.context.close()
                    except Exception as e:
                        logger.error(
                            "%s: %s error: %s", self.shop_name, label, e,
                        )

            except Exception as e:
                logger.error("%s: scraping error: %s", self.shop_name, e)
            finally:
                browser.close()

        logger.info("%s: scraped %d items", self.shop_name, len(items))
        return items

    def _extract_from_page(
        self, page, items: list[ScrapedItem], seen: set[str],
    ) -> list[str]:
        """Extract products from the current page. ページ上の全行の href を返す。"""
        rows = page.evaluate(
            r"""() => [...document.querySelectorAll('div.mm1551-prow')].map(r => {
                const a = r.querySelector('.mm1551-prow__name a');
                return {
                    name: a ? a.textContent : '',
                    href: a ? (a.getAttribute('href') || '') : '',
                    price: r.dataset.condNewPrice || '',
                    hidden: r.dataset.priceDispFlg === '1',
                };
            })"""
        )
        skipped_single = 0
        for row in rows:
            name = re.sub(r"\s+", " ", row["name"]).strip()
            m = re.search(r"/category/(\w+)/product/", row["href"])
            if (m and m.group(1) in SINGLE_CATEGORIES) or SINGLE_NAME_RE.search(name):
                skipped_single += 1
                continue
            if row["hidden"]:
                continue
            price = self.parse_price(row["price"])
            if name and price > 0 and name not in seen:
                seen.add(name)
                items.append(ScrapedItem(name=name, price=price))
        if skipped_single:
            logger.debug("%s: シングル %d 件を除外", self.shop_name, skipped_single)
        return [row["href"] for row in rows]

    def _open_with_retry(self, browser, search_url: str = SEARCH_URL,
                         max_attempts: int = OPEN_ATTEMPTS):
        """Open the search page with retries.

        morimori-kaitori.jp resets the HTTP/2 connection
        (ERR_HTTP2_PROTOCOL_ERROR) for headless Chromium, so the browser is
        launched headful (see scrape()). headful でも稀に H2 リセットや
        ネットワーク揺らぎで失敗するため多めにリトライする。
        wait_until は domcontentloaded（networkidle は常時接続の EC で
        idle に到達せず timeout する失敗モードがあるため避ける。商品の
        描画は直後の wait_for_selector で担保する）。
        """
        last_err: Exception | None = None
        backoff = [2, 4, 8, 12, 16]
        for attempt in range(max_attempts):
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="ja-JP",
            )
            page = context.new_page()
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_selector(ROW_SELECTOR, timeout=30000)
                return page
            except Exception as e:
                last_err = e
                logger.warning(
                    "%s: open attempt %d/%d failed: %s",
                    self.shop_name, attempt + 1, max_attempts, e,
                )
                context.close()
                if attempt < max_attempts - 1:
                    time.sleep(backoff[min(attempt, len(backoff) - 1)])
        raise last_err if last_err else RuntimeError("open failed")
