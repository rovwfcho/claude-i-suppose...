#!/usr/bin/env python3
"""Debug round 8: methods not used in rounds 1-7.

1. Wall webs: sections through the middle of each outer wall (x-z or y-z planes), eroded by
   0.5 mm: any strip of wall narrower than 1 mm between two openings disappears and is reported
2. Determinism: two builds in a row must write byte-identical STL files
3. Tessellation: rebuilt with half the circle resolution, the board must still clear the case
4. Path independence: the generator run from another working directory, into another folder
"""
import hashlib
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled, vol  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
def wall_webs(variant, min_web=1.0):
    import trimesh
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    shell, _, cover_asm, _ = load_assembled(variant)
    planes = []
    for t in (0.3, case.WALL / 2, case.WALL - 0.3):  # near the outside, middle, near the inside
        planes += [(f"bottom wall {t:.1f} in", [0, case.Y0 + t, 0], [0, 1, 0], (0, 2)),
                   (f"top wall {t:.1f} in", [0, case.Y1 - t, 0], [0, 1, 0], (0, 2)),
                   (f"left wall {t:.1f} in", [case.X0 + t, 0, 0], [1, 0, 0], (1, 2)),
                   (f"right wall {t:.1f} in", [case.X1 - t, 0, 0], [1, 0, 0], (1, 2))]
    # the clips' grooves are blind, on the inside of the long walls (1.8 mm of wall stays behind them)
    grooves = [(x - case.CLIP_HOOK_L / 2 - 1.5, x + case.CLIP_HOOK_L / 2 + 1.5) for x, _ in case.CLIPS]
    for name, o, n, axes in planes:
        region = None
        for part in (shell, cover_asm):          # each part on its own: they share points at the seam
            sec = part.section(plane_origin=o, plane_normal=n)
            if sec is None:
                continue
            polys = []
            for ent in sec.discrete:
                if len(ent) >= 4:
                    p = Polygon(ent[:, list(axes)])
                    if p.is_valid and p.area > 0.01:
                        polys.append(p)
            # nested loops: build the region with even-odd filling
            part_region = None
            for p in sorted(polys, key=lambda q: -q.area):
                part_region = p if part_region is None else part_region.symmetric_difference(p)
            if part_region is not None:
                region = part_region if region is None else region.union(part_region)
        if region is None:
            report(False, f"{variant} {name}: no section")
            continue
        r = min_web / 2
        opened = region.buffer(-r, join_style=2).buffer(r, join_style=2)
        lost = region.difference(opened)
        pieces = [g for g in getattr(lost, "geoms", [lost]) if g.area > 0.05]
        # the rounded front/back edges thin out toward the faces by design; ignore pieces that
        # touch the top or bottom of the section (the faces), keep webs between openings
        zmin, zmax = region.bounds[1], region.bounds[3]
        webs = [g for g in pieces if g.bounds[1] > zmin + 0.3 and g.bounds[3] < zmax - 0.3]
        if name.startswith(("bottom", "top")) and "2.1" in name:
            webs = [g for g in webs if not (any(a <= g.centroid.x <= b for a, b in grooves) and g.centroid.y > 9.0)]
        desc = [(round(g.area, 2), tuple(np.round(g.centroid.coords[0], 1))) for g in webs]
        report(not webs, f"{variant} {name}: webs narrower than {min_web} mm between openings: {desc or 'none'}")


# ------------------------------------------------------------------ 2
def determinism():
    hashes = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as d:
            case.build(d)
            hashes.append({f: hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest()
                           for f in sorted(os.listdir(d))})
    report(hashes[0] == hashes[1], f"determinism: two builds wrote identical files ({len(hashes[0])} STLs)")


# ------------------------------------------------------------------ 3
def tessellation():
    saved = case.SEG
    try:
        case.SEG = 48
        for variant, cav in case.CAVITY.items():
            z_total = case.Z_B + cav + case.T_BACK
            S, C = case.front_shell(z_total), case.back_cover(z_total, variant)
            bad = {}
            for name, g in case.board_model().items():
                if name == "pcb":
                    continue
                v = vol(g ^ (S + C))
                if v > 1e-3:
                    bad[name] = round(v, 4)
            from round1 import hook_zones
            rigid = vol(S ^ (C - hook_zones()))
            report(not bad and rigid < 1e-3,
                   f"{variant} at {case.SEG} segments per circle: board overlaps {bad or 'none'}, "
                   f"lid/cover overlap away from the clip hooks {rigid:.4f} mm3")
    finally:
        case.SEG = saved


# ------------------------------------------------------------------ 4
def path_independence():
    with tempfile.TemporaryDirectory() as out, tempfile.TemporaryDirectory() as cwd:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "case.py"), out], cwd=cwd,
                           capture_output=True, text=True)
        files = sorted(os.listdir(out))
        report(r.returncode == 0 and len(files) == 2 * len(case.CAVITY),
               f"generator run from another folder: exit {r.returncode}, wrote {files}")


if __name__ == "__main__":
    for v in case.CAVITY:
        print(f"\n### {v}")
        wall_webs(v)
    print()
    determinism()
    tessellation()
    path_independence()
    print(f"\nRound 8: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
