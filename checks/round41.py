#!/usr/bin/env python3
"""Debug round 41 (session 5): methods not used in rounds 1-40.

1. case.py's own comments, recomputed: every number the comments beside the session-5 constants
   state (how far the glass floats, how far a screw goes in, the recess's room, the posts' clearance
   at the corners, what the clip length and undercut leave with print errors) is recomputed from the
   code; a comment that no longer matches the code would mislead whoever edits it next.
2. Heat and cold: PLA grows about 68 um per metre per degree, the board's glass-epoxy about 15. From
   0 to 50 degC (the README warns about 55), the mismatch over the board's length must stay inside
   its 0.3 mm side clearance, the screws' spacing must stay inside the holes' play, and the clips'
   preload must not vanish (the lid shrinking or growing in depth against the cover).
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
def comments():
    src = open(os.path.join(ROOT, "case.py"), encoding="utf-8").read()
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    seat = z_total - case.SCREW_HEAD_DEPTH
    glass = case.PANEL_SPACE - case.PANEL_T + case.GLASS_RELIEF
    into = case.SCREW_LEN - (seat - case.POST_Z)
    room = case.SCREW_HEAD_R - 2.5                        # a 5 mm head's room to sit off centre
    play = case.SCREW_HOLE_R - 1.25
    # the posts' corner arc vs the lid's, along the diagonal (the lid's inner corner: radius BR + CLR)
    w = case.SKIRT_CLR
    lid_c = (case.BR + case.CLR) * (1 - 1 / math.sqrt(2))
    post_c = w + case.POST_CORNER_R * (1 - 1 / math.sqrt(2))
    diag = (post_c - lid_c) * math.sqrt(2)
    strain = 100 * 12 * (case.CLIP_UNDERCUT + 0.3) * case.SKIRT_T / case.CLIP_L ** 2
    reach = case.CLIP_UNDERCUT - 0.3
    claims = [
        (r"GLASS_RELIEF = [\d.]+ .*it floats ([\d.]+) mm above it", glass),
        (r"so an 8 mm screw seated in the recess goes\s*#?\s*([\d.]+) mm into the standoff", into),
        (r"SCREW_HOLE_R = [\d.]+ .*passes with ([\d.]+) mm to spare", play),
        (r"SCREW_HEAD_R = [\d.]+ .*M2 washer\) fits ([\d.]+) mm off centre", room),
        (r"so they stay ([\d.]+) mm off them along the\s*#\s*diagonal", diag),
        (r"CLIP_L = [\d.]+ .*0\.3 mm of print error still bends it under ([\d.]+) %", strain),
        (r"CLIP_UNDERCUT = [\d.]+ .*\(([\d.]+) left after 0\.3 mm of error\)", reach),
        (r"CLIP_PRELOAD = ([\d.]+) ", case.CLIP_PRELOAD),
    ]
    bad, n = [], 0
    for rx, value in claims:
        m = re.search(rx, src)
        if not m:
            bad.append(f"not found: {rx}")
            continue
        n += 1
        s = m.group(1)
        dec = len(s.split(".")[1]) if "." in s else 0
        # "under X" claims are limits: the value must be below them; the rest must round to them
        if "under" in rx:
            ok = value < float(s)
        elif "off centre" in rx or "spare" in rx:
            ok = value >= float(s) - 1e-9 and value - float(s) < 0.15
        else:
            ok = abs(value - float(s)) <= 0.5 * 10 ** -dec + 1e-9
        if not ok:
            bad.append(f"'{m.group(0)[:70]}': says {s}, the code gives {value:.3f}")
    report(not bad, f"{n} numbers in case.py's comments on the new closure, recomputed from the code: {bad or 'all agree'}")


# ------------------------------------------------------------------ 2
def heat():
    a_pla, a_pcb = 68e-6, 15e-6
    rows, bad = [], []
    for t in (0.0, 50.0):
        dT = t - 20.0                               # printed and measured at about 20 degC
        # the board inside the lid: growth difference over the board's length, shared by both ends
        side = abs((a_pla - a_pcb) * dT * case.BW) / 2
        # the screws: the posts move with the PLA, the standoffs with the board, from the middle out
        spread = abs((a_pla - a_pcb) * dT * (case.POSTS[1][0] - case.POSTS[0][0])) / 2
        # depth: the lid's rim-to-catch height and the cover's shoulder-to-hook height are both PLA,
        # so the preload changes only with their difference in length (about the hook's height)
        p, za, zb, zc, zd = case.clip_levels()
        pre = case.CLIP_PRELOAD - abs(a_pla * dT * (case.Z_SPLIT - zc))
        rows.append((t, side, spread, pre))
        # each screw's play as printed must cover round 35's worst offset (0.29) plus this
        if side >= case.CLR or spread > (case.SCREW_HOLE_R - 1.25 - 0.075) - 0.29 or pre <= 0:
            bad.append(t)
    report(not bad, "heat and cold: " + "; ".join(
        f"at {t:.0f} °C the board's ends move {s:.3f} mm against its 0.3 mm clearance, each screw {sp:.3f} mm in its "
        f"hole, the clips' preload is {pr:.3f} mm" for t, s, sp, pr in rows))


if __name__ == "__main__":
    comments()
    heat()
    print(f"\nRound 41: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
