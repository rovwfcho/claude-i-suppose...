#!/usr/bin/env python3
"""Debug round 13: checks for the battery layout (454261 battery + speaker side by side).

1. Battery drop-in: the cell (the owner's measured one, the largest plausible one and a bay-sized
   block) lowered straight into its bay must not touch the guides; once in, the guides must keep it
   within the bay's free space of its place
2. Speaker: its pocket must clear the battery, guides, posts and blocks; the speaker must fit the
   pocket in every position the brackets allow; every grille opening must stay under the membrane
   (so it is never blocked) and well inside the sealed face (so nothing leaks round the speaker)
3. Wires: tubes as thick as the wires (2.5 mm battery pair, 2.8 mm sleeved speaker cable) along the
   routes in case.py, and the spare speaker cable's loop, must be clear of the closed case, the board
   parts, the battery and the speaker
4. Thickness: the battery version is exactly parts room + battery room + the fixed stack
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

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def setup():
    shell, _, cover_asm, z_total = load_assembled("battery")
    return to_manifold(shell), to_manifold(cover_asm), z_total, z_total - case.T_BACK


# ------------------------------------------------------------------ 1
def battery_drop():
    S, C, z_total, z_in = setup()
    x0, x1, y0, y1 = case.BATTERY_BAY
    L, W, T = case.BATTERY_SIZE
    for label, (bl, bw, bt) in (("454261 as measured (%.1f x %.1f x %.1f)" % (L, W, T), (L, W, T)),
                                ("454261 largest (%.1f x %.1f x %.1f)" % case.BATTERY_MAX, case.BATTERY_MAX),
                                ("bay-sized block", (x1 - x0, y1 - y0, case.BATTERY_SPACE))):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cell = case.box(cx - bl / 2, cx + bl / 2, cy - bw / 2, cy + bw / 2, z_in - bt, z_in)
        # with the cover lying open side up, the cell comes down onto the floor: in assembly
        # coordinates that is a move toward +z, ending on the inside of the back wall
        path = Manifold.hull(cell + cell.translate([0, 0, -25]))
        hit = vol(path ^ C)
        report(hit < 1e-3, f"battery drop-in, {label}: touches the cover {hit:.4f} mm3")
    # how far can the real cell slide before a guide stops it
    cell = case.box((x0 + x1) / 2 - L / 2, (x0 + x1) / 2 + L / 2, (y0 + y1) / 2 - W / 2, (y0 + y1) / 2 + W / 2, z_in - T, z_in)
    worst = 0.0
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        lo, hi = 0.0, 10.0
        for _ in range(30):
            mid = (lo + hi) / 2
            if vol(cell.translate([d[0] * mid, d[1] * mid, 0]) ^ C) > 1e-4:
                hi = mid
            else:
                lo = mid
        worst = max(worst, lo)
    play = max((x1 - x0) - L, (y1 - y0) - W) / 2
    report(worst <= play + 0.05, f"battery held by the guides: the measured cell can slide at most {worst:.2f} mm "
                                 f"(the free space is {play:.2f} mm; a larger cell has less)")


# ------------------------------------------------------------------ 2
def speaker():
    S, C, z_total, z_in = setup()
    sx, sy = case.SPEAKER["battery"]
    w, h, t = case.SPEAKER_BOX["battery"]
    spk = case.box(sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2, z_in - t, z_in)
    x0, x1, y0, y1 = case.BATTERY_BAY
    bat = case.box(x0, x1, y0, y1, z_in - case.BATTERY_SPACE, z_in)
    report(vol(spk ^ (C + bat)) < 1e-3, f"speaker pocket {w:.1f} x {h:.1f} x {t} mm at ({sx}, {sy}): overlap with "
                                         f"cover/battery {vol(spk ^ (C + bat)):.4f} mm3")
    # the measured speaker, pushed into every corner and edge the brackets allow (0.01 mm short of touching)
    a, b, c = case.SPEAKER_SIZE
    rx, ry = case.SPK_ROOM[0] - 0.01, case.SPK_ROOM[1] - 0.01
    worst = 0.0
    for dx in (-rx, 0.0, rx):
        for dy in (-ry, 0.0, ry):
            sp = case.box(sx + dx - a / 2, sx + dx + a / 2, sy + dy - b / 2, sy + dy + b / 2, z_in - c, z_in)
            worst = max(worst, vol(sp ^ C))
    report(worst < 1e-3, f"speaker {a} x {b} x {c} mm in every position the brackets allow "
                         f"({case.SPK_ROOM[0]:.2f} / {case.SPK_ROOM[1]:.2f} mm each way): "
                         f"worst overlap with the cover {worst:.4f} mm3")
    # grille openings: found as through-holes in the back wall with vertical rays on a fine grid
    tm = case.to_trimesh(C)
    xs, ys = np.meshgrid(np.arange(sx - 15, sx + 15, 0.1), np.arange(sy - 12, sy + 12, 0.1))
    o = np.column_stack([xs.ravel(), ys.ravel(), np.full(xs.size, z_total + 1)])
    hit = tm.ray.intersects_any(o, np.tile([0, 0, -1.0], (len(o), 1)))
    holes = o[~hit][:, :2]
    dx, dy = np.abs(holes[:, 0] - sx), np.abs(holes[:, 1] - sy)
    mw, mh = case.SPEAKER_WINDOW
    # under the membrane even with the speaker pushed fully to one side of its pocket
    under = (dx <= mw / 2 - case.SPK_ROOM[0]) & (dy <= mh / 2 - case.SPK_ROOM[1])
    # at least 1.5 mm inside the speaker's face (its gasket and tape seal there), wherever it sits
    sealed = (dx <= a / 2 - case.SPK_ROOM[0] - 1.5) & (dy <= b / 2 - case.SPK_ROOM[1] - 1.5)
    report(len(holes) > 0 and under.all() and sealed.all(),
           f"grille: {len(holes)} open grid points (0.1 mm), {dx.max():.2f} x {dy.max():.2f} mm from the centre at most; "
           f"all under the {mw} x {mh} mm membrane in every speaker position: {bool(under.all())}; "
           f"all 1.5 mm inside its sealed face: {bool(sealed.all())}")


# ------------------------------------------------------------------ 3
def tube(points, r=1.25):
    out = Manifold()
    for a, b in zip(points[:-1], points[1:]):
        out += Manifold.hull(Manifold.sphere(r, 24).translate(list(a)) + Manifold.sphere(r, 24).translate(list(b)))
    return out


def wires():
    S, C, z_total, z_in = setup()
    board = case.board_model()
    every = Manifold()
    for g in board.values():
        every += g
    x0, x1, y0, y1 = case.BATTERY_BAY
    bat = case.box(x0, x1, y0, y1, z_in - case.BATTERY_SPACE, z_in)
    sx, sy = case.SPEAKER["battery"]
    w, h, t = case.SPEAKER_BOX["battery"]
    spk = case.box(sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2, z_in - t, z_in)
    obst = S + C + every + bat + spk   # case, board parts, battery (whole bay) and speaker all count
    # battery wire: leaves the battery's end face, drops beside the bay, runs along the bottom of the
    # board over the microSD socket and stops in front of the BAT header (x 29.5-38.5, y 0.5-5)
    bat_path, rb = case.battery_wire_route()
    hit_b = vol(tube(bat_path, rb) ^ obst)
    Lb = sum(np.linalg.norm(np.subtract(a, b)) for a, b in zip(bat_path[:-1], bat_path[1:]))
    report(hit_b < 1e-3, f"battery wire route to the BAT header, clear of case, board parts, battery and speaker: "
                         f"{hit_b:.4f} mm3 (about {Lb:.0f} mm long; the wire is about 57 mm)")
    # speaker cable: leaves the speaker's long side facing the battery, drops through the gap between
    # the bay and the pocket and runs under the battery to the front of the SPK header (x 52.5-61.5)
    spk_path, rs = case.speaker_wire_route()
    hit_s = vol(tube(spk_path, rs) ^ obst)
    Ls = sum(np.linalg.norm(np.subtract(a, b)) for a, b in zip(spk_path[:-1], spk_path[1:]))
    report(hit_s < 1e-3, f"speaker wire route to the SPK header, clear of case, board parts, battery and speaker: "
                         f"{hit_s:.4f} mm3 (about {Ls:.0f} mm long; the cable is about 106 mm)")
    # the spare speaker cable: one loop lying on the back cover above the speaker
    coil, rc = case.speaker_cable_coil()
    hit_c = vol(tube(coil, rc) ^ obst)
    Lc = sum(np.linalg.norm(np.subtract(a, b)) for a, b in zip(coil[:-1], coil[1:]))
    report(hit_c < 1e-3, f"spare speaker cable loop above the speaker, clear of everything: {hit_c:.4f} mm3 "
                         f"(holds about {Lc:.0f} mm of cable)")


# ------------------------------------------------------------------ 4
def thickness():
    _, _, z_total, _ = setup()
    fixed = case.T_FRONT + case.PANEL_SPACE + case.PCB_T + case.T_BACK
    report(abs(z_total - (fixed + case.PARTS_SPACE + case.BATTERY_SPACE)) < 1e-6 and abs(z_total - 16.7) < 1e-6,
           f"battery version {z_total:.1f} mm = {fixed:.1f} fixed + {case.PARTS_SPACE} parts + {case.BATTERY_SPACE} battery")


if __name__ == "__main__":
    thickness()
    battery_drop()
    speaker()
    wires()
    print(f"\nRound 13: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
