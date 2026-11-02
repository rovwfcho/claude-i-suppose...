#!/usr/bin/env python3
"""Debug round 13: checks for the battery layout (454261 battery + speaker side by side).

1. Battery drop-in: the cell (and an oversize 63 x 43 x 5 mm version) lowered straight into its bay
   must not touch the guides; once in, the guides must keep it within 1 mm of its place
2. Speaker: its space must clear the battery, guides, posts and blocks, and every grille hole must
   sit under the speaker (estimated 18 x 13 mm face)
3. Wires: 2.5 mm tubes from the battery's and the speaker's corners to the BAT and SPK headers must
   find a path through the free space of the closed case (around the screw blocks)
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
    for label, (bl, bw, bt) in (("454261 nominal (61 x 42 x 4.5)", (L, W, T)),
                                ("454261 largest (64.6 x 43 x 4.8)", case.BATTERY_MAX),
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
    report(worst <= play + 0.05, f"battery held by the guides: the nominal cell can slide at most {worst:.2f} mm "
                                 f"(the free space is {play:.2f} mm; a longer cell has less)")


# ------------------------------------------------------------------ 2
def speaker():
    S, C, z_total, z_in = setup()
    sx, sy = case.SPEAKER["battery"]
    w, h, t = case.SPEAKER_BOX["battery"]
    spk = case.box(sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2, z_in - t, z_in)
    x0, x1, y0, y1 = case.BATTERY_BAY
    bat = case.box(x0, x1, y0, y1, z_in - case.BATTERY_SPACE, z_in)
    report(vol(spk ^ (C + bat)) < 1e-3, f"speaker space {w:.0f} x {h:.0f} x {t} mm at ({sx}, {sy}): overlap with "
                                         f"cover/battery {vol(spk ^ (C + bat)):.4f} mm3")
    # grille holes: find them as through-holes in the back wall with vertical rays on a fine grid
    import trimesh
    tm = case.to_trimesh(C)
    xs, ys = np.meshgrid(np.arange(sx - 15, sx + 15, 0.2), np.arange(sy - 12, sy + 12, 0.2))
    o = np.column_stack([xs.ravel(), ys.ravel(), np.full(xs.size, z_total + 1)])
    hit = tm.ray.intersects_any(o, np.tile([0, 0, -1.0], (len(o), 1)))
    holes = o[~hit][:, :2]
    inside = (np.abs(holes[:, 0] - sx) <= 6.5) & (np.abs(holes[:, 1] - sy) <= 9.0)  # 13 x 18 face (turned)
    report(len(holes) > 0 and inside.all(), f"grille: {len(holes)} open grid points, all under a 13 x 18 mm speaker "
                                            f"face: {bool(inside.all())}")


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
    obst = S + C + every + bat + spk   # case, board parts, battery and speaker all count
    zs = case.Z_B + 1.9 + 1.25            # resting on top of the microSD socket (1.9 mm tall)
    # battery wire: leaves the battery's end face, drops beside the bay, runs along the bottom of the
    # board over the microSD socket and stops in front of the BAT header (x 29.5-38.5, y 0.5-5)
    bat_path = [(x0 - 1.4, y0 + 3.0, z_in - case.BATTERY_SPACE / 2), (3.5, y0 + 3.0, zs),
                (3.5, 7.6, zs), (34.0, 7.6, zs), (34.0, 6.4, zs)]
    hit_b = vol(tube(bat_path) ^ obst)
    Lb = sum(np.linalg.norm(np.subtract(a, b)) for a, b in zip(bat_path[:-1], bat_path[1:]))
    report(hit_b < 1e-3, f"battery wire route to the BAT header, clear of case, board parts, battery and speaker: "
                         f"{hit_b:.4f} mm3 (about {Lb:.0f} mm long)")
    # speaker wire: leaves the speaker's lower side, drops in the gap right of the screw block at
    # x = 64, then runs left under the battery to the front of the SPK header (x 52.5-61.5)
    zl = case.Z_B + 1.4 + 1.25 + 0.05
    spk_path = [(sx - w / 2 + 2.0, sy - h / 2 - 1.4, z_in - t / 2), (68.5, 4.0, z_in - t / 2), (68.5, 4.0, zl),
                (68.5, 7.6, zl), (57.0, 7.6, zl), (57.0, 6.4, zl)]
    hit_s = vol(tube(spk_path) ^ obst)
    Ls = sum(np.linalg.norm(np.subtract(a, b)) for a, b in zip(spk_path[:-1], spk_path[1:]))
    report(hit_s < 1e-3, f"speaker wire route to the SPK header, clear of case, board parts, battery and speaker: "
                         f"{hit_s:.4f} mm3 (about {Ls:.0f} mm long; its cable is about 95 mm)")


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
