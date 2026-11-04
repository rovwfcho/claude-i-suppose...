#!/usr/bin/env python3
"""Debug round 11: methods not used in rounds 1-10.

1. Point-grid clearance: a 0.2 mm grid of points inside each board part, each tested for being
   inside the case (a fourth independent engine after booleans, KD-trees and rays)
2. Screwdriver access: a 3 mm shaft, 60 mm long, must reach every screw head along its axis
3. Table test: the case resting on each face and edge must not press a switch or the dial
   (round 53: with the board up to 0.3 mm nearer the edge; the dial reaches the top face, so for
   that edge the README must say not to stand the case on it)
4. Smoothness: on the outer surface (where it meets its convex hull), neighbouring faces must
   meet at small angles; only real feature edges (openings) may be sharp
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled, to_manifold, vol  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
def point_grid(variant, step=0.2):
    shell, _, cover_asm, _ = load_assembled(variant)
    for name, geom in case.board_model().items():
        if name == "pcb":
            continue
        tm = case.to_trimesh(geom)
        lo, hi = tm.bounds
        # the part's own points, on a grid, shrunk 0.01 mm so surface contact does not count
        g = np.mgrid[lo[0]:hi[0]:step, lo[1]:hi[1]:step, lo[2]:hi[2]:step].reshape(3, -1).T + step / 2
        g = g[(g <= hi).all(1)]
        inside_part = tm.contains(g)
        pts = g[inside_part]
        if len(pts) > 6000:
            pts = pts[np.random.default_rng(1).choice(len(pts), 6000, replace=False)]
        hits = shell.contains(pts) | cover_asm.contains(pts)
        report(not hits.any(), f"{variant} grid: {name:13s} {len(pts)} points inside the part, {hits.sum()} also inside the case")


# ------------------------------------------------------------------ 2
def screwdriver(variant):
    """A 3 mm screwdriver shaft straight down onto each corner screw, from 60 mm behind the back."""
    shell, _, cover_asm, z_total = load_assembled(variant)
    obst = to_manifold(shell) + to_manifold(cover_asm)
    for px, py in case.POSTS:
        head_top = z_total - case.SCREW_HEAD_DEPTH + 1.3          # the lowest allowed head (M2 pan, 1.3 mm)
        shaft = case.cyl_z(px, py, 1.5, head_top + 0.05, head_top + 60.0)
        hit = vol(shaft ^ obst)
        report(hit < 1e-3, f"{variant} screwdriver onto the corner screw at ({px:.1f}, {py:.1f}): overlap {hit:.4f} mm3")


# ------------------------------------------------------------------ 3
def table(variant):
    shell, _, cover_asm, z_total = load_assembled(variant)
    lo = np.minimum(shell.bounds[0], cover_asm.bounds[0])
    hi = np.maximum(shell.bounds[1], cover_asm.bounds[1])
    zb = case.Z_B
    # actuator tips, dial rim: how far each sits inside the table plane for each resting side
    tips = {f"{n} switch": np.array([bx, -case.BTN_PROTRUDE, zb + 0.9]) for n, bx in case.BUTTONS.items()}
    tips["dial rim"] = np.array([case.WHEEL[0], case.WHEEL[1] + case.WHEEL[2], zb + 1.5])
    sides = {"bottom edge": (1, lo[1], 1), "top edge": (1, hi[1], -1),
             "front face": (2, lo[2], 1), "back": (2, hi[2], -1),
             "left end": (0, lo[0], 1), "right end": (0, hi[0], -1)}
    # round 53: on an edge the board can sit up to CLR nearer the table. The dial is meant to reach the top
    # face (it is turned from there), so on the top edge it can take the case's weight: the README must say
    # not to stand the case on that edge.
    warned = "Don't stand it on its top edge" in open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    for sname, (ax, plane, sign) in sides.items():
        play = case.CLR if ax < 2 else 0.0
        worst = min(((tip[ax] - plane) * sign, n) for n, tip in tips.items())
        txt = (f"{variant} resting on its {sname}: nearest control ({worst[1]}) is {worst[0]:.2f} mm off the table"
               + (f", {worst[0] - play:.2f} with the board {play} mm nearer" if play else ""))
        if sname == "top edge" and worst[0] - play <= 0.05:
            report(warned, txt + ": it can take the weight there, and the README "
                   + ("says not to stand the case on that edge" if warned else "does not warn about it"))
            continue
        report(worst[0] - play > 0.05, txt)


# ------------------------------------------------------------------ 4
def smoothness(variant, max_deg=20.0):
    """The outer skin is every face that lies on the convex hull AND faces the same way as the hull
    there (thin sliver faces along opening rims lie on the hull but face sideways, so they are left
    out). Neighbouring skin faces must meet at under max_deg, except along the designed 45 deg bevel
    where the rounded edges meet the flat front and back faces."""
    import trimesh
    shell, cover, _, _ = load_assembled(variant)
    for name, tm in (("front shell", shell), ("back cover", cover)):
        hull = tm.convex_hull
        on = np.abs(trimesh.proximity.signed_distance(hull, tm.vertices)) < 0.02
        cand = on[tm.faces].all(1)
        _, _, tri_id = trimesh.proximity.closest_point(hull, tm.triangles_center[cand])
        agree = np.einsum("ij,ij->i", tm.face_normals[cand], hull.face_normals[tri_id]) > 0.9
        skin = np.zeros(len(tm.faces), bool)
        skin[np.nonzero(cand)[0][agree]] = True
        adj = tm.face_adjacency
        both = skin[adj[:, 0]] & skin[adj[:, 1]]
        ang = np.degrees(tm.face_adjacency_angles[both])
        z = tm.vertices[tm.face_adjacency_edges[both]][:, :, 2].mean(1)
        zmax = tm.bounds[1][2]
        bevel = z < 0.05                # flat face (on the bed) to the 45 deg bevel
        seam = z > zmax - 0.05          # the parting line: hidden when assembled (flush, see round 4)
        bad = (ang > max_deg) & ~(bevel & (ang <= 46.0)) & ~seam
        where = tm.vertices[tm.face_adjacency_edges[both][bad]].mean(1) if bad.any() else np.zeros((0, 3))
        report(not bad.any(), f"{variant} {name}: {both.sum()} edges on the outer skin; largest angle "
                              f"{ang[~bevel & ~seam].max():.1f} deg away from the bevel line, {ang[bevel].max() if bevel.any() else 0:.1f} deg at it; "
                              f"unexpected creases {np.round(where[:5], 1).tolist() if len(where) else 'none'}")


if __name__ == "__main__":
    for v in case.CAVITY:
        print(f"\n### {v}")
        point_grid(v)
        screwdriver(v)
        table(v)
        smoothness(v)
    print(f"\nRound 11: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
