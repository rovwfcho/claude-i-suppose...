#!/usr/bin/env python3
"""Debug round 2: different methods from round 1.

1. KD-tree clearance: minimum gap from every board part to the case, from surface samples
2. Opening sizes measured off STL cross-sections and compared with the parts that must pass
3. Monte Carlo: random board tolerances, count how often anything collides or loses its clamp
4. Overhang analysis by face angle in print orientation
5. Assembly motions: back cover lowered onto the shell, screws driven in along their axis
6. Photo overlay: openings drawn onto Waveshare's own photos (catches mirrored coordinates)
"""
import math
import os
import sys

import numpy as np
from manifold3d import Manifold
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled, to_manifold, vol  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)

skipped = []


def skip(msg):
    """A check that could not run here (for example, a reference image could not be downloaded)."""
    print("  SKIP " + msg)
    skipped.append(msg)


# ------------------------------------------------------------------ 1
def kd_clearance(variant):
    """Gap from each board part to the case, from dense surface samples and a KD-tree
    (no boolean operations), plus an inside test to catch any penetration."""
    from scipy.spatial import cKDTree
    shell, _, cover_asm, _ = load_assembled(variant)
    case_pts = np.concatenate([trimesh.sample.sample_surface_even(m, 600000, seed=3)[0]
                               for m in (shell, cover_asm)])
    tree = cKDTree(case_pts)
    spacing = np.sqrt((shell.area + cover_asm.area) / len(case_pts))
    for name, geom in case.board_model().items():
        tm = case.to_trimesh(geom)
        pts, fid = trimesh.sample.sample_surface_even(tm, 80000, seed=4)
        pts = pts - tm.face_normals[fid] * 0.01  # just inside the part, off any shared plane
        d = tree.query(pts)[0]
        # inside test (slow): every point near the case plus a random 3000 of the rest
        rng = np.random.default_rng(5)
        test = np.nonzero(d < 0.3)[0][:20000]
        test = np.union1d(test, rng.choice(len(pts), min(3000, len(pts)), replace=False))
        inside = np.zeros(len(pts), bool)
        inside[test] = shell.contains(pts[test]) | cover_asm.contains(pts[test])
        gap = d.min()
        if name == "pcb":  # clamped on purpose; only check nothing goes into it
            deep = inside & (d > 0.05)
            report(not deep.any(), f"{variant} kd: pcb clamped, {deep.sum()} sample points inside the case")
        else:
            report(not inside.any(), f"{variant} kd: {name:13s} nearest case surface {gap:.2f} mm "
                                     f"(sample spacing ~{spacing:.2f}), points inside case: {inside.sum()}")


# ------------------------------------------------------------------ 2
def section_boxes(tm, origin, normal):
    """Bounding boxes of the holes (interior rings) in a planar section."""
    sec = tm.section(plane_origin=origin, plane_normal=normal)
    if sec is None:
        return []
    planar, to3d = sec.to_2D()
    holes = []
    for poly in planar.polygons_full:
        for ring in poly.interiors:
            xy = np.asarray(ring.coords)
            p3 = trimesh.transform_points(np.column_stack([xy, np.zeros(len(xy))]), to3d)
            holes.append((p3.min(0), p3.max(0)))
    return holes


def find_hole(holes, point):
    for a, b in holes:
        if (a - 1e-6 <= point).all() and (point <= b + 1e-6).all():
            return a, b
    return None


def find_hole_robust(mesh, origin, normal, point):
    """Look for the hole in up to three nearby parallel sections. A section that passes exactly
    through mesh vertices can come out malformed and lose holes (it does not resize them), so the
    first section that contains the hole is used."""
    n = np.asarray(normal, float)
    for off in (0.0, 0.013, -0.017):
        o = np.asarray(origin, float) + n * off
        h = find_hole(section_boxes(mesh, o, n), np.asarray(point, float) + n * off)
        if h is not None:
            return h
    return None


def opening_sizes(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    asm = trimesh.util.concatenate([shell, cover_asm])
    zb = case.Z_B
    # USB-C, cut 1.5 mm inside the outer wall (plane normal x)
    h = find_hole_robust(asm, [-2.0, 0, 0], [1, 0, 0], [-2.0, case.USB_Y, zb + 1.63])
    if h:
        w, t = h[1][1] - h[0][1], h[1][2] - h[0][2]
        # a 12.4 x 6.6 plug overmold centred on the receptacle, with 4 mm and with 3 mm standoffs
        room = [min(zc - 3.3 - h[0][2], h[1][2] - (zc + 3.3)) for zc in (zb + 1.63, zb + 2.63)]
        report(w >= 12.4 and min(room) >= 0.1,
               f"{variant} USB-C opening measured {w:.2f} x {t:.2f} mm (z {h[0][2]:.2f}-{h[1][2]:.2f}); a 12.4 x 6.6 "
               f"plug overmold has {room[0]:.2f} mm to spare with 4 mm standoffs, {room[1]:.2f} with 3 mm")
    else:
        report(False, f"{variant} USB-C opening not found in section")
    # microSD
    h = find_hole_robust(asm, [-1.0, 0, 0], [1, 0, 0], [-1.0, case.SD_Y, zb + 0.9])
    if h:
        w, t = h[1][1] - h[0][1], h[1][2] - h[0][2]
        room = [min(zc - 0.4 - h[0][2], h[1][2] - (zc + 0.4)) for zc in (zb + 0.9, zb + 1.9)]
        report(w >= 11.6 and min(room) >= 0.5, f"{variant} microSD opening {w:.2f} x {t:.2f} mm (card 11 x 0.8): "
                                               f"{room[0]:.2f} mm round the card with 4 mm standoffs, {room[1]:.2f} with 3 mm")
    else:
        report(False, f"{variant} microSD opening not found")
    # display window at the front face plane and at the lip's inner face
    for z in (0.05, case.T_FRONT - 0.05):
        h = find_hole_robust(shell, [0, 0, z], [0, 0, 1], [case.WIN_CX, case.WIN_CY, z])
        if h is None:
            report(False, f"{variant} display window not found at z={z}")
            continue
        (x0, y0, _), (x1, y1, _) = h
        # the active area where Waveshare's drawing puts it (round 45: this used to assume it centred
        # in the window, which the window has not been since round 44)
        ax0, ax1, ay0, ay1 = 9.3, 95.7, 4.1, 55.9
        m = min(ax0 - x0, x1 - ax1, ay0 - y0, y1 - ay1)
        report(m >= 0.5, f"{variant} window at z={z:.2f}: {x1 - x0:.2f} x {y1 - y0:.2f} mm, "
                         f"smallest margin around the drawing's 86.40 x 51.84 active area {m:.2f} mm")
    # button opening: rays from the switch tip outward along the wall plane measure the opening,
    # and a ray straight out from the tip must leave the case without touching plastic
    for name, bx in case.BUTTONS.items():
        o = np.array([bx, -case.BTN_PROTRUDE - 0.01, zb + 0.9])
        dirs = np.array([[1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1], [0, -1, 0]], float)
        locs, ir, _ = asm.ray.intersects_location(np.repeat(o[None], 5, 0), dirs, multiple_hits=False)
        dist = {int(i): float(np.linalg.norm(l - o)) for l, i in zip(locs, ir)}
        w = dist.get(0, 99) + dist.get(1, 99)
        report(min(dist.get(0, 99), dist.get(1, 99)) >= 5.0 and 4 not in dist,
               f"{variant} {name}: opening edges {dist.get(1, 99):.1f} / {dist.get(0, 99):.1f} mm to the sides, "
               f"{'nothing' if 4 not in dist else 'PLASTIC'} in front of the switch tip")


# ------------------------------------------------------------------ 3
def best_shift(err, limit=0.65, step=0.01):
    """The board translation (within limit) that brings its standoffs nearest the hole centres:
    returns (translation, the largest remaining offset of any screw from its hole's centre)."""
    g = np.arange(-limit, limit + 1e-9, step)
    tx, ty = np.meshgrid(g, g)
    worst = np.zeros_like(tx)
    for ex, ey in err:
        worst = np.maximum(worst, np.hypot(ex + tx, ey + ty))
    i = np.unravel_index(np.argmin(worst), worst.shape)
    return (float(tx[i]), float(ty[i])), float(worst[i])


def monte_carlo(variant, n=60, seed=7):
    """Perturb the board within the stated uncertainties and re-run the collision test. The standoffs
    are off their estimated positions by a common shift (up to 0.35 mm) plus up to 0.25 mm each way
    for each one; the board then sits where all four screws fit best (it can move 0.3 mm in the lid,
    and the lid 0.35 mm on the skirt), and every screw must still pass its hole and seat in its recess."""
    shell, _, cover_asm, _ = load_assembled(variant)
    S, C = to_manifold(shell), to_manifold(cover_asm)
    both = S + C
    rng = np.random.default_rng(seed)
    saved = {k: getattr(case, k) for k in ("POSTS", "USB_Y", "SD_Y", "WHEEL", "BUTTONS", "STANDOFF_D",
                                           "STANDOFF_H", "BTN_PROTRUDE", "PANEL_T")}
    play = case.SCREW_HOLE_R - 1.25 - 0.075              # M2.5 in a hole printed 0.15 mm small
    fails = {}
    worst_off, worst_shift, screw_bad = 0.0, 0.0, 0
    try:
        for i in range(n):
            j = lambda s=0.5: rng.uniform(-s, s)
            case.STANDOFF_D = rng.uniform(3.8, 4.6)
            r, a_ = 0.35 * math.sqrt(rng.uniform()), rng.uniform(0, 2 * math.pi)
            cx, cy = r * math.cos(a_), r * math.sin(a_)
            err = [(cx + j(0.25), cy + j(0.25)) for _ in saved["POSTS"]]
            case.POSTS = [(x + ex, y + ey) for (x, y), (ex, ey) in zip(saved["POSTS"], err)]
            case.USB_Y = saved["USB_Y"] + j()
            case.SD_Y = saved["SD_Y"] + j()
            wx, wy, wr = saved["WHEEL"]
            case.WHEEL = (wx + j(), wy + j(0.3), wr + j(0.3))
            case.BUTTONS = {k: v + j() for k, v in saved["BUTTONS"].items()}
            h = rng.uniform(case.STANDOFF_H_MIN, case.STANDOFF_H)
            case.BTN_PROTRUDE = rng.uniform(0.5, 1.0)
            case.PANEL_T = rng.uniform(1.0, 1.6)
            (dx, dy), off = best_shift(err)
            worst_off, worst_shift = max(worst_off, off), max(worst_shift, math.hypot(dx, dy))
            if off > play:
                screw_bad += 1
            # the board is held on the cover at (dx, dy); the lid floats on the skirt (0.35 mm) and
            # follows it as far as it can
            lx, ly = (float(np.clip(v, -case.SKIRT_CLR, case.SKIRT_CLR)) for v in (dx, dy))
            for name, g in case.board_model(h).items():
                if name == "pcb":
                    continue
                if vol(g.translate([dx, dy, 0]) ^ C) > 1e-3 or vol(g.translate([dx - lx, dy - ly, 0]) ^ S) > 1e-3:
                    fails[name] = fails.get(name, 0) + 1
    finally:
        for k, v in saved.items():
            setattr(case, k, v)
    report(not fails, f"{variant} Monte Carlo ({n} random boards, standoffs 3-4 mm): collisions {fails or 'none'}")
    report(screw_bad == 0, f"{variant} Monte Carlo: all 4 screws reach their standoffs in {n - screw_bad}/{n} boards "
                           f"(worst screw {worst_off:.2f} mm off its hole's centre, play {play:.2f}; board moved at "
                           f"most {worst_shift:.2f} mm)")


# ------------------------------------------------------------------ 4
def overhangs(variant, limit_deg=50):
    """Faces steeper than limit_deg from vertical, grouped into connected patches. A patch no wider
    than 5 mm across is the top of a small hole or slot, which FDM printers bridge without support."""
    import networkx as nx
    shell, cover, _, _ = load_assembled(variant)
    for name, tm in (("front shell", shell), ("back cover", cover)):
        nz = tm.face_normals[:, 2]
        centers = tm.triangles_center
        bad = (nz < -math.cos(math.radians(90 - limit_deg))) & (centers[:, 2] > 0.01)
        idx = set(np.nonzero(bad)[0].tolist())
        g = nx.Graph()
        g.add_nodes_from(idx)
        for a, b in tm.face_adjacency:
            if a in idx and b in idx:
                g.add_edge(a, b)
        flagged, small = [], 0
        for comp in nx.connected_components(g):
            comp = np.fromiter(comp, int)
            pts = tm.triangles[comp].reshape(-1, 3)
            ext = pts.max(0) - pts.min(0)
            area = tm.area_faces[comp].sum()
            if min(ext[0], ext[1]) <= 5.0 or area < 0.5:
                small += 1
            else:
                flagged.append((round(float(area), 1), np.round(pts.mean(0), 1), np.round(ext[:2], 1)))
        report(not flagged, f"{variant} {name}: {small} small hole/slot tops (<= 5 mm span), "
                            f"larger unsupported patches: {flagged[:6]}")


# ------------------------------------------------------------------ 5
def assembly_motion(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    S, C = to_manifold(shell), to_manifold(cover_asm)
    hooks = Manifold()
    for x, side in case.CLIPS:
        hooks += case.clip_hook(x, side)
    R = C - hooks                                     # everything but the springy hooks
    worst = 0.0
    for dz in np.arange(0.0, 15.0, 0.1):
        worst = max(worst, vol(R.translate([0, 0, dz]) ^ S))
    report(worst < 1e-3, f"{variant} back cover lowered straight onto the lid (hooks left out): worst overlap {worst:.4f} mm3")
    # cover with the board already in the lid: the board must not stop the cover early
    board = case.board_model()
    every = board["pcb"]
    for k, g in board.items():
        if k != "pcb":
            every += g
    w2 = max(vol(C.translate([0, 0, dz]) ^ every) for dz in np.arange(0.1, 15.0, 0.1))
    report(w2 < 1e-3, f"{variant} back cover passes over the installed board until the last 0.1 mm: worst {w2:.4f} mm3")
    z_total = case.Z_B + case.CAVITY[variant] + case.T_BACK
    for px, py in case.POSTS:
        seat = z_total - case.SCREW_HEAD_DEPTH
        hit = 0.0
        for t in np.arange(0.0, 8.01, 0.25):  # screw travels in from outside until the head seats
            screw = case.cyl_z(px, py, 2.5, seat + t, seat + t + 1.8) + case.cyl_z(px, py, 1.25, seat + t - 8.0, seat + t)
            hit = max(hit, vol(screw ^ (S + C)))
        report(hit < 1e-3, f"{variant} corner screw ({px:.1f}, {py:.1f}): goes in and seats freely ({hit:.4f} mm3)")


# ------------------------------------------------------------------ 6
def photo_overlay(out_path):
    from PIL import Image, ImageDraw
    import reference
    try:
        front = Image.open(reference.path("front")).convert("RGB")
        back = Image.open(reference.path("back")).convert("RGB")
    except reference.Unavailable as e:
        skip(f"photo overlay not redrawn: Waveshare's photos could not be downloaded ({e})")
        return
    # board outline pixels measured earlier: front (295..1307, 304..912), back (298..1305, 304..911)
    def to_front(x, y):
        return 295 + x * (1012 / 99.5), 912 - y * (608 / 60.0)

    def to_back(x, y):  # the back photo is mirrored left-right
        return 1305 - x * (1007 / 99.5), 911 - y * (607 / 60.0)

    d = ImageDraw.Draw(front)
    x0, y0 = to_front(case.WIN_CX - case.WIN_W / 2, case.WIN_CY + case.WIN_H / 2)
    x1, y1 = to_front(case.WIN_CX + case.WIN_W / 2, case.WIN_CY - case.WIN_H / 2)
    d.rectangle([x0, y0, x1, y1], outline=(255, 0, 0), width=3)
    a = to_front(case.BTN_NOTCH[0], 0)
    b = to_front(case.BTN_NOTCH[1], -3)
    d.rectangle([a[0], a[1], b[0], b[1]], outline=(255, 0, 0), width=3)
    wx, wy, wr = case.WHEEL
    c = to_front(wx, wy)
    r = wr * 1012 / 99.5
    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(255, 0, 0), width=3)
    e = ImageDraw.Draw(back)
    for px, py in case.POSTS:
        c = to_back(px, py)
        r = case.STANDOFF_D / 2 * 10.1
        e.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(255, 0, 0), width=3)
    for yc, half in ((case.USB_Y, 4.47), (case.SD_Y, 5.5)):
        a, b = to_back(-0.5, yc - half), to_back(3.0, yc + half)
        e.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], outline=(255, 0, 0), width=3)
    for bx in case.BUTTONS.values():
        a, b = to_back(bx - 2, 0), to_back(bx + 2, 3.5)
        e.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], outline=(255, 0, 0), width=3)
    c = to_back(wx, wy)
    rw = wr * 1007 / 99.5
    e.ellipse([c[0] - rw, c[1] - rw, c[0] + rw, c[1] + rw], outline=(255, 0, 0), width=3)
    for mx, my in (case.MIC, case.DHT):
        c = to_back(mx, my)
        e.ellipse([c[0] - 12, c[1] - 12, c[0] + 12, c[1] + 12], outline=(255, 0, 0), width=3)
    W = Image.new("RGB", (1600, 600), "white")
    W.paste(front.crop((240, 250, 1360, 970)).resize((800, 514)), (0, 40))
    W.paste(back.crop((240, 250, 1360, 970)).resize((800, 514)), (800, 40))
    ImageDraw.Draw(W).text((10, 10), "Front photo: window, dial, button windows   |   Back photo: standoffs, USB-C, microSD, buttons, dial, mic, DHT", fill=(0, 0, 0))
    W.save(out_path)
    print(f"  ..   photo overlay written to {out_path} (inspect by eye)")


if __name__ == "__main__":
    for v in case.CAVITY:
        print(f"\n### {v}")
        kd_clearance(v)
        opening_sizes(v)
        monte_carlo(v)
        overhangs(v)
        assembly_motion(v)
    photo_overlay(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "preview", "photo_overlay.png"))
    print(f"\nRound 2: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
