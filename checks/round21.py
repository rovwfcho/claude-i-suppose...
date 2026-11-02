#!/usr/bin/env python3
"""Debug round 21: methods not used in rounds 1-20.

As-sliced vs as-designed, layer by layer: each part is sliced by PrusaSlicer (README settings, no
supports, no skirt) and, on every second layer, the G-code is compared with a section of the STL
at the same height:
1. Nothing is extruded outside the model: no opening in any wall (USB-C, microSD, PWR/BOOT, dial,
   vents, screw holes) gets bridged over or filled by the slicer
2. The outer ring of every wall (the first 0.6 mm inside the outline) really gets printed: thin
   walls or webs the slicer would drop show up as uncovered points

Needs PrusaSlicer on the PATH (prusa-slicer); skipped with a note if it isn't installed.
"""
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from round19 import SETTINGS  # noqa: E402
from round20 import extrusions, seg_dist  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def compare(exe, name):
    import trimesh
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from shapely import prepared
    stl = os.path.join(ROOT, "stl", name + ".stl")
    tm = trimesh.load(stl)
    with tempfile.TemporaryDirectory() as d:
        g = os.path.join(d, "out.gcode")
        subprocess.run([exe, "--export-gcode", *SETTINGS, "--support-material=0", "--skirts=0", "--brim-width=0",
                        "-o", g, stl], capture_output=True, text=True, timeout=900, check=True)
        ex = extrusions(open(g).read())
    lo, hi = tm.bounds
    shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2
    outside, uncovered, checked = [], [], 0
    zs = sorted(ex)
    for zl in zs[::2]:
        zc = zl - 0.1  # the slicer cuts each layer at its middle
        # sections just above and below the middle: a flat face lying exactly on the cutting plane
        # (pad tops, ledges) would otherwise drop out of one of them
        cuts = []
        for dz in (-0.02, 0.02):
            sec = tm.section(plane_origin=[0, 0, zc + dz], plane_normal=[0, 0, 1])
            if sec is not None:
                planar, _ = sec.to_2D(to_2D=np.eye(4))
                cuts.append(unary_union(list(planar.polygons_full)))
        if not cuts:
            continue
        polys = unary_union(cuts)          # where the slicer may extrude
        core = cuts[0].intersection(cuts[-1]) if len(cuts) == 2 else cuts[0]  # where it must
        if polys.is_empty:
            continue
        segs = ex[zl] - np.tile(shift, 2)
        # 1. extrusion outside the model (0.3 mm slack for line width and the slicer's smoothing)
        grown = prepared.prep(polys.buffer(0.3))
        mids = (segs[:, :2] + segs[:, 2:]) / 2
        out = [m for m in mids if not grown.contains(Point(m))]
        if out:
            outside.append((zl, len(out), np.round(out[0], 1).tolist()))
        # 2. the outer ring must be printed: sample points 0.2 mm inside the outline
        ring = core.buffer(-0.2).boundary
        geoms = getattr(ring, "geoms", [ring])
        pts = []
        for gm in geoms:
            n = max(int(gm.length / 0.5), 4)
            pts += [gm.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, n, endpoint=False)]
        pts = np.array(pts)
        if len(pts):
            dist = seg_dist(pts, segs)
            miss = pts[dist > 0.45]  # farther than one line width from any extrusion
            if len(miss):
                uncovered.append((zl, len(miss), np.round(miss[0], 1).tolist()))
        checked += 1
    report(not outside, f"{name}: {checked} layers compared; extrusion outside the model: "
                        f"{outside[:4] or 'none'}")
    report(not uncovered, f"{name}: outer ring of every wall printed; unprinted spots (layer, count, first): "
                          f"{uncovered[:6] or 'none'}")


def main():
    exe = shutil.which("prusa-slicer")
    if not exe:
        print("  ..   PrusaSlicer not installed; round 21 skipped")
        return
    for name in ("front_shell_battery", "back_cover_battery"):
        compare(exe, name)


if __name__ == "__main__":
    main()
    print(f"\nRound 21: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
