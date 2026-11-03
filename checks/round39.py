#!/usr/bin/env python3
"""Debug round 39 (session 5): methods not used in rounds 1-38.

1. The assembly as the guides order it, on the meshes, with 4 mm and with 3 mm standoffs. Step 1: the
   board lies face down in the lid; it rests on its pads (found by lowering it until it touches), and
   the glass must then be clear of the lid. Step 3: the cover clicks on; its posts must not reach the
   standoffs yet (the clips close with nothing pressing the board). Step 4: each screw drops through
   its hole onto its standoff; it must catch the thread (be at least one M2.5 pitch, 0.45 mm, into
   the standoff) before its head seats, and then pull the board back off the pads until the
   standoff meets the post, with the head in its recess and 2 mm of thread engaged.
2. The lid's grooves as sliced: in PrusaSlicer's G-code for the lid (0.2 mm layers), no plastic
   inside a groove at the layers it spans, the lip above each groove printed, and the plate over the
   glass at the thickness the design gives it.
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled, to_manifold, vol  # noqa: E402

problems = []
skipped = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def skip(msg):
    print("  SKIP " + msg)
    skipped.append(msg)


# ------------------------------------------------------------------ 1
def assembly():
    shell, _, cover, z_total = load_assembled("battery")
    S, C = to_manifold(shell), to_manifold(cover)
    seat = z_total - case.SCREW_HEAD_DEPTH
    rows, bad = [], []
    for h in (case.STANDOFF_H, case.STANDOFF_H_MIN):
        b = case.board_model(h)
        pcb_etc = b["pcb"] + b["standoffs"]
        # step 1: lower the board (face down) toward the front until it touches the lid
        lo, hi = 0.0, 3.0
        for _ in range(24):
            mid = (lo + hi) / 2
            if vol(pcb_etc.translate([0, 0, -mid]) ^ S) > 1e-4:
                hi = mid
            else:
                lo = mid
        rest = lo                                  # how far in front of its screwed place it rests
        glass = None
        for d in np.arange(0.0, 2.0, 0.02):
            if vol(b["panel"].translate([0, 0, -rest - d]) ^ S) > 1e-4:
                glass = d
                break
        touches_pcb = vol(b["pcb"].translate([0, 0, -rest - 0.02]) ^ S) > 1e-4
        # step 3: the cover clicked on, the board still resting: posts vs standoffs
        post_gap = rest - 0.0                     # the standoffs meet the posts only when the board is screwed back
        hit = vol(b["standoffs"].translate([0, 0, -rest]) ^ C)
        # step 4: the screw drops onto the standoff top; then it is turned in
        top = case.POST_Z - rest                  # standoff top while the board rests
        head_above = (top + case.SCREW_LEN) - seat  # head height over its seat when the tip touches the top
        caught = head_above                       # thread engaged when the head seats (the screw goes in that far)
        final = case.SCREW_LEN - (seat - case.POST_Z)
        rows.append((h, rest, glass, touches_pcb, hit, head_above, final))
        if not (touches_pcb and glass is not None and glass >= 0.2 and hit < 1e-3 and post_gap > 0
                and caught >= 0.45 and abs(final - 2.6) < 0.05):      # 2.6 mm in: the README's figure
            bad.append(h)
    report(not bad, "assembly in the guides' order: " + "; ".join(
        f"{h:.0f} mm standoffs: the board rests on its pads {r:.2f} mm in front of its screwed place, glass "
        f"{g:.2f} mm off the lid; posts clear of the standoffs while the clips close ({x:.3f} mm3); each screw "
        f"catches {c:.2f} mm of thread before its head seats, then pulls the board {r:.2f} mm back and ends "
        f"{f:.2f} mm in" for h, r, g, t, x, c, f in rows) + (f"; problems with {bad}" if bad else ""))


# ------------------------------------------------------------------ 2
def lid_sliced():
    exe = shutil.which("prusa-slicer")
    if not exe:
        skip("lid as sliced: PrusaSlicer not installed")
        return
    import trimesh
    from round19 import SETTINGS
    from round35 import extrusions_typed
    stl = os.path.join(ROOT, "stl", "front_shell_battery.stl")
    tm = trimesh.load(stl)
    lo, hi = tm.bounds
    shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2
    with tempfile.TemporaryDirectory() as d:
        g = os.path.join(d, "out.gcode")
        subprocess.run([exe, "--export-gcode", *SETTINGS, "--support-material=0", "-o", g, stl],
                       capture_output=True, text=True, timeout=900, check=True)
        ex = extrusions_typed(open(g).read())
    zs = sorted(ex)
    mirror = lambda x: case.BW - x                 # noqa: E731  front_for_print mirrors x about the board's middle

    def near(z, x, y, r):
        """Extrusion (with its half width) within r of the point (design x, y) on layer z."""
        px, py = mirror(x) + shift[0], y + shift[1]
        for s in ex[z]:
            a, b = np.array(s[:2]), np.array(s[2:4])
            t = np.clip(np.dot([px, py] - a, b - a) / max(np.dot(b - a, b - a), 1e-12), 0, 1)
            if np.hypot(*(a + t * (b - a) - [px, py])) < r + s[4] / 2:
                return True
        return False
    p, za, zb, zc, zd = case.clip_levels()
    bad = []
    for x, side in case.CLIPS:
        s = 1 if side == "bottom" else -1
        wall = -case.CLR if side == "bottom" else case.BH + case.CLR
        y_in = wall - s * (case.CLIP_UNDERCUT + case.GROOVE_CLR) * 0.6     # inside the groove, short of its bottom
        z_lo, z_hi = za, case.clip_catch_z(-case.CLR - case.CLIP_UNDERCUT - case.GROOVE_CLR)
        filled = [z for z in zs if z - 0.2 >= z_lo + 0.05 and z <= z_hi - 0.05 and near(z, x, y_in, 0.05)]   # layers inside the groove
        lip = [z for z in zs if case.Z_SPLIT - 0.6 < z <= case.Z_SPLIT + 0.01 and near(z, x, wall - s * 1.0, 0.1)]
        if filled or not lip:
            bad.append((side, x, filled, lip))
    # the plate over the glass: the top layer with plastic at a point over the glass, beside the window
    plate = max((z for z in zs if z < 3 and near(z, 52.0, 2.2, 0.1)), default=None)
    want = case.T_FRONT - case.GLASS_RELIEF
    ok_plate = plate is not None and abs(plate - want) <= 0.1 + 1e-6
    report(not bad and ok_plate, f"lid as sliced (0.2 mm layers): {len(case.CLIPS)} grooves empty of plastic over the "
                                 f"layers they span, each with its lip printed above; the plate over the glass ends at "
                                 f"{plate} mm (designed {want:.1f}){'; problems: ' + str(bad) if bad else ''}")


if __name__ == "__main__":
    assembly()
    lid_sliced()
    print(f"\nRound 39: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
