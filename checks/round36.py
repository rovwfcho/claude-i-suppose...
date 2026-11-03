#!/usr/bin/env python3
"""Debug round 36 (session 5): methods not used in rounds 1-35.

1. The lid closing, step by step, on the meshes: the lid (read back from its STL) is moved from 3 mm
   short of closed to closed in 0.05 mm steps; at each step, the least each hook must bend inward to
   clear the lid is found by bisection. That curve must rise to CLIP_UNDERCUT at most, must never
   rise faster than 1 mm of bend per mm of travel (steeper would jam), and closed must leave the
   designed preload.
2. The same with print errors: the lid 0.15 mm small inside and the cover 0.15 mm large outside on
   each side (the worst way round; PLA usually errs a little that way), and the other way round.
   The worst bend while closing must keep the beam under 1.8 % strain (printed PLA yields at about
   2-2.5 %); the other way round the hook must still catch (reach past the lid's wall when closed).
3. The wires with 3 mm standoffs: the board, and the wires that lie on it, sit 1 mm further back.
   The battery wire (on the microSD socket) and the sleeved speaker cable (on the board's low parts)
   must then still clear the bottom of your 4.3 mm battery by 0.2 mm; against the largest cell the
   README allows (4.8 mm) the squeeze is reported.
"""
import math
import os
import sys

import numpy as np
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


def bend_curve(lid, x, side, steps=np.arange(3.0, -0.001, -0.05)):
    """Least inward bend (mm) of the hook at (x, side) that clears the lid, for each distance from closed."""
    s = 1 if side == "bottom" else -1
    hook = case.clip_hook(x, side)
    y_lid = -case.CLR if side == "bottom" else case.BH + case.CLR
    near = lid ^ case.box(x - case.CLIP_HOOK_L, x + case.CLIP_HOOK_L, min(y_lid - 3 * s, y_lid + 3 * s),
                          max(y_lid - 3 * s, y_lid + 3 * s), 3.0, case.Z_SPLIT + 1)      # the lid near this hook
    out = []
    for d in steps:
        L = near.translate([0, 0, -d])
        lo, hi = 0.0, 1.5
        if vol(hook ^ L) < 1e-4:
            out.append(0.0)
            continue
        for _ in range(14):
            mid = (lo + hi) / 2
            if vol(hook.translate([0, s * mid, 0]) ^ L) < 1e-4:
                hi = mid
            else:
                lo = mid
        out.append(hi)
    return np.array(steps), np.array(out)


def scaled(m, ky):
    c = np.array([case.BW / 2, case.BH / 2, 0])
    return m.translate(-c).scale([1.0, ky, 1.0]).translate(c)


def closing():
    shell, _, cover, _ = load_assembled("battery")
    lid = to_manifold(shell)
    eps_of = lambda b: 12 * b * case.SKIRT_T / case.CLIP_L ** 2   # noqa: E731
    worst = []
    for x, side in case.CLIPS:
        d, b = bend_curve(lid, x, side)
        slope = np.max(np.abs(np.diff(b)) / 0.05)
        worst.append((x, side, b.max(), slope, b[-1]))
    bmax = max(w[2] for w in worst)
    smax = max(w[3] for w in worst)
    pre = [w[4] for w in worst]
    report(bmax <= case.CLIP_UNDERCUT + 0.02 and smax <= 1.0 + 0.05
           and all(abs(p - case.CLIP_PRELOAD) <= 0.03 for p in pre),
           f"lid closing on the meshes, {len(worst)} clips: hooks bend at most {bmax:.3f} mm ({100 * eps_of(bmax):.2f} % "
           f"strain), never faster than {smax:.2f} mm per mm of travel; closed they stay bent {min(pre):.3f}-{max(pre):.3f} mm "
           f"(designed {case.CLIP_PRELOAD})")
    # print errors: 0.15 mm on each side, the lid's inside and the cover's outside
    err = 0.15
    k = err / (case.BH / 2 + case.CLR)
    res = {}
    for label, kl, kc in (("lid small, cover large", 1 - k, 1 + k), ("lid large, cover small", 1 + k, 1 - k)):
        # the cover's error moves the hook outward: same as moving the lid inward by as much
        bmaxes, closed = [], []
        for x, side in case.CLIPS:
            s = 1 if side == "bottom" else -1
            L = scaled(lid, kl).translate([0, s * (kc - 1) * (case.BH / 2 + case.CLR), 0])
            d, b = bend_curve(L, x, side)
            bmaxes.append(b.max())
            closed.append(b[-1])
        res[label] = (max(bmaxes), min(closed))
    hi = res["lid small, cover large"][0]
    reach_lo = case.CLIP_UNDERCUT - 2 * err           # how far the hook still reaches past the wall
    report(eps_of(hi) <= 0.018 and reach_lo >= 0.1,
           f"with 0.15 mm print errors: lid small and cover large, the hooks bend up to {hi:.2f} mm while closing "
           f"({100 * eps_of(hi):.2f} % strain, want under 1.8), closed {res['lid small, cover large'][1]:.2f} mm; lid "
           f"large and cover small, they bend up to {res['lid large, cover small'][0]:.2f} mm and still reach "
           f"{reach_lo:.2f} mm past the lid's wall")


# ------------------------------------------------------------------ 3
def wires_3mm():
    from round13 import tube
    dz = case.STANDOFF_H - case.STANDOFF_H_MIN
    z_in = case.Z_B + case.CAVITY["battery"]
    x0, x1, y0, y1 = case.BATTERY_BAY
    rows = []
    for (pts, r), label in ((case.battery_wire_route(), "battery wire"), (case.speaker_wire_route(), "speaker cable")):
        # the parts of the route that lie on the board (under the battery) move back with it
        lifted = [(x, y, z + dz) if z < z_in - case.BATTERY_SPACE else (x, y, z) for x, y, z in pts]
        t = tube(lifted, r) ^ case.box(x0, x1, y0, y1, 0, 50)
        top = t.bounding_box()[5] if not t.is_empty() else -np.inf
        rows.append((label, z_in - case.BATTERY_SIZE[2] - top, z_in - case.BATTERY_MAX[2] - top))
    # and nothing of the board itself reaches the battery
    every = Manifold()
    for g in case.board_model(case.STANDOFF_H_MIN).values():
        every += g
    under = every ^ case.box(x0, x1, y0, y1, 0, 50)
    board_gap = z_in - case.BATTERY_SIZE[2] - under.bounding_box()[5]
    ok = all(a >= 0.2 for _, a, _ in rows) and board_gap >= 0.5
    report(ok, "3 mm standoffs: under your 4.3 mm battery " + ", ".join(
        f"the {label} has {a:.2f} mm to spare (a 4.8 mm cell would squeeze it {max(-b, 0):.2f} mm)" for label, a, b in rows)
        + f"; the board's parts {board_gap:.2f} mm")


if __name__ == "__main__":
    closing()
    wires_3mm()
    print(f"\nRound 36: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
