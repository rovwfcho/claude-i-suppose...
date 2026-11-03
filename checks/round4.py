#!/usr/bin/env python3
"""Debug round 4: methods not used in rounds 1-3.

1. Dial reach with the smaller protrusion seen on Waveshare's drawing (2.0 mm instead of 2.6)
2. Worst-case corners (not random): PCB 1.5/1.7 mm, panel 1.0/1.6 mm, standoffs pushed inward
3. Seam: outer outlines of shell and cover compared at the parting plane (no step or lip)
4. Longest usable screw, from rays along each screw axis
5. Thinnest web between the display window and the panel-tail relief, from 2D sections
6. README numbers compared with the STL files
7. Cross-section images for review by eye
"""
import math
import os
import re
import sys

import numpy as np
import trimesh

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


# ------------------------------------------------------------------ 1
def dial_small(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    obstacle = to_manifold(shell) + to_manifold(cover_asm)
    wx, wy, wr = case.WHEEL
    rim_y = case.BH + 2.0  # drawing value
    z = case.Z_B + 1.5
    for r in (6.0, 8.0):
        for ang in (0, 30, -30):
            d = np.array([math.sin(math.radians(ang)), -1.0, 0.0])
            d /= np.linalg.norm(d)
            target = np.array([wx, rim_y, z])
            sph = Manifold.sphere(r, 96)
            start = target - d * (r + 20)
            hit = lambda t: not (sph.translate(list(start + d * t)) ^ obstacle).is_empty()
            lo, hi = 0.0, 20.0
            if hit(hi):
                for _ in range(35):
                    mid = (lo + hi) / 2
                    lo, hi = (mid, hi) if not hit(mid) else (lo, mid)
                short = 20.0 - lo
            else:
                short = 0.0
            report(short <= 0.5, f"{variant} dial (2.0 mm proud) finger r={r:.0f} at {ang:+d} deg: "
                                 f"stops {short:.2f} mm before the rim")


# ------------------------------------------------------------------ 2
def worst_corners(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    S, C = to_manifold(shell), to_manifold(cover_asm)
    # stack-up with the board screwed to the posts: PCB 1.5-1.7 mm, standoffs 3-4 mm, panel stack
    # 1.0-1.6 mm. The pads must never press the PCB, the glass never touch the lid.
    lip = case.T_FRONT - case.GLASS_RELIEF
    pad_top = case.Z_PF - case.PAD_GAP
    worst_pad, worst_glass = np.inf, np.inf
    for t in (1.5, 1.6, 1.7):
        for h in (case.STANDOFF_H_MIN, case.STANDOFF_H):
            front = case.POST_Z - h - t
            worst_pad = min(worst_pad, front - pad_top)
            for p in (1.0, 1.2, 1.6):
                worst_glass = min(worst_glass, front - p - lip)
    report(worst_pad > 0, f"{variant} worst case PCB 1.7 mm on 4 mm standoffs: pads {worst_pad:.2f} mm in front of it")
    report(worst_glass >= 0.15, f"{variant} worst case PCB 1.7 mm, 4 mm standoffs, 1.6 mm panel stack: glass "
                                f"{worst_glass:.2f} mm from the lid (1.2 mm stack: {worst_glass + 0.4:.2f})")
    # standoffs 0.5 mm toward the board centre, at the largest measured size, 3 and 4 mm tall: they may
    # only touch the posts' end faces
    r = 4.6 / 2
    worst = 0.0
    for h in (case.STANDOFF_H_MIN, case.STANDOFF_H):
        z0 = case.POST_Z - h
        for px, py in case.POSTS:
            sx = 1 if px < case.BW / 2 else -1
            sy = 1 if py < case.BH / 2 else -1
            for dx, dy in ((0.5 * sx, 0), (0, 0.5 * sy), (0.5 * sx, 0.5 * sy)):
                cyl = case.cyl_z(px + dx, py + dy, r, z0, case.POST_Z - 0.001)
                worst = max(worst, vol(cyl ^ (S + C)))
    report(worst < 1e-3, f"{variant} worst case standoffs 4.6 mm wide, 3 or 4 mm tall, 0.5 mm inward: overlap {worst:.3f} mm3")


# ------------------------------------------------------------------ 3
def seam(variant):
    """The outer surface is convex, so compare the convex hulls of the two parts' sections taken
    just either side of the parting plane (slots and notches at the seam do not disturb the hull)."""
    from scipy.spatial import ConvexHull
    from shapely.geometry import Polygon
    shell, _, cover_asm, _ = load_assembled(variant)
    z = case.Z_SPLIT
    hulls = []
    for mesh, zz in ((shell, z - 0.02), (cover_asm, z + 0.02)):
        sec = mesh.section(plane_origin=[0, 0, zz], plane_normal=[0, 0, 1])
        pts = np.concatenate([e[:, :2] for e in sec.discrete])
        hulls.append(Polygon(pts[ConvexHull(pts).vertices]))
    hd = hulls[0].exterior.hausdorff_distance(hulls[1].exterior)
    report(hd <= 0.1, f"{variant} seam: outer outlines of shell and cover differ by at most {hd:.3f} mm "
                      f"(0.04 mm apart in height, so a curved edge alone accounts for a few hundredths)")


# ------------------------------------------------------------------ 4
def screw_length(variant):
    """Down each corner hole from the head's seat: clear plastic to the post end, then the standoff;
    the PCB itself must stay beyond the tip of an 8 mm screw even with 3 mm standoffs."""
    shell, _, cover_asm, z_total = load_assembled(variant)
    asm = trimesh.util.concatenate([shell, cover_asm])
    for px, py in case.POSTS:
        seat = z_total - case.SCREW_HEAD_DEPTH
        o = np.array([px, py, seat - 0.01])
        d = np.array([0, 0, -1.0])
        locs, _, _ = asm.ray.intersects_location([o], [d], multiple_hits=True)
        clear = seat - locs[:, 2].max() if len(locs) else np.inf         # plastic on the axis below the seat
        res = []
        for h in (case.STANDOFF_H, case.STANDOFF_H_MIN):
            b = case.board_model(h)
            pcb = case.to_trimesh(b["pcb"])
            bl, _, _ = pcb.ray.intersects_location([o], [d], multiple_hits=False)
            res.append(seat - bl[0][2] if len(bl) else np.inf)            # seat to the PCB along the axis
        longest = math.floor(min(res) - 0.5)
        report(clear >= seat - case.POST_Z and longest >= case.SCREW_LEN and seat - case.POST_Z + 1.5 <= case.SCREW_LEN,
               f"{variant} corner screw ({px:.1f}, {py:.1f}): hole clear down to the standoff; seat to PCB "
               f"{res[0]:.2f} mm (4 mm standoffs) / {res[1]:.2f} mm (3 mm) -> M2.5 x {case.SCREW_LEN:.0f} goes "
               f"{case.SCREW_LEN - (seat - case.POST_Z):.1f} mm into the standoff, longest safe {longest} mm")


# ------------------------------------------------------------------ 5
def window_web(variant):
    shell, _, _, _ = load_assembled(variant)
    from shapely.geometry import Polygon
    worst = np.inf
    for z in np.arange(case.T_FRONT - 0.49, case.T_FRONT - 0.01, 0.05):
        sec = shell.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        planar, tf = sec.to_2D()
        for poly in planar.polygons_full:
            pts3 = lambda ring: trimesh.transform_points(np.column_stack([np.asarray(ring.coords), np.zeros(len(ring.coords))]), tf)[:, :2]
            ext = Polygon(pts3(poly.exterior), [pts3(r) for r in poly.interiors])
            # web: material strip between x = TAIL_X1 and the window's left edge
            strip = ext.intersection(Polygon([(case.TAIL_X1 - 0.5, 5), (case.WIN_CX, 5), (case.WIN_CX, 55), (case.TAIL_X1 - 0.5, 55)]))
            if not strip.is_empty:
                for g in getattr(strip, "geoms", [strip]):
                    if g.area > 0.01:
                        minx, _, maxx, _ = g.bounds
                        if minx < case.TAIL_X1 + 0.6:
                            worst = min(worst, maxx - minx)
    report(worst >= 0.8, f"{variant} thinnest web between panel-tail relief and window: {worst:.2f} mm")


# ------------------------------------------------------------------ 6
def readme_numbers():
    text = open(os.path.join(ROOT, "README.md")).read()
    for variant in case.CAVITY:
        shell, cover, _, z_total = load_assembled(variant)
        size = shell.bounds[1] - shell.bounds[0]
        m = re.search(r"It measures ([\d.]+) x ([\d.]+) x ([\d.]+) mm", text)
        ok = m and abs(float(m.group(1)) - size[0]) < 0.05 and abs(float(m.group(2)) - size[1]) < 0.05 \
            and abs(float(m.group(3)) - z_total) < 0.05
        report(bool(ok), f"README {variant} size {m.groups() if m else None} vs STL {size[0]:.1f} x {size[1]:.1f} x {z_total:.1f}")
    m = re.search(r"Display window:\*\* ([\d.]+) x ([\d.]+) mm", text)
    report(m and float(m.group(1)) == case.WIN_W and float(m.group(2)) == case.WIN_H,
           f"README window {m.groups() if m else None} vs model {case.WIN_W} x {case.WIN_H}")
    m = re.search(r"opening ([\d.]+) mm wide", text)
    w = case.BTN_NOTCH[1] - case.BTN_NOTCH[0]
    report(m and abs(float(m.group(1)) - w) < 0.05, f"README button opening {m.group(1) if m else None} vs model {w:.1f}")
    want = f"{len(case.POSTS)} × M2.5 × {case.SCREW_LEN:.0f} mm screws"
    report(want in text, f"README screws: '{want}' present: {want in text}")


# ------------------------------------------------------------------ 7
def section_images(variant, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    shell, _, cover_asm, _ = load_assembled(variant)
    board = case.board_model()
    every = board["pcb"]
    for k, g in board.items():
        if k != "pcb":
            every += g
    btm = case.to_trimesh(every)
    cuts = [("x = 74 (BOOT)", [74.0, 0, 0], [1, 0, 0], 1, (-5, 10)),
            ("x = 20 (bottom screw)", [20.0, 0, 0], [1, 0, 0], 1, (-5, 10)),
            ("x = 79 (dial)", [79.0, 0, 0], [1, 0, 0], 1, (50, 65)),
            ("y = 30 (USB-C)", [0, 30.0, 0], [0, 1, 0], 0, (-5, 10)),
            ("y = 14 (microSD)", [0, 13.95, 0], [0, 1, 0], 0, (-5, 10)),
            ("y = 2.85 (standoff + pad)", [0, 2.85, 0], [0, 1, 0], 0, (-5, 12))]
    fig, axs = plt.subplots(2, 3, figsize=(15, 9), dpi=100)
    for ax, (title, o, n, axis, lim) in zip(axs.ravel(), cuts):
        for mesh, col in ((shell, "#6b8fd6"), (cover_asm, "#d69b6b"), (btm, "#2f8a4c")):
            sec = mesh.section(plane_origin=o, plane_normal=n)
            if sec is None:
                continue
            for ent in sec.discrete:
                ax.fill(ent[:, axis], ent[:, 2], color=col, alpha=0.8, lw=0)
        ax.set_xlim(*lim)
        ax.set_ylim(case.Z_B + case.CAVITY[variant] + case.T_BACK + 0.5, -0.5)
        ax.set_aspect("equal")
        ax.set_title(title)
        ax.grid(alpha=0.3)
    fig.suptitle(f"{variant}: blue = front shell, orange = back cover, green = board model (z down = toward back)")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"  ..   section images written to {out} (review by eye)")


if __name__ == "__main__":
    readme_numbers()
    for v in case.CAVITY:
        print(f"\n### {v}")
        dial_small(v)
        worst_corners(v)
        seam(v)
        screw_length(v)
        window_web(v)
        section_images(v, os.path.join(ROOT, "preview", f"checks_sections_{v}.png"))
    print(f"\nRound 4: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
