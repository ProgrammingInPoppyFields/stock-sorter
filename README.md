# stock_sorter.py 🗂️

<img src="https://images.unsplash.com/photo-1717079556930-804fbc52e4fa?q=80&w=1740&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" alt="hero" width="100%" style="height:300px;object-fit:cover;display:block;" />

A Python script that looks at your images and puts them in folders based on what color they are. Very groundbreaking stuff.

---

## What it actually does

You have a folder full of stock photos. They are all just sitting there, loose, unsorted, living in chaos. This script fixes that by analyzing each image's pixel colors, deciding which color vibe it belongs to, and moving it into the appropriate folder. The folders live inside whatever directory you point it at.

It also unpacks everything back out if you change your mind, and can delete duplicate files if you've somehow ended up with the same image twice (happens to the best of us).

---

## Requirements

Python 3.x and Pillow. If you don't have Pillow:

```
pip install pillow
```

---

## Usage

```
python stock_sorter.py /path/to/your/image/folder
```

Then pick one of three options:

1. **Sort** — moves all loose images into color subfolders
2. **Unpack** — moves everything back out to the root directory
3. **Remove duplicates** — finds exact duplicate files and offers to delete them

"Loose images" means files sitting directly in the target directory. Anything already inside a subfolder is left alone, so you can run this multiple times without it re-sorting things that are already sorted.

---

## Color categories

The script sorts images into these folders:

| Folder | What ends up there |
|---|---|
| `RED` | Red things |
| `ORANGE` | Orange things |
| `YELLOW` | Yellow things |
| `GREEN` | Green things |
| `TURQUOISE` | Teal, cyan, that kind of situation |
| `BLUE` | Blue things |
| `PURPLE` | Purple things |
| `PINK` | Pink things |
| `BROWN` | Warm tones with low saturation — wood, dirt, coffee, leather, your Monday morning |
| `MONOCHROME` | Barely any color to speak of. Black, white, gray, fog, concrete, despair |
| `RAINBOW` | Couldn't make up its mind. No single color owned more than 50% of the saturated pixels, so here it lives |

Classification works by downsampling each image to 150×150, converting pixels to HSV, filtering out near-black, blown-out, and low-saturation pixels, then seeing which color bucket wins. If nothing dominates, it's a rainbow. If the whole thing is basically desaturated, it's monochrome.

---

## A word of warning

The color sorting is math, not magic. It downsamples your image to a tiny thumbnail, runs some HSV arithmetic, and makes its best guess. This works surprisingly well most of the time, and then occasionally it will put a perfectly normal sunset photo in MONOCHROME or file a green forest shot under RAINBOW and you will have no idea why.

This is not a bug. This is a statistical model making a judgment call on 22,500 pixels of heavily compressed image data. Sometimes it's wrong. Sometimes it's confidently, spectacularly wrong. A photo of a red barn at dusk might end up in ORANGE. A blue sky with a lot of clouds might land in MONOCHROME. An image that looks clearly purple to your human eyes might register as PINK because the hue was 319° and the cutoff is 320°.

You can re-sort anything that ends up in the wrong place manually. That's what folders are for. Don't blame us, blame the HSV color space.

---

## Notes

- Large images are supported. The decompression bomb limit is disabled, so massive stock photos won't crash it.
- GIF support exists but only the first frame is analyzed. Animated GIFs will be sorted based on their opening shot, which may or may not be representative.
- Duplicate detection is MD5-based, meaning byte-for-byte identical files only. A resaved JPEG of the same photo will not be caught.
- If you unpack into a folder that already has a file with the same name, it will rename the incoming file rather than overwrite anything.