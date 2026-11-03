#!/usr/bin/env python3
"""Debug round 46 (session 5): methods not used in rounds 1-45.

1. Stiffness, not strength: how far the parts bend under a press, against the gaps they must keep.
   - The display lip over the PWR/BOOT opening, a bar clamped at both ends of the opening, 10 N pressed
     onto its middle: deflection F L^3 / (192 E I) with I measured on the STL (its weakest section).
     It must stay under the pads' 0.5 mm gap to the PCB (the pad rides on the lip) and the glass's
     0.8 mm.
   - The back plate pressed in its middle with 10 N (a firm hold), as a plate fixed along the walls
     (Roark, rectangular plate, all edges fixed, central load): the battery is taped to it, so it
     moves toward the board by as much. It must stay under the room between your 4.3 mm battery and
     what lies under it, with 3 mm standoffs (the tighter case: the wires on the board, and the board).
   E = 3.0 GPa for printed PLA (3.5 GPa moulded).
2. The lid's first layer on the bed: the lid prints face down, with its front edge rounded and its
   window chamfered, so only a band of the front face touches the bed. That band, cut from the STL
   just above the bed, must be one closed ring round the window, at least 2 mm wide everywhere
   (5 extrusion lines), so the frame is anchored all round and no side starts in mid-air.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled  # noqa: E402

problems = []
E = 3000.0                                   # MPa, printed PLA


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def section_x(mesh, xc, ymax):
    """The mesh's section across x = xc, below y = ymax, as a shapely geometry in (y, z)."""
    import trimesh
    from shapely.geometry import Polygon, box
    sec = mesh.section(plane_origin=[xc, 0, 0], plane_normal=[1, 0, 0])
    planar, tf = sec.to_2D()
    pts = lambda r: trimesh.transform_points(np.column_stack([np.asarray(r.coords), np.zeros(len(r.coords))]), tf)[:, 1:3]  # noqa: E731
    out = None
    for p in planar.polygons_full:
        g = Polygon(pts(p.exterior), [pts(r) for r in p.interiors]).intersection(box(-10, -10, ymax, case.Z_SPLIT))
        if g.area > 0.01:
            out = g if out is None else out.union(g)
    return out


def inertia(g):
    """Second moment of area (mm4) about the centroid's axis along y: bending under a load along z."""
    from shapely import contains_xy
    y0, z0, y1, z1 = g.bounds
    Y, Z = np.meshgrid(np.arange(y0, y1, 0.01) + 0.005, np.arange(z0, z1, 0.01) + 0.005)
    m = contains_xy(g, Y, Z)
    zc = Z[m].mean()
    return ((Z[m] - zc) ** 2).sum() * 1e-4


# ------------------------------------------------------------------ 1
def lip():
    shell, _, _, _ = load_assembled("battery")
    x0, x1 = case.BTN_NOTCH
    wb = case.WIN_CY - case.WIN_H / 2
    i_min, where = min((inertia(section_x(shell, xc, wb)), xc) for xc in np.arange(x0 + 0.25, x1, 0.5))
    L, F = x1 - x0, 10.0
    d = F * L ** 3 / (192 * E * i_min)
    glass = case.PANEL_SPACE - case.PANEL_T + case.GLASS_RELIEF
    report(d < case.PAD_GAP and d < glass,
           f"display lip over the PWR/BOOT opening ({L:.0f} mm, weakest section at x {where:.1f}, I = {i_min:.2f} mm4) "
           f"pressed with 10 N: bends {d:.3f} mm, against the pads' {case.PAD_GAP} mm to the PCB and the glass's {glass:.1f} mm")


def roark_alpha(ratio):
    """Roark, Table 11.4: rectangular plate, all edges fixed, load at the centre (nu = 0.3)."""
    r = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 1e9]
    a = [0.0611, 0.0706, 0.0755, 0.0777, 0.0786, 0.0788, 0.0791]
    return float(np.interp(ratio, r, a))


def back_plate():
    from manifold3d import Manifold
    from round13 import tube
    # the back plate's free span: the cavity inside the walls
    a, b = case.BW + 2 * case.CLR, case.BH + 2 * case.CLR
    t, F = case.T_BACK, 10.0
    d = roark_alpha(a / b) * F * b ** 2 / (E * t ** 3)
    # the room under the battery with 3 mm standoffs (as round 36 works it out)
    dz = case.STANDOFF_H - case.STANDOFF_H_MIN
    z_in = case.Z_B + case.CAVITY["battery"]
    x0, x1, y0, y1 = case.BATTERY_BAY
    gaps = {}
    for (pts, r), label in ((case.battery_wire_route(), "battery wire"), (case.speaker_wire_route(), "speaker cable")):
        lifted = [(x, y, z + dz) if z < z_in - case.BATTERY_SPACE else (x, y, z) for x, y, z in pts]
        tb = tube(lifted, r) ^ case.box(x0, x1, y0, y1, 0, 50)
        if not tb.is_empty():
            gaps[label] = z_in - case.BATTERY_SIZE[2] - tb.bounding_box()[5]
    every = Manifold()
    for g in case.board_model(case.STANDOFF_H_MIN).values():
        every += g
    gaps["board"] = z_in - case.BATTERY_SIZE[2] - (every ^ case.box(x0, x1, y0, y1, 0, 50)).bounding_box()[5]
    room = min(gaps.values())
    report(d < room, f"back plate ({a:.1f} x {b:.1f} x {t} mm, fixed along the walls) pressed in the middle with 10 N: "
                     f"bends {d:.3f} mm, against the room under your battery with 3 mm standoffs: "
                     + ", ".join(f"{k} {v:.2f} mm" for k, v in gaps.items())
                     + f" (at about {room / d * F:.0f} N it would touch the {min(gaps, key=gaps.get)})")


# ------------------------------------------------------------------ 2
def bed_band():
    import trimesh
    from shapely.geometry import LineString, Polygon
    shell, _, _, _ = load_assembled("battery")
    sec = shell.section(plane_origin=[0, 0, 0.05], plane_normal=[0, 0, 1])
    planar, tf = sec.to_2D()
    pts = lambda r: trimesh.transform_points(np.column_stack([np.asarray(r.coords), np.zeros(len(r.coords))]), tf)[:, :2]  # noqa: E731
    polys = [Polygon(pts(p.exterior), [pts(r) for r in p.interiors]) for p in planar.polygons_full]
    ring = len(polys) == 1 and len(polys[0].interiors) == 1
    # the band's width along lines from the window's centre outward, every 2 degrees
    cx, cy = case.WIN_CX, case.WIN_CY
    widths = []
    for ang in np.radians(np.arange(0, 360, 2)):
        line = LineString([(cx, cy), (cx + 80 * np.cos(ang), cy + 80 * np.sin(ang))])
        widths.append(sum(p.intersection(line).length for p in polys))
    # along a slanted line the band looks wider than it is; on the four sides the lines are square to it
    side = {"left": widths[90], "right": widths[0], "bottom": widths[135], "top": widths[45]}
    ok = ring and min(side.values()) >= 2.0 and min(widths) >= 2.0
    report(ok, f"lid's first layer on the bed: {'one closed ring round the window' if ring else 'NOT one closed ring'}, "
               f"{polys[0].area if polys else 0:.0f} mm2; band width on each side "
               + ", ".join(f"{k} {v:.1f}" for k, v in side.items())
               + f" mm, narrowest along any line from the window's centre {min(widths):.1f} mm (want 2.0)")


if __name__ == "__main__":
    lip()
    back_plate()
    bed_band()
    print(f"\nRound 46: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
