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
def clips():
    """Snap clips, textbook beam formulas: each beam is fixed at both ends (anchored in the skirt) with
    the hook's load at its middle. Strain while the hook passes the lid's wall, the force to close and
    to pull the lid off (friction 0.3), against PLA's limits (printed PLA yields at about 2 % strain
    along the lines; keep under 1.5 % so it can be opened many times)."""
    E = 3000.0                                    # MPa, printed PLA along the lines
    L, t = case.CLIP_L, case.SKIRT_T
    h = case.SKIRT_H - case.CLIP_SLOT             # beam height (z)
    d = case.CLIP_UNDERCUT                        # bend while the hook passes the wall
    I = h * t ** 3 / 12
    P = 192 * E * I * d / L ** 3                  # fixed-fixed beam, load in the middle
    eps = 12 * d * t / L ** 2
    mu = 0.3
    lead = math.radians(case.RIM_CHAMFER[1])      # the lid's 30 deg rim chamfer does the pushing
    catch = math.radians(case.CLIP_CATCH)
    close = P * (math.tan(lead) + mu) / (1 - mu * math.tan(lead))
    pull = P * (math.tan(catch) + mu) / (1 - mu * math.tan(catch))
    pre = 12 * case.CLIP_PRELOAD * t / L ** 2
    n = len(case.CLIPS)
    report(eps <= 0.015 and pre <= 0.005 and pull > close and n * pull >= 25,     # firm: 2.5 kg straight off
           f"clip beams {L:.0f} x {t} x {h:.1f} mm: {100 * eps:.2f} % strain at full bend ({d} mm), "
           f"{100 * pre:.2f} % while closed; about {n * close:.0f} N to close, {n * pull:.0f} N to pull the lid "
           f"straight off ({n} clips)")


def screw_length():
    """Found screws come in any length: which ones reach the PCB through the standoff? Worst case: 3 mm
    standoffs (the board 1 mm further back)."""
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    seat = z_total - case.SCREW_HEAD_DEPTH
    pcb_back = case.POST_Z - case.STANDOFF_H_MIN
    first = None
    for L in (6, 7, 8, 9, 10, 12):
        if seat - L <= pcb_back + 0.3:
            first = L
            break
    short = [L for L in (6, 7, 8) if L - (seat - case.POST_Z) < 1.5]
    report(first is not None and first > case.SCREW_LEN and case.SCREW_LEN not in short,
           f"corner screws: {short} mm are too short (under 1.5 mm in the standoff); {first} mm and longer can reach "
           f"the PCB with 3 mm standoffs; {case.SCREW_LEN:.0f} mm is right for both")


if __name__ == "__main__":
    back_plate()
    clips()
    screw_length()
    print(f"\nRound 22: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
