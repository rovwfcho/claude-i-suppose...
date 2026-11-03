#!/usr/bin/env python3
"""Debug round 6: methods not used in rounds 1-5.

1. Continuous sweeps: the convex hull of each part at the start and end of its motion is its exact
   swept volume (parts are convex boxes and cylinders), so nothing can slip between sample steps
2. Packing: the speaker's pocket and the battery bay placed in the cover (sizes in case.py)
3. Plastic around each screw thread, measured by radial rays from the pilot-hole axis
4. microSD push-push: a 1 mm tool must reach 2 mm past the latched card face; dial pressed 0.5 mm in
"""
import math
import os
import sys

import numpy as np
import trimesh
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled, to_manifold, vol  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def swept(part, move):
    """Exact swept volume of a convex part translated along a straight line."""
    return Manifold.hull(part + part.translate(list(move)))


# ------------------------------------------------------------------ 1
def sweeps(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    S, C = to_manifold(shell), to_manifold(cover_asm)
    m = case.board_model()
    pieces = []
    for name, g in m.items():
        for p in g.decompose():
            pieces.append((name, p))
    worst = {}
    for name, p in pieces:
        if name == "pcb":
            # the PCB rests on the front pads at the end of its travel; sweep it down to 0.01 mm above
            sw = swept(p.translate([0, 0, 0.01]), [0, 0, 20])
        else:
            sw = swept(p, [0, 0, 20])
        worst[name] = max(worst.get(name, 0.0), vol(sw ^ S))
    bad = {k: round(v, 4) for k, v in worst.items() if v > 1e-3}
    report(not bad, f"{variant} sweep: board lowered 20 mm into the shell along one continuous path, "
                    f"overlaps {bad or 'none'}")
    # back cover: everything of it below the seam, projected and extruded straight up to the seam,
    # must miss the shell (the cover is lowered straight down)
    from round1 import hooks
    below = (C - hooks()) ^ case.box(-50, 150, -50, 150, -50, case.Z_SPLIT - 0.001)   # the hooks bend out of the way
    # anything of the cover below the seam, extruded straight up to the seam, must miss the shell
    proj = below.project()
    prism = Manifold.extrude(proj, case.Z_SPLIT - (case.Z_B - 1)).translate([0, 0, case.Z_B - 1])
    lowest = below.bounding_box()[2] if not below.is_empty() else case.Z_SPLIT
    prism = prism ^ case.box(-50, 150, -50, 150, lowest, case.Z_SPLIT)
    hit = vol(prism ^ S)
    report(hit < 1e-3, f"{variant} sweep: every part of the cover that goes below the seam has a clear "
                       f"vertical path through the shell (overlap {hit:.4f} mm3)")
    # USB-C plug: overmold 12.4 x 6.6 (r 1 corners) pushed from 30 mm out to the receptacle face
    hits = []
    for dz in (0.0, case.STANDOFF_H - case.STANDOFF_H_MIN):          # 4 mm and 3 mm standoffs
        zc = case.Z_B + 1.63 + dz
        over = case.prism(case.rrect(12.4, 6.6, 1.0, case.USB_Y, zc), -0.4 - 25, -0.4).transform(
            [[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])
        hits.append(vol(swept(over.translate([-30, 0, 0]), [30, 0, 0]) ^ (S + C)))
    report(max(hits) < 1e-3, f"{variant} sweep: USB-C plug pushed in from 30 mm away, overlap {hits[0]:.4f} mm3 "
                             f"(4 mm standoffs) / {hits[1]:.4f} mm3 (3 mm)")


# ------------------------------------------------------------------ 2
def packing(variant):
    shell, _, cover_asm, z_total = load_assembled(variant)
    C = to_manifold(cover_asm)
    z_in = z_total - case.T_BACK
    sx, sy = case.SPEAKER[variant]
    w, h, t = case.SPEAKER_BOX[variant]
    spk = case.box(sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2, z_in - t, z_in)
    report(vol(spk ^ C) < 1e-3, f"{variant} packing: {w:.1f} x {h:.1f} x {t} mm speaker pocket on the grille touches the cover "
                                f"{vol(spk ^ C):.3f} mm3; its underside is {z_in - t - case.Z_B:.1f} mm above the PCB back "
                                f"(parts under it must be lower)")
    if variant != "battery":
        return
    # the whole battery bay (the owner's 454261 plus its clearance), next to the speaker
    x0, x1, y0, y1 = case.BATTERY_BAY
    bat = case.box(x0, x1, y0, y1, z_in - case.BATTERY_SPACE, z_in)
    hit = vol(bat ^ (C + spk))
    report(hit < 1e-3, f"{variant} packing: battery bay {x1 - x0:.1f} x {y1 - y0:.1f} x {case.BATTERY_SPACE} mm "
                       f"(for the {case.BATTERY_SIZE[0]:.1f} x {case.BATTERY_SIZE[1]:.1f} x {case.BATTERY_SIZE[2]} mm 454261) "
                       f"is clear of the cover and the speaker ({hit:.3f} mm3); "
                       f"{z_in - case.BATTERY_SPACE - case.Z_B:.1f} mm above the PCB back")


# ------------------------------------------------------------------ 3
def screw_walls(variant):
    """Plastic round each corner screw, by rays from its axis: around the head's recess to the outside
    (thinnest near the rounded corner) and around the hole in the post."""
    _, _, cover_asm, z_total = load_assembled(variant)
    angles = np.radians(np.arange(0, 360, 5))
    dirs = np.column_stack([np.cos(angles), np.sin(angles), np.zeros(len(angles))])
    for px, py in case.POSTS:
        worst = {}
        for label, z, r0 in (("recess", z_total - 0.05, case.SCREW_HEAD_R), ("recess", z_total - 0.3, case.SCREW_HEAD_R),
                             ("recess", z_total - 1.0, case.SCREW_HEAD_R), ("post", case.Z_SPLIT + 1.0, case.SCREW_HOLE_R),
                             ("post", case.POST_Z + 1.0, case.SCREW_HOLE_R)):
            o = np.array([px, py, z]) + dirs * (r0 + 0.01)
            locs, ir, _ = cover_asm.ray.intersects_location(o, dirs, multiple_hits=False)
            dist = np.full(len(dirs), np.inf)
            dist[ir] = np.linalg.norm(locs - o[ir], axis=1) + 0.01
            worst[label] = min(worst.get(label, np.inf), dist.min())
        report(worst["recess"] >= 0.8 and worst["post"] >= 0.6,
               f"{variant} corner screw ({px:.1f}, {py:.1f}): thinnest plastic round the head recess "
               f"{worst['recess']:.2f} mm, round the hole in the post {worst['post']:.2f} mm")


# ------------------------------------------------------------------ 4
def usability(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    obst = to_manifold(shell) + to_manifold(cover_asm)
    # microSD: latched card face assumed at the socket face, x = 1.5; push-push needs ~2 mm more
    zs = case.Z_B + 0.9
    tool = case.cyl_x(case.SD_Y, zs, 0.5, -30, 1.5 + 2.0 - 15)
    hit = vol(swept(tool, [15, 0, 0]) ^ obst)
    report(hit < 1e-3, f"{variant} microSD: a 1 mm pin (pen tip, nail edge) reaches 2 mm past the latched card "
                       f"(overlap {hit:.4f} mm3)")
    tip_depth = 1.5 - case.X0
    print(f"  ..   {variant} microSD: latched card face is about {tip_depth:.1f} mm in from the outer wall "
          f"(not reachable with a bare fingertip; use a nail or pen tip)")
    # dial pressed 0.5 mm toward the board centre, and turned (a cylinder turning stays the same shape)
    wx, wy, wr = case.WHEEL
    wheel = case.cyl_z(wx, wy, wr, case.Z_B + 0.2, case.Z_B + 2.8)
    hit = vol(swept(wheel, [0, -0.5, 0]) ^ obst)
    report(hit < 1e-3, f"{variant} dial: pressed 0.5 mm in, overlap with case {hit:.4f} mm3")


if __name__ == "__main__":
    for v in case.CAVITY:
        print(f"\n### {v}")
        sweeps(v)
        packing(v)
        screw_walls(v)
        usability(v)
    print(f"\nRound 6: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
