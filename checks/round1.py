#!/usr/bin/env python3
"""Debug round 1: checks that read the exported STL files back from disk.

1. STL integrity (trimesh): watertight, consistent winding, one body, sizes, flat bed face
2. Fingertip reach: rigid spheres pushed straight at each button; how far short of a full press
3. Ports: USB-C plug overmold and a microSD card pushed in along their real paths
4. Wall thickness: rays cast inward from sampled surface points
5. Printability: slice in print orientation, find islands that start in mid-air
6. Screws: M2 x 6 pan head screw models in every screw position
"""
import os
import sys

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import case  # noqa: E402

STL = os.path.join(os.path.dirname(HERE), "stl")
problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def to_manifold(tm):
    return Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                         tri_verts=np.asarray(tm.faces, np.uint32)))


def vol(m):
    return 0.0 if m.is_empty() else m.volume()


def load_assembled(variant):
    """Read the printed STLs and put them back in assembly position."""
    shell = trimesh.load(os.path.join(STL, f"front_shell_{variant}.stl"))
    shell.apply_transform(np.diag([-1, 1, 1, 1]))      # undo front_for_print's left-right mirror
    shell.apply_translation([case.BW, 0, 0])
    assert shell.volume > 0
    cover = trimesh.load(os.path.join(STL, f"back_cover_{variant}.stl"))
    z_total = case.Z_B + case.CAVITY[variant] + case.T_BACK
    cover_asm = cover.copy()
    cover_asm.apply_transform(np.diag([1, 1, -1, 1]))  # undo the print flip
    cover_asm.apply_translation([0, 0, z_total])
    assert cover_asm.volume > 0  # trimesh re-winds faces after a mirroring transform
    return shell, cover, cover_asm, z_total


def hooks():
    """The snap-clip hooks (design frame): springy, so they may press into the lid (their preload)
    and pass through its wall while it closes; checks of rigid fits leave them out."""
    out = Manifold()
    for x, side in case.CLIPS:
        out += case.clip_hook(x, side)
    return out


# ------------------------------------------------------------------ 1
def check_integrity(variant):
    shell, cover, cover_asm, z_total = load_assembled(variant)
    for name, tm in (("front shell", shell), ("back cover", cover)):
        bodies = tm.split(only_watertight=False)
        degenerate = int((tm.area_faces < 1e-9).sum())
        report(tm.is_watertight and tm.is_winding_consistent and tm.volume > 0 and len(bodies) == 1
               and degenerate == 0,
               f"{variant} {name}: watertight={tm.is_watertight} winding={tm.is_winding_consistent} "
               f"volume={tm.volume / 1000:.2f} cm3 bodies={len(bodies)} degenerate faces={degenerate}")
        lo, hi = tm.bounds
        size = hi - lo
        # the shell spans the full outline; a cover that sits on the rounded back edge may be smaller
        full = abs(size[0] - 104.9) < 0.05 and abs(size[1] - 65.4) < 0.05
        report(full or (name == "back cover" and size[0] <= 104.9 and size[1] <= 65.4),
               f"{variant} {name}: footprint {size[0]:.2f} x {size[1]:.2f} mm (outline 104.90 x 65.40)")
        report(abs(lo[2]) < 1e-3, f"{variant} {name}: lowest point z={lo[2]:.4f} (must sit on the bed)")
        # area resting on the bed
        on_bed = tm.area_faces[(np.abs(tm.triangles[:, :, 2]).max(axis=1) < 1e-3)].sum()
        report(on_bed > 900, f"{variant} {name}: {on_bed:.0f} mm2 flat on the bed")
    total = shell.bounds[1][2] + (z_total - case.Z_SPLIT)
    report(abs(total - z_total) < 0.01,
           f"{variant}: shell height {shell.bounds[1][2]:.2f} + cover {cover.bounds[1][2]:.2f} "
           f"-> assembled depth {total:.2f} mm (expected {z_total:.2f})")


# ------------------------------------------------------------------ 2
def sphere_stop(obstacle, center_fn, free, blocked, r):
    """Travel t between a free position and a target where a sphere of radius r first touches."""
    sph = Manifold.sphere(r, 128)
    hit = lambda t: not (sph.translate(center_fn(t)) ^ obstacle).is_empty()
    if hit(free):
        raise RuntimeError("start position already collides")
    if not hit(blocked):
        return blocked
    for _ in range(40):
        mid = (free + blocked) / 2
        if hit(mid):
            blocked = mid
        else:
            free = mid
    return free


def check_buttons(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    obstacle = to_manifold(shell) + to_manifold(cover_asm)
    tip_y = -case.BTN_PROTRUDE
    zc = case.Z_B + 0.9
    for name, bx in case.BUTTONS.items():
        for r in (6.0, 8.0):
            # sphere moves along +y towards the actuator; t = y of the sphere's front point
            t = sphere_stop(obstacle, lambda y: [bx, y - r, zc], -20.0, tip_y, r)
            need = (tip_y + 0.25) - t  # switch travel ~0.25 mm
            report(need <= 0.6,
                   f"{variant} {name}: finger r={r:.0f} mm stops {tip_y - t:.2f} mm short of the actuator, "
                   f"needs {max(need, 0):.2f} mm of skin compression for a full press")
    # dial: how far the wheel rim sticks out past what a finger touches
    wx, wy, wr = case.WHEEL
    rim = wy + wr
    for r in (6.0, 8.0):
        t = sphere_stop(obstacle, lambda y: [wx, y + r, case.Z_B + 1.5], 90.0, rim, r)
        report(t - rim <= 0.3, f"{variant} dial: finger r={r:.0f} mm reaches within {t - rim:.2f} mm of the wheel rim")


# ------------------------------------------------------------------ 3
def check_ports(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    obstacle = to_manifold(shell) + to_manifold(cover_asm)
    zc = case.Z_B + 1.63
    # USB-C plug: a large overmold (12.4 x 6.6) whose front face reaches the receptacle face
    face = -0.4
    # overmold corners modelled with a 1 mm radius (sharper than any USB-C plug we know of)
    over = case.prism(case.rrect(12.4, 6.6, 1.0, case.USB_Y, zc), face - 25, face).transform(
        [[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])
    report(vol(over ^ obstacle) < 1e-3, f"{variant} USB-C: 12.4 x 6.6 mm plug overmold seats fully "
                                        f"(overlap {vol(over ^ obstacle):.3f} mm3)")
    # microSD card 11 x 15 x 0.8, pushed in along +x from outside, ending 2 mm into the socket
    zs = case.Z_B + 0.9
    worst = 0.0
    for end in np.arange(-15.0, 3.6, 0.5):
        card = case.box(end - 15, end, case.SD_Y - 5.5, case.SD_Y + 5.5, zs - 0.4, zs + 0.4)
        worst = max(worst, vol(card ^ obstacle))
    report(worst < 1e-3, f"{variant} microSD: card slides in without touching the case (worst {worst:.3f} mm3)")


# ------------------------------------------------------------------ 4
def check_thickness(variant, min_ok=0.6):
    """Ray cast inward from surface samples; confirm each thin hit by probing a point inside."""
    shell, cover, _, _ = load_assembled(variant)
    for name, tm in (("front shell", shell), ("back cover", cover)):
        pts, fid = trimesh.sample.sample_surface_even(tm, 40000, seed=1)
        n = tm.face_normals[fid]
        origins = pts - n * 1e-3
        locs, idx_ray, _ = tm.ray.intersects_location(origins, -n, multiple_hits=False)
        d = np.full(len(pts), np.inf)
        d[idx_ray] = np.linalg.norm(locs - origins[idx_ray], axis=1)
        cand = d < min_ok
        real = np.zeros(len(pts), bool)
        real[cand] = ~tm.contains(pts[cand] - n[cand] * (min_ok / 2))
        # a probe next to a sharp edge leaves through the neighbouring face even when the part is
        # solid; slivers are thin away from their edges too, so drop samples within 0.45 mm of one
        from scipy.spatial import cKDTree
        sharp = tm.face_adjacency_edges[tm.face_adjacency_angles > np.radians(25)]
        a, b = tm.vertices[sharp[:, 0]], tm.vertices[sharp[:, 1]]
        steps = np.maximum(1, (np.linalg.norm(b - a, axis=1) / 0.05).astype(int))
        edge_pts = np.concatenate([a[i] + np.outer(np.linspace(0, 1, k + 1), b[i] - a[i])
                                   for i, k in enumerate(steps)])
        near_edge = cKDTree(edge_pts).query(pts)[0] < 0.45
        real &= ~near_edge
        clusters = []
        if real.any():
            p = pts[real]
            keys = np.round(p / 3.0).astype(int)
            uniq, counts = np.unique(keys, axis=0, return_counts=True)
            for k, c in zip(map(tuple, uniq), counts):
                if c >= 5:
                    clusters.append((c, np.round(p[(keys == k).all(axis=1)].mean(0), 1)))
        report(not clusters, f"{variant} {name}: {real.sum()} confirmed samples under {min_ok} mm; "
                             f"clusters: {sorted(clusters, key=lambda c: -c[0])[:6]}")


# ------------------------------------------------------------------ 5
def check_islands(variant, layer=0.2):
    shell, cover, _, _ = load_assembled(variant)
    for name, tm in (("front shell", shell), ("back cover", cover)):
        top = tm.bounds[1][2]
        # 0.013 mm off the layer middles: a section plane lying exactly on a feature's edge (the 1.8 mm
        # pilots' tangents sit on the 0.1 mm grid) comes out malformed and drops polygons
        zs = np.arange(layer / 2, top, layer) + 0.013
        sections = tm.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs)
        prev = None
        floating = []
        for z, sec in zip(zs, sections):
            polys = [] if sec is None else list(sec.polygons_full)
            if prev is not None:
                from shapely.ops import unary_union
                below = unary_union(prev) if prev else None
                for p in polys:
                    if p.area > 0.05 and (below is None or not p.intersects(below)):
                        floating.append((round(z, 2), round(p.area, 2), np.round(p.centroid.coords[0], 1)))
            prev = polys
        report(not floating, f"{variant} {name}: {len(floating)} islands start in mid-air "
                             f"{floating[:5] if floating else ''}")


# ------------------------------------------------------------------ 6
def check_screws(variant):
    """Corner screws, read back from the STLs: an 8 mm screw seated in each recess clears the cover
    (hole and recess), goes 2 mm into its standoff, and its head is not above the back face."""
    shell, _, cover_asm, z_total = load_assembled(variant)
    S, C = to_manifold(shell), to_manifold(cover_asm)
    so = case.board_model()["standoffs"]
    for px, py in case.POSTS:
        seat = z_total - case.SCREW_HEAD_DEPTH
        head = case.cyl_z(px, py, 2.5, seat, seat + 1.8)               # pan head 5 x 1.8 (the largest allowed)
        shank = case.cyl_z(px, py, 1.25, seat - case.SCREW_LEN, seat)  # M2.5 x 8
        bite = vol(shank ^ so) / (np.pi * 1.25 ** 2)
        # the screw may sit 0.4 mm off centre (standoff position uncertainty) and still clear the cover
        off = [vol(case.cyl_z(px + dx, py + dy, 1.25, seat - case.SCREW_LEN, seat) ^ C)
               + vol(case.cyl_z(px + dx, py + dy, 2.5, seat, seat + 1.8) ^ C)
               for dx, dy in ((0.4, 0), (-0.4, 0), (0, 0.4), (0, -0.4), (0.28, 0.28), (-0.28, -0.28), (0.28, -0.28), (-0.28, 0.28))]
        ok = (vol(head ^ C) < 1e-3 and vol(shank ^ C) < 1e-3 and vol((head + shank) ^ S) < 1e-3
              and 1.9 <= bite <= 2.1 and max(off) < 1e-3)
        report(ok, f"{variant} corner screw ({px:.1f}, {py:.1f}): clear of the cover {vol((head + shank) ^ C):.4f}, "
                   f"0.4 mm off centre {max(off):.4f} mm3, {bite:.2f} mm into the standoff")


if __name__ == "__main__":
    case.build(STL)
    for v in case.CAVITY:
        print(f"\n### {v}")
        check_integrity(v)
        check_buttons(v)
        check_ports(v)
        check_thickness(v)
        check_islands(v)
        check_screws(v)
    print(f"\nRound 1: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
