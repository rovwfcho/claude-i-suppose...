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
2. The window's corners: the drawing's picture area and the light field from both front photos
   (along the board, round 44; across it, above) must lie inside the window's rounded corners too,
   not just between its straight edges, which is all rounds 2, 44 and the check above look at.
3. How hard the screws may be tightened: the plastic each screw clamps, read from the back cover's
   STL for every head the documents offered (round 5 estimated one head size by hand). Under the head: the recess floor's first layer is two bridged segments with a 3.4 mm slot
   between them (round 35's bridging trick), so a head presses only on the parts of it outside the
   slot. At the post's end: the ring of the brass standoff's top outside the 3.4 mm hole (4.5 mm
   round as measured, or a 4 mm hex), with the screw up to 0.29 mm off centre (round 35's worst).
   With a fingertip-tight 0.05 N m (preload about T / (0.2 d)), the pressure on the plastic must stay
   under 30 MPa (printed PLA starts to yield at about 50 and creeps above about half that), for the
   heads the README recommends.
4. The window as sliced: in PrusaSlicer's G-code for the lid (printed face down, mirrored for print),
   the opening's four edges, found along lines through the window's centre on four layers (two in the
   chamfer, two in the straight part), must sit where case.py puts them, within 0.1 mm. That
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
LIGHT_Y = [3.0, 56.4]                    # replaced by what across_photos() measures


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
    LIGHT_Y[:] = [lo, hi]
    agree = max(abs(res[0][3] - res[1][3]), abs(res[0][4] - res[1][4]))
    ok = wb <= lo - 0.1 and wt >= hi + 0.1 and agree < 0.3 and all(abs(r[4] - r[3] - 53.2) < 0.6 for r in res)
    report(ok, "light field across the board: " + "; ".join(
        f"photo {p}: board {px} px tall, field y {a:.2f}-{b:.2f} mm" for _, p, px, a, b in res)
        + f" (the photos agree within {agree:.2f} mm); the window runs y {wb:.2f}-{wt:.2f}, "
          f"{lo - wb:.2f} mm past the field at the bottom and {wt - hi:.2f} mm at the top")


# ------------------------------------------------------------------ 2
def corners():
    wl, wr = case.WIN_CX - case.WIN_W / 2, case.WIN_CX + case.WIN_W / 2
    wb, wt = case.WIN_CY - case.WIN_H / 2, case.WIN_CY + case.WIN_H / 2
    r = case.WIN_R

    def margin(x, y):
        """How far inside the rounded window the point is (negative: outside)."""
        cx, cy = min(max(x, wl + r), wr - r), min(max(y, wb + r), wt - r)
        if (cx, cy) == (x, y):
            return min(x - wl, wr - x, y - wb, wt - y)
        return r - float(np.hypot(x - cx, y - cy))
    fields = {"drawing's picture area": (9.3, 95.7, 4.1, 55.9),
              "light field (your photos)": (8.0, 95.2, LIGHT_Y[0], LIGHT_Y[1])}
    out, ok = [], True
    for name, (x0, x1, y0, y1) in fields.items():
        m = [margin(x, y) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        ok = ok and min(m) > 0
        out.append(f"{name} corners {min(m):.2f} mm inside at least")
    report(ok, f"window corners ({r:.1f} mm round): " + "; ".join(out))


# ------------------------------------------------------------------ 3
def section_xy(mesh, z):
    """The mesh's section at height z as a shapely geometry in the design's x, y."""
    import trimesh
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    planar, tf = sec.to_2D()
    to3 = lambda ring: trimesh.transform_points(np.column_stack([np.asarray(ring.coords), np.zeros(len(ring.coords))]), tf)[:, :2]  # noqa: E731
    return unary_union([Polygon(to3(p.exterior), [to3(r) for r in p.interiors]) for p in planar.polygons_full])


def clamp():
    from shapely.geometry import Point, Polygon
    sys.path.insert(0, HERE)
    from round1 import load_assembled
    _, _, cover, z_total = load_assembled("battery")
    seat = z_total - case.SCREW_HEAD_DEPTH
    floor = section_xy(cover, seat - case.RECESS_BRIDGE / 2)      # the layer the head presses on
    end = section_xy(cover, case.POST_Z + 0.1)                      # the post's end face on the standoff
    torque, k, d, limit = 0.05, 0.2, 2.5e-3, 30.0
    force = torque / (k * d)                                       # N
    offs = [(0.0, 0.0)] + [(0.29 * np.cos(a), 0.29 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 16, endpoint=False)]

    def hexagon(cx, cy, af, rot):
        rc = af / np.sqrt(3)
        return Polygon([(cx + rc * np.cos(rot + i * np.pi / 3), cy + rc * np.sin(rot + i * np.pi / 3)) for i in range(6)])
    heads = {"5.0 mm pan head (ISO 7045) or 5 mm M2 washer": 5.0, "4.7 mm button head (ISO 7380)": 4.7,
             "4.5 mm cheese head (ISO 1207)": 4.5}
    areas = {}
    for px, py in case.POSTS:
        for name, dk in heads.items():
            for ox, oy in offs:
                a = floor.intersection(Point(px + ox, py + oy).buffer(dk / 2, 256)).area
                areas[name] = min(areas.get(name, 1e9), a)
        for ox, oy in offs:
            a = end.intersection(Point(px + ox, py + oy).buffer(case.STANDOFF_D / 2, 256)).area
            areas["post end on a 4.5 mm round standoff"] = min(areas.get("post end on a 4.5 mm round standoff", 1e9), a)
            for rot in np.linspace(0, np.pi / 3, 7):
                a = end.intersection(hexagon(px + ox, py + oy, 4.0, rot)).area
                areas["post end on a 4 mm hex standoff"] = min(areas.get("post end on a 4 mm hex standoff", 1e9), a)
    # the README and both guides must steer away from the smaller heads; otherwise they count
    g = os.path.join(ROOT, "docs", "guide-src")
    warned = all(w in open(f, encoding="utf-8").read() for f, w in (
        (os.path.join(ROOT, "README.md"), "Not cheese or button heads"),
        (os.path.join(g, "text_en.py"), "Not cheese or button heads"),
        (os.path.join(g, "text_bg.py"), "Не използвайте цилиндрични или полусферични (бутонни) глави")))
    recommended = [n for n in areas if "head" not in n or n.startswith("5.0") or not warned]
    worst = max(force / areas[n] for n in recommended)
    report(worst <= limit, f"screw clamp at a fingertip-tight {torque} N m ({force:.0f} N): " + "; ".join(
        f"{n} {areas[n]:.1f} mm2, {force / areas[n]:.0f} MPa, yields at about {50e6 * areas[n] * 1e-6 * k * d:.2f} N m"
        for n in areas) + f"; the README and both guides warn off the smaller heads: {warned}; worst for the heads they offer "
             f"{worst:.0f} MPa (want {limit:.0f})")


# ------------------------------------------------------------------ 4
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
    c = case.WIN_CHAMFER                                           # the window's chamfer: depth, widths
    width = {"left": case.WIN_CHAMFER_LEFT, "right": c, "bottom": case.WIN_CHAMFER_BOTTOM, "top": c}
    half_w, half_h = case.WIN_W / 2, case.WIN_H / 2
    rows, worst = [], 0.0
    for z_top in (0.4, 0.6, 1.0, 1.2):
        z = min(ex, key=lambda k: abs(k - z_top))
        seg = np.array([s[:5] for s in ex[z]])
        a, b, w = seg[:, :2], seg[:, 2:4], seg[:, 4]
        grow = max(0.0, 1 - (z - 0.1) / c)                         # share of the chamfer's width (layer middle)
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
            want = (half_w if d_[0] else half_h) + grow * width[name]
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
    corners()
    clamp()
    window_sliced()
    print(f"\nRound 45: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
