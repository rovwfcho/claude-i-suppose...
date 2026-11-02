#!/usr/bin/env python3
"""Debug round 20: methods not used in rounds 1-19.

1. Openings after slicing: every hole through the back plate (grille, mic, sensor) is found on the
   printed STL, and the extrusion paths PrusaSlicer writes into the G-code for the back plate's
   layers are checked: each hole must keep a clear gap at least 0.5 mm across, so the slicer has not
   closed it with perimeters (round 19 only looked at the slicer's warnings)
2. Same for the display window in the front skin
3. Bookkeeping: every check script is run by run_all.sh and has its round in DEBUG_LOG.md

Needs PrusaSlicer on the PATH (prusa-slicer); part 1-2 is skipped with a note if it isn't installed.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from round19 import SETTINGS  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def extrusions(gcode):
    """{layer z: array of extrusion segments [x0, y0, x1, y1]} from PrusaSlicer G-code."""
    rel = "\nM83" in gcode
    out, z, x, y, e, cur = {}, 0.0, 0.0, 0.0, 0.0, []
    for line in gcode.splitlines():
        if line.startswith(";Z:"):
            if cur:
                out.setdefault(z, []).extend(cur)
            z, cur = round(float(line[3:]), 2), []
        elif line.startswith("G92") and " E" in line:
            e = 0.0
        elif line.startswith(("G1 ", "G0 ")):
            p = dict((m[0], float(m[1:])) for m in line.split(";")[0].split()[1:] if m[0] in "XYZE")
            nx, ny = p.get("X", x), p.get("Y", y)
            if "E" in p:
                de = p["E"] if rel else p["E"] - e
                if not rel:
                    e = p["E"]
                if de > 0 and (nx, ny) != (x, y):
                    cur.append((x, y, nx, ny))
            x, y = nx, ny
    if cur:
        out.setdefault(z, []).extend(cur)
    return {k: np.array(v) for k, v in out.items()}


def seg_dist(pts, segs):
    """Smallest distance from each point to any segment."""
    a, b = segs[:, :2], segs[:, 2:]
    ab = b - a
    L2 = np.maximum((ab ** 2).sum(1), 1e-12)
    best = np.full(len(pts), np.inf)
    for i in range(0, len(pts), 256):
        p = pts[i:i + 256, None, :]
        t = np.clip(((p - a) * ab).sum(2) / L2, 0, 1)
        d = np.linalg.norm(p - (a + t[..., None] * ab), axis=2).min(1)
        best[i:i + 256] = d
    return best


def holes(tm, step=0.1):
    """Through-holes in a part lying on the bed, found with vertical rays: list of point arrays."""
    from scipy import ndimage
    lo, hi = tm.bounds
    xs = np.arange(lo[0] + 1.0, hi[0] - 1.0, step)
    ys = np.arange(lo[1] + 1.0, hi[1] - 1.0, step)
    X, Y = np.meshgrid(xs, ys)
    o = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, hi[2] + 1)])
    # a through-hole: the ray reaches the bed (no hit at all inside the outline)
    hit = tm.ray.intersects_any(o, np.tile([0, 0, -1.0], (len(o), 1))).reshape(X.shape)
    lab, n = ndimage.label(~hit)
    out = []
    for k in range(1, n + 1):
        m = lab == k
        if m[0, :].any() or m[-1, :].any() or m[:, 0].any() or m[:, -1].any():
            continue  # touches the scan edge: outside the part, not a hole
        out.append(np.column_stack([X[m], Y[m]]))
    return out


def sliced_openings(exe, name, layers_to_check, label):
    import trimesh
    stl = os.path.join(ROOT, "stl", name + ".stl")
    tm = trimesh.load(stl)
    hs = holes(tm)
    with tempfile.TemporaryDirectory() as d:
        g = os.path.join(d, "out.gcode")
        subprocess.run([exe, "--export-gcode", *SETTINGS, "--support-material=0", "-o", g, stl],
                       capture_output=True, text=True, timeout=900, check=True)
        ex = extrusions(open(g).read())
    lo, hi = tm.bounds
    shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2  # --center 125,105 centres the bounding box
    bad, sizes = [], []
    for zl in layers_to_check:
        segs = ex[min(ex, key=lambda z: abs(z - zl))]
        for h in hs:
            clear = seg_dist(h + shift, segs).max()  # radius of the largest clear circle centred on a hole point
            sizes.append(clear)
            # extrusion lines are about 0.45 mm wide, so the clear gap is 2 * (clear - 0.225)
            if 2 * (clear - 0.225) < 0.5:
                bad.append((round(float(h[:, 0].mean()), 1), round(float(h[:, 1].mean()), 1), zl,
                            round(2 * (clear - 0.225), 2)))
    report(len(hs) > 0 and not bad,
           f"{label}: {len(hs)} openings through the bed face, checked in the G-code at z {layers_to_check}; "
           f"smallest clear gap {2 * (min(sizes) - 0.225):.2f} mm; closed or nearly closed: {bad or 'none'}")
    return hs


def bookkeeping():
    run_all = open(os.path.join(HERE, "run_all.sh")).read()
    log = open(os.path.join(ROOT, "DEBUG_LOG.md")).read()
    scripts = sorted((int(m.group(1)) for f in os.listdir(HERE) if (m := re.match(r"round(\d+)\.py$", f))))
    me = int(re.search(r"round(\d+)", os.path.basename(__file__)).group(1))
    not_run = [n for n in scripts if f"checks/round{n}.py" not in run_all]
    not_logged = [n for n in scripts if n != me and not re.search(rf"^## Round {n}\b", log, re.M)]
    report(not not_run and not not_logged, f"{len(scripts)} check scripts; not in run_all.sh: {not_run or 'none'}; "
                                           f"no DEBUG_LOG entry: {not_logged or 'none'}")


def main():
    bookkeeping()
    exe = shutil.which("prusa-slicer")
    if not exe:
        print("  ..   PrusaSlicer not installed; slicing part of round 20 skipped")
        return
    n = sliced_openings(exe, "back_cover_battery", [0.2, 0.8, 1.6], "back cover (grille, mic, sensor)")
    print(f"  ..   back cover openings found: {len(n)}")
    sliced_openings(exe, "front_shell_battery", [0.2, 1.0], "front shell (display window)")


if __name__ == "__main__":
    main()
    print(f"\nRound 20: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
