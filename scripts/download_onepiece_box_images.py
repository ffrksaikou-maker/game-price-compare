"""ONE PIECEカードゲーム公式サイトからBOX/パック商品画像を取得する。

https://www.onepiece-cardgame.com/products/{code}.html の商品ページから
主商品画像(img_item01.webp)を抽出し、images/boxes/{slug}.webp + .jpg に保存する。
ポケカ側 download_box_images.py と同じ自己ホスト方式。

※公式は現行商品の個別ページのみ生存(旧弾はアーカイブ削除)。取得できる弾だけ
処理し、404はスキップする。SLUG_CODE に弾を足せば対象が増える。

商品ページには関連商品の img_item01 も混在するため、DOM出現順で最初の
img_item01.webp(=そのページ自身の主商品)を採用する。
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow が必要です: pip install Pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "images" / "boxes"
BASE = "https://www.onepiece-cardgame.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# slug(当サイト) -> 公式商品コード。公式に個別ページがある弾のみ。
SLUG_CODE = {
    "st-30": "st30",
}

# slug -> プレミアムバンダイ商品ID。公式CDN(bandai-a.akamaihd.net)の
# /bc/img/model/b/{id}_1.jpg が箱+パックの透かし無し公式商品画像。
# p-bandaiの商品ページURL末尾 item-XXXXXXXXXX の数字部分。
PBANDAI_ID = {
    "op-16": "1000253295",
    "op-13": "1000248929",
    "op-09": "1000215674",
    "op-06": "1000203166",
    "eb-03": "1000248932",
    "eb-01": "1000206789",
}
PBANDAI_CDN = "https://bandai-a.akamaihd.net/bc/img/model/b/{id}_1.jpg"


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30).read()


def _main_image_url(html: str) -> str | None:
    """DOM出現順で最初の img_item01.webp(そのページ自身の主商品画像)を返す。"""
    m = re.search(r'/onepiececg/bccard/jp/products/[^"\' >]+/img_item01\.webp', html)
    return (BASE + m.group(0)) if m else None


def _save(slug: str, data: bytes, src_name: str) -> str:
    webp_path = OUT_DIR / f"{slug}.webp"
    jpg_path = OUT_DIR / f"{slug}.jpg"
    im = Image.open(__import__("io").BytesIO(data)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    rgb = bg.convert("RGB")
    rgb.save(jpg_path, "JPEG", quality=85, optimize=True, progressive=True)
    rgb.save(webp_path, "WEBP", quality=85, method=6)
    return f"{slug}: {src_name} -> {webp_path.name}+{jpg_path.name} ({im.size[0]}x{im.size[1]})"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done, skipped = 0, []
    # プレミアムバンダイ公式CDN(箱+パック画像)を優先取得
    for slug, item_id in PBANDAI_ID.items():
        url = PBANDAI_CDN.format(id=item_id)
        try:
            print("OK " + _save(slug, _fetch(url), f"pbandai {item_id}"))
            done += 1
        except Exception as e:
            skipped.append((slug, f"pbandai {e}"))
    for slug, code in SLUG_CODE.items():
        page_url = f"{BASE}/products/{code}.html"
        try:
            html = _fetch(page_url).decode("utf-8", "ignore")
        except Exception as e:
            skipped.append((slug, f"page {e}"))
            continue
        img_url = _main_image_url(html)
        if not img_url:
            skipped.append((slug, "img_item01 not found"))
            continue
        try:
            data = _fetch(img_url)
        except Exception as e:
            skipped.append((slug, f"img {e}"))
            continue
        webp_path = OUT_DIR / f"{slug}.webp"
        jpg_path = OUT_DIR / f"{slug}.jpg"
        webp_path.write_bytes(data)
        # 白背景に合成してjpgフォールバックを作る(透過pngフォールバック回避)
        im = Image.open(webp_path).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        bg.convert("RGB").save(jpg_path, "JPEG", quality=85, optimize=True, progressive=True)
        print(f"OK {slug}: {img_url.split('/')[-1]} -> {webp_path.name} + {jpg_path.name} ({im.size[0]}x{im.size[1]})")
        done += 1
    print(f"\n完了: {done}件取得")
    for slug, why in skipped:
        print(f"  SKIP {slug}: {why}")


if __name__ == "__main__":
    main()
