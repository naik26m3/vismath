"""
Contact sheets of every question crop, for checking by eye.

    python tools/sheets.py mhr-grade-9 [out_dir]
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
book = sys.argv[1] if len(sys.argv) > 1 else "mhr-grade-9"
out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "tools" / "sheets"
out.mkdir(parents=True, exist_ok=True)

files = sorted((ROOT / "assets" / "books" / book / "questions").glob("*.webp"))
W, MAXH, PER = 560, 330, 14


def tile(p):
    im = Image.open(p).convert("RGB")
    im.thumbnail((W, MAXH))
    c = Image.new("RGB", (W, im.height + 20), "white")
    c.paste(im, (0, 20))
    d = ImageDraw.Draw(c)
    d.rectangle([0, 20, im.width - 1, im.height + 19], outline=(255, 0, 0))
    d.text((4, 3), p.stem, fill=(200, 0, 0))
    return c


for n, i in enumerate(range(0, len(files), PER)):
    tiles = [tile(p) for p in files[i:i + PER]]
    rows = [tiles[j:j + 2] for j in range(0, len(tiles), 2)]
    h = sum(max(t.height for t in r) + 6 for r in rows)
    sheet = Image.new("RGB", (W * 2 + 6, h), (170, 170, 170))
    y = 0
    for r in rows:
        for c, t in enumerate(r):
            sheet.paste(t, (c * (W + 6), y))
        y += max(t.height for t in r) + 6
    sheet.save(out / f"sheet-{n:02d}.png")
    print(f"sheet-{n:02d}.png  {files[i].stem} .. {files[min(i + PER, len(files)) - 1].stem}")
