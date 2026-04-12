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

    print(f"\n--- Summary: {total} downloaded, {skipped} skipped, {failed} failed ---")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
