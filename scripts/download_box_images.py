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

# slug -> (series_code, filename)
# verified via probe_box_images.sh + follow-up checks
BOX_IMAGES: dict[str, tuple[str, str]] = {
    # MEGA series
    "mega-brave": ("m1", "product-img-1.png"),
    "mega-sinfonia": ("m1", "product-img-2.png"),
    "inferno": ("m2", "product-img-01.png"),
    "mega-ex": ("m2a", "product-img-01.png"),
    "munikis-zero": ("m3", "product-img-02.png"),
    "ninja-spinner": ("m4", "product-img-01-4gmgu.png"),
    # SV numbered
    "scarlet-ex": ("sv1", "hero-visual.jpg"),
    "violet-ex": ("sv1", "hero-visual.jpg"),  # same landing page as scarlet-ex
    "151": ("sv2a", "hero-visual.png"),
    "ruler-of-black-flame": ("sv3", "hero-visual.jpg"),
    "ancient-roar": ("sv4", "hero-visual.jpg"),
    "future-flash": ("sv4", "hero-visual.jpg"),  # same landing page
    "shiny-treasure-ex": ("sv4a", "hero-visual.png"),
    "hengen-no-kamen": ("sv6", "hero-visual.jpg"),
    "stellar-miracle": ("sv7", "hero-visual.jpg"),
    "chouden-breaker": ("sv8", "hero-visual.jpg"),
    "terastal-fes-ex": ("sv8a", "hero-pack.png"),
    "battle-partners": ("sv9", "hero-visual.jpg"),
    "rocket-dan-no-eiko": ("sv10", "hero-visual.jpg"),
    "black-bolt": ("sv11", "point03-box-1.png"),
    "white-flare": ("sv11", "point04-box-1.png"),
    # SS series
    "star-birth": ("s9", "product-img-1.png"),
    "time-gazer": ("s10", "product-img-1.png"),
    "space-juggler": ("s10", "hero-img-3.png"),  # different image on same landing page
    "pokemon-go": ("s10b", "product-img-1.png"),
    "paradigm-trigger": ("s12", "product-img-1.png"),
    "vstar-universe": ("s12a", "product-img-1.png"),
    "vmax-climax": ("s8b", "product-img-1.png"),
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

    for slug, (code, fname) in BOX_IMAGES.items():
        ext = Path(fname).suffix.lower()  # .png / .jpg
        dest = OUT_DIR / f"{slug}{ext}"

        if dest.exists():
            print(f"SKIP: {slug} (exists at {dest.name})")
            skipped += 1
            continue

        url = f"{BASE}/{code}/assets/images/{fname}"
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
