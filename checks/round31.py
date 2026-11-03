#!/usr/bin/env python3
"""Debug round 31 (session 4): methods not used in rounds 1-30.

1. Cable routes found by a search, not drawn: the closed case is turned into a 0.5 mm voxel map
   (sections of the shell, cover, board parts, battery and speaker, filled in layer by layer), every
   voxel gets its distance to the nearest obstacle (a distance transform), and Dijkstra's shortest
   path runs through the voxels with room for each cable (2.8 mm speaker cable, 2.5 mm battery pair).
   A route must exist from the speaker's cable exit to the SPK plug and from the battery's wire corner
   to the BAT plug, and the hand-drawn routes in case.py may not be shorter than the searched ones by
   more than the voxel size allows (if they were, they'd go through something).
2. Every new number in the README accounted for: the numbers that are in the README now but were not
   in session 4's README are listed, and each one must come from case.py, a check's result or a
   measurement, by a rule written here; anything unexplained fails.
3. The cover closing with its load: the battery (largest plausible), the speaker and the spare-cable
   loop are stuck to the back cover, so they travel with it. Each is swept along the closing motion
   (straight down the last 20 mm) as an exact convex sweep and must miss the board and the shell.
"""
import contextlib
import io
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from manifold3d import Manifold  # noqa: E402
from round1 import load_assembled, to_manifold, vol  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def path_len(pts):
    return float(np.linalg.norm(np.diff(np.asarray(pts, float), axis=0), axis=1).sum())


# ------------------------------------------------------------------ 1
def voxel_routes(step=0.5):
    from matplotlib.path import Path
    from scipy import ndimage
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    shell, _, cover_asm, z_total = load_assembled("battery")
    z_in = z_total - case.T_BACK
    obst = to_manifold(shell) + to_manifold(cover_asm)
    for g in case.board_model().values():
        obst += g
    x0, x1, y0, y1 = case.BATTERY_BAY
    L, W, T = case.BATTERY_MAX
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    obst += case.box(cx - L / 2, cx + L / 2, cy - W / 2, cy + W / 2, z_in - T, z_in)   # the largest cell
    sx, sy = case.SPEAKER["battery"]
    a, b, t = case.SPEAKER_SIZE
    obst += case.box(sx - a / 2, sx + a / 2, sy - b / 2, sy + b / 2, z_in - t, z_in)
    xs = np.arange(-case.CLR + step / 2, case.BW + case.CLR, step)
    ys = np.arange(-case.CLR + step / 2, case.BH + case.CLR, step)
    zs = np.arange(case.Z_B + step / 2, z_in, step)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    pts = np.column_stack([X.ravel(), Y.ravel()])
    solid = np.zeros((len(xs), len(ys), len(zs)), bool)
    for k, z in enumerate(zs):
        inside = np.zeros(len(pts), bool)
        for poly in obst.slice(z).to_polygons():      # even-odd fill of the section's outlines
            inside ^= Path(np.asarray(poly)).contains_points(pts)
        solid[:, :, k] = inside.reshape(X.shape)
    clear = ndimage.distance_transform_edt(~solid) * step   # mm from each voxel centre to the nearest solid
    idx = -np.ones(solid.shape, int)

    def route(r, start, goal, label, drawn):
        free = clear >= r + step / 2
        n = int(free.sum())
        idx[:] = -1
        idx[free] = np.arange(n)
        rows, cols, w = [], [], []
        for d in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, -1, 0), (1, 0, 1), (1, 0, -1), (0, 1, 1), (0, 1, -1)]:
            sl_a = tuple(slice(max(0, -s), solid.shape[i] - max(0, s)) for i, s in enumerate(d))
            sl_b = tuple(slice(max(0, s), solid.shape[i] - max(0, -s)) for i, s in enumerate(d))
            ia, ib = idx[sl_a], idx[sl_b]
            m = (ia >= 0) & (ib >= 0)
            rows.append(ia[m])
            cols.append(ib[m])
            w.append(np.full(m.sum(), step * float(np.linalg.norm(d))))
        g = coo_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()

        def nearest(p):
            i, j, k = (np.abs(xs - p[0]).argmin(), np.abs(ys - p[1]).argmin(), np.abs(zs - p[2]).argmin())
            cand = np.argwhere(free)
            dd = np.linalg.norm((cand - [i, j, k]) * step, axis=1)
            q = cand[dd.argmin()]
            return idx[tuple(q)], dd.min()
        s, ds = nearest(start)
        e, de = nearest(goal)
        dist = dijkstra(g, directed=False, indices=s)[e]
        ok = np.isfinite(dist) and ds <= 1.5 and de <= 1.5 and drawn >= dist - 3 * step
        report(ok, f"{label}: searched route for a {2 * r:.1f} mm cable through the voxel map {dist:.0f} mm "
                   f"(ends within {max(ds, de):.1f} mm of the asked points); the drawn route is {drawn:.0f} mm")
    bp, rb = case.battery_wire_route()
    route(rb, bp[0], bp[-1], "battery wire, wire corner to BAT", path_len(bp))
    sp, rs = case.speaker_wire_route()
    route(rs, sp[1], sp[-1], "speaker cable, from the gap beside the speaker to SPK", path_len(sp[1:]))


# ------------------------------------------------------------------ 2
def readme_inventory():
    old = subprocess.run(["git", "-C", ROOT, "show", "13d2cbf:README.md"], capture_output=True, text=True).stdout
    if not old:
        report(False, "README inventory: session 4's README (commit 13d2cbf) could not be read")
        return
    new = open(os.path.join(ROOT, "README.md")).read()
    tok = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
    old_set, new_set = set(tok.findall(old)), set(tok.findall(new))
    fresh = sorted(new_set - old_set, key=float)
    import round13
    import round28
    import round29
    import round30
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        round13.wires()
        round13.battery_drop()
        got = round28.sizes()
        round30.cable_lengths()
    out = buf.getvalue()
    traced_bat = int(re.search(r"battery wire (\d+) mm for a", out).group(1))
    lb, ls = (int(v) for v in re.findall(r"about (\d+) mm long", out)[:2])
    loop = int(re.search(r"holds about (\d+) mm of cable", out).group(1))
    slide = float(re.search(r"slide at most ([\d.]+) mm", out).group(1))
    x0, x1, y0, y1 = case.BATTERY_BAY
    pw, ph, _ = case.SPEAKER_BOX["battery"]
    gw, gl, gp = case.GRILLE_SLOTS
    f1 = lambda v: f"{v:.1f}"  # noqa: E731
    explain = {
        f1(x1 - x0): "bay length", f1(y1 - y0): "bay width",
        f1(got["battery length"]): "battery length (round 28)", f1(got["battery width"]): "battery width (round 28)",
        f1(got["speaker length"]): "speaker length (round 28)", f1(got["speaker width"]): "speaker width (round 28)",
        f1(got["speaker thickness"]): "speaker thickness (round 28)",
        f1(pw): "pocket width", f1(ph): "pocket length", f1(slide): "battery play (round 13)",
        str(lb): "battery wire route (round 13)", str(ls): "speaker cable route (round 13)",
        str(round(loop / 10)): "loop room in cm (round 13)", f1(gw): "slot width", f1(gl): "slot length",
        f1(gp - gw): "web between slots", f1(2 * case.SCREW_HOLE_R): "screw hole diameter",
        f1(case.ANTENNA[0] - (case.SPEAKER["battery"][0] + pw / 2)): "pocket to antenna",
        "1.7": "the old pilot it is compared with", "70": "pull-out per screw (round 22: 73 N)",
        "10": "speaker cable 10-11 cm / membrane 10.1", "11": "speaker cable 10-11 cm",
        str(traced_bat): "battery wire length (round 30)", "2.9": "cable exit from the peg end (SPK_CABLE_EXIT)",
        str(traced_bat - lb): "battery wire to spare (round 30's length minus round 13's route)",
        "1.6": "peg protrusion (round 28)", f1(case.BATTERY_GUIDE[1]): "guide height",
        "10.1": "membrane length (round 28)", "5.8": "membrane width (round 28 / SPEAKER_WINDOW)",
        "0.3": "measuring error / membrane centring", "17": "fewest ticks per photo (round 28)",
        "43": "most ticks per photo (round 28)", "15": "run_all.sh run time in minutes",
        "0.1": "thin tape 0.1-0.2 mm", "0.2": "thin tape 0.1-0.2 mm", "0.48": "board check worst (round 28)",
        "1": "peg 1 mm off the middle", "19": "round 19 slices the parts", "28": "round 28",
        "4.3": "battery thickness (round 28: 4.32)", "40.7": "battery width (round 28: 40.73)",
        "61.1": "battery length (round 28: 61.08)", "0.7": "bay room per side", "8": "loop room 8 cm",
        "3": "bend radius 3 mm / three slots", "7.0": "slot length", "1.0": "slot width",
        "0.8": "webs between slots", "0.9": "battery play / bay room per side",
    }
    # session 5: the corner screws, the clips, the standoff estimates
    import round22
    import round35
    import round36
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        round22.clips()
        round35.standoffs()
        round36.closing()
    out5 = buf.getvalue()
    eps = float(re.search(r"([\d.]+) % strain at full bend", out5).group(1))
    pull = re.search(r"(\d+) N to pull", out5).group(1)
    reach = float(re.search(r"still reach ([\d.]+) mm past", out5).group(1))
    est = [[tuple(float(v) for v in p) for p in re.findall(r"\(([\d.]+), ([\d.]+)\)", line)]
           for line in out5.splitlines() if "photo, camera axis" in line]
    # each side has two standoffs: left (0, 2), right (1, 3), bottom (0, 1), top (2, 3)
    rng = lambda ids, k: (f"{min(e[i][k] for e in est for i in ids):.1f}–"  # noqa: E731
                          f"{max(e[i][k] for e in est for i in ids):.1f}")
    sides = (rng((0, 2), 0), rng((1, 3), 0), rng((0, 1), 1), rng((2, 3), 1))
    ranges = f"x {sides[0]} / {sides[1]} and y {sides[2]} / {sides[3]} mm"
    if ranges not in new:
        report(False, f"README: the photo's standoff estimates should read '{ranges}'")
    for part in sides:
        for v in part.split("–"):
            explain[v] = "standoff estimate range (round 35)"
    (x0p, y0p), (x1p, y1p) = case.POSTS[0], case.POSTS[3]
    explain.update({
        f"{x0p:g}": "POSTS", f"{x1p:g}": "POSTS", f"{y0p:g}": "POSTS", f"{y1p:g}": "POSTS",
        f"{x1p - x0p:.1f}": "POSTS spacing in x", f"{y1p - y0p:.2f}": "POSTS spacing in y",
        "96.7": "Waveshare's estimate (round 35)", "2.85": "Waveshare's estimate (round 35)", "57.4": "Waveshare's estimate",
        "0.45": "round 35's limit for the estimates", "150": "round 35's camera-axis range",
        f1(2 * case.SCREW_HEAD_R): "recess diameter", "5.0": "largest head (ISO 7045 M2.5: 5.0 x 1.75)",
        "1.75": "ISO 7045 M2.5 head height", "7045": "ISO 7045", "7985": "DIN 7985", "7089": "ISO 7089", "125": "DIN 125",
        f1(case.PANEL_SPACE - case.PANEL_T + case.GLASS_RELIEF): "glass to lid",
        f"{case.CLIP_L:.0f}": "clip beam length", pull: "pull-off force (round 22)", f1(eps): "clip strain (round 22)",
        "0.15": "print error per side (round 36)", f"{reach:.2f}": "hook reach with errors (round 36)",
        "35": "round 35",
    })
    m = re.search(r"about (\d+) g of PLA", new)
    if m:
        explain[m.group(1)] = "PLA estimate (round 19 checks it against the slicer)"
    unexplained = [v for v in fresh if v not in explain]
    report(not unexplained, f"README: {len(fresh)} numbers new since session 4, each traced to case.py, a check or a "
                            f"measurement; unexplained: {unexplained or 'none'}")


# ------------------------------------------------------------------ 3
def loaded_cover():
    shell, _, cover_asm, z_total = load_assembled("battery")
    S = to_manifold(shell)
    z_in = z_total - case.T_BACK
    board = Manifold()
    for g in case.board_model().values():
        board += g
    x0, x1, y0, y1 = case.BATTERY_BAY
    L, W, T = case.BATTERY_MAX
    pieces = []
    # the largest cell, pushed into each corner of its bay
    for ex in (-1, 1):
        for ey in (-1, 1):
            cx = (x0 + x1) / 2 + ex * ((x1 - x0) - L) / 2
            cy = (y0 + y1) / 2 + ey * ((y1 - y0) - W) / 2
            pieces.append(("battery", case.box(cx - L / 2, cx + L / 2, cy - W / 2, cy + W / 2, z_in - T, z_in)))
    sx, sy = case.SPEAKER["battery"]
    a, b, t = case.SPEAKER_SIZE
    rx, ry = case.SPK_ROOM
    for ex in (-1, 1):
        for ey in (-1, 1):
            pieces.append(("speaker", case.box(sx + ex * rx - a / 2, sx + ex * rx + a / 2, sy + ey * ry - b / 2,
                                               sy + ey * ry + b / 2, z_in - t, z_in)))
    coil, r = case.speaker_cable_coil()
    for p, q in zip(coil[:-1], coil[1:]):
        pieces.append(("loop", Manifold.hull(Manifold.sphere(r, 16).translate(list(p))
                                             + Manifold.sphere(r, 16).translate(list(q)))))
    worst = {}
    for name, p in pieces:
        sweep = Manifold.hull(p + p.translate([0, 0, 20.0]))   # convex piece moved 20 mm: exact swept volume
        worst[name] = max(worst.get(name, 0.0), vol(sweep ^ board), vol(sweep ^ S))
    report(all(v < 1e-3 for v in worst.values()),
           f"back cover closing with its load: battery (largest, any corner), speaker (any position) and cable loop "
           f"swept over the last 20 mm; worst overlap with the board or shell {worst}")


if __name__ == "__main__":
    loaded_cover()
    readme_inventory()
    voxel_routes()
    print(f"\nRound 31: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
