"""Compress BOX images for faster Netlify delivery.

- JPGs are re-saved with quality=82 and progressive encoding
- PNGs are re-saved with optimize=True
- If the image is > 1200px wide, it's scaled down to 1200px max
- Only writes if the new file is smaller than the original
- Idempotent: re-running skips already-compressed files via a marker file
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
BOXES_DIR = ROOT / "images" / "boxes"
MARKER_FILE = BOXES_DIR / ".compressed"

MAX_WIDTH = 1200
JPG_QUALITY = 82

def main():
    if not BOXES_DIR.exists():
        print(f"ERROR: {BOXES_DIR} not found")
        sys.exit(1)

    already_done: set[str] = set()
    if MARKER_FILE.exists():
        already_done = set(MARKER_FILE.read_text(encoding="utf-8").strip().split("\n"))

    total_before = 0
    total_after = 0
    processed = 0
    skipped = 0

    for img_path in sorted(BOXES_DIR.glob("*")):
        if img_path.name.startswith(".") or img_path.is_dir():
            continue
        if img_path.name in already_done:
            skipped += 1
            continue

        ext = img_path.suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue

        before_size = img_path.stat().st_size

        try:
            img = Image.open(img_path)
        except Exception as e:
            print(f"FAIL: {img_path.name} - {e}")
            continue

        # Resize if too wide
        resized = False
        if img.width > MAX_WIDTH:
            new_h = int(img.height * MAX_WIDTH / img.width)
            img = img.resize((MAX_WIDTH, new_h), Image.LANCZOS)
            resized = True

        # Save to temp path, then swap if smaller
        tmp_path = img_path.with_suffix(img_path.suffix + ".tmp")
        save_kwargs: dict = {}
        fmt = None

        if ext in {".jpg", ".jpeg"}:
            # Preserve mode
            if img.mode != "RGB":
                img = img.convert("RGB")
            save_kwargs = {"quality": JPG_QUALITY, "optimize": True, "progressive": True}
            fmt = "JPEG"
        elif ext == ".png":
            save_kwargs = {"optimize": True}
            fmt = "PNG"
        elif ext == ".webp":
            save_kwargs = {"quality": 85, "method": 6}
            fmt = "WEBP"

        try:
            img.save(tmp_path, format=fmt, **save_kwargs)
        except Exception as e:
            print(f"FAIL save: {img_path.name} - {e}")
            tmp_path.unlink(missing_ok=True)
            continue

        after_size = tmp_path.stat().st_size

        if after_size < before_size:
            # Replace original
            tmp_path.replace(img_path)
            saved = before_size - after_size
            pct = (saved / before_size) * 100
            extra = " (resized)" if resized else ""
            print(f"OK:   {img_path.name}  {before_size:>8,} -> {after_size:>8,}  -{pct:.0f}%{extra}")
            total_before += before_size
            total_after += after_size
            processed += 1
            already_done.add(img_path.name)
        else:
            tmp_path.unlink(missing_ok=True)
            print(f"SKIP: {img_path.name}  already optimal ({before_size:,})")
            already_done.add(img_path.name)

    # Persist marker
    MARKER_FILE.write_text("\n".join(sorted(already_done)), encoding="utf-8")

    if processed:
        saved_total = total_before - total_after
        pct_total = (saved_total / total_before) * 100 if total_before else 0
        print(
            f"\n=== {processed} compressed, {skipped} skipped (already done) ===\n"
            f"Total: {total_before:,} -> {total_after:,}  "
            f"(saved {saved_total:,} bytes, -{pct_total:.0f}%)"
        )
    else:
        print(f"\n=== All done ({skipped} already compressed) ===")


if __name__ == "__main__":
    main()
