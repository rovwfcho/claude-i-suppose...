#!/usr/bin/env python3
"""Debug round 44 (session 5): your front photo (photo 14: the ruler along the board's long edge).

Methods not used in rounds 1-43:
1. The ruler's scale is not the same along the photo (the camera was tilted: about 16.1 px/mm near
   the left end of the board and 15.4 near the right), so instead of one scale, the ruler's own
   centimetre and half-centimetre ticks are found (the longest ticks) and positions along the board
   are read between them.
2. Along a clean line through the display: where the light field starts and ends, from the left end
   of the board (the ruler's zero sits 0.4 mm inside it).
3. The text on the screen ("Turned off ..."), which the firmware centres on the picture: the middle
   of its extent along the board.
The window must start before the light field and before the picture area the text's centre implies
(and before Waveshare's drawing's), and end after both.
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import case  # noqa: E402

problems = []
EDGE = -0.4          # the board's left end on the ruler (its zero tick is 0.4 mm inside the board's edge)


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def main():
    meta = json.load(open(os.path.join(HERE, "owner_photos", "crops.json")))["front_long"]
    ox, oy = meta["offset"]
    g = np.asarray(Image.open(os.path.join(HERE, "owner_photos", "front_long.jpg")).convert("L")).astype(float)
    # 1. the ruler's cm and half-cm ticks (full-photo y, found as the longest ticks, round 44), and a
    # smooth curve through them: mm along the ruler at any photo row
    # (the 50 mm tick is left out: the big circled 5 printed over it pulls the found tick 0.5 mm)
    ticks = [(205.0, 0), (365.5, 10), (447.0, 15), (525.5, 20), (603.5, 25), (684.0, 30), (759.5, 35),
             (920.5, 45), (1156.0, 60), (1234.0, 65), (1313.0, 70), (1392.0, 75), (1474.0, 80),
             (1547.0, 85), (1625.0, 90), (1701.5, 95)]
    ty, tm = np.array(ticks).T
    fit = np.polyfit(ty, tm, 2)
    res = tm - np.polyval(fit, ty)
    to_mm = lambda y: float(np.polyval(fit, y)) - EDGE   # noqa: E731
    d1 = np.polyval(np.polyder(fit), ty)
    local = 1 / d1
    # 2. the light field along the photo column x 1100 (no text there)
    col = gaussian_filter1d(g[:, 1100 - ox - 3:1100 - ox + 4].mean(1), 1.5)
    gr = np.diff(col)
    y_start = 300 - oy + int(np.argmax(gr[300 - oy:360 - oy]))             # dark band -> light field
    y_end = 1680 - oy + int(np.argmin(gr[1680 - oy:1715 - oy]))            # light field -> its edge line
    light = (to_mm(y_start + oy + 0.5), to_mm(y_end + oy + 0.5))
    # 3. the text: dark pixels in the display between photo x 760 and 1360
    sub = g[300 - oy:1700 - oy, 760 - ox:1360 - ox] < 90
    rows = np.where(sub.sum(1) > 2)[0] + 300
    rows = rows[rows > 400]                                  # leave out the tail strip's printing
    text_mid = to_mm((rows.min() + rows.max()) / 2)
    implied = (text_mid - 43.2, text_mid + 43.2)            # 86.4 mm picture centred on the text
    wl, wr = case.WIN_CX - case.WIN_W / 2, case.WIN_CX + case.WIN_W / 2
    print(f"  ..   ruler: {len(ticks)} cm and half-cm ticks, scale {local.max():.2f} px/mm at the left end to "
          f"{local.min():.2f} at the right, the curve within {np.abs(res).max():.2f} mm of every tick")
    ok = wl <= min(light[0], implied[0] + 0.15, 9.3) and wr >= max(light[1], 95.7) and implied[1] <= wr
    ok = ok and np.abs(res).max() < 0.4
    report(ok, f"your front photo: light field {light[0]:.1f}-{light[1]:.1f} mm from the left end, text centred at "
               f"{text_mid:.1f} mm (a centred 86.4 mm picture would be {implied[0]:.1f}-{implied[1]:.1f}); Waveshare's "
               f"drawing 9.3-95.7; the window runs {wl:.1f}-{wr:.1f} mm and covers all of them")


if __name__ == "__main__":
    main()
    print(f"\nRound 44: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
