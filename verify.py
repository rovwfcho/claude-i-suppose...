#!/usr/bin/env python3
"""Fit checks and section plots for case.py.

Checks, for each variant, with 4 mm and with 3 mm standoffs:
  * every part is a single watertight solid
  * the simplified board model does not intersect either part when assembled
  * the board can be dropped into the lid from the back, and the back cover (with the board screwed
    on) can be lowered onto the lid, without hitting anything but the springy clip hooks
  * the back cover and the lid touch only where the hooks are meant to press (their preload)
  * the corner posts land on the standoff tops, an 8 mm screw goes 2 mm into each standoff and its
    head sits in the recess, not above the back
  * the lid's pads stay PAD_GAP in front of the PCB, and the lip clears the glass
"""
import math
import os
import sys

import numpy as np

from manifold3d import Manifold

import case

TOL = 1e-3  # mm3


def vol(m):
    return 0.0 if m.is_empty() else m.volume()


def check_variant(name, shell, bc, z_total):
    ok = True
    print(f"\n== {name} (total depth {z_total:.1f} mm, outside "
          f"{case.X1 - case.X0:.1f} x {case.Y1 - case.Y0:.1f} mm)")
    for label, m in (("front shell", shell), ("back cover", bc)):
        tm = case.to_trimesh(m)
        bodies = len(m.decompose())
        print(f"  {label}: watertight={tm.is_watertight} bodies={bodies} volume={m.volume() / 1000:.1f} cm3")
        ok &= tm.is_watertight and bodies == 1

    hooks = Manifold()
    for x, side in case.CLIPS:
        hooks += case.clip_hook(x, side)
    for h in (case.STANDOFF_H, case.STANDOFF_H_MIN):
        print(f"  -- {h:.0f} mm standoffs")
        ok &= check_board(shell, bc, z_total, hooks, h)

    # the lid and the cover touch only at the hooks (CLIP_PRELOAD); elsewhere not at all
    ov = vol(shell ^ (bc - hooks))
    pre = vol(shell ^ hooks)
    good = ov < TOL and 0.0 < pre < 4 * 1.0
    ok &= good
    print(f"  {'OK ' if good else 'BAD'} cover/lid overlap away from the hooks {ov:.4f} mm3; hooks press the lid "
          f"{pre:.3f} mm3 (the designed {case.CLIP_PRELOAD} mm preload)")
    return ok


def check_board(shell, bc, z_total, hooks, standoff_h):
    ok = True
    board = case.board_model(standoff_h)
    for part, geom in board.items():
        a = vol(geom ^ shell)
        b = vol(geom ^ bc)
        good = a < TOL and b < TOL
        ok &= good
        print(f"  {'OK ' if good else 'BAD'} {part:13s} overlap lid={a:.3f} cover={b:.3f} mm3")

    # insertion: the board drops into the lid from far behind; and the cover with the board screwed
    # on comes down onto the lid (only the hooks may touch: their beams bend)
    every = board["pcb"]
    for k, g in board.items():
        if k != "pcb":
            every += g
    worst = worst2 = 0.0
    rigid = bc - hooks
    for dz in np.arange(0.0, 16.01, 0.25):
        worst = max(worst, vol(every.translate([0, 0, dz]) ^ shell))
        worst2 = max(worst2, vol((every + rigid).translate([0, 0, dz]) ^ shell))
    good = worst < TOL and worst2 < TOL
    ok &= good
    print(f"  {'OK ' if good else 'BAD'} insertion paths: board into the lid {worst:.3f} mm3, cover with board onto "
          f"the lid {worst2:.3f} mm3 (hooks left out)")

    # posts land on the standoff tops: touching, not overlapping
    so = board["standoffs"]
    touch = vol(so.translate([0, 0, 0.05]) ^ bc)
    good = vol(so ^ bc) < TOL and touch > 4 * 0.05 * 3.0
    ok &= good
    print(f"  {'OK ' if good else 'BAD'} posts on the standoff tops (0.05 mm probe {touch:.2f} mm3)")

    # screws: head in the recess, not above the back face; 8 mm shank goes 2 mm into the standoff
    for px, py in case.POSTS:
        seat = z_total - case.SCREW_HEAD_DEPTH
        head = case.cyl_z(px, py, 2.5, seat, seat + 1.8)
        shank = case.cyl_z(px, py, 1.25, seat - case.SCREW_LEN, seat)
        bite = vol(shank ^ so) / (math.pi * 1.25 ** 2)
        good = vol(head ^ bc) < TOL and vol(shank ^ bc) < TOL and seat + 1.8 <= z_total + 1e-9 and 1.9 <= bite <= 2.1
        ok &= good
        below = (seat - case.SCREW_LEN) - (case.POST_Z - standoff_h)
        good &= below >= 0.9
        ok &= good
        print(f"  {'OK ' if good else 'BAD'} screw at ({px:.1f}, {py:.1f}): head in its recess, {bite:.2f} mm into the "
              f"standoff, tip {below:.2f} mm short of the PCB")

    # pads: PAD_GAP in front of the PCB; glass well clear of the lid
    pcb = board["pcb"]
    near = vol(pcb.translate([0, 0, -(case.PAD_GAP - 0.03)]) ^ shell)
    far = vol(pcb.translate([0, 0, -(case.PAD_GAP + 0.05)]) ^ shell)
    want = case.PAD_GAP + (case.POST_Z - case.Z_B - standoff_h)
    good = near < TOL and (far > 0.1 or standoff_h < case.STANDOFF_H)
    ok &= good
    print(f"  {'OK ' if good else 'BAD'} pads {want:.2f} mm in front of the PCB (never pressing it)")
    gap = None
    for d in np.arange(0.0, 2.5, 0.05):
        if vol(board["panel"].translate([0, 0, -d]) ^ shell) > TOL:
            gap = d
            break
    good = gap is not None and gap >= 0.6
    ok &= bool(good)
    print(f"  {'OK ' if good else 'BAD'} lip-to-glass clearance ~{gap:.2f} mm")
    return ok


def sections(name, shell, bc, out_dir):
    """Cross-sections through the dial and the PWR button showing the stack-up."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    board = case.board_model()
    pcb_etc = board["pcb"] + board["panel"]
    for k in ("usb_c", "sd_socket", "wheel", "buttons", "standoffs", "esp32_module", "connectors"):
        pcb_etc += board[k]

    os.makedirs(out_dir, exist_ok=True)
    fig, axs = plt.subplots(2, 1, figsize=(12, 7), dpi=110)
    for ax, (label, plane_x) in zip(axs, (("Section at x = 79 (dial, top edge)", 79.0),
                                         ("Section at x = 84 (PWR button, bottom edge)", 84.0))):
        for m, col in ((shell, "#6b8fd6"), (bc, "#d69b6b"), (pcb_etc, "#2f8a4c")):
            cs = m.rotate([0, -90, 0]).slice(plane_x)  # rotate so x becomes the slicing height
            for poly in cs.to_polygons():
                p = np.asarray(poly)
                ax.fill(p[:, 1], -p[:, 0], color=col, alpha=0.85)  # rotated frame: x' = -z
        ax.set_aspect("equal")
        ax.set_xlabel("y (mm)")
        ax.set_ylabel("z (mm, 0 = front face)")
        ax.set_title(label)
        ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, f"section_{name}.png"))
    plt.close(fig)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "stl")
    res = case.build(out)
    all_ok = True
    for name, (shell, bc, z_total) in res.items():
        all_ok &= check_variant(name, shell, bc, z_total)
        sections(name, shell, bc, os.path.join(here, "preview"))
    print("\nALL CHECKS PASSED" if all_ok else "\nSOME CHECKS FAILED")
    sys.exit(0 if all_ok else 1)
