#!/usr/bin/env python3
"""Debug round 58 (session 5): an independent review, and its findings made into checks.

A reviewer who had not built the case (a separate agent, with only the project and the owner's
photos) went through it after round 57. It found nothing that stops the case being printed or put
together, but 5 small mistakes and 3 gaps in the instructions (DEBUG_LOG.md, round 58). Each is
fixed, and each that a script can see is checked here, by methods not used in rounds 1-57:

1. The two screw pictures number the screws the same way. preview/screw_locations.png and the
   guide's step 4 picture are drawn from renders_specs.json and specs.json; their labels must be the
   same four points in the same order, and that order must be a cross (each screw diagonally across
   from the one before it, for the first and the second pair).
2. The USB-C plug the README promises, pushed in with the board anywhere it can sit: the grip size
   the README gives ("up to about W x T mm"), with corners only 1 mm round (sharper than any real
   plug), with 4 mm and with 3 mm standoffs and the board at 36 points round its 0.3 mm play circle
   (round 1 tried it only with the board centred) must not touch the case.
3. The window as printed, against the light field moved round the play circle. Round 49 works from
   case.py's numbers; here the window is cut out of the lid's STL (its section under the outside
   chamfer and in front of the glass relief), and the light field in your photos, moved to 360
   points round the circle, must lie at least 0.1 mm inside it. The window's corner radius is
   measured from the same section (from how far the outline stands off its bounding box's corner)
   and must be the one the README gives.
"""
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def readme():
    return open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()


# ------------------------------------------------------------------ 1
def screw_numbers():
    import json
    g = os.path.join(ROOT, "docs", "guide-src")
    preview = json.load(open(os.path.join(g, "renders_specs.json"), encoding="utf-8"))["r_screws"]["labels"]
    guide = json.load(open(os.path.join(g, "specs.json"), encoding="utf-8"))["step4a"]["labels"]
    same = len(preview) == len(guide) == 4 and all(np.allclose(a, b) for a, b in zip(preview, guide))
    cx, cy = case.BW / 2, case.BH / 2

    def diagonal(a, b):        # b is across the board's centre from a
        return (a[0] - cx) * (b[0] - cx) < 0 and (a[1] - cy) * (b[1] - cy) < 0
    cross = diagonal(guide[0], guide[1]) and diagonal(guide[2], guide[3])
    names = {(True, True): "bottom-right", (False, True): "bottom-left", (True, False): "top-right",
             (False, False): "top-left"}            # as the pictures show them: seen from the back
    order = [names[(p[0] < cx, p[1] < cy)] for p in guide]
    report(same and cross, f"the screw pictures: preview/screw_locations.png and the guide's step 4 number them "
                           f"{'the same way' if same else 'DIFFERENTLY'} ({', '.join(order)}, seen from the back), "
                           f"{'a cross' if cross else 'NOT a cross'}")


# ------------------------------------------------------------------ 2
def usb_plug():
    from round1 import load_assembled, to_manifold
    m = re.search(r"moulded grip is up to about ([\d.]+) x ([\d.]+) mm", readme())
    if not m:
        report(False, "USB-C: the README's grip size not found")
        return
    w, t = float(m.group(1)), float(m.group(2))
    shell, _, cover, _ = load_assembled("battery")
    obstacle = to_manifold(shell) + to_manifold(cover)
    face = -0.4
    p = case.CLR
    play = [(0.0, 0.0)] + [(p * math.cos(a), p * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 36, endpoint=False)]
    worst, n = 0.0, 0
    for dz in (0.0, case.STANDOFF_H - case.STANDOFF_H_MIN):          # 4 mm and 3 mm standoffs
        for dx, dy in play:
            zc = case.Z_B + 1.63 + dz
            over = case.prism(case.rrect(w, t, 1.0, case.USB_Y + dy, zc), face + dx - 25, face + dx).transform(
                [[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])
            v = over ^ obstacle
            worst = max(worst, 0.0 if v.is_empty() else v.volume())
            n += 1
    big = case.prism(case.rrect(13.0, 7.0, 1.0, case.USB_Y + p, case.Z_B + 1.63), face - 25, face).transform(
        [[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]]) ^ obstacle
    big = 0.0 if big.is_empty() else big.volume()
    report(worst < 1e-3, f"USB-C: the README's {w} x {t} mm grip (corners 1 mm round), with 4 and 3 mm standoffs and "
                         f"the board at {n // 2} points of its play: overlaps at most {worst:.3f} mm3 (control: a "
                         f"13 x 7 grip with the board 0.3 mm along the edge overlaps {big:.1f} mm3)")
    if big < 0.01:
        report(False, "USB-C control: the 13 x 7 grip should hit with the board off centre, and doesn't")


# ------------------------------------------------------------------ 3
def window_from_stl():
    import contextlib
    import io

    import round45
    from round1 import load_assembled
    from shapely import affinity
    from shapely.geometry import Point, Polygon, box
    with contextlib.redirect_stdout(io.StringIO()):
        round45.across_photos()
    shell = load_assembled("battery")[0]
    z = (case.WIN_CHAMFER + case.T_FRONT - case.GLASS_RELIEF) / 2        # under the chamfer, in front of the relief
    sec = shell.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    rings = [Polygon(np.asarray(e)[:, :2]) for e in sec.discrete]
    centre = Point(case.WIN_CX, case.WIN_CY)
    holes = [r for r in rings if r.is_valid and r.contains(centre) and r.area < 0.95 * case.BW * case.BH]
    win = min(holes, key=lambda r: r.area)
    x0, y0, x1, y1 = win.bounds
    # corner radius: the outline stands R (sqrt 2 - 1) off its bounding box's corner, along the diagonal
    rs = [win.exterior.distance(Point(x, y)) / (math.sqrt(2) - 1) for x in (x0, x1) for y in (y0, y1)]
    field = box(8.0, round45.LIGHT_Y[0], 95.2, round45.LIGHT_Y[1])
    p = case.CLR
    worst = 9.0
    for a in np.linspace(0, 2 * math.pi, 360, endpoint=False):
        f = affinity.translate(field, p * math.cos(a), p * math.sin(a))
        inside = win.contains(f)
        d = min(win.exterior.distance(Point(c)) for c in f.exterior.coords) if inside else -1.0
        worst = min(worst, d)
    m = re.search(r"the window's corners are rounded only ([\d.]+) mm", readme())
    said = float(m.group(1)) if m else None
    ok = worst >= 0.1 - 1e-6 and said is not None and all(abs(r - said) < 0.03 for r in rs)
    report(ok, f"the window cut from the lid's STL at z {z:.2f}: x {x0:.2f}-{x1:.2f}, y {y0:.2f}-{y1:.2f}, corners "
               f"{min(rs):.2f}-{max(rs):.2f} mm round (README: {said}); the light field, moved to 360 points round the "
               f"{p} mm play circle, stays at least {worst:.3f} mm inside it (want 0.1)")


if __name__ == "__main__":
    screw_numbers()
    usb_plug()
    window_from_stl()
    print("  ..   the review's other findings (wording, the steps it found missing) are fixed in the README and both "
          "guides, and round 37 now looks for the four new steps: see DEBUG_LOG.md, round 58")
    print(f"\nRound 58: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
