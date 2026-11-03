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
3. Air under the bridges, as sliced, with each extrusion's real height: PrusaSlicer's default "thick
   bridges" prints bridges and overhang perimeters as 0.4 mm tall strands, so their undersides sit
   0.2 mm lower than the layer they belong to (and a feature that ends on a layer boundary can land
   on either side of it). Measured in the G-code (every extrusion sampled along its length, not by
   its middle):
   - each clip slot: from the top of the last plastic under the beam to the underside of the first
     strand over it; at least 0.5 mm of air, so the beam can't fuse to the cover;
   - each screw recess: from the bed (the back face) to the underside of the first strand where the
     head bears; at least SCREW_HEAD_K (the tallest head the README allows), so the head is flush.
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


# ------------------------------------------------------------------ 3
def gcode_layers(gcode, shift):
    """{layer z: [(x, y, strand height, type)]}: points every 0.2 mm along each extrusion (design x, y)."""
    out, z, h, typ, x, y = {}, 0.0, 0.2, "", 0.0, 0.0
    rel = "\nM83" in gcode
    e = 0.0
    for line in gcode.splitlines():
        if line.startswith(";Z:"):
            z = round(float(line[3:]), 3)
        elif line.startswith(";HEIGHT:"):
            h = float(line[8:])
        elif line.startswith(";TYPE:"):
            typ = line[6:].strip()
        elif line.startswith("G92") and " E" in line:
            e = 0.0
        elif line.startswith(("G1 ", "G0 ")):
            q = dict((m[0], float(m[1:])) for m in line.split(";")[0].split()[1:] if m[0] in "XYZE")
            nx, ny = q.get("X", x), q.get("Y", y)
            if "E" in q:
                de = q["E"] if rel else q["E"] - e
                if not rel:
                    e = q["E"]
                if de > 0 and (nx, ny) != (x, y):
                    n = max(1, int(np.hypot(nx - x, ny - y) / 0.2))
                    for t in (np.arange(n) + 0.5) / n:
                        out.setdefault(z, []).append((x + t * (nx - x) - shift[0], y + t * (ny - y) - shift[1], h, typ))
            x, y = nx, ny
    return out


def air_as_sliced():
    import shutil
    import subprocess
    import tempfile
    import trimesh
    from round19 import SETTINGS
    exe = shutil.which("prusa-slicer")
    if not exe:
        print("  SKIP air under the bridges: PrusaSlicer not installed")
        return
    stl = os.path.join(ROOT, "stl", "back_cover_battery.stl")
    lo, hi = trimesh.load(stl).bounds
    shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2
    with tempfile.TemporaryDirectory() as d:
        g = os.path.join(d, "out.gcode")
        subprocess.run([exe, "--export-gcode", *SETTINGS, "--support-material=0", "-o", g, stl],
                       capture_output=True, text=True, timeout=900, check=True)
        layers = gcode_layers(open(g).read(), shift)
    zs = sorted(layers)

    def pts(z, keep):
        return [p for p in layers[z] if keep(p[0], p[1])]
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    split = z_total - case.Z_SPLIT                               # print height of the parting plane
    slots = []
    for x, side in case.CLIPS:
        yf = -case.CLR + case.SKIRT_CLR
        y0, y1 = (yf + 0.15, yf + case.SKIRT_T - 0.15) if side == "bottom" else \
            (case.BH - yf - case.SKIRT_T + 0.15, case.BH - yf - 0.15)
        x0, x1 = x - case.CLIP_L / 2 + 1.0, x + case.CLIP_L / 2 - 1.0
        keep = lambda a, b: x0 <= a <= x1 and y0 <= b <= y1   # noqa: E731
        filled = [z for z in zs if pts(z, keep)]
        below = max((z for z in filled if z <= split + 0.15), default=None)
        over = min((z for z in filled if z > split + 0.15), default=None)
        if below is None or over is None:
            slots.append((side, x, None))
            continue
        h = max(p[2] for p in pts(over, keep))
        slots.append((side, x, round(over - h - below, 2)))
    recesses = []
    for px, py in case.POSTS:
        r0, r1 = case.SCREW_HOLE_R + 0.2, 2.4                   # where a 5 mm head bears
        keep = lambda a, b: r0 <= np.hypot(a - px, b - py) <= r1   # noqa: E731
        first = min((z for z in zs if pts(z, keep)), default=None)
        if first is None:
            recesses.append((px, py, None))
            continue
        under = min(first - p[2] for p in pts(first, keep))
        recesses.append((px, py, round(under, 2)))
    ok_s = all(a is not None and a >= 0.5 for _, _, a in slots)
    ok_r = all(u is not None and u >= case.SCREW_HEAD_K - 1e-6 for _, _, u in recesses)
    report(ok_s, "clip slots as sliced, air between the cover and the beam's first strand: "
                 + ", ".join(f"{side} x {x:.0f}: {a} mm" for side, x, a in slots) + " (want 0.5)")
    report(ok_r, "screw recesses as sliced, bed to the underside of the first strand where the head bears: "
                 + ", ".join(f"({px:.1f}, {py:.1f}): {u} mm" for px, py, u in recesses)
                 + f" (the tallest head allowed: {case.SCREW_HEAD_K} mm)")


if __name__ == "__main__":
    lip()
    back_plate()
    bed_band()
    air_as_sliced()
    print(f"\nRound 46: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
