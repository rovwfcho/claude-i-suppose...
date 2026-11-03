#!/usr/bin/env python3
"""preview/explained.png: why the frame is wider on the left, and the thickness, from case.py.

  python3 make_explained.py specs   -> writes explained_specs.json (two renders: front, bottom edge)
  python3 make_explained.py compose -> the picture, with a to-scale diagram of the board's front
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

G = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(G))
sys.path.insert(0, G)
from make_specs import BOARD, case, parts  # noqa: E402

FONT, BOLD = "/usr/share/fonts/opentype/inter/Inter-Regular.otf", "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
BG, RED, INK, MUTE = (244, 244, 242), (200, 30, 30), (29, 29, 31), (90, 90, 96)
Z_TOTAL = case.Z_B + case.CAVITY["battery"] + case.T_BACK
WL, WR = case.WIN_CX - case.WIN_W / 2, case.WIN_CX + case.WIN_W / 2
WB, WT = case.WIN_CY - case.WIN_H / 2, case.WIN_CY + case.WIN_H / 2
LIGHT = (8.0, 95.2)            # the light field along the board in the owner's front photo (round 44)
ACTIVE = (9.3, 95.7, 4.1, 55.9)  # Waveshare's drawing


def specs():
    whole = parts(["shell", "cover"] + BOARD)
    s = {"e_front": {"parts": whole, "cam": {"t": [49.75, 30, 0], "o": [0, 0, 900]}, "fov": 7.5, "w": 1300, "h": 900,
                     "labels": [[case.X0, 30, 0], [WL, 30, 0], [WR, 30, 0], [case.X1, 30, 0],
                                [52, case.Y1, 0], [52, WT, 0], [52, WB, 0], [52, case.Y0, 0]]},
         "e_edge": {"parts": whole, "cam": {"t": [49.75, case.Y0, Z_TOTAL / 2], "o": [0, -900, 0], "up": [0, 0, 1]},
                    "fov": 7.5, "w": 1300, "h": 420, "labels": [[case.X1, case.Y0, 0], [case.X1, case.Y0, Z_TOTAL]]}}
    json.dump(s, open(os.path.join(G, "explained_specs.json"), "w"))
    print("wrote explained_specs.json")


def crop_white(im, pts, pad=30):
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y][0] > 250 and px[x, y][1] > 250 and px[x, y][2] > 250:
                px[x, y] = BG
    return im.crop((x0, y0, x1, y1)), [(x - x0, y - y0) for x, y in pts]


def dim(d, a, b, text, font, horizontal=True):
    d.line([a, b], fill=RED, width=3)
    for p in (a, b):
        d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=RED)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    d.text((mx, my - 26) if horizontal else (mx + 14, my), text, font=font, fill=RED, anchor="mm" if horizontal else "lm")


def diagram(width):
    """The board's front to scale: PCB, glass, the drawing's picture area, the photo's light field, the window."""
    k = (width - 60) / case.BW
    H = int(case.BH * k) + 60
    im = Image.new("RGB", (width, H), BG)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 20)
    X = lambda x: 30 + x * k            # noqa: E731
    Y = lambda y: 30 + (case.BH - y) * k  # noqa: E731
    d.rounded_rectangle([X(0), Y(case.BH), X(case.BW), Y(0)], radius=int(case.BR * k), fill=(29, 79, 145))
    d.rectangle([X(0.75), Y(58.5), X(98.5), Y(1.5)], fill=(236, 236, 232))                  # glass
    d.rectangle([X(LIGHT[0]), Y(57.6), X(LIGHT[1]), Y(2.4)], fill=(214, 216, 214))         # light field (photo)
    ax0, ax1, ay0, ay1 = ACTIVE
    d.rectangle([X(ax0), Y(ay1), X(ax1), Y(ay0)], outline=(60, 60, 60), width=2)            # drawing's picture
    d.rectangle([X(WL), Y(WT), X(WR), Y(WB)], outline=RED, width=4)                          # window
    d.text((X(ax0) + 8, Y(ay1) + 8), "picture area (Waveshare's drawing)", font=f, fill=(60, 60, 60))
    d.text((X(WL) + 8, Y(WB) - 30), "case window", font=f, fill=RED)
    d.text((X(1.2), Y(30)), "glass\nstrip", font=f, fill=MUTE)
    return im


def fit(im, pts, w, h):
    s = min(w / im.width, h / im.height)
    return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS), [(x * s, y * s) for x, y in pts]


def wrap(d, text, font, x, y, width, fill=INK, gap=10):
    words, line = text.split(), ""
    for wd in words:
        t = (line + " " + wd).strip()
        if d.textlength(t, font=font) > width:
            d.text((x, y), line, font=font, fill=fill)
            y += font.size + gap
            line = wd
        else:
            line = t
    d.text((x, y), line, font=font, fill=fill)
    return y + font.size + gap


def compose():
    labels = json.load(open(os.path.join(G, "labels.json")))
    font, small, bold = ImageFont.truetype(FONT, 26), ImageFont.truetype(FONT, 22), ImageFont.truetype(BOLD, 34)
    front, fp = crop_white(Image.open(os.path.join(G, "e_front.png")).convert("RGB"), labels["e_front"]["labels"])
    edge, ep = crop_white(Image.open(os.path.join(G, "e_edge.png")).convert("RGB"), labels["e_edge"]["labels"])
    front, fp = fit(front, fp, 840, 600)
    edge, ep = fit(edge, ep, 760, 200)
    dd = ImageDraw.Draw(front)
    lab = ImageFont.truetype(BOLD, 28)
    for (a, b), v, hor in (((0, 1), WL - case.X0, True), ((2, 3), case.X1 - WR, True),
                           ((4, 5), case.Y1 - WT, False), ((6, 7), WB - case.Y0, False)):
        dim(dd, fp[a], fp[b], f"{v:.1f}" + (" mm" if a == 0 else ""), lab, hor)
    W = 1800
    sheet = Image.new("RGB", (W, 1330), BG)
    d = ImageDraw.Draw(sheet)
    d.text((40, 28), f"Final case: {case.X1 - case.X0:.1f} × {case.Y1 - case.Y0:.1f} × {Z_TOTAL:.1f} mm: board screwed "
                     f"to the back, lid on 4 clips", font=bold, fill=INK)
    sheet.paste(front, (40, 100))
    dia = diagram(880)
    sheet.paste(dia, (W - dia.width - 30, 100 + (front.height - dia.height) // 2))
    ax0, ax1, ay0, ay1 = ACTIVE
    y = 100 + max(front.height, dia.height) + 24
    y = wrap(d, f"Why the left edge is wider ({WL - case.X0:.1f} mm vs about 6 mm elsewhere): the display's picture area is "
                f"not centred on the board. Waveshare's drawing puts it {ax0:.1f} mm from the left PCB edge but only "
                f"{case.BW - ax1:.1f} mm from the right; the strip on the left is inactive glass with the display's ribbon "
                f"cable. In your front photo the light field starts {LIGHT[0]:.1f} mm from the left edge and the centred "
                f"text sits 1.2 mm left of the drawing's centre, so the window reaches to {WL:.1f} mm, "
                f"{ax0 - WL:.1f} mm before the drawing's picture area (and {WR - ax1:.1f} mm past it on the right): "
                f"whichever is right, no pixel is hidden.", font, 40, y, W - 80)
    y = wrap(d, f"Seen edge-on (bottom edge): {Z_TOTAL:.1f} mm thick. The speaker sits beside the battery, so it adds "
                f"no thickness; the opening is for the PWR and BOOT buttons.", font, 40, y + 14, W - 80)
    sheet.paste(edge, ((W - edge.width) // 2 - 100, y + 10))
    ex = (W - edge.width) // 2 - 100 + edge.width + 40
    top, bot = y + 10 + ep[1][1], y + 10 + ep[0][1]
    top, bot = min(top, bot), max(top, bot)
    d.line([(ex, top), (ex, bot)], fill=RED, width=3)
    for yy in (top, bot):
        d.line([(ex - 10, yy), (ex + 10, yy)], fill=RED, width=3)
    d.text((ex + 22, (top + bot) / 2), f"{Z_TOTAL:.1f} mm", font=lab, fill=RED, anchor="lm")
    y = y + 10 + edge.height + 24
    y = wrap(d, f"Thickness = {case.T_FRONT:.1f} front + {case.PANEL_SPACE:.1f} display + {case.PCB_T:.1f} PCB + "
                f"{case.PARTS_SPACE:.1f} parts room + {case.BATTERY_SPACE:.1f} battery room "
                f"({case.BATTERY_SIZE[2]:.1f} mm cell) + {case.T_BACK:.1f} back.", font, 40, y, W - 80)
    d.text((40, y + 4), "Renders from the STL files; the diagram is to scale from case.py, Waveshare's drawing and your "
                        "front photo.", font=small, fill=MUTE)
    sheet = sheet.crop((0, 0, W, min(sheet.height, y + 50)))
    out = os.path.join(ROOT, "preview", "explained.png")
    sheet.save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    {"specs": specs, "compose": compose}[sys.argv[1]]()
