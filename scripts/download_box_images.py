"""Download BOX package images from pokemon-card.com official landing pages.

Saves to images/boxes/{slug}.{ext}. Uses pre-verified URL mappings.
Idempotent - skips files that already exist.

2026-04-12 initial 28 BOXes.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "images" / "boxes"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
BASE = "https://www.pokemon-card.com/ex"

# slug -> (series_code, path_prefix, filename)
# path_prefix is 'assets/images' for newer pages or 'images' for old Nuxt.js pages
# verified via probe_box_images.sh + probe_ogp_images.sh
BOX_IMAGES: dict[str, tuple[str, str, str]] = {
    # MEGA series (all use assets/images + product-img)
    "mega-brave": ("m1", "assets/images", "product-img-1.png"),
    "mega-sinfonia": ("m1", "assets/images", "product-img-2.png"),
    "inferno": ("m2", "assets/images", "product-img-01.png"),
    "mega-ex": ("m2a", "assets/images", "product-img-01.png"),
    "munikis-zero": ("m3", "assets/images", "product-img-02.png"),
    "ninja-spinner": ("m4", "assets/images", "product-img-01-4gmgu.png"),
    "battle-collection": ("mc", "assets/images", "ogp.jpg"),
    # SV numbered (hero-visual or ogp)
    "scarlet-ex": ("sv1", "assets/images", "hero-visual.jpg"),
    "violet-ex": ("sv1", "assets/images", "hero-visual.jpg"),  # same landing page
    "151": ("sv2a", "assets/images", "hero-visual.png"),
    "ruler-of-black-flame": ("sv3", "assets/images", "hero-visual.jpg"),
    "ancient-roar": ("sv4", "assets/images", "hero-visual.jpg"),
    "future-flash": ("sv4", "assets/images", "hero-visual.jpg"),
    "shiny-treasure-ex": ("sv4a", "assets/images", "hero-visual.png"),
    "hengen-no-kamen": ("sv6", "assets/images", "hero-visual.jpg"),
    "stellar-miracle": ("sv7", "assets/images", "hero-visual.jpg"),
    "chouden-breaker": ("sv8", "assets/images", "hero-visual.jpg"),
    "terastal-fes-ex": ("sv8a", "assets/images", "hero-pack.png"),
    "battle-partners": ("sv9", "assets/images", "hero-visual.jpg"),
    "rocket-dan-no-eiko": ("sv10", "assets/images", "hero-visual.jpg"),
    "black-bolt": ("sv11", "assets/images", "point03-box-1.png"),
    "white-flare": ("sv11", "assets/images", "point04-box-1.png"),
    # Newer SS series (assets/images + product-img)
    "vmax-climax": ("s8b", "assets/images", "product-img-1.png"),
    "star-birth": ("s9", "assets/images", "product-img-1.png"),
    "time-gazer": ("s10", "assets/images", "product-img-1.png"),
    "space-juggler": ("s10", "assets/images", "hero-img-3.png"),
    "pokemon-go": ("s10b", "assets/images", "product-img-1.png"),
    "paradigm-trigger": ("s12", "assets/images", "product-img-1.png"),
    "vstar-universe": ("s12a", "assets/images", "product-img-1.png"),
    # Old Nuxt.js SS pages (old pattern: /images/ogp.jpg)
    "sword": ("s1", "images", "ogp.jpg"),
    "shield": ("s1", "images", "ogp.jpg"),
    "rebellion-crash": ("s2", "images", "ogp.jpg"),
    "infinity-zone": ("s3", "images", "ogp.jpg"),
    "astonishing-voltecker": ("s4", "images", "ogp.jpg"),
    # Newer SS with ogp
    "shiny-star": ("s4a", "assets/images", "ogp.png"),
    "eevee-heroes": ("s6a", "assets/images", "ogp.png"),
    "lost-abyss": ("s11", "assets/images", "ogp.png"),
}

# Additional images using direct /products/{year}/images/ paths
# (these don't follow the /ex/{code}/ structure)
BOX_IMAGES_DIRECT: dict[str, str] = {
    # SV pkg pattern
    "triplet-beat": "https://www.pokemon-card.com/products/2023/images/sv1a_pkg.jpg",
    "raging-surf": "https://www.pokemon-card.com/products/2023/images/1512_SV3a_pkg.jpg",
    # SV2 dual: SV2P=Snow Hazard, SV2D=Clay Burst
    "snow-hazard": "https://www.pokemon-card.com/products/2023/images/1508_SV2P_pillow_img.png",
    "clay-burst": "https://www.pokemon-card.com/products/2023/images/1509_SV2D_pillow_img.png",
    # S&S pillow_img pattern
    "single-strike-master": "https://www.pokemon-card.com/products/2020/images/1418_S5_ICHIGEKI_pillow_img.jpg",
    "rapid-strike-master": "https://www.pokemon-card.com/products/2020/images/1418_S5_RENGEEKI_pillow_img.jpg",
    "silver-lance": "https://www.pokemon-card.com/products/2021/images/1423_S6H_pillow_img.jpg",
    "jet-black-geist": "https://www.pokemon-card.com/products/2021/images/1423_S6K_pillow_img.jpg",
    "fusion-arts": "https://www.pokemon-card.com/products/2021/images/1431_S8_pillow_img.png",
    # vmax-rising = s1a era, sequential 01_S1a.jpg etc
    "vmax-rising": "https://www.pokemon-card.com/products/2020/images/01_S1a.jpg",
    # SV later sub-series
    "neppuu-arena": "https://www.pokemon-card.com/products/2025/images/sv9a_pillow.jpg",
    "crimson-haze": "https://www.pokemon-card.com/products/2024/images/SV5a_1.jpg",
    "night-wanderer": "https://www.pokemon-card.com/products/2024/images/SV6a_1.png",
    "rakuen-dragona": "https://www.pokemon-card.com/products/2024/images/sv7a_1.png",
    # Older SS hash images (smallest hash = likely BOX product shot)
    "25th-anniversary-collection": "https://www.pokemon-card.com/ex/25th/assets/images/ogp.png",
    "legendary-heartbeat": "https://www.pokemon-card.com/products/2020/images/eb668ccf27a31544008326b25c3d9fede7f13c44.jpg",
    "battle-region": "https://www.pokemon-card.com/products/2022/images/79746767519b5ba6dd56f6db2b0cc45f7b339239.jpg",
    "dark-phantasma": "https://www.pokemon-card.com/products/2022/images/37473c1c891bda09413eba43ee4026dff189d231.jpg",
    "incandescent-arcana": "https://www.pokemon-card.com/products/2022/images/448a6c0644b25b43d1b7797a87acc3cf5956a12d.png",
    "skyscraping-perfect": "https://www.pokemon-card.com/products/2021/images/e7ea10f26dd5be124ed3d4a4c4093a25010e2b5d.jpg",
    "blue-sky-stream": "https://www.pokemon-card.com/products/2021/images/65230c1563ea750dd0bd17ad6f820e84fc4a9c3c.jpg",
}


def download(url: str, dest: Path) -> int:
    """Download URL to dest. Returns size in bytes. Raises on error."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return len(data)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    skipped = 0
    failed = 0

    for slug, (code, path_prefix, fname) in BOX_IMAGES.items():
        ext = Path(fname).suffix.lower()  # .png / .jpg
        dest = OUT_DIR / f"{slug}{ext}"

        if dest.exists():
            print(f"SKIP: {slug} (exists at {dest.name})")
            skipped += 1
            continue

        url = f"{BASE}/{code}/{path_prefix}/{fname}"
        try:
            size = download(url, dest)
            print(f"OK:   {slug} -> {dest.name} ({size:,} bytes)")
            total += 1
        except Exception as e:
            print(f"FAIL: {slug} [{url}]: {e}")
            failed += 1

    # Direct URL group
    for slug, url in BOX_IMAGES_DIRECT.items():
        ext = Path(url.split("?")[0]).suffix.lower()
        dest = OUT_DIR / f"{slug}{ext}"
        if dest.exists():
            print(f"SKIP: {slug} (exists at {dest.name})")
            skipped += 1
            continue
        try:
            size = download(url, dest)
            print(f"OK:   {slug} -> {dest.name} ({size:,} bytes) [direct]")
            total += 1
        except Exception as e:
            print(f"FAIL: {slug} [{url}]: {e}")
            failed += 1

    print(f"\n--- Summary: {total} downloaded, {skipped} skipped, {failed} failed ---")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
