#!/usr/bin/env python3
"""Debug round 14: methods not used in rounds 1-13 (battery layout).

1. Antenna keep-out: metal parts (battery, speaker) must stay at least 6 mm, in plan, from the
   ESP32 module's antenna end, and away from it in height too
2. Monte Carlo over real part sizes: batteries 60-63 x 41-43 x 4.2-5.0 mm (anywhere the guides let
   them sit) and speakers 15-18 x 11-13 x 3-4.5 mm (within 0.5 mm of their spot) must clear the
   cover, the guides and each other
3. Battery fitted the other way round (wire end toward the speaker): is there still a wire route?
   Reported for the README, which tells you which way round to fit it
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from manifold3d import Manifold  # noqa: E402
from round1 import load_assembled, to_manifold, vol  # noqa: E402
from round13 import tube  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def plan_gap(a, b):
    """Gap between two axis-aligned rectangles (x0, x1, y0, y1)."""
    dx = max(b[0] - a[1], a[0] - b[1], 0.0)
    dy = max(b[2] - a[3], a[2] - b[3], 0.0)
    return float(np.hypot(dx, dy))


# ------------------------------------------------------------------ 1
def antenna():
    sx, sy = case.SPEAKER["battery"]
    w, h, _ = case.SPEAKER_BOX["battery"]
    spk = (sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2)
    g_s = plan_gap(spk, case.ANTENNA)
    g_b = plan_gap(case.BATTERY_BAY, case.ANTENNA)
    report(g_s >= 6.0 and g_b >= 6.0, f"antenna keep-out (estimated antenna at x {case.ANTENNA[0]}-{case.ANTENNA[1]}, "
                                      f"y {case.ANTENNA[2]}-{case.ANTENNA[3]}): speaker space {g_s:.1f} mm away, "
                                      f"battery bay {g_b:.1f} mm away (want >= 6)")


# ------------------------------------------------------------------ 2
def sizes(n=80, seed=11):
    shell, _, cover_asm, z_total = load_assembled("battery")
    C = to_manifold(cover_asm)
    z_in = z_total - case.T_BACK
    rng = np.random.default_rng(seed)
    x0, x1, y0, y1 = case.BATTERY_BAY
    bcx, bcy = (x0 + x1) / 2, (y0 + y1) / 2
    sx, sy = case.SPEAKER["battery"]
    bad = []
    for i in range(n):
        L, W, T = rng.uniform(60, 65.5), rng.uniform(41, 43.8), rng.uniform(4.2, 5.0)
        # the guides only let it move as far as the free space around it in the bay
        dx = rng.uniform(-1, 1) * ((x1 - x0) - L) / 2
        dy = rng.uniform(-1, 1) * ((y1 - y0) - W) / 2
        bat = case.box(bcx + dx - L / 2, bcx + dx + L / 2, bcy + dy - W / 2, bcy + dy + W / 2, z_in - T, z_in)
        a, b, t = rng.uniform(11, 13.5), rng.uniform(15, 18.5), rng.uniform(3.0, 4.5)  # turned: narrow in x
        ex, ey = rng.uniform(-0.5, 0.5, 2)
        spk = case.box(sx + ex - a / 2, sx + ex + a / 2, sy + ey - b / 2, sy + ey + b / 2, z_in - t, z_in)
        v1, v2, v3 = vol(bat ^ C), vol(spk ^ C), vol(bat ^ spk)
        if max(v1, v2, v3) > 1e-3:
            bad.append((round(L, 1), round(W, 1), round(T, 2), round(v1, 3), round(v2, 3), round(v3, 3)))
    report(not bad, f"{n} random battery/speaker sizes and placements: {len(bad)} clashes {bad[:4]}")


# ------------------------------------------------------------------ 3
def flipped():
    shell, _, cover_asm, z_total = load_assembled("battery")
    S, C = to_manifold(shell), to_manifold(cover_asm)
    z_in = z_total - case.T_BACK
    x0, x1, y0, y1 = case.BATTERY_BAY
    bat = case.box(x0, x1, y0, y1, z_in - case.BATTERY_SPACE, z_in)
    sx, sy = case.SPEAKER["battery"]
    w, h, t = case.SPEAKER_BOX["battery"]
    spk = case.box(sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2, z_in - t, z_in)
    every = Manifold()
    for g in case.board_model().values():
        every += g
    obst = S + C + every + bat + spk
    zs = case.Z_B + 1.9 + 1.25
    # wire end at the speaker side: the only gap between the bay (x <= 70) and the speaker (x >= 71.5)
    # is 1.5 mm, so try going over the top of the bay toward the top edge and round instead
    path = [(x1 - 3.0, y1 + 1.4, z_in - case.BATTERY_SPACE / 2), (x1 - 3.0, y1 + 1.4, zs + 3.0),
            (40.0, y1 + 1.4, zs + 3.0)]
    hit = vol(tube(path) ^ obst)
    print(f"  ..   battery fitted the other way round: a wire route along the top of the bay "
          f"{'is clear' if hit < 1e-3 else 'is blocked (%.3f mm3)' % hit}; the README says to fit it with the "
          f"wire end toward the USB-C side, where the route is checked in round 13")


if __name__ == "__main__":
    antenna()
    sizes()
    flipped()
    print(f"\nRound 14: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
