#!/usr/bin/env python3
"""Debug round 9: methods not used in rounds 1-8.

1. Thickness maps: a 0.5 mm grid of rays straight through the front face and the back, and through
   each wall at many heights; material thinner than 0.6 mm is reported (intended openings excluded)
2. Opening map: every through-hole found by those wall rays is matched against the list of openings
   the design is supposed to have; anything unexpected (a pinhole) or missing is reported
(3. A slim-vs-battery shell comparison ran here while there were two versions; removed with the
   slim version.)
"""
import os
import sys

import numpy as np

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


def runs(mesh, origins, d):
    """For each ray, list of (enter, exit) distances through material."""
    locs, ir, _ = mesh.ray.intersects_location(origins, np.tile(d, (len(origins), 1)), multiple_hits=True)
    out = [[] for _ in range(len(origins))]
    for l, i in zip(locs, ir):
        out[i].append(float((l - origins[i]) @ d))
    res = []
    for hits in out:
        h = sorted(hits)
        res.append([(h[k], h[k + 1]) for k in range(0, len(h) - 1, 2)])
    return res


# ------------------------------------------------------------------ 1 + 2
def faces(variant):
    shell, _, cover_asm, z_total = load_assembled(variant)
    xs, ys = np.meshgrid(np.arange(case.X0 + 0.25, case.X1, 0.5), np.arange(case.Y0 + 0.25, case.Y1, 0.5))
    pts = np.column_stack([xs.ravel(), ys.ravel()])
    for name, mesh, z0, d in (("front face", shell, -5.0, np.array([0, 0, 1.0])),
                              ("back", cover_asm, z_total + 5.0, np.array([0, 0, -1.0]))):
        o = np.column_stack([pts, np.full(len(pts), z0)])
        r = runs(mesh, o, d)
        thin = []
        for p, rr in zip(pts, r):
            # only where the ray starts on the flat face itself (5 mm from its origin); rays that
            # first meet the rounded edges or the window chamfer are not measuring the face
            if rr and abs(rr[0][0] - 5.0) < 0.01:
                t = rr[0][1] - rr[0][0]
                if t < 0.6:
                    thin.append((round(t, 2), tuple(np.round(p, 1))))
        report(not thin, f"{variant} {name}: {len(pts)} rays, first material under 0.6 mm at "
                         f"{sorted(thin)[:6] if thin else 'no point'}")


def expected_openings():
    """(wall, along-wall centre, z centre, half-width, half-height) of every intended opening."""
    zb = case.Z_B
    ops = [("left", case.USB_Y, zb + 1.6, 6.5, 3.5, "USB-C"),
           ("left", case.SD_Y, zb + 1.1, 6.5, 1.6, "microSD"),
           ("bottom", sum(case.BTN_NOTCH) / 2, 6.0, 12.5, 12.0, "button opening"),
           ("top", case.WHEEL[0], 8.0, 7.6, 4.0, "dial slot")]
    for dy in (-2.0, 0.0, 2.0):
        ops.append(("left", case.MIC[1] + dy, zb + 1.0, 0.6, 0.6, "mic hole"))
    for y in (40.0, 42.5, 45.0, 47.5):
        ops.append(("right", y, zb + 1.8, 0.6, 1.5, "sensor vent"))
    for pos, side in case.SCREWS:
        ops.append((side, pos, case.SCREW_Z - case.SCREW_DRAW, case.SCREW_WALL_R, case.SCREW_WALL_R, "screw hole"))
    # the pry notch is a shallow dish, not a hole; listed so the thickness scan does not flag its rim
    ops.append(("right", 30.0, case.Z_SPLIT, 5.0, 1.8, "pry notch (dish)"))
    return ops


def wall_openings(variant):
    shell, _, cover_asm, z_total = load_assembled(variant)
    import trimesh
    asm = trimesh.util.concatenate([shell, cover_asm])
    zs = np.arange(0.263, z_total, 0.25)  # offset so no ray runs exactly along a row of mesh vertices
    walls = {"bottom": (np.arange(case.X0 + 7.5, case.X1 - 7.5, 0.25), lambda a, z: [a, case.Y0 - 3, z], np.array([0, 1.0, 0])),
             "top": (np.arange(case.X0 + 7.5, case.X1 - 7.5, 0.25), lambda a, z: [a, case.Y1 + 3, z], np.array([0, -1.0, 0])),
             "left": (np.arange(case.Y0 + 7.5, case.Y1 - 7.5, 0.25), lambda a, z: [case.X0 - 3, a, z], np.array([1.0, 0, 0])),
             "right": (np.arange(case.Y0 + 7.5, case.Y1 - 7.5, 0.25), lambda a, z: [case.X1 + 3, a, z], np.array([-1.0, 0, 0]))}
    ops = expected_openings()
    for wall, (along, f, d) in walls.items():
        A, Z = np.meshgrid(along, zs)
        o = np.array([f(a, z) for a, z in zip(A.ravel(), Z.ravel())])
        r = runs(asm, o, d)
        unexpected, thin = [], []
        found = {i: False for i, op in enumerate(ops) if op[0] == wall}
        for (a, z), rr in zip(zip(A.ravel(), Z.ravel()), r):
            inset = case.surface_inset(z, z_total)
            if inset > case.WALL - 0.3:
                continue  # this height is in the rounded edge, beyond the wall
            # the wall spans from the outer surface (3 mm + inset from the ray origin) to the inside
            lo, hi = 3 + inset - 0.01, 3 + case.WALL + 0.2
            inwall = [(s, e) for s, e in rr if s < hi and e > lo]
            if not inwall:
                match = [i for i, op in enumerate(ops) if op[0] == wall and abs(a - op[1]) <= op[3] + 1.5
                         and abs(z - op[2]) <= op[4] + 1.5]
                if match:
                    for i in match:
                        found[i] = True
                else:
                    unexpected.append((round(a, 2), round(z, 2)))
            else:
                t = inwall[0][1] - inwall[0][0]  # the whole run of material, even past the wall
                near_op = any(op[0] == wall and abs(a - op[1]) <= op[3] + 2.6 and abs(z - op[2]) <= op[4] + 2.6
                              for op in ops)
                if t < 0.6 and not near_op:
                    thin.append((round(t, 2), round(a, 1), round(z, 1)))
        missing = [ops[i][5] for i, ok in found.items() if not ok and "dish" not in ops[i][5]]
        report(not unexpected and not missing,
               f"{variant} {wall} wall: unexpected holes {unexpected[:5] or 'none'}; "
               f"intended openings not found {missing or 'none'}")
        report(not thin, f"{variant} {wall} wall: material under 0.6 mm away from openings: {sorted(thin)[:5] or 'none'}")


if __name__ == "__main__":
    for v in case.CAVITY:
        print(f"\n### {v}")
        faces(v)
        wall_openings(v)
    print(f"\nRound 9: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
