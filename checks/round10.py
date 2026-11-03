#!/usr/bin/env python3
"""Debug round 10: methods not used in rounds 1-9.

1. Layer support: each 0.2 mm layer (print orientation) is compared with the layer below; material
   more than 1.5 mm out over air, that is not a bridge (supported at both ends), is reported
2. Screw alignment: the axis of each clearance hole in the shell and of the pilot hole in the cover,
   each recovered from the meshes, must line up
3. Display corners: the rounded window corners must not clip the corners of the active area
"""
import math
import os
import sys

import numpy as np

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


# ------------------------------------------------------------------ 1
def layer_support(variant, layer=0.2, reach=1.5):
    from shapely.ops import unary_union
    shell, cover, _, _ = load_assembled(variant)
    for name, tm in (("front shell", shell), ("back cover", cover)):
        zs = np.arange(layer / 2 + 0.013, tm.bounds[1][2], layer)  # off the mesh's vertex rows
        secs = tm.section_multiplane([0, 0, 0], [0, 0, 1], zs)
        prev, bad = None, []
        for z, sec in zip(zs, secs):
            cur = unary_union(list(sec.polygons_full)) if sec is not None else None
            if prev is not None and cur is not None:
                over = cur.difference(prev.buffer(reach))  # further than `reach` from anything below
                for g in getattr(over, "geoms", [over]):
                    if g.area < 0.05:
                        continue
                    # a bridge: the overhanging piece meets supported material along two or more
                    # separate stretches of its outline (one on each side of the gap it spans)
                    edge = g.boundary.intersection(prev.buffer(reach + 0.05))
                    parts = [e for e in getattr(edge, "geoms", [edge]) if e.length > 0.3]
                    merged = unary_union(parts).buffer(0.2) if parts else None
                    ends = len(getattr(merged, "geoms", [merged])) if merged is not None else 0
                    if ends < 2:
                        bad.append((round(float(z), 2), round(g.area, 2), tuple(np.round(g.centroid.coords[0], 1))))
            prev = cur
        report(not bad, f"{variant} {name}: layers with material more than {reach} mm out over air "
                        f"(not bridged): {bad[:5] or 'none'}")


# ------------------------------------------------------------------ 2
def screw_alignment(variant):
    """Corner holes found in the STL: centre and radius of the hole (in the post) and of the recess,
    by a circle fit to where rays from near the axis meet the walls."""
    _, _, cover_asm, z_total = load_assembled(variant)
    angles = np.radians(np.arange(0, 360, 10))
    dirs = np.column_stack([np.cos(angles), np.sin(angles), np.zeros(len(angles))])

    def circle(c):
        locs, _, _ = cover_asm.ray.intersects_location(np.tile(c, (len(dirs), 1)), dirs, multiple_hits=False)
        if len(locs) < 30:
            return None, None
        u, w = locs[:, 0], locs[:, 1]
        A = np.column_stack([2 * u, 2 * w, np.ones(len(u))])
        (cu, cw, k), *_ = np.linalg.lstsq(A, u ** 2 + w ** 2, rcond=None)
        return np.array([cu, cw]), float(np.sqrt(k + cu ** 2 + cw ** 2))

    for px, py in case.POSTS:
        ch, rh = circle(np.array([px + 0.2, py - 0.1, case.Z_SPLIT + 1.0]))       # hole, inside the post
        cr, rr = circle(np.array([px - 0.3, py + 0.2, z_total - 0.9]))            # head recess
        if ch is None or cr is None:
            report(False, f"{variant} corner hole at ({px}, {py}): not found")
            continue
        off = max(np.hypot(*(ch - (px, py))), np.hypot(*(cr - (px, py))))
        report(off < 0.03 and abs(rh - case.SCREW_HOLE_R) < 0.03 and abs(rr - case.SCREW_HEAD_R) < 0.03,
               f"{variant} corner hole ({px}, {py}): hole r={rh:.3f}, recess r={rr:.3f}, both centred within "
               f"{off:.3f} mm of the standoff estimate")


# ------------------------------------------------------------------ 3
def window_corners(variant):
    shell, _, _, _ = load_assembled(variant)
    # active area per the drawing's dimension lines (their centre), 86.40 x 51.84
    ax0, ax1, ay0, ay1 = 52.48 - 43.2, 52.48 + 43.2, 30.0 - 25.92, 30.0 + 25.92
    z = case.T_FRONT - 0.05  # just under the lip, the narrowest part of the window
    worst = np.inf
    for cx, cy in ((ax0, ay0), (ax0, ay1), (ax1, ay0), (ax1, ay1)):
        o = np.array([[cx, cy, z]])
        # distance from the active-area corner to the nearest lip material in this plane
        for a in np.radians(np.arange(0, 360, 5)):
            d = np.array([[math.cos(a), math.sin(a), 0.0]])
            locs, _, _ = shell.ray.intersects_location(o, d, multiple_hits=False)
            inside_lip = shell.contains(o)[0]
            if inside_lip:
                worst = -1.0
            elif len(locs):
                worst = min(worst, float(np.linalg.norm(locs[0] - o[0])))
    report(worst >= 0.4, f"{variant} window corners: active-area corners are {worst:.2f} mm from the lip at its "
                         f"narrowest (inside face)")


if __name__ == "__main__":
    for v in case.CAVITY:
        print(f"\n### {v}")
        layer_support(v)
        screw_alignment(v)
        window_corners(v)
    print(f"\nRound 10: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
