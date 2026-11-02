#!/usr/bin/env python3
"""Debug round 22: methods not used in rounds 1-21 (textbook mechanics, estimates).

1. Back plate pressed over the battery: deflection of the 1.8 mm back plate under a point load,
   from the Navier series for a simply supported rectangular plate (more bendy than the real,
   screwed and skirted edges, so on the safe side), for PLA (E about 3.5 GPa) and PETG (about
   2.0 GPa). The pushed-in battery (the largest the README allows, 4.8 mm) must stay clear of the
   board's parts: those in the board model (depth rays), and, more strictly, a 4 mm part anywhere
   (the README's assumption). A firm thumb (20 N) must leave a gap; a 50 N squeeze is reported.
2. Screw pull-out: thread engagement of an M2 x 6 in each block, measured along the screw axis on
   the model, and a pull-out force from the sheared thread area with layer-bond strength
   (about 10 MPa, a low value for printed PLA/PETG) and a 50 % thread fill

The material values are typical published figures, not measured; treat the results as estimates.
"""
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
MATERIALS = {"PLA": 3500.0, "PETG": 2000.0}  # E in MPa
NU = 0.35
BIG_CELL = 4.8


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def plate_w(xi, eta, P, E, a, b, t, N=41):
    """Deflection under a point load P at (xi, eta) on a simply supported a x b plate (Navier)."""
    D = E * t ** 3 / (12 * (1 - NU ** 2))
    m = np.arange(1, N + 1)[:, None]
    n = np.arange(1, N + 1)[None, :]
    s = (np.sin(m * np.pi * xi / a) ** 2 * np.sin(n * np.pi * eta / b) ** 2 / ((m / a) ** 2 + (n / b) ** 2) ** 2)
    return 4 * P / (np.pi ** 4 * D * a * b) * s.sum()


# ------------------------------------------------------------------ 1
def back_plate():
    import trimesh
    a, b = case.BW + 2 * case.CLR, case.BH + 2 * case.CLR  # the free span inside the walls
    # sanity check of the series against the textbook coefficient for a square plate (0.0116 P a^2 / D)
    D = 2000.0 * 1.8 ** 3 / (12 * (1 - NU ** 2))
    coef = plate_w(30, 30, 1.0, 2000.0, 60, 60, 1.8) * D / 60 ** 2
    report(abs(coef - 0.0116) < 0.0004, f"Navier series vs Timoshenko's square-plate value: {coef:.5f} (0.0116)")
    shell, _, _, z_total = load_assembled("battery")
    scene = trimesh.util.concatenate([shell] + [case.to_trimesh(g) for g in case.board_model().values()])
    z_in = z_total - case.T_BACK
    x0, x1, y0, y1 = case.BATTERY_BAY
    pts = [(x, y) for x in np.arange(x0 + 1, x1, 2.0) for y in np.arange(y0 + 1, y1, 2.0)]
    o = np.array([[x, y, z_in - 0.02] for x, y in pts])
    loc, ray, _ = scene.ray.intersects_location(o, np.tile([0, 0, -1.0], (len(o), 1)), multiple_hits=False)
    free = np.full(len(o), 99.0)
    free[ray] = o[ray, 2] - loc[:, 2]
    gap_model = free - BIG_CELL
    gap_generic = np.minimum(gap_model, (z_in - BIG_CELL) - case.Z_COMP)
    for mat, E in MATERIALS.items():
        for P in (20.0, 50.0):
            w = np.array([plate_w(x + case.CLR, y + case.CLR, P, E, a, b, case.T_BACK) for x, y in pts])
            m1, m2 = (gap_model - w).min(), (gap_generic - w).min()
            i = int(np.argmin(gap_generic - w))
            msg = (f"{mat}, {P:.0f} N pressed anywhere over the battery: plate bends up to {w.max():.2f} mm; "
                   f"smallest gap left to modelled parts {m1:.2f} mm, to a 4 mm part anywhere {m2:.2f} mm "
                   f"(at x {pts[i][0]:.0f}, y {pts[i][1]:.0f})")
            if P == 20.0:
                report(m1 >= 0.5 and m2 >= 0.0, msg)
            else:
                print("  ..   " + msg)


# ------------------------------------------------------------------ 2
def screws():
    tau = 10.0
    fill = 0.5 * (1.0 - case.SCREW_PILOT_R) / 0.2   # 50 % thread fill for a 1.6 mm pilot, less for a bigger one
    for pos, side in case.SCREWS:
        p, d, wall = case.screw_frame(pos, side)
        along = abs(wall - p @ np.abs(d))            # outer wall plane to the cavity wall
        block0 = along + case.SKIRT_CLR               # block face
        block1 = along + case.BLOCK_DEPTH             # far face of the block
        tip = case.SCREW_HEAD_DEPTH + 6.0             # under-head length of an M2 x 6
        L = min(tip, block1) - block0
        F = tau * np.pi * 2.0 * L * fill
        report(L >= 3.0 and F >= 50.0, f"{side} screw at {pos}: {L:.2f} mm of thread in the block, pull-out about "
                                        f"{F:.0f} N (the whole device weighs about 1-1.5 N)")


def screw_length():
    """Found screws come in any length: which ones reach the battery? Worst case: the largest cell the
    README allows (4.8 mm) pushed against the bay's edge."""
    from manifold3d import Manifold
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    z_in = z_total - case.T_BACK
    x0, x1, y0, y1 = case.BATTERY_BAY
    cell = case.box(x0, x1, y0, y1, z_in - 4.8, z_in)
    first_hit = {}
    for pos, side in case.SCREWS:
        p, d, _ = case.screw_frame(pos, side)
        for L in (5, 6, 7, 8, 10, 12):
            shank = case.cyl_along(p, d, case.SCREW_HEAD_DEPTH, case.SCREW_HEAD_DEPTH + L, 1.0)
            if not (shank ^ cell).is_empty() and (shank ^ cell).volume() > 1e-4:
                first_hit[f"{side} {pos}"] = L
                break
    shortest = min(first_hit.values()) if first_hit else None
    report(shortest is None or shortest > 7, f"screw lengths that reach the battery: {first_hit or 'none up to 12 mm'} "
                                             f"(the README allows 5-6 mm, never more than 7)")


if __name__ == "__main__":
    back_plate()
    screws()
    screw_length()
    print(f"\nRound 22: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
