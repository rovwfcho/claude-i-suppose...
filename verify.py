#!/usr/bin/env python3
"""Fit checks and section plots for case.py.

Checks, for each variant:
  * every part is a single watertight solid
  * the simplified board model does not intersect either part when assembled
  * the board can be dropped into the front shell from the back without hitting anything
  * the back cover and the shell do not overlap (nothing has to flex to close the case)
  * the PCB is clamped: ledge pads touch its front face, posts its back face
  * the lip clears the glass
"""
import math
import os
import sys

import numpy as np

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

    board = case.board_model()
    for part, geom in board.items():
        a = vol(geom ^ shell)
        b = vol(geom ^ bc)
        good = a < TOL and b < TOL
        ok &= good
        print(f"  {'OK ' if good else 'BAD'} {part:13s} overlap shell={a:.3f} cover={b:.3f} mm3")

    # insertion: board moves from far behind straight down into place
    every = board["pcb"]
    for k, g in board.items():
        if k != "pcb":
            every += g
    worst = 0.0
    for dz in np.arange(0.0, 16.01, 0.25):
        worst = max(worst, vol(every.translate([0, 0, dz]) ^ shell))
    good = worst < TOL
    ok &= good
    print(f"  {'OK ' if good else 'BAD'} board insertion path, worst overlap {worst:.3f} mm3")

    # cover vs shell: rigid parts, so no overlap at all
    ov = vol(shell ^ bc)
    good = ov < TOL
    ok &= good
    print(f"  {'OK ' if good else 'BAD'} cover/shell overlap {ov:.4f} mm3")

    # clamping contacts
    pcb = board["pcb"]
    front_touch = vol(pcb.translate([0, 0, -0.05]) ^ shell)
    # behind: the ring faces stay exactly FOAM_GAP behind the PCB, where the foam tape presses it
    back_near = vol(pcb.translate([0, 0, case.FOAM_GAP - 0.02]) ^ bc)
    back_at = vol(pcb.translate([0, 0, case.FOAM_GAP + 0.05]) ^ bc)
    good = front_touch > 0.1 and back_near < TOL and back_at > 0.1
    ok &= good
    print(f"  {'OK ' if good else 'BAD'} PCB clamped: front pads {front_touch:.2f} mm3 (0.05 mm probe); ring faces "
          f"{case.FOAM_GAP} mm behind it for {case.FOAM_T} mm foam tape ({100 * (1 - case.FOAM_GAP / case.FOAM_T):.0f} % squeeze)")

    # glass must not be loaded
    gap = None
    for d in np.arange(0.0, 1.0, 0.05):
        if vol(board["panel"].translate([0, 0, -d]) ^ shell) > TOL:
            gap = d
            break
    good = gap is not None and gap >= 0.25
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
