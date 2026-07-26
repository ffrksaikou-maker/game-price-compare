"""買取価格の異常値検知。同日の他店価格・過去履歴を基準に外れ値を判定する。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from statistics import median

logger = logging.getLogger(__name__)

WARN_HIGH_RATIO = 2.5
WARN_LOW_RATIO = 0.4
DROP_HIGH_RATIO = 5.0
DROP_LOW_RATIO = 0.2
MIN_DIFF = 3000
HISTORY_WINDOW = 14
MIN_SAMPLES = 5

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "anomaly_state.json"


@dataclass
class Anomaly:
    """基準値から乖離した (商品, ショップ) の価格。"""
    product: str
    shop: str
    price: int
    ref: int
    ref_source: str
    ratio: float
    drop: bool

    @property
    def key(self) -> str:
        return f"{self.product}|{self.shop}"

    def describe(self, shop_name: str = "") -> str:
        action = "自動除外" if self.drop else "要確認"
        return (
            f"{shop_name or self.shop}: {self.product} ¥{self.price:,} "
            f"(基準¥{self.ref:,} {self.ref_source} 比 x{self.ratio:.1f}) [{action}]"
        )


def _recent_prices(history_dir: Path) -> tuple[dict, dict]:
    """直近履歴から (商品,店)別 と 商品別 の価格リストを作る。"""
    own: dict[tuple[str, str], list[int]] = {}
    whole: dict[str, list[int]] = {}
    if not history_dir.exists():
        return own, whole

    for path in sorted(history_dir.glob("*.json"))[-HISTORY_WINDOW:]:
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for item in snapshot:
            name = item.get("name", "")
            for shop, price in (item.get("prices") or {}).items():
                if price > 0:
                    own.setdefault((name, shop), []).append(price)
                    whole.setdefault(name, []).append(price)
    return own, whole


def _reference(
    name: str, shop: str, prices: dict, own: dict, whole: dict
) -> tuple[float, str]:
    """基準価格を 同日他店 → 自店履歴 → 全店履歴 の順に決める。"""
    others = [v for s, v in prices.items() if s != shop and v > 0]
    if len(others) >= 2:
        return median(others), "同日他店"

    own_prices = own.get((name, shop), [])
    if len(own_prices) >= MIN_SAMPLES:
        return median(own_prices), f"自店{HISTORY_WINDOW}日"

    whole_prices = whole.get(name, [])
    if len(whole_prices) >= MIN_SAMPLES:
        return median(whole_prices), f"全店{HISTORY_WINDOW}日"

    return 0.0, ""


def detect_anomalies(products: list, history_dir: Path) -> list[Anomaly]:
    """マッチ済み商品の価格から異常値を検出する。"""
    own, whole = _recent_prices(history_dir)

    found: list[Anomaly] = []
    for product in products:
        for shop, price in product.prices.items():
            if price <= 0:
                continue
            ref, source = _reference(product.name, shop, product.prices, own, whole)
            if ref <= 0:
                continue
            ratio = price / ref
            if WARN_LOW_RATIO <= ratio <= WARN_HIGH_RATIO:
                continue
            if abs(price - ref) < MIN_DIFF:
                continue
            found.append(
                Anomaly(
                    product=product.name,
                    shop=shop,
                    price=price,
                    ref=int(ref),
                    ref_source=source,
                    ratio=ratio,
                    drop=ratio >= DROP_HIGH_RATIO or ratio <= DROP_LOW_RATIO,
                )
            )
    return found


def drop_anomalies(products: list, anomalies: list[Anomaly]) -> list[Anomaly]:
    """自動除外対象の価格を採用対象から外す。"""
    dropped = [a for a in anomalies if a.drop]
    if not dropped:
        return []

    index = {p.name: p for p in products}
    for anomaly in dropped:
        product = index.get(anomaly.product)
        if product and product.prices.get(anomaly.shop) == anomaly.price:
            del product.prices[anomaly.shop]
            logger.warning("価格異常を除外: %s", anomaly.describe())
    return dropped


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def update_state(anomalies: list[Anomaly]) -> tuple[list[Anomaly], list[str]]:
    """前回状態と比較し、(新規発生, 解消したキー) を返して状態を保存する。"""
    previous = load_state()
    current = {
        a.key: {"price": a.price, "ref": a.ref, "ratio": round(a.ratio, 2), "drop": a.drop}
        for a in anomalies
    }

    raised = [a for a in anomalies if a.key not in previous]
    resolved = [k for k in previous if k not in current]

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return raised, resolved
