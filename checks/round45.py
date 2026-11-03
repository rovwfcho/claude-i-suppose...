#!/usr/bin/env python3
"""Debug round 45 (session 5): methods not used in rounds 1-44.

1. Your two front photos with the ruler ACROSS the board (photos 11 and 12, cropped into
   owner_photos/front_across_a.jpg and front_across_b.jpg): round 44 measured the light field along
   the board; this measures it across, in y. The board's own 60 mm height is the scale: its two long
   edges are where the blue PCB starts and ends. The light field is bounded on each side by a thin
   dark line, with about 0.9 mm of lighter glass border and the glass's bright edge beyond it.
   Which way up: the text on the screen is upright in the picture's own frame, and its tops point to
   the photo's left, so the board's top edge (y = 60) is on the photo's left (round 44's photo, where
   the tops point right with the left end at the top, gives the same rule: the picture's up is +y).
   The glass is nearer the camera than the PCB, so its features look further from the photo's centre
   than they are; leaving that out makes the field look larger, the safe way round for this check.
   The window must cover the light field in both photos, with at least 0.1 mm to spare.
2. The window as sliced: in PrusaSlicer's G-code for the lid (printed face down, mirrored for print),
   the opening's four edges, found along lines through the window's centre on four layers (two in the
   45 deg chamfer, two in the straight part), must sit where case.py puts them, within 0.1 mm. That
   also confirms that the wide frame is on the end the printer actually prints it on.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402

problems = []
skipped = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def skip(msg):
    print("  SKIP " + msg)
    skipped.append(msg)


# ------------------------------------------------------------------ 1
def edges(path):
    """Board edges and light-field lines (photo columns) in one crop, from the median of its rows."""
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    lum = np.median(a.mean(2), 0)
    blue = np.median(a[:, :, 2] - a[:, :, 0], 0)
    b = np.where(blue > 20)[0]
    left, right = int(b[0]), int(b[-1])                       # the PCB's outer edges (blue solder mask)
    px_mm = (right - left) / case.BH

    def line(start, step):
        """Walking out from 8 mm inside the board's edge (clear of the text on the screen) towards the
        edge: the first column darker than the columns 4 px either side of it by more than 8 levels,
        and the darkest within 3 px of it."""
        i = int(round(start))
        while not ((lum[i - 4] + lum[i + 4]) / 2 - lum[i] > 8 and lum[i] <= lum[i - 3:i + 4].min()):
            i += step
        return i
    return left, right, line(left + 8 * px_mm, -1), line(right - 8 * px_mm, 1)


def across_photos():
    meta = json.load(open(os.path.join(HERE, "owner_photos", "crops.json")))
    wb, wt = case.WIN_CY - case.WIN_H / 2, case.WIN_CY + case.WIN_H / 2
    res = []
    for name in ("front_across_a", "front_across_b"):
        left, right, ll, lr = edges(os.path.join(HERE, "owner_photos", name + ".jpg"))
        to_y = lambda c: case.BH - (c - left) / (right - left) * case.BH   # noqa: E731  photo left = top edge
        res.append((name, meta[name]["photo"], right - left, to_y(lr), to_y(ll)))
    lo = min(r[3] for r in res)
    hi = max(r[4] for r in res)
    agree = max(abs(res[0][3] - res[1][3]), abs(res[0][4] - res[1][4]))
    ok = wb <= lo - 0.1 and wt >= hi + 0.1 and agree < 0.3 and all(abs(r[4] - r[3] - 53.2) < 0.6 for r in res)
    report(ok, "light field across the board: " + "; ".join(
        f"photo {p}: board {px} px tall, field y {a:.2f}-{b:.2f} mm" for _, p, px, a, b in res)
        + f" (the photos agree within {agree:.2f} mm); the window runs y {wb:.2f}-{wt:.2f}, "
          f"{lo - wb:.2f} mm past the field at the bottom and {wt - hi:.2f} mm at the top")


# ------------------------------------------------------------------ 2
def window_sliced():
    exe = shutil.which("prusa-slicer")
    if not exe:
        skip("window as sliced: PrusaSlicer not installed")
        return
    import trimesh
    from round19 import SETTINGS
    from round35 import extrusions_typed
    stl = os.path.join(ROOT, "stl", "front_shell_battery.stl")
    lo, hi = trimesh.load(stl).bounds
    shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2
    with tempfile.TemporaryDirectory() as d:
        g = os.path.join(d, "out.gcode")
        subprocess.run([exe, "--export-gcode", *SETTINGS, "--support-material=0", "-o", g, stl],
                       capture_output=True, text=True, timeout=900, check=True)
        ex = extrusions_typed(open(g).read())
    c = 0.8                                                        # the window's 45 deg chamfer (case.py)
    half_w, half_h = case.WIN_W / 2, case.WIN_H / 2
    rows, worst = [], 0.0
    for z_top in (0.4, 0.6, 1.0, 1.2):
        z = min(ex, key=lambda k: abs(k - z_top))
        seg = np.array([s[:5] for s in ex[z]])
        a, b, w = seg[:, :2], seg[:, 2:4], seg[:, 4]
        grow = max(0.0, c - (z - 0.1))                             # sliced at the layer's middle
        found = {}
        for name, d_ in (("left", (-1, 0)), ("right", (1, 0)), ("bottom", (0, -1)), ("top", (0, 1))):
            t = np.arange(0, 50, 0.01)
            px = case.WIN_CX + d_[0] * t                           # design coordinates along the line
            py = case.WIN_CY + d_[1] * t
            gx, gy = case.BW - px + shift[0], py + shift[1]        # mirrored for print (front_for_print)
            P = np.column_stack([gx, gy])
            ab = b - a
            tt = np.clip(((P[:, None, :] - a[None]) * ab[None]).sum(2) / np.maximum((ab * ab).sum(1), 1e-12)[None], 0, 1)
            dist = np.linalg.norm(a[None] + tt[..., None] * ab[None] - P[:, None, :], axis=2)
            hit = np.where((dist < w[None] / 2).any(1))[0]
            edge = t[hit[0]] if len(hit) else np.nan
            want = (half_w if d_[0] else half_h) + grow
            found[name] = (edge, want)
            worst = max(worst, abs(edge - want)) if not np.isnan(edge) else 99
        rows.append((z, found))
    left_frame = case.WIN_CX - half_w - case.X0
    ok = worst <= 0.1
    report(ok, f"window as sliced (lid face down, mirrored for print): its edges on layers "
               f"{', '.join(f'{z:.1f}' for z, _ in rows)} mm sit within {worst:.2f} mm of case.py's (want 0.1); "
               f"at {rows[-1][0]:.1f} mm the opening runs x {case.WIN_CX - rows[-1][1]['left'][0]:.2f}-"
               f"{case.WIN_CX + rows[-1][1]['right'][0]:.2f}, y {case.WIN_CY - rows[-1][1]['bottom'][0]:.2f}-"
               f"{case.WIN_CY + rows[-1][1]['top'][0]:.2f} (the {left_frame:.1f} mm frame on the USB-C end)")


if __name__ == "__main__":
    across_photos()
    window_sliced()
    print(f"\nRound 45: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
