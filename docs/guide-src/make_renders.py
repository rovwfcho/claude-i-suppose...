#!/usr/bin/env python3
"""preview/renders.png: six views of the case, rendered with scene.html (see build_all.sh).

  python3 make_renders.py specs   -> writes renders_specs.json (the six scenes)
  python3 make_renders.py compose -> puts the rendered r_*.png together with captions
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

G = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(G))
sys.path.insert(0, G)
from make_specs import BOARD, INSIDE, parts  # noqa: E402

FONT = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
BG = (244, 244, 242)
VIEWS = [
    ("r_front", "Front: display window, rounded 7 mm corners and 4.5 mm edges",
     {"parts": parts(["shell", "cover"] + BOARD), "cam": {"t": [49.75, 30, 8], "o": [-75, -120, 185]}}),
    ("r_back", "Back: speaker slots, mic and sensor vents, 4 side screws",
     {"parts": parts(["shell", "cover"] + BOARD), "cam": {"t": [49.75, 30, 8], "o": [80, -120, -185]}}),
    ("r_left", "Left end: USB-C, microSD with finger scoop, mic holes",
     {"parts": parts(["shell", "cover"] + BOARD), "cam": {"t": [-2, 30, 8.3], "o": [-190, -25, 75]}, "fov": 26}),
    ("r_bottom", "Bottom edge: PWR and BOOT left fully open",
     {"parts": parts(["shell", "cover"] + BOARD), "cam": {"t": [72, -2, 7], "o": [35, -95, 70]}, "fov": 30}),
    ("r_top", "Top edge: dial in its thumb scoop",
     {"parts": parts(["shell", "cover"] + BOARD), "cam": {"t": [79, 62, 8.5], "o": [-25, 80, 75]}, "fov": 30}),
    ("r_inside", "Inside the back cover: your battery and speaker, each in its own bay",
     {"parts": parts(["cover"] + INSIDE + ["wire_bat", "wire_spk", "coil_spk"]),
      "cam": {"t": [49.75, 30, 12], "o": [-28, -92, 150]}}),
]
W, H = 900, 640


def specs():
    out = {}
    for name, _, sp in VIEWS:
        sp = dict(sp, w=W, h=H)
        out[name] = sp
    json.dump(out, open(os.path.join(G, "renders_specs.json"), "w"))
    print("wrote renders_specs.json")


def compose():
    font = ImageFont.truetype(FONT, 26)
    tiles = []
    for name, caption, _ in VIEWS:
        im = Image.open(os.path.join(G, name + ".png")).convert("RGB")
        white = Image.new("RGB", im.size, (255, 255, 255))
        box = ImageChops.difference(im, white).getbbox()
        im = im.crop(box)
        im.thumbnail((W - 40, H - 120))
        # the renderer's white background becomes the sheet's warm grey
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                r, g, b = px[x, y]
                if r > 250 and g > 250 and b > 250:
                    px[x, y] = BG
        tiles.append((caption, im))
    sheet = Image.new("RGB", (2 * W, 3 * H), BG)
    d = ImageDraw.Draw(sheet)
    for i, (caption, im) in enumerate(tiles):
        cx, cy = (i % 2) * W, (i // 2) * H
        d.text((cx + 24, cy + 18), caption, font=font, fill=(29, 29, 31))
        sheet.paste(im, (cx + (W - im.width) // 2, cy + 70 + (H - 90 - im.height) // 2))
    out = os.path.join(ROOT, "preview", "renders.png")
    sheet.save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    {"specs": specs, "compose": compose}[sys.argv[1]]()
