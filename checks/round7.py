#!/usr/bin/env python3
"""Debug round 7: methods not used in rounds 1-6.

1. Exact point-to-mesh distances from every corner of the board model to the case (no sampling)
2. Edge gap map: rays fired outward all around the PCB edge, at PCB height, measure the wall gap
3. Viewing angle: share of the active area visible when the display is looked at 30 and 45 deg
   off-axis from each side (the bezel and its chamfer must not hide much)
"""
import math
import os
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
def vertex_distances(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    for name, geom in case.board_model().items():
        tm = case.to_trimesh(geom)
        v = tm.vertices
        worst = np.inf
        for m in (shell, cover_asm):
            sd = trimesh.proximity.signed_distance(m, v)  # positive = inside the case material
            worst = min(worst, -sd.max())
        if name == "pcb":
            report(worst > -1e-3, f"{variant} exact: pcb corners at least {worst:.3f} mm from the case (touching allowed)")
        else:
            report(worst > 1e-3, f"{variant} exact: {name:13s} closest vertex {worst:.3f} mm from the case")


# ------------------------------------------------------------------ 2
def edge_gaps(variant):
    shell, _, _, _ = load_assembled(variant)
    z = (case.Z_PF + case.Z_B) / 2
    outline = case.rrect(case.BW, case.BH, case.BR, case.BW / 2, case.BH / 2).to_polygons()[0]
    pts = np.asarray(outline)
    # resample the outline every 0.5 mm, with outward normals
    seg = np.roll(pts, -1, 0) - pts
    samples, normals = [], []
    for p, s in zip(pts, seg):
        L = np.linalg.norm(s)
        n = np.array([s[1], -s[0]]) / L  # outward for a counter-clockwise outline
        for t in np.arange(0, L, 0.5):
            samples.append(p + s * t / L)
            normals.append(n)
    samples, normals = np.array(samples), np.array(normals)
    o = np.column_stack([samples, np.full(len(samples), z)])
    d = np.column_stack([normals, np.zeros(len(normals))])
    locs, ir, _ = shell.ray.intersects_location(o, d, multiple_hits=False)
    gap = np.full(len(o), np.inf)
    gap[ir] = np.linalg.norm(locs - o[ir], axis=1)
    finite = gap[np.isfinite(gap)]
    openings = (~np.isfinite(gap)) | (gap > 1.0)
    report(abs(finite.min() - case.CLR) < 0.02 and (gap[~openings] <= case.CLR + 0.02).all(),
           f"{variant} edge gaps at PCB height: {len(o)} rays, wall gap {finite.min():.3f}-"
           f"{gap[~openings].max():.3f} mm where there is wall, {openings.sum()} rays leave through openings")
    # where are the openings at PCB height? group them
    xs = samples[openings]
    if len(xs):
        groups = []
        for p in xs:
            if groups and np.linalg.norm(p - groups[-1][-1]) < 1.0:
                groups[-1].append(p)
            else:
                groups.append([p])
        desc = [f"({np.round(np.mean(g, 0), 1).tolist()}, {len(g) * 0.5:.1f} mm)" for g in groups]
        expected = len(groups) <= 4
        report(expected, f"{variant} openings at PCB height: {', '.join(desc)} "
                         f"(expected: button opening, USB-C, dial notch)")


# ------------------------------------------------------------------ 3
def viewing(variant):
    shell, _, _, _ = load_assembled(variant)
    ax0, ax1 = 52.48 - 43.2, 52.48 + 43.2   # active area per Waveshare's drawing (centre of its lines)
    ay0, ay1 = 30.0 - 25.92, 30.0 + 25.92
    xs, ys = np.meshgrid(np.linspace(ax0, ax1, 120), np.linspace(ay0, ay1, 72))
    z = case.Z_PF - case.PANEL_T  # top of the glass
    pts = np.column_stack([xs.ravel(), ys.ravel(), np.full(xs.size, z)])
    for ang in (0, 30, 45):
        res = []
        for label, d in (("left", (-1, 0)), ("right", (1, 0)), ("bottom", (0, -1)), ("top", (0, 1))):
            dirv = np.array([d[0] * math.sin(math.radians(ang)), d[1] * math.sin(math.radians(ang)),
                             -math.cos(math.radians(ang))])
            hit = shell.ray.intersects_any(pts + dirv * 1e-3, np.tile(dirv, (len(pts), 1)))
            res.append((label, 100.0 * (1 - hit.mean())))
            if ang == 0:
                break
        worst = min(r[1] for r in res)
        need = {0: 100.0, 30: 97.0, 45: 93.0}[ang]
        report(worst >= need - 1e-6, f"{variant} viewed {ang} deg off-axis: visible active area "
                                      + ", ".join(f"{l} {v:.1f}%" for l, v in res) + f" (need >= {need}%)")


if __name__ == "__main__":
    for v in case.CAVITY:
        print(f"\n### {v}")
        vertex_distances(v)
        edge_gaps(v)
        viewing(v)
    print(f"\nRound 7: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
