#!/usr/bin/env python3
"""Debug round 35 (session 5: the board screwed to the back cover, the lid on snap clips). Methods not
used in rounds 1-34.

1. The standoff positions, measured in your back photo (owner_photos/board_back.jpg, photo 9). The
   PCB's left, right and top edges are fitted as straight lines on clean stretches (none under the
   ruler), the bottom edge follows from the board's 60 mm height, and that gives the board's plane.
   The brass rings are fitted as circles. Their tops are about 4 mm nearer the camera than the board,
   which makes them look further out; the ruler lies on them, so its 10 mm dots, mapped onto the
   board's plane, give the factor to pull them back by, toward the point under the camera. With that
   point anywhere within 150 px of the photo's centre, and with Waveshare's photo positions, POSTS
   must be within 0.45 mm of every estimate, and for each estimate the board must have a position
   where all four screws pass their holes (with the holes printed 0.15 mm small).
2. The clips as built, read back from the STL files: each beam's slot is open along its whole length
   (no plastic between the beam and the cover), the beam is there below it at the designed length,
   the hook reaches CLIP_UNDERCUT past the lid's inner wall, the lid has a groove at each hook that
   is deeper than the hook, and closed, the hook's catch face presses the lid's by CLIP_PRELOAD.
3. The clips and the screw recesses as sliced: in PrusaSlicer's G-code for the back cover, the slot
   layers have no extrusion inside a beam's footprint and the beam's first layer over the slot is
   printed as a bridge; the first layer over each screw recess is a bridge too, and no layer puts
   plastic inside a screw hole.
"""
import contextlib
import io
import math
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402

problems = []
skipped = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def skip(msg):
    print("  SKIP " + msg)
    skipped.append(msg)


# ------------------------------------------------------------------ 1
OFFSET = (150.0, 80.0)                    # the crop's place in photo 9 (owner_photos/crops.json)
CENTRE = np.array([1000.0, 750.0])        # photo 9 is 2000 x 1500
# the ruler's 10 mm dots (full-photo px; the ones not hidden behind parts on the board) and their index
DOTS = [(311.85, 795.66, 0), (452.28, 801.45, 1), (593.39, 801.62, 2), (732.71, 804.73, 3), (872.38, 809.57, 4),
        (1153.68, 812.81, 6), (1288.84, 812.06, 7), (1427.96, 817.70, 8), (1564.72, 821.62, 9), (1706.43, 822.41, 10)]
RINGS = [(277.1, 174.6), (1590.8, 189.6), (267.5, 936.5), (1584.5, 945.5)]   # starting guesses, as in round 28
WAVESHARE = [(2.2, 2.85), (96.7, 2.85), (2.2, 57.4), (96.7, 57.4)]           # session 1-4 estimate


class Photo:
    def __init__(self):
        a = np.asarray(Image.open(os.path.join(HERE, "owner_photos", "board_back.jpg")).convert("RGB")).astype(float)
        self.sm = ndi.gaussian_filter(a, (1.2, 1.2, 0))
        self.gx = np.sqrt((np.diff(self.sm, axis=1) ** 2).sum(2))
        self.gy = np.sqrt((np.diff(self.sm, axis=0) ** 2).sum(2))

    def edge(self, axis, lines, guess, win=8):
        """Strongest colour step near `guess` on each line; returns full-photo (x, y) points."""
        ox, oy = OFFSET
        pts = []
        for L in lines:
            g = self.gx[int(L - oy), :] if axis == "x" else self.gy[:, int(L - ox)]
            g0 = guess - (ox if axis == "x" else oy)
            lo = int(g0 - win)
            i = lo + int(np.argmax(g[lo:int(g0 + win)]))
            den = g[i - 1] - 2 * g[i] + g[i + 1]
            p = i + 0.5 + (0.5 * (g[i - 1] - g[i + 1]) / den if den else 0.0)
            pts.append((p + ox, L) if axis == "x" else (L, p + oy))
        return np.array(pts)

    def ring(self, c0, rmin=22, rmax=38, n=120):
        """Circle through the outer edge of a brass ring (outermost strong step along rays from c0)."""
        ox, oy = OFFSET
        c0 = np.array(c0) - (ox, oy)
        pts = []
        for ang in np.linspace(0, 2 * np.pi, n, endpoint=False):
            rs = np.arange(rmin, rmax, 0.25)
            xs, ys = c0[0] + rs * np.cos(ang), c0[1] + rs * np.sin(ang)
            prof = np.stack([ndi.map_coordinates(self.sm[:, :, ch], [ys, xs], order=1) for ch in range(3)], 1)
            g = ndi.gaussian_filter1d(np.sqrt((np.diff(prof, axis=0) ** 2).sum(1)), 1.5)
            pk = [j for j in range(1, len(g) - 1) if g[j] >= g[j - 1] and g[j] >= g[j + 1] and g[j] >= 0.5 * g.max()]
            if pk:
                j = max(pk)
                pts.append((c0[0] + (rs[j] + 0.125) * np.cos(ang), c0[1] + (rs[j] + 0.125) * np.sin(ang)))
        p = np.array(pts)
        keep = np.ones(len(p), bool)
        for _ in range(6):
            A = np.c_[2 * p[keep], np.ones(keep.sum())]
            cx, cy, c = np.linalg.lstsq(A, (p[keep] ** 2).sum(1), rcond=None)[0]
            r = np.sqrt(c + cx ** 2 + cy ** 2)
            res = np.hypot(p[:, 0] - cx, p[:, 1] - cy) - r
            keep = np.abs(res) < max(2.5 * np.std(res[keep]), 0.8)
        return np.array([cx + ox, cy + oy])


def fit_line(pts, axis):
    """Robust straight line: x = a y + b for a vertical edge, y = a x + b for a horizontal one."""
    t, s = (pts[:, 1], pts[:, 0]) if axis == "x" else (pts[:, 0], pts[:, 1])
    keep = np.ones(len(t), bool)
    for _ in range(5):
        a, b = np.polyfit(t[keep], s[keep], 1)
        r = s - (a * t + b)
        keep = np.abs(r) < max(2.5 * np.std(r[keep]), 0.6)
    return a, b, float(np.std(r[keep]))


def cross(v, h):
    a1, b1 = v
    a2, b2 = h
    y = (a2 * b1 + b2) / (1 - a1 * a2)
    return np.array([a1 * y + b1, y])


def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A))
    return vt[-1].reshape(3, 3) / vt[-1][-1]


def apply(h, p):
    q = h @ np.array([p[0], p[1], 1.0])
    return q[:2] / q[2]


def standoffs():
    ph = Photo()
    left = fit_line(ph.edge("x", list(range(448, 494, 3)) + list(range(612, 732, 3)), 244), "x")
    right = fit_line(ph.edge("x", list(range(232, 340, 3)) + list(range(380, 700, 4)), 1618), "x")
    top = fit_line(ph.edge("y", list(range(420, 560, 4)) + list(range(680, 1240, 4)) + list(range(1300, 1500, 4)), 146), "y")
    tl, tr = cross(left[:2], top[:2]), cross(right[:2], top[:2])
    rings = np.array([ph.ring(c) for c in RINGS])
    # camera tilt from the two pairs of standoff tops (the scale grows toward the photo's bottom)
    beta = (np.linalg.norm(rings[3] - rings[2]) / np.linalg.norm(rings[1] - rings[0]) - 1) \
        / (rings[2:, 1].mean() - rings[:2, 1].mean())
    sx = np.linalg.norm(tr - tl) / case.BW

    def down(p, edge):                            # 60 mm down an edge, at the local scale
        d = np.array([edge[0], 1.0])
        d /= np.linalg.norm(d)
        L = case.BH * sx
        for _ in range(5):
            L = case.BH * sx * (1 + beta * d[1] * L / 2)
        return p + d * L
    H = homography([tl, tr, down(tr, right[:2]), down(tl, left[:2])],
                   [(0, 0), (case.BW, 0), (case.BW, case.BH), (0, case.BH)])
    dp = np.array([apply(H, d[:2]) for d in DOTS])
    u = (dp[-1] - dp[0]) / np.linalg.norm(dp[-1] - dp[0])
    pitch = np.polyfit([d[2] for d in DOTS], (dp - dp[0]) @ u, 1)[0]
    k = 10.0 / pitch                              # the standoff tops' image, shrunk back by this
    on_board = np.array([apply(H, c) for c in rings])
    estimates = {}
    for label, off in (("centre", (0, 0)), ("150 px left", (-150, 0)), ("150 px right", (150, 0)),
                       ("150 px up", (0, -150)), ("150 px down", (0, 150))):
        N = apply(H, CENTRE + off)
        # photo 9 shows the back with y flipped: its top edge is the front view's y = 0
        estimates[f"photo, camera axis {label}"] = [tuple(N + (p - N) * k) for p in on_board]
    estimates["Waveshare's photos"] = WAVESHARE
    from round2 import best_shift
    play = case.SCREW_HOLE_R - 1.25 - 0.075
    worst_d, worst_fit, lines = 0.0, 0.0, []
    for label, est in estimates.items():
        err = [(ex - px, ey - py) for (ex, ey), (px, py) in zip(est, case.POSTS)]
        d = max(math.hypot(*e) for e in err)
        (_, _), off = best_shift(err)
        worst_d, worst_fit = max(worst_d, d), max(worst_fit, off)
        lines.append(f"{label}: " + " ".join(f"({x:.2f}, {y:.2f})" for x, y in est) + f", farthest {d:.2f} mm, "
                     f"screws {off:.2f} mm off centre at best")
    print("  ..   edges: left/right/top line scatter %.2f / %.2f / %.2f px; ruler dots -> standoff tops %.2f %% nearer "
          "the camera" % (left[2], right[2], top[2], 100 * (1 / k - 1)))
    for line in lines:
        print("  ..   " + line)
    report(worst_d <= 0.45 and worst_fit <= play,
           f"standoff estimates ({len(estimates)}): POSTS within {worst_d:.2f} mm of every one (want 0.45); with the "
           f"board placed best, every screw within {worst_fit:.2f} mm of its hole's centre (play {play:.2f})")


# ------------------------------------------------------------------ 2
def clips_as_built():
    import trimesh
    from round1 import load_assembled
    shell, _, cover, z_total = load_assembled("battery")
    p, za, zb, zc, zd = case.clip_levels()
    bad = []
    for x, side in case.CLIPS:
        s = 1 if side == "bottom" else -1             # +1: the wall is at low y
        y_face = -case.CLR + case.SKIRT_CLR if side == "bottom" else case.BH + case.CLR - case.SKIRT_CLR
        y_mid = y_face + s * case.SKIRT_T / 2
        xs = np.linspace(x - case.CLIP_L / 2 + 0.2, x + case.CLIP_L / 2 - 0.2, 45)
        slot = [(xx, y_mid, z) for xx in xs for z in np.linspace(case.Z_SPLIT - case.CLIP_SLOT + 0.08, case.Z_SPLIT - 0.08, 4)]
        beam = [(xx, y_mid, z) for xx in xs for z in np.linspace(case.Z_SPLIT - case.SKIRT_H + 0.1,
                                                                   case.Z_SPLIT - case.CLIP_SLOT - 0.1, 4)]
        in_slot = int(cover.contains(np.array(slot)).sum())
        in_beam = float(cover.contains(np.array(beam)).mean())
        # beam ends: material just past each end of the slot (the anchors)
        anchors = cover.contains(np.array([(x - s0 * (case.CLIP_L / 2 + 0.3), y_mid, case.Z_SPLIT - 0.3) for s0 in (1, -1)]))
        # hook: ray from outside the skirt toward the wall's middle, at the crest
        zc_mid = (zb + zc) / 2
        o = np.array([[x, y_face - s * 3.0, zc_mid]])
        d = np.array([[0, s * 1.0, 0]])
        locs, _, _ = cover.ray.intersects_location(o, d, multiple_hits=True)
        reach = (min(abs(l[1] - o[0][1]) for l in locs) if len(locs) else np.nan)
        hook_tip = o[0][1] + s * reach                # y of the hook's tip
        lid_wall = -case.CLR if side == "bottom" else case.BH + case.CLR
        undercut = s * (lid_wall - hook_tip)
        # groove: ray from the cavity outward into the lid's wall, below its catch face (where the
        # hook's tip goes past the wall while the lid closes), and 2 mm beside the hook
        z_low = (za + case.clip_catch_z(-case.CLR - case.CLIP_UNDERCUT - case.GROOVE_CLR)) / 2
        def wall_depth(xx):
            o2 = np.array([[xx, lid_wall + s * 2.0, z_low]])
            l2, _, _ = shell.ray.intersects_location(o2, -d, multiple_hits=True)
            return min(abs(l[1] - o2[0][1]) for l in l2) - 2.0 if len(l2) else np.nan
        groove, plain = wall_depth(x), wall_depth(x + case.CLIP_HOOK_L / 2 + 2.0)
        tip_room = groove - undercut
        if not (in_slot == 0 and in_beam > 0.99 and anchors.all() and abs(undercut - case.CLIP_UNDERCUT) < 0.02
                and abs(plain) < 0.02 and 0.1 <= tip_room <= 0.3 + 1e-6):
            bad.append((x, side, in_slot, round(in_beam, 2), anchors.tolist(), round(undercut, 3), round(groove, 3),
                        round(plain, 3)))
        print(f"  ..   clip {side} x={x:.0f}: slot points inside plastic {in_slot}/{len(slot)}, beam {100 * in_beam:.0f} % "
              f"solid, anchored at both ends {bool(anchors.all())}; hook {undercut:.2f} mm past the lid's wall, groove "
              f"{groove:.2f} mm deep ({tip_room:.2f} mm beyond the hook; plain wall {plain:+.2f})")
    # preload: the hooks' overlap with the lid, against the designed CLIP_PRELOAD on a 45 deg face
    from round1 import hooks, to_manifold
    over = (to_manifold(shell) ^ hooks()).volume()
    # the lid's catch face lies CLIP_PRELOAD lower than the hook's (both 45 deg); between the lid's wall
    # and the hook's tip (CLIP_UNDERCUT apart) that leaves a strip CLIP_PRELOAD tall, along the hook
    want = len(case.CLIPS) * case.CLIP_PRELOAD * case.CLIP_UNDERCUT * case.CLIP_HOOK_L
    report(not bad and abs(over - want) <= 0.1 * want,
           f"{len(case.CLIPS)} clips read back from the STLs: slots open, beams anchored at both ends, hooks "
           f"{case.CLIP_UNDERCUT} mm past the wall into grooves deep enough; closed, the hooks press the lid {over:.2f} mm3 "
           f"(worked out by hand for the {case.CLIP_PRELOAD} mm preload: {want:.2f}){'; problems: ' + str(bad) if bad else ''}")


# ------------------------------------------------------------------ 3
def extrusions_typed(gcode):
    """{layer z: list of (x0, y0, x1, y1, width, type)} from PrusaSlicer G-code."""
    rel = "\nM83" in gcode
    out, z, x, y, e, w, typ, cur = {}, 0.0, 0.0, 0.0, 0.0, 0.45, "", []
    for line in gcode.splitlines():
        if line.startswith(";Z:"):
            if cur:
                out.setdefault(z, []).extend(cur)
            z, cur = round(float(line[3:]), 3), []
        elif line.startswith(";TYPE:"):
            typ = line[6:].strip()
        elif line.startswith(";WIDTH:"):
            w = float(line[7:])
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
                    cur.append((x, y, nx, ny, w, typ))
            x, y = nx, ny
    if cur:
        out.setdefault(z, []).extend(cur)
    return out


def sliced():
    exe = shutil.which("prusa-slicer")
    if not exe:
        skip("clips and recesses as sliced: PrusaSlicer not installed")
        return
    import trimesh
    from round19 import SETTINGS
    stl = os.path.join(ROOT, "stl", "back_cover_battery.stl")
    tm = trimesh.load(stl)
    lo, hi = tm.bounds
    shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    with tempfile.TemporaryDirectory() as d:
        g = os.path.join(d, "out.gcode")
        subprocess.run([exe, "--export-gcode", *SETTINGS, "--support-material=0", "-o", g, stl],
                       capture_output=True, text=True, timeout=900, check=True)
        ex = extrusions_typed(open(g).read())
    zs = sorted(ex)

    def inside(segs, x0, x1, y0, y1):
        """Extrusion segments with their middle inside the box (design coordinates)."""
        out = []
        for s in segs:
            mx, my = (s[0] + s[2]) / 2 - shift[0], (s[1] + s[3]) / 2 - shift[1]
            if x0 <= mx <= x1 and y0 <= my <= y1:
                out.append(s)
        return out
    # print height: the back face is on the bed; z_print = z_total - z (design)
    slot_lo, slot_hi = z_total - case.Z_SPLIT, z_total - (case.Z_SPLIT - case.CLIP_SLOT)
    bad = []
    for x, side in case.CLIPS:
        yf = -case.CLR + case.SKIRT_CLR
        y0, y1 = (yf + 0.15, yf + case.SKIRT_T - 0.15) if side == "bottom" else \
            (case.BH - yf - case.SKIRT_T + 0.15, case.BH - yf - 0.15)
        box = (x - case.CLIP_L / 2 + 1.0, x + case.CLIP_L / 2 - 1.0, y0, y1)
        in_slot = [z for z in zs if slot_lo + 0.05 < z < slot_hi - 0.05 and inside(ex[z], *box)]
        first = min((z for z in zs if z > slot_hi - 0.05 and inside(ex[z], *box)), default=None)
        types = {s[5] for s in inside(ex[first], *box)} if first else set()
        if in_slot or not ({"Bridge infill", "Overhang perimeter"} & types):
            bad.append((side, x, in_slot, first, sorted(types)))
        print(f"  ..   clip {side} x={x:.0f}: slot layers with plastic in the beam's footprint: {in_slot or 'none'}; first "
              f"layer over the slot (z {first}) printed as {sorted(types)}")
    rec = []
    hole_layers = []
    for px, py in case.POSTS:
        top = z_total - (z_total - case.SCREW_HEAD_DEPTH)            # print height of the recess ceiling
        first = min((z for z in zs if z > top + 0.01 and inside(ex[z], px - 2.0, px + 2.0, py - 2.0, py + 2.0)), default=None)
        ring = inside(ex[first], px - case.SCREW_HEAD_R + 0.3, px + case.SCREW_HEAD_R - 0.3, py - case.SCREW_HEAD_R + 0.3,
                      py + case.SCREW_HEAD_R - 0.3) if first else []
        types = {s[5] for s in ring}
        rec.append((px, py, first, sorted(types)))
        # the slot layer leaves two strips 1.3 mm wide: the slicer prints them as perimeters over air
        # ("Overhang perimeter", with bridge flow) or as bridge infill
        if not types or not ({"Bridge infill", "Overhang perimeter"} & types):
            bad.append(("recess", px, py, first, sorted(types)))
        # nothing inside the screw's own path (r 1.25, plus 0.1) on any layer above the recess
        for z in zs:
            if z > top:
                for s in inside(ex[z], px - 1.35, px + 1.35, py - 1.35, py + 1.35):
                    mx, my = (s[0] + s[2]) / 2 - shift[0], (s[1] + s[3]) / 2 - shift[1]
                    if math.hypot(mx - px, my - py) < 1.25 + 0.1 + s[4] / 2:
                        hole_layers.append((round(px, 1), round(py, 1), z))
    print("  ..   recess ceilings: " + "; ".join(f"({px:.1f}, {py:.1f}) first layer z {f}: {t}" for px, py, f, t in rec))
    report(not bad and not hole_layers,
           f"as sliced (0.2 mm layers): the {len(case.CLIPS)} clip slots stay open and each beam starts as a bridge; the "
           f"{len(case.POSTS)} screw recess ceilings start as bridges; plastic in a screw's path: "
           f"{sorted(set(hole_layers))[:6] or 'none'}{'; problems: ' + str(bad) if bad else ''}")


if __name__ == "__main__":
    standoffs()
    clips_as_built()
    sliced()
    print(f"\nRound 35: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
