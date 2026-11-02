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
    shell, _, cover_asm, _ = load_assembled(variant)
    for pos, side in case.SCREWS:
        p, d, wall = case.screw_frame(pos, side)
        across = np.array([abs(d[1]), abs(d[0]), 0.0])
        up = np.array([0, 0, 1.0])

        def hole_centre(mesh, depth, r_guess):
            # cast rays outward from a point near the axis in 16 directions and fit a circle to the
            # points where they meet the hole wall (a plain centroid is only right if the rays start
            # at the hole's own centre, which the drawn wall hole doesn't)
            c = p + d * depth
            angles = np.radians(np.arange(0, 360, 22.5))
            dirs = np.outer(np.cos(angles), across) + np.outer(np.sin(angles), up)
            locs, ir, _ = mesh.ray.intersects_location(np.tile(c, (len(dirs), 1)), dirs, multiple_hits=False)
            if len(locs) < 12:
                return None, None
            u, w = (locs - c) @ across, (locs - c) @ up
            A = np.column_stack([2 * u, 2 * w, np.ones(len(u))])
            (cu, cw, k), *_ = np.linalg.lstsq(A, u ** 2 + w ** 2, rcond=None)
            return c + cu * across + cw * up, float(np.sqrt(k + cu ** 2 + cw ** 2))

        cs, rs = hole_centre(shell, 1.5, case.SCREW_WALL_R)          # inside the shell wall
        cc, rc = hole_centre(cover_asm, case.WALL + 2.0, case.SCREW_PILOT_R)  # inside the cover block
        if cs is None or cc is None:
            report(False, f"{variant} screw {side} {pos}: hole not found (shell {cs is not None}, cover {cc is not None})")
            continue
        v = (cs - cc) - ((cs - cc) @ d) * d   # offset of the wall hole from the pilot, across the axis
        want = np.array([0, 0, -case.SCREW_DRAW])  # drawn toward the front by design
        off = np.linalg.norm(v - want)
        report(off < 0.05 and abs(rs - case.SCREW_WALL_R) < 0.05 and abs(rc - case.SCREW_PILOT_R) < 0.05,
               f"{variant} screw {side} {pos}: clearance hole r={rs:.2f}, pilot r={rc:.2f}, hole offset "
               f"{np.round(v, 3).tolist()} (designed {want.tolist()}), error {off:.3f} mm")


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
