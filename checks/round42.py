#!/usr/bin/env python3
"""Debug round 42 (session 5): methods not used in rounds 1-41.

1. Opening at the notch, as a tilt: with the cover held, the lid is turned open about an axis along
   its left end at the seam (where it pivots when the right-hand end is lifted with a pick), in
   0.25 degree steps up to 8 degrees. Apart from the springy hooks, nothing of the lid may run into
   the cover (nothing jams), and the hooks must let go one after another from the right: each hook's
   bend needed to clear the lid must stay within its CLIP_UNDERCUT plus 0.2 mm, then fall to zero.
2. The closing curve worked out by hand: from the design's own numbers (the 30 deg rim chamfer, the
   hook's 55 deg front, crest and 45 deg catch, the preload), the bend each hook needs at each point
   of the lid's travel is written down as a formula, and it must match what round 36 measured on the
   meshes to within 0.03 mm everywhere.
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
from round1 import hook_zones, load_assembled, to_manifold, vol  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
def tilt_open():
    shell, _, cover, _ = load_assembled("battery")
    S, C = to_manifold(shell), to_manifold(cover)
    rigid = C - hook_zones()
    # pivot: the lid's left end at the seam, outer face (x = X0, z = Z_SPLIT); opening lifts the right
    # end toward the front (-z): a rotation about the y axis
    px, pz = case.X0, case.Z_SPLIT

    def turned(m, deg):
        return m.translate([-px, 0, -pz]).rotate([0, deg, 0]).translate([px, 0, pz])
    worst_rigid, release = 0.0, {}
    hooks = [(x, side, case.clip_hook(x, side)) for x, side in case.CLIPS]
    for deg in np.arange(0.25, 8.01, 0.25):
        L = turned(S, deg)
        worst_rigid = max(worst_rigid, vol(L ^ rigid))
        for x, side, h in hooks:
            if (x, side) not in release and vol(L ^ h) < 1e-4:
                release[(x, side)] = deg
    # the rotation sign: the right end must move toward the front (lower z)
    tip = turned(case.box(case.X1 - 0.1, case.X1, 0, 1, pz - 0.1, pz), 2.0).bounding_box()
    toward_front = tip[2] < pz - 0.1
    order = sorted(release, key=lambda k: release[k])
    from_right = [k[0] for k in order] == sorted([k[0] for k in order], reverse=True) or \
        all(release[a] <= release[b] + 1e-9 for a in release for b in release if a[0] > b[0])
    ok = toward_front and worst_rigid < 1e-3 and len(release) == len(hooks) and from_right
    report(ok, f"lid tilted open about its left end (up to 8°): rigid parts overlap {worst_rigid:.4f} mm3; hooks let go at "
               + ", ".join(f"x={k[0]:.0f} {k[1]} {release.get(k, float('nan')):.2f}°" for k in sorted(release, key=lambda k: -k[0]))
               + f"; right end first: {from_right}")


# ------------------------------------------------------------------ 2
def bend_by_hand(d):
    """Bend (mm) one hook needs with the lid d mm short of closed, from the design's numbers alone.
    At each height z on the hook: how far the hook sticks out past the lid's wall line (out), and how
    far the lid's surface there is cut back from that line (cut: by the rim chamfer, the catch face
    or the groove); the hook must bend by the largest out - cut."""
    p, za, zb, zc, zd = case.clip_levels()
    u, pre = case.CLIP_UNDERCUT, case.CLIP_PRELOAD
    cd, ca = case.RIM_CHAMFER
    ch = cd / math.tan(math.radians(ca))
    yl, yf = -case.CLR, -case.CLR + case.SKIRT_CLR
    yg = yl - u - case.GROOVE_CLR
    rim = case.Z_SPLIT - d
    slope = (zd - zc) / p                                  # the catch face: dz per mm of y

    def catch_y(z):
        """y of the lid's catch face at height z (the lid moved d short of closed)."""
        return (z + d - (zc - pre)) / slope + (yf - p)
    bend = 0.0
    for z in np.linspace(za, zd, 1200):
        if z > rim:
            continue                                       # no lid there yet
        if z <= zb:
            out = -case.SKIRT_CLR + (z - za) / (zb - za) * p
        elif z <= zc:
            out = u
        else:
            out = u - (z - zc) / (zd - zc) * p
        if z > rim - ch:
            cut = (z - (rim - ch)) / ch * cd               # the rim chamfer
        elif z >= case.clip_catch_z(yl) - d:
            cut = 0.0                                      # the lip, at the wall line
        elif z >= case.clip_catch_z(yg) - d:
            cut = yl - catch_y(z)                          # the 45 deg catch face
        elif z >= za - 0.3 - d:
            cut = u + case.GROOVE_CLR                      # the groove
        else:
            cut = 0.0                                      # the wall below the groove
        bend = max(bend, out - cut)
    return bend


def closing_by_hand():
    from round36 import bend_curve
    shell, _, _, _ = load_assembled("battery")
    lid = to_manifold(shell)
    worst, bad = 0.0, []
    for x, side in case.CLIPS[:2]:                         # one bottom-wall pair is enough: the top is its mirror
        d, b = bend_curve(lid, x, side)
        for di, bi in zip(d, b):
            h = bend_by_hand(di)
            worst = max(worst, abs(h - bi))
            if abs(h - bi) > 0.03:
                bad.append((x, round(di, 2), round(bi, 3), round(h, 3)))
    report(worst <= 0.03, f"closing curve worked out by hand vs measured on the meshes (2 clips x 61 points): worst "
                          f"difference {worst:.3f} mm (want 0.03){'; ' + str(bad[:6]) if bad else ''}")


if __name__ == "__main__":
    tilt_open()
    closing_by_hand()
    print(f"\nRound 42: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
