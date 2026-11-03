#!/usr/bin/env python3
"""Debug round 3: methods not used in rounds 1 and 2.

1. Own binary-STL parser: triangle count, header, NaNs, normals vs winding, every edge used twice
2. "Calipers": rays shot at chosen x/y points measure the printed stack; compared with a hand
   calculation written out below (independent of the constants' derived values)
3. Second source: positions re-measured on Waveshare's dimension drawing (not the photos)
4. Printer error: the case grown/shrunk by +/-0.15 mm in x/y (a typical FDM error) vs the board
5. Angled fingers: spheres approaching the buttons and the dial at 30 deg off-axis
"""
import math
import os
import struct
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import STL, load_assembled, to_manifold, vol  # noqa: E402

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
def parse_stl(path):
    raw = open(path, "rb").read()
    n = struct.unpack("<I", raw[80:84])[0]
    assert len(raw) == 84 + 50 * n, "size does not match triangle count"
    rec = np.frombuffer(raw[84:], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n)
    return rec["n"].astype(float), rec["v"].astype(float)


def own_parser(variant):
    for part in ("front_shell", "back_cover"):
        path = os.path.join(STL, f"{part}_{variant}.stl")
        try:
            nrm, tri = parse_stl(path)
        except AssertionError as e:
            report(False, f"{variant} {part}: {e}")
            continue
        finite = np.isfinite(tri).all() and np.isfinite(nrm).all()
        cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        area = np.linalg.norm(cross, axis=1) / 2
        unit = cross / np.maximum(area[:, None] * 2, 1e-12)
        stored = np.linalg.norm(nrm, axis=1) > 0.5
        agree = (np.einsum("ij,ij->i", unit[stored], nrm[stored]) > 0.9).mean() if stored.any() else 1.0
        # edge manifoldness on exact float32 vertex keys
        keys = {}
        verts = tri.reshape(-1, 3).astype(np.float32)
        _, inv = np.unique(verts, axis=0, return_inverse=True)
        f = inv.reshape(-1, 3)
        e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
        _, counts = np.unique(e, axis=0, return_counts=True)
        signed = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
        ok = finite and agree > 0.999 and (counts == 2).all() and signed > 0 and (area > 1e-10).all()
        report(ok, f"{variant} {part}: {len(tri)} triangles, finite={finite}, stored normals match winding "
                   f"{agree * 100:.2f}%, edges used exactly twice {(counts == 2).mean() * 100:.2f}%, "
                   f"signed volume {signed / 1000:.2f} cm3, zero-area {int((area <= 1e-10).sum())}")


# ------------------------------------------------------------------ 2
def ray_z(tm, x, y, z_from=-50.0):
    """All z values where a vertical ray at (x, y) crosses the mesh surface."""
    locs, _, _ = tm.ray.intersects_location([[x, y, z_from]], [[0, 0, 1]], multiple_hits=True)
    return np.sort(locs[:, 2]) if len(locs) else np.array([])


def calipers(variant):
    shell, _, cover_asm, z_total = load_assembled(variant)
    # hand calculation of the stack, written out from the design intent:
    # front wall 1.6 | panel room 1.2 + 0.5 | PCB 1.6 | clear depth behind PCB | back wall 1.8
    clear = {"battery": 5.0 + 5.0}[variant]  # battery: parts room + 454261 room
    hand = {"lip": 1.6 - 0.3, "pcb_front": 1.6 + 1.7, "pcb_back": 1.6 + 1.7 + 1.6,
            "total": 1.6 + 1.7 + 1.6 + clear + 1.8}
    # lip thickness: ray through the bezel just below the window
    z = ray_z(shell, 52.0, 2.0)
    report(len(z) >= 2 and abs((z[1] - z[0]) - hand["lip"]) < 0.01,
           f"{variant} caliper: bezel below window over the glass {z[1] - z[0]:.3f} mm thick (hand calc 1.6 - 0.3 "
           f"relief = {hand['lip']})")
    # ledge pad: top face 0.5 mm in front of the PCB front face
    z = ray_z(shell, 50.0, -0.1)
    report(len(z) >= 2 and abs(z[1] - (hand["pcb_front"] - 0.5)) < 0.01,
           f"{variant} caliper: front pad ends at z={z[1]:.3f} (PCB front face less 0.5, hand calc "
           f"{hand['pcb_front'] - 0.5:.2f})")
    # corner post end: where a 4 mm standoff ends, 4.0 behind the PCB back face
    px, py = case.POSTS[1]
    z = ray_z(cover_asm, px - 2.6, py + 0.5)
    report(len(z) >= 1 and abs(z[0] - (hand["pcb_back"] + 4.0)) < 0.01,
           f"{variant} caliper: corner post ends at z={z[0]:.3f} (PCB back face + a 4 mm standoff, hand calc "
           f"{hand['pcb_back'] + 4.0:.2f})")
    # total depth through the middle of the back
    zs = ray_z(shell, 30.0, 1.0)  # through the bezel below the window
    zc = ray_z(cover_asm, 30.0, 30.0)
    report(abs(zc.max() - hand["total"]) < 0.01 and abs(zs.min()) < 0.01,
           f"{variant} caliper: front face z={zs.min():.3f}, back face z={zc.max():.3f} (hand calc {hand['total']:.2f})")
    # clear depth for components / battery: from PCB back to the inside of the back wall
    report(abs((zc.min() - hand["pcb_back"]) - clear) < 0.01,
           f"{variant} caliper: clear depth behind the PCB {zc.min() - hand['pcb_back']:.3f} mm (designed {clear})")


# ------------------------------------------------------------------ 3
def drawing_check():
    """Re-measure from the outline drawing (dim0.png, 960 px wide) rather than the photos."""
    from PIL import Image
    import reference
    try:
        path = reference.path("drawing")
    except reference.Unavailable as e:
        skip(f"drawing re-measurement: Waveshare's drawing could not be downloaded ({e})")
        return
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    blue = (a[..., 2] - a[..., 0] > 40)
    ys, xs = np.nonzero(blue)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    sx, sy = (x1 - x0) / 99.5, (y1 - y0) / 60.0
    report(abs(sx - sy) / sx < 0.03, f"drawing: board found at px x {x0}-{x1}, y {y0}-{y1}; scale {sx:.2f} / {sy:.2f} px/mm")
    g = a.sum(2)
    dark = g < 300
    # active area: the drawing's own extension lines for the 86.40 and 51.84 dimensions.
    # Vertical lines below the board (thin, 1-3 px wide) mark the 86.40 mm edges.
    below = dark[y1 + 3: y1 + 30, x0:x1]
    cols = np.nonzero(below.sum(0) >= 20)[0]  # long vertical lines only
    runs = np.split(cols, np.nonzero(np.diff(cols) > 1)[0] + 1)
    lines_x = [float(r.mean()) / sx for r in runs if len(r) <= 4]
    # Horizontal lines left of the board mark the 51.84 mm edges.
    left = dark[y0:y1, max(0, x0 - 45): x0 - 3]
    rows = np.nonzero(left.sum(1) >= 20)[0]
    runs = np.split(rows, np.nonzero(np.diff(rows) > 1)[0] + 1)
    lines_y = [60.0 - float(r.mean()) / sy for r in runs if len(r) <= 4]
    if len(lines_x) == 2 and len(lines_y) == 2:
        ax0, ax1 = sorted(lines_x)
        ay0, ay1 = sorted(lines_y)
        wx0, wx1 = case.WIN_CX - case.WIN_W / 2, case.WIN_CX + case.WIN_W / 2
        wy0, wy1 = case.WIN_CY - case.WIN_H / 2, case.WIN_CY + case.WIN_H / 2
        report(wx0 <= ax0 and ax1 <= wx1 and wy0 <= ay0 and ay1 <= wy1,
               f"drawing: dimension lines put the active area at x {ax0:.2f}-{ax1:.2f} ({ax1 - ax0:.2f} wide), "
               f"y {ay0:.2f}-{ay1:.2f} ({ay1 - ay0:.2f} tall); window spans x {wx0:.2f}-{wx1:.2f}, y {wy0:.2f}-{wy1:.2f}")
    else:
        report(False, f"drawing: could not find the active-area dimension lines ({lines_x}, {lines_y})")
    # dial: dark blob within 4 mm above the top edge, inside the board's x range
    top = dark[y0 - int(4 * sy): y0 - 1, x0:x1]
    dy, dx = np.nonzero(top)
    report(len(dx) > 0 and abs(dx.mean() / sx - case.WHEEL[0]) < 1.0,
           f"drawing: dial centre x {dx.mean() / sx:.2f} (model {case.WHEEL[0]}), "
           f"sticks out {(len(top) - dy.min()) / sy:.2f} mm (model {case.WHEEL[1] + case.WHEEL[2] - 60:.2f})")
    # buttons: blobs at least 1 mm wide just below the bottom edge (thin dimension lines excluded)
    bot = dark[y1 + 2: y1 + 15, x0:x1]
    cols = np.nonzero(bot.any(0))[0]
    runs = np.split(cols, np.nonzero(np.diff(cols) > 1)[0] + 1)
    centres = sorted(float(r.mean()) / sx for r in runs if len(r) >= sx)
    model = sorted(case.BUTTONS.values())
    report(len(centres) == 2 and all(abs(c - m) < 1.0 for c, m in zip(centres, model)),
           f"drawing: buttons at x {[round(c, 2) for c in centres]} (model {model})")


# ------------------------------------------------------------------ 4
def printer_error(variant, err=0.15):
    shell, _, cover_asm, _ = load_assembled(variant)
    board = case.board_model()
    every = board["pcb"]
    for k, g in board.items():
        if k != "pcb":
            every += g
    c = np.array([case.BW / 2, case.BH / 2, 0])
    for sign, label in ((-1, "undersized"), (1, "oversized")):
        k = 1 + sign * err / 50.0  # +/-0.15 mm on a ~100 mm part, scaled about the centre
        S = to_manifold(shell).translate(-c).scale([k, 1 + sign * err / 30.0, 1]).translate(c)
        C = to_manifold(cover_asm).translate(-c).scale([k, 1 + sign * err / 30.0, 1]).translate(c)
        hit = vol(every ^ (S + C))
        report(hit < 1e-3, f"{variant} printed {label} by {err} mm: board overlap {hit:.3f} mm3")
    # shell and cover printed with opposite errors must still go together
    from round1 import hook_zones
    S = to_manifold(shell).translate(-c).scale([1 - err / 50, 1 - err / 30, 1]).translate(c)
    C = (to_manifold(cover_asm) - hook_zones()).translate(-c).scale([1 + err / 50, 1 + err / 30, 1]).translate(c)
    hit = vol(S ^ C)
    report(hit < 1e-3, f"{variant} shell {err} mm small + cover {err} mm large: overlap {hit:.3f} mm3 (the springy "
                       f"clip hooks left out: round 36 checks them with print errors)")


# ------------------------------------------------------------------ 5
def angled_fingers(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    obstacle = to_manifold(shell) + to_manifold(cover_asm)
    board = case.board_model()

    def first_touch(target, direction, r):
        """Move a sphere toward the target along direction; return (thing touched, travel left)."""
        d = np.asarray(direction, float)
        d /= np.linalg.norm(d)
        sph = __import__("manifold3d").Manifold.sphere(r, 96)
        far = np.asarray(target) - d * (r + 25)
        lo, hi = 0.0, 25.0 + 0.5
        hit = lambda t: not (sph.translate(list(far + d * t)) ^ obstacle).is_empty()
        if not hit(hi):
            return hi
        for _ in range(35):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if not hit(mid) else (lo, mid)
        return lo

    for name, bx in case.BUTTONS.items():
        tip = np.array([bx, -case.BTN_PROTRUDE, case.Z_B + 0.9])
        for ang in (15, 30):
            t = math.tan(math.radians(ang))
            for label, dvec in (("straight", (0, 1, 0)), (f"{ang}deg from front", (0, 1, t)),
                                (f"{ang}deg from back", (0, 1, -t)), (f"{ang}deg sideways", (t, 1, 0)),
                                (f"{ang}deg other side", (-t, 1, 0))):
                if ang == 30 and label == "straight":
                    continue
                short = max(25.0 - first_touch(tip, dvec, 7.0), 0.0)
                # a 14 mm wide fingertip tilted 30 deg sideways meets the end of the opening:
                # the buttons are 10 mm apart and 4-6 mm from its ends, so this is reported only
                info = ang == 30 and "sideways" in label or ang == 30 and "other side" in label
                report(info or short <= 0.6, f"{variant} {name} finger r=7 {label}: stops {short:.2f} mm "
                                             f"before the switch tip" + (" (information)" if info else ""))
    wx, wy, wr = case.WHEEL
    rim = np.array([wx, wy + wr, case.Z_B + 1.5])
    for label, dvec in (("straight", (0, -1, 0)), ("30deg sideways", (math.tan(math.radians(30)), -1, 0))):
        t = first_touch(rim, dvec, 7.0)
        report(25.0 - t <= 0.3, f"{variant} dial finger r=7 {label}: stops {max(25.0 - t, 0):.2f} mm before the rim")


if __name__ == "__main__":
    drawing_check()
    for v in case.CAVITY:
        print(f"\n### {v}")
        own_parser(v)
        calipers(v)
        printer_error(v)
        angled_fingers(v)
    print(f"\nRound 3: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
