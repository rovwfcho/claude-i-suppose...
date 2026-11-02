#!/usr/bin/env python3
"""Debug round 5: methods not used in rounds 1-4.

1. Nozzle erosion: every 0.2 mm layer is opened by a 0.4 mm nozzle (erode 0.2, dilate 0.2);
   material that disappears is thinner than one extrusion line and would not print
2. Line of sight: a grid of rays from outside onto each switch tip must reach it unobstructed
3. Strength estimates by hand formulas (PLA, conservative 30 MPa allowable)
4. Port and standoff positions re-measured from the back photo by colour segmentation
   (silver metal parts, brass standoffs) instead of the hand reading used originally
"""
import math
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)

skipped = []


def skip(msg):
    """A check that could not run here (for example, a reference image could not be downloaded)."""
    print("  SKIP " + msg)
    skipped.append(msg)


# ------------------------------------------------------------------ 1
def erosion(variant, layer=0.2, nozzle=0.4):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    shell, cover, _, _ = load_assembled(variant)
    for name, tm in (("front shell", shell), ("back cover", cover)):
        lost_total, worst = 0.0, []
        zs = np.arange(layer / 2, tm.bounds[1][2], layer)
        for z, sec in zip(zs, tm.section_multiplane([0, 0, 0], [0, 0, 1], zs)):
            if sec is None:
                continue
            geom = unary_union(list(sec.polygons_full))
            opened = geom.buffer(-nozzle / 2, join_style=2).buffer(nozzle / 2, join_style=2)
            lost = geom.difference(opened)
            pieces = [g for g in getattr(lost, "geoms", [lost]) if g.area > 0.05]
            for g in pieces:
                lost_total += g.area * layer
                worst.append((round(float(z), 2), round(g.area, 2), tuple(np.round(g.centroid.coords[0], 1))))
        worst.sort(key=lambda w: -w[1])
        report(lost_total < 0.5, f"{variant} {name}: {lost_total:.2f} mm3 thinner than a {nozzle} mm line "
                                 f"(would not print); biggest {worst[:5]}")


# ------------------------------------------------------------------ 2
def line_of_sight(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    asm = trimesh.util.concatenate([shell, cover_asm])
    for name, bx in case.BUTTONS.items():
        tip_y = -case.BTN_PROTRUDE
        xs = np.linspace(bx - 0.7, bx + 0.7, 8)
        zs = np.linspace(case.Z_B + 0.5, case.Z_B + 1.3, 6)
        o = np.array([[x, -20.0, z] for x in xs for z in zs])
        d = np.tile([0.0, 1.0, 0.0], (len(o), 1))
        locs, ir, _ = asm.ray.intersects_location(o, d, multiple_hits=False)
        blocked = sum(1 for l in locs if l[1] < tip_y)
        report(blocked == 0, f"{variant} {name}: {len(o) - blocked}/{len(o)} straight-on rays reach the switch tip "
                             f"with no plastic in the way")


# ------------------------------------------------------------------ 3
def strength():
    s_allow = 30.0  # MPa, PLA printed, conservative
    # display lip bridging the button opening: 3.7 x 1.6 mm bar (lip from the wall to the window),
    # clamped at both ends, 10 N pressed onto its middle
    b, t = case.WIN_CY - case.WIN_H / 2 + case.CLR, case.T_FRONT
    L, F = case.BTN_NOTCH[1] - case.BTN_NOTCH[0], 10.0
    sigma = 6 * (F * L / 8) / (b * t ** 2)
    report(sigma < s_allow, f"display lip over the button opening ({b:.1f} x {t} mm, {L:.0f} mm span): "
                            f"{sigma:.1f} MPa at 10 N (allow {s_allow})")
    # screw block: M2 thread in plastic, 4 mm engagement, shear area pi*d*L*0.6
    eng = 4.8
    area = math.pi * 2.0 * eng * 0.6
    pull = area * 15.0  # 15 MPa shear in printed plastic
    report(pull > 100, f"M2 thread, {eng} mm engaged: strips at roughly {pull:.0f} N each (4 screws hold a 60 g device)")
    # thin wall left by the dial scoop
    wall = (case.Y1 + 0.9 - 2.8) - (case.BH + case.CLR)
    report(wall >= 0.45, f"dial scoop leaves {wall:.2f} mm of wall at its deepest point beside the slot")
    # standoff pads: bearing pressure when the cover is pushed hard (50 N) onto 4 pads
    a0, a1 = case.POST_SECTORS[1]
    pad = math.radians(a1 - a0) / 2 * (case.POST_ROUT ** 2 - case.POST_RIN ** 2)
    pad_small = math.radians(case.POST_SECTORS[0][1] - case.POST_SECTORS[0][0]) / 2 * (case.POST_ROUT ** 2 - case.POST_RIN ** 2)
    p = 50.0 / (3 * pad + pad_small)
    report(p < 5.0, f"back pads: {3 * pad + pad_small:.1f} mm2 in total, {p:.2f} MPa on the PCB at 50 N")


# ------------------------------------------------------------------ 4
def photo_segmentation():
    from PIL import Image
    from scipy import ndimage
    import reference
    try:
        src = reference.path("back")
    except reference.Unavailable as e:
        skip(f"photo segmentation: Waveshare's back photo could not be downloaded ({e})")
        return
    a = np.asarray(Image.open(src).convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    x0, y0, x1, y1 = 298, 304, 1305, 911
    sx, sy = (x1 - x0) / 99.5, (y1 - y0) / 60.0
    to_front = lambda px, py: (99.5 - (px - x0) / sx, 60.0 - (py - y0) / sy)  # back photo is mirrored
    silver = (np.abs(r - g) < 18) & (np.abs(g - b) < 22) & (r > 150) & (r < 245)
    lab, n = ndimage.label(ndimage.binary_opening(silver, iterations=2))
    found = []
    for k, sl in enumerate(ndimage.find_objects(lab), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h * w > 2500:
            cy = (sl[0].start + sl[0].stop) / 2
            cx = (sl[1].start + sl[1].stop) / 2
            found.append((to_front(cx, cy), (w / sx, h / sy), (to_front(sl[1].stop, cy)[0])))
    # the USB-C shell is ~9 x 7 mm at the edge, the microSD socket ~14 x 15 mm at the edge
    def near_edge(item):
        return item[2] < 3.0
    usb = [f for f in found if near_edge(f) and 6 < f[1][1] < 11 and f[1][0] < 9]
    sd = [f for f in found if near_edge(f) and f[1][1] > 11]
    if usb:
        report(abs(usb[0][0][1] - case.USB_Y) < 0.7, f"segmentation: USB-C centre y {usb[0][0][1]:.2f} (model {case.USB_Y})")
    else:
        report(False, f"segmentation: USB-C not found among {[(np.round(f[0], 1), np.round(f[1], 1)) for f in found]}")
    if sd:
        report(abs(sd[0][0][1] - case.SD_Y) < 1.0, f"segmentation: microSD socket centre y {sd[0][0][1]:.2f} (model {case.SD_Y})")
    else:
        report(False, f"segmentation: microSD socket not found among {[(np.round(f[0], 1), np.round(f[1], 1)) for f in found]}")
    # brass: yellow-orange and fairly bright; the display flex is orange too but long and thin,
    # so keep only roughly round blobs of standoff size (3.5-5 mm)
    brass = (r > 120) & (g > 80) & (b < 100) & (r - b > 60) & (g - b > 30)
    lab, n = ndimage.label(ndimage.binary_closing(brass, iterations=3))
    blobs = []
    for sl in ndimage.find_objects(lab):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 3.0 * sx < w < 5.5 * sx and 3.0 * sy < h < 5.5 * sy and 0.7 < w / h < 1.4:
            blobs.append(to_front((sl[1].start + sl[1].stop) / 2, (sl[0].start + sl[0].stop) / 2))
    errs = [min(math.hypot(bx - px, by - py) for bx, by in blobs) for px, py in case.POSTS] if blobs else [99]
    report(len(blobs) == 4 and max(errs) < 0.6, f"segmentation: {len(blobs)} brass standoffs, "
                                                 f"largest distance to the model positions {max(errs):.2f} mm")


if __name__ == "__main__":
    strength()
    photo_segmentation()
    for v in case.CAVITY:
        print(f"\n### {v}")
        erosion(v)
        line_of_sight(v)
    print(f"\nRound 5: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
