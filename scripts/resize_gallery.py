"""
Makes web-sized copies of the photos in images/gallery_og/.

  images/gallery_og/         ← put your original photos here (any size).
    2019-bandung/              Gitignored: never uploaded. Subfolders = albums.
      IMG_1234.jpg
        │
        ▼   python scripts/resize_gallery.py
  images/gallery/            ← web copies. These get committed and published.
    2019-bandung/
      IMG_1234.jpg             display size (long side 2000px max)
      thumb/IMG_1234.jpg       thumbnail (long side 600px max), for grids

What it does to each photo:
  - rotates it upright (phones store rotation as a tag, not in the pixels)
  - shrinks it (never enlarges a photo that's already small)
  - saves it as a compressed JPEG
  - drops all metadata (EXIF). Phone photos usually contain the GPS
    location where they were taken, which you don't want to publish.

Run it on your own PC after adding or removing photos. It skips photos
that are already done, and deletes copies whose original you removed.

Don't put files into images/gallery/ by hand: the script treats that
folder as its own output and deletes any photo there that has no
original in images/gallery_og/.

Needs Pillow (the Python image library):   pip install pillow
"""

import shutil
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow isn't installed. Run:  pip install pillow")

# ── Settings ──
DISPLAY_SIZE = 2000   # longest side of the display copy, in pixels
THUMB_SIZE = 600      # longest side of the thumbnail, in pixels
QUALITY = 82          # JPEG quality, 1-100. ~80 looks identical on screen
                      # and is a fraction of the file size.

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "images" / "gallery_og"
OUTPUT = ROOT / "images" / "gallery"
PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def save_resized(img, size, dest, src, clean_jpeg):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if clean_jpeg and max(img.size) <= size:
        # Already a small JPEG with no metadata: copy it as is. Re-saving
        # an already-compressed JPEG makes it bigger, not better.
        shutil.copyfile(src, dest)
        return
    copy = img.copy()
    copy.thumbnail((size, size), Image.LANCZOS)  # shrink to fit, keep proportions
    # No exif= argument, so no metadata is written
    copy.save(dest, "JPEG", quality=QUALITY, optimize=True, progressive=True)


def main():
    if not SOURCE.exists():
        sys.exit(f"No {SOURCE.relative_to(ROOT)} folder. Put photos there first.")

    made, skipped, expected = 0, 0, set()
    for src in sorted(SOURCE.rglob("*")):
        if not src.is_file():
            continue
        if src.suffix.lower() not in PHOTO_TYPES:
            if src.suffix.lower() in {".heic", ".heif"}:
                print(f"  skipped {src.name}: iPhone HEIC format. Export it as JPEG first.")
            continue

        rel = src.relative_to(SOURCE).with_suffix(".jpg")  # every output is a .jpg
        display = OUTPUT / rel
        thumb = OUTPUT / rel.parent / "thumb" / rel.name
        expected.update({display, thumb})

        # Already done, and the original hasn't changed since? Skip it.
        if (display.exists() and thumb.exists()
                and display.stat().st_mtime >= src.stat().st_mtime):
            skipped += 1
            continue

        with Image.open(src) as img:
            # A JPEG with no metadata at all (no EXIF, no rotation tag)
            clean_jpeg = img.format == "JPEG" and len(img.getexif()) == 0
            img = ImageOps.exif_transpose(img)  # rotate upright
            img = img.convert("RGB")            # JPEG has no transparency
            save_resized(img, DISPLAY_SIZE, display, src, clean_jpeg)
            save_resized(img, THUMB_SIZE, thumb, src, clean_jpeg)
        made += 1
        print(f"  {rel.as_posix()}: {src.stat().st_size // 1024} KB -> "
              f"{display.stat().st_size // 1024} KB (+ {thumb.stat().st_size // 1024} KB thumb)")

    # Delete copies whose original is gone
    removed = 0
    if OUTPUT.exists():
        for out in OUTPUT.rglob("*.jpg"):
            if out not in expected:
                out.unlink()
                removed += 1
        for folder in sorted(OUTPUT.rglob("*"), reverse=True):  # tidy empty folders
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()

    print(f"Done: {made} resized, {skipped} already up to date, {removed} removed.")


if __name__ == "__main__":
    main()
