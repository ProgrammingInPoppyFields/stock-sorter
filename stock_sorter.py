from PIL import Image
import os
import sys
import shutil
import colorsys
import hashlib

# Disable decompression bomb protection for large stock photos
Image.MAX_IMAGE_PIXELS = None

"""
IMAGE COLOR SORTER
==================

WHAT THIS DOES:
- Sorts loose images in a given directory into color category subfolders
- Only processes free-floating images (top-level files); already-sorted
  images sitting inside color subfolders are left untouched
- If no single color covers >50% of saturated pixels → RAINBOW folder
- Unpacks sorted images back to the root of that directory
- Removes duplicate images based on file content

HOW TO USE:
  python stock_sorter.py /path/to/your/image/folder

Then choose an option:
  1. Sort loose images by color
  2. Unpack all sorted images back to root
  3. Remove duplicate images (loose files only)

COLOR FOLDERS (created directly inside the target directory):
  RED, ORANGE, YELLOW, GREEN, TURQUOISE, BLUE, PURPLE, PINK
  BROWN      — warm hue + low saturation
  MONOCHROME — black/white/gray (low saturation overall)
  RAINBOW    — no single hue dominates ≥50% of saturated pixels

REQUIREMENTS:
  Python 3.x
  Pillow: pip install pillow
"""

# ---------------------------------------------------------------------------
# Color category definitions
# Each entry: (name, list of (hue_min, hue_max) ranges in degrees)
# Hue is 0–360. Red wraps around so it gets two ranges — both are checked
# because hue_to_base_category iterates all ranges per name before moving on.
# ---------------------------------------------------------------------------
COLOR_RANGES = [
    ("RED",       [(0, 15), (345, 360)]),
    ("ORANGE",    [(15, 45)]),
    ("YELLOW",    [(45, 75)]),
    ("GREEN",     [(75, 150)]),
    ("TURQUOISE", [(150, 200)]),
    ("BLUE",      [(200, 270)]),
    ("PURPLE",    [(270, 320)]),
    ("PINK",      [(320, 345)]),
]

ALL_CATEGORIES = [name for name, _ in COLOR_RANGES] + ["BROWN", "MONOCHROME", "RAINBOW"]

# Minimum fraction of saturated pixels a color must own to "win"
DOMINANCE_THRESHOLD = 0.50

# Saturation cutoff — pixels below this are ignored for hue analysis
SAT_MIN = 0.20

# Brightness window — ignore near-black and blown-out pixels
BRIGHT_MIN = 20
BRIGHT_MAX = 235

# Brown: warm hue range + low saturation
BROWN_HUE_MIN = 20
BROWN_HUE_MAX = 70
BROWN_SAT_MAX = 0.35

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def hue_to_base_category(hue: float) -> str | None:
    """Map a hue angle (0–360) to a named color category. Returns None for gaps."""
    for name, ranges in COLOR_RANGES:
        for lo, hi in ranges:
            if lo <= hue < hi:
                return name
    return None


def classify_image(image_path: str) -> str:
    """
    Classify an image into a color category.

    Strategy:
    1. Downsample for speed.
    2. For each pixel, compute HSV.
    3. Skip unsaturated / extreme-brightness pixels.
    4. Check if the pixel is "brown" (warm hue + low saturation).
    5. Otherwise bucket it by hue into a named color category.
    6. If one category owns ≥ DOMINANCE_THRESHOLD of saturated pixels → winner.
    7. If overall saturation is very low → MONOCHROME.
    8. Otherwise → RAINBOW.
    """
    try:
        img = Image.open(image_path)
        img.thumbnail((150, 150), Image.Resampling.LANCZOS)
        img = img.convert("RGB")
        pixels = list(img.getdata())
    except Exception as e:
        print(f"  ✗ Could not open image: {e}")
        return "MONOCHROME"

    buckets: dict[str, int] = {name: 0 for name in ALL_CATEGORIES}
    total_pixels = len(pixels)
    saturated_count = 0

    for r, g, b in pixels:
        brightness = (r + g + b) / 3

        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        hue = h * 360

        # Skip near-black and blown-out
        if not (BRIGHT_MIN < brightness < BRIGHT_MAX):
            continue

        # Skip low-saturation pixels for hue analysis
        if s < SAT_MIN:
            continue

        saturated_count += 1

        # Brown check: warm hue but muted saturation
        if BROWN_HUE_MIN <= hue < BROWN_HUE_MAX and s < BROWN_SAT_MAX:
            buckets["BROWN"] += 1
            continue

        category = hue_to_base_category(hue)
        if category:
            buckets[category] += 1

    # Very few saturated pixels overall → monochrome
    saturation_ratio = saturated_count / total_pixels if total_pixels else 0
    if saturation_ratio < 0.10:
        return "MONOCHROME"

    # Find the dominant category
    winner = max(buckets, key=lambda k: buckets[k])
    winner_fraction = buckets[winner] / saturated_count if saturated_count else 0

    return winner if winner_fraction >= DOMINANCE_THRESHOLD else "RAINBOW"


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

def loose_images_in(folder: str) -> list[str]:
    """
    Return filenames of image files sitting directly in folder (not in subfolders).
    This intentionally skips anything inside a subdirectory, so already-sorted
    images are never touched.
    """
    return [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and os.path.splitext(f.lower())[1] in IMAGE_EXTENSIONS
    ]


def sort_images_by_color(target_dir: str):
    """
    Sort loose images in target_dir into color category subfolders.
    Color folders are created directly inside target_dir.
    Images already inside any subfolder are not touched.
    """
    # Create color subfolders inside target_dir
    for category in ALL_CATEGORIES:
        os.makedirs(os.path.join(target_dir, category), exist_ok=True)

    image_files = loose_images_in(target_dir)

    if not image_files:
        print("No loose images found to sort.")
        return

    print(f"Found {len(image_files)} loose images to sort\n")

    category_counts: dict[str, int] = {c: 0 for c in ALL_CATEGORIES}

    for idx, filename in enumerate(image_files, 1):
        src = os.path.join(target_dir, filename)
        print(f"[{idx}/{len(image_files)}] {filename}")

        category = classify_image(src)
        dst = os.path.join(target_dir, category, filename)

        # Safe copy-then-delete (no data loss if interrupted mid-run)
        shutil.copy2(src, dst)
        os.remove(src)

        category_counts[category] += 1
        print(f"  → {category}")

    print(f"\n{'='*60}")
    print("Done! Breakdown:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        if count:
            print(f"  {cat:<12} {count}")
    print(f"{'='*60}")


def unpack_all_images(target_dir: str):
    """
    Move all images from color category subfolders back into target_dir root.
    Only unpacks known color category folders; ignores anything else.
    """
    existing_categories = [
        c for c in ALL_CATEGORIES
        if os.path.isdir(os.path.join(target_dir, c))
    ]

    if not existing_categories:
        print("No color category folders found inside the target directory.")
        return

    print(f"Unpacking from {len(existing_categories)} color folder(s)...\n")

    total_moved = 0

    for category in existing_categories:
        folder_path = os.path.join(target_dir, category)
        files = [
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]
        print(f"  {category}: {len(files)} images")

        for filename in files:
            src = os.path.join(folder_path, filename)
            dst = os.path.join(target_dir, filename)

            # Resolve filename conflicts
            if os.path.exists(dst):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dst):
                    dst = os.path.join(target_dir, f"{base}_{counter}{ext}")
                    counter += 1

            shutil.move(src, dst)
            total_moved += 1

    print(f"\n{'='*60}")
    print(f"Done! Moved {total_moved} image(s) back to: {target_dir}")
    print(f"{'='*60}")


def remove_duplicates(target_dir: str):
    """
    Remove duplicate images in target_dir root based on file content hash.
    Only checks loose (top-level) files.
    """
    image_files = loose_images_in(target_dir)

    if not image_files:
        print("No loose images found to check.")
        return

    print(f"Found {len(image_files)} loose images to check\n")

    seen_hashes: dict[str, str] = {}
    duplicates: list[str] = []

    for idx, filename in enumerate(image_files, 1):
        filepath = os.path.join(target_dir, filename)
        print(f"[{idx}/{len(image_files)}] {filename}")

        with open(filepath, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        if file_hash in seen_hashes:
            duplicates.append(filepath)
            print(f"  ✗ Duplicate of {seen_hashes[file_hash]}")
        else:
            seen_hashes[file_hash] = filename
            print(f"  ✓ Unique")

    if duplicates:
        print(f"\n{'='*60}")
        print(f"Found {len(duplicates)} duplicate(s)")
        print(f"{'='*60}\n")
        confirm = input("Delete these duplicates? (y/n): ").strip().lower()
        if confirm == "y":
            for dup in duplicates:
                os.remove(dup)
                print(f"  Deleted: {os.path.basename(dup)}")
            print(f"\n✓ Removed {len(duplicates)} duplicate(s)")
        else:
            print("Cancelled. No files deleted.")
    else:
        print(f"\n{'='*60}")
        print("No duplicates found!")
        print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stock_sorter.py /path/to/image/folder")
        sys.exit(1)

    target_dir = os.path.abspath(sys.argv[1])

    if not os.path.isdir(target_dir):
        print(f"Error: '{target_dir}' is not a valid directory.")
        sys.exit(1)

    print("=" * 60)
    print("IMAGE COLOR SORTER")
    print(f"Target: {target_dir}")
    print("=" * 60)
    print("\nOptions:")
    print("1. Sort loose images by color")
    print("2. Unpack all images (move back to root)")
    print("3. Remove duplicate images (loose files only)")

    choice = input("\nEnter your choice (1, 2, or 3): ").strip()

    if choice == "1":
        print(f"\nSorting loose images in: {target_dir}\n")
        sort_images_by_color(target_dir)
    elif choice == "2":
        print(f"\nUnpacking images to: {target_dir}\n")
        unpack_all_images(target_dir)
    elif choice == "3":
        print(f"\nChecking for duplicates in: {target_dir}\n")
        remove_duplicates(target_dir)
    else:
        print("Invalid choice!")