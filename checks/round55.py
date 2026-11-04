#!/usr/bin/env python3
"""Debug round 55 (session 5): methods not used in rounds 1-54.

1. Put together the wrong way round. Round 37 checked that the documents answer the mistakes a
   person could make; here the parts themselves are tried. The board is put into the lid turned
   round in its plane (display still down, the dial at the bottom), and turned over about either axis
   (display toward the back); the back cover is put onto the lid turned round (its dial tab at the
   bottom). Each must run into the lid by more than 1 mm3, so it can't sit flat or close without you
   noticing. As a control, the right way round must overlap nothing (the clip hooks, which are
   springs, left out of the cover).
2. The guides' finished pages, looked at by me (not a script): all 7 pages of each PDF, as printed.
3. A read-through of the debug log's entries for rounds 51-54 as a whole: every figure in them that a
   later round changed must be corrected in a later entry.
"""
import os
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


def wrong_way():
    from manifold3d import Manifold
    from round1 import hooks
    zt = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    lid = case.front_shell(zt)
    cover = case.back_cover(zt, "battery") - hooks()
    parts = case.board_model()
    board = Manifold()
    for m in parts.values():
        board += m
    cx, cy = case.BW / 2, case.BH / 2
    bb = parts["pcb"].bounding_box()
    zm = (bb[2] + bb[5]) / 2                                   # the PCB's mid-plane

    def turned(m, how):
        m = m.translate([-cx, -cy, -zm])
        m = {"round": m.rotate([0, 0, 180]), "over long": m.rotate([180, 0, 0]), "over short": m.rotate([0, 180, 0])}[how]
        return m.translate([cx, cy, zm])
    ctrl_board, ctrl_cover = (board ^ lid).volume(), (cover ^ lid).volume()
    ctrl_board_cover = (cover ^ board).volume()
    rows, ok = [], ctrl_board < 0.01 and ctrl_cover < 0.01 and ctrl_board_cover < 0.01
    for label, how in (("the board turned round (dial at the bottom)", "round"),
                       ("the board turned over about its long axis", "over long"),
                       ("the board turned over about its short axis", "over short")):
        v = (turned(board, how) ^ lid).volume()
        hit = sorted(((turned(m, how) ^ lid).volume(), k) for k, m in parts.items())[-1]
        ok &= v > 1.0
        rows.append(f"{label}: {v:.0f} mm3 into the lid (most of it the {hit[1].replace('_', ' ')}, {hit[0]:.0f} mm3)")
    c = cover.translate([-cx, -cy, 0]).rotate([0, 0, 180]).translate([cx, cy, 0])
    v = (c ^ lid).volume()
    ok &= v > 1.0
    rows.append(f"the back cover turned round (tab at the bottom): {v:.0f} mm3 into the lid")
    report(ok, f"put together the wrong way round (control, the right way: board and lid {ctrl_board:.2f} mm3, cover "
               f"and lid {ctrl_cover:.2f}, cover and board {ctrl_board_cover:.2f}): " + "; ".join(rows)
               + " (want more than 1 mm3 each, so none can sit flat or close unnoticed)")


if __name__ == "__main__":
    wrong_way()
    print("  ..   the guides' pages looked at, and the log's entries for rounds 51-54 read: see DEBUG_LOG.md, round 55")
    print(f"\nRound 55: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
