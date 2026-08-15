"""メルカリのフリマ相場だけを取得して beyblade.html を作り直す。

買取価格の取得(全店スクレイプ)とは切り離して1日1回だけ走らせるための入口。
メルカリ相場は44商品ぶんの検索が必要で10分前後かかるが、日次で十分な粒度の
データなので、ポケカの価格更新(1日3回)を巻き込んで遅くする理由がない。

買取価格側は data/cache.json の最新取得結果をそのまま流用する。
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper.matcher import match_products  # noqa: E402
from scraper.products_beyblade import BEYBLADE_PRODUCTS, BEYBLADE_CONFIG  # noqa: E402
from scraper.generator_beyblade import generate_beyblade_html  # noqa: E402
from scraper import mercari  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    cache_path = ROOT / "data" / "cache.json"
    if not cache_path.exists():
        logger.error("cache.json が無いため中止 (先に価格更新を走らせてください)")
        sys.exit(1)

    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    for product in BEYBLADE_PRODUCTS:
        product.prices.clear()
    for shop_id, items in cache.items():
        pairs = [(i[0], i[1]) for i in items if len(i) >= 2]
        match_products(pairs, shop_id, BEYBLADE_PRODUCTS, BEYBLADE_CONFIG)

    with_prices = sum(1 for p in BEYBLADE_PRODUCTS if p.prices)
    logger.info(
        "買取価格をキャッシュから復元: %d/%d商品 (%d店)",
        with_prices, len(BEYBLADE_PRODUCTS), len(cache),
    )

    # 取得に失敗した商品は前回キャッシュの相場で埋まる
    market = mercari.fetch_with_cache(BEYBLADE_PRODUCTS)
    generate_beyblade_html(BEYBLADE_PRODUCTS, market)
    logger.info("Done! beyblade.html has been generated.")


if __name__ == "__main__":
    main()
