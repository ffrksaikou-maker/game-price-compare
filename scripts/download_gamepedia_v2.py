"""Download pack images from gamepedia using exact title-image pairs.

Uses the pre-extracted gamepedia_pairs.json (183 title+img entries)
and matches against MASTER_PRODUCTS by checking if the gamepedia title
appears INSIDE the master product name (e.g., "拡張パック「インフェルノX」"
matches "MEGA 拡張パック「インフェルノX」").

Direct URL download (no CDN transformation) to avoid 415 errors.
"""

from __future__ import annotations

import json
import sys
import urllib.request
import io
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow required")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper.matcher import MASTER_PRODUCTS
from scraper.generator import _generate_slug

OUT_DIR = ROOT / "images" / "boxes"
PAIRS_FILE = Path("C:/Users/fifty/gamepedia_pairs.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def main():
    pairs = json.loads(PAIRS_FILE.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build slug -> product name map
    slug_name: dict[str, str] = {}
    for p in MASTER_PRODUCTS:
        slug = _generate_slug(p.name)
        slug_name[slug] = p.name

    # For each gamepedia pair, find matching slug
    matched: dict[str, str] = {}  # slug -> direct image URL

    for pair in pairs:
        gp_title = pair["title"].strip()
        gp_img = pair["img"]
        if not gp_title:
            continue

        # Extract direct URL from CDN URL
        # CDN: https://tfi.gamepedia.jp/image/w=200,.../media.gamepedia.jp/...
        # Direct: https://media.gamepedia.jp/... or https://assets.gamepedia.jp/...
        if "media.gamepedia.jp/" in gp_img:
            direct = "https://media.gamepedia.jp/" + gp_img.split("media.gamepedia.jp/")[1]
        elif "assets.gamepedia.jp/" in gp_img:
            direct = "https://assets.gamepedia.jp/" + gp_img.split("assets.gamepedia.jp/")[1]
        else:
            continue

        # Match: gamepedia title should appear inside our product name
        # e.g., gp_title = '拡張パック「インフェルノX」'
        #        product = 'MEGA 拡張パック「インフェルノX」'
        for slug, pname in slug_name.items():
            if gp_title in pname or gp_title.replace(" ", "") in pname.replace(" ", ""):
                if slug not in matched:  # first match wins (gamepedia is ordered newest first)
                    matched[slug] = direct
                break

    print(f"Matched {len(matched)}/{len(slug_name)} slugs")

    # Show matches for verification
    downloaded = 0
    for slug, url in sorted(matched.items()):
        dest = OUT_DIR / f"{slug}.jpg"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data))
            if img.width > 600:
                new_h = int(img.height * 600 / img.width)
                img = img.resize((600, new_h), Image.LANCZOS)
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(dest, "JPEG", quality=80, optimize=True)
            downloaded += 1
            print(f"OK: {slug:40s} {dest.stat().st_size:>8,}B")
        except Exception as e:
            print(f"FAIL: {slug:40s} {e}")

    # Show unmatched slugs
    unmatched = set(slug_name.keys()) - set(matched.keys())
    if unmatched:
        print(f"\nUnmatched ({len(unmatched)}):")
        for s in sorted(unmatched):
            print(f"  {s}: {slug_name[s]}")

    print(f"\nDone: {downloaded} downloaded")


if __name__ == "__main__":
    main()
