#!/usr/bin/env python3
"""Debug round 49 (session 5): methods not used in rounds 1-48.

1. The window with the board anywhere it can sit. Rounds 2, 44 and 45 put the board model in the
   middle of the lid. But the board lies loose in the lid until the screws hold it, and the lid's
   walls let it sit up to CLR (0.3 mm) off centre; the screws' holes allow more, so the walls are the
   limit. The cavity is the PCB outline grown by CLR, so the board can move anywhere in a 0.3 mm
   circle (pushed into a corner it moves 0.3 mm diagonally, not 0.3 each way). With the board at 360
   points round that circle, the window, its rounded corners included (round 58), must still clear
   the light field in your photos (rounds 44 and 45) and the picture area on Waveshare's drawing by
   at least 0.1 mm on every side and at every corner, and still cover the panel's
   tail strip (TAIL_X1) on the left by at least 0.1 mm. The pads in front of the PCB's rim reach
   deeper than the glass's front face, so with the board in any of those positions the glass must
   also keep clear of them, and by more than its outline's measuring error (0.3 mm, the README's
   figure for your photos): cut from the lid's STL at the pads' height, the nearest plastic to the
   glass, moved 0.3 mm each way, must be at least 0.3 mm away.
2. The lid's first layer, its true width. Round 46 measured the band of the lid's front face that
   lies on the bed along lines from the window's centre. At the corners those lines cross the band
   at a slant, so they read it wider than it is. Here every point of the band's inner edge is taken
   in turn, and its distance to the nearest point of the outer edge is the band's width there. It
   must be at least 2.0 mm everywhere.
3. The download zip, file by file: every file in it must be byte for byte the file at the same
   place in the project, it must hold everything the README's Files table says the zip holds, and
   every picture the README shows must be in it, so the README reads the same inside the zip.
4. Every picture the README and the guides show, looked at by me after rounds 47-49 changed the
   connectors and the window (not a script). What it found is in DEBUG_LOG.md.
"""
import contextlib
import io
import math
import os
import re
import sys
import zipfile

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


# ------------------------------------------------------------------ 1
def window_with_play():
    import round45
    with contextlib.redirect_stdout(io.StringIO()):
        round45.across_photos()                     # measures the light field across the board
    fields = {"light field (your photos)": (8.0, 95.2, *round45.LIGHT_Y),
              "drawing's picture area": (9.3, 95.7, 4.1, 55.9)}
    wl, wr = case.WIN_CX - case.WIN_W / 2, case.WIN_CX + case.WIN_W / 2
    wb, wt = case.WIN_CY - case.WIN_H / 2, case.WIN_CY + case.WIN_H / 2
    r, p = case.WIN_R, case.CLR

    def margin(x, y):
        """How far inside the rounded window the point is (round 45's measure)."""
        cx, cy = min(max(x, wl + r), wr - r), min(max(y, wb + r), wt - r)
        if (cx, cy) == (x, y):
            return min(x - wl, wr - x, y - wb, wt - y)
        return r - float(np.hypot(x - cx, y - cy))
    play = [(0.0, 0.0)] + [(p * math.cos(a), p * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 360, endpoint=False)]
    rows, ok = [], True
    for name, (x0, x1, y0, y1) in fields.items():
        worst = {}
        for dx, dy in play:
            m = {"left": x0 + dx - wl, "right": wr - (x1 + dx), "bottom": y0 + dy - wb, "top": wt - (y1 + dy),
                 "corners": min(margin(x + dx, y + dy) for x in (x0, x1) for y in (y0, y1))}
            for k, v in m.items():
                worst[k] = min(worst.get(k, 9.0), v)
        ok &= min(worst.values()) >= 0.1 - 1e-9
        rows.append(f"{name}: " + ", ".join(f"{k} {v:.2f}" for k, v in worst.items()))
    tail = wl - (case.TAIL_X1 + p)
    ok &= tail >= 0.1 - 1e-9
    report(ok, f"window with the board anywhere within {p} mm of centre (360 points round the circle, mm to spare; "
               f"window corners {r} mm round): " + "; ".join(rows) + f"; the panel's tail strip stays {tail:.2f} mm "
               f"under the frame (want 0.1 everywhere)")


def pads_and_glass():
    import trimesh
    from shapely.geometry import Polygon, box as sbox
    from shapely.ops import unary_union
    from round1 import load_assembled
    shell = load_assembled("battery")[0]
    g = case.board_model()["panel"].bounding_box()            # x0, y0, z0, x1, y1, z1
    z = case.Z_PF - case.PAD_GAP - 0.05                       # just short of the pads' faces, inside the glass
    sec = shell.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    planar, tf = sec.to_2D()
    pts = lambda r: trimesh.transform_points(np.column_stack([np.asarray(r.coords), np.zeros(len(r.coords))]), tf)[:, :2]  # noqa: E731
    lid = unary_union([Polygon(pts(p.exterior), [pts(r) for r in p.interiors]) for p in planar.polygons_full])
    p, err = case.CLR, 0.3
    edges = {"left": sbox(g[0] - p - 1e-3, g[1], g[0] - p, g[4]), "right": sbox(g[3] + p, g[1], g[3] + p + 1e-3, g[4]),
             "bottom": sbox(g[0], g[1] - p - 1e-3, g[3], g[1] - p), "top": sbox(g[0], g[4] + p, g[3], g[4] + p + 1e-3)}
    room = {k: e.distance(lid) for k, e in edges.items()}
    report(min(room.values()) >= err - 1e-9 and g[2] < z < g[5],
           f"glass ({g[0]:.2f}-{g[3]:.2f} x {g[1]:.2f}-{g[4]:.2f} mm) with the board {p} mm toward each wall, against "
           f"the lid at the pads' height (z {z:.2f}): nearest plastic " + ", ".join(f"{k} {v:.2f}" for k, v in room.items())
           + f" mm (want {err}, the measuring error)")


# ------------------------------------------------------------------ 2
def true_band():
    import trimesh
    from shapely.geometry import Polygon
    from round1 import load_assembled
    shell, _, _, _ = load_assembled("battery")
    sec = shell.section(plane_origin=[0, 0, 0.05], plane_normal=[0, 0, 1])
    planar, tf = sec.to_2D()
    pts = lambda r: trimesh.transform_points(np.column_stack([np.asarray(r.coords), np.zeros(len(r.coords))]), tf)[:, :2]  # noqa: E731
    polys = [Polygon(pts(p.exterior), [pts(r) for r in p.interiors]) for p in planar.polygons_full]
    if len(polys) != 1 or len(polys[0].interiors) != 1:
        report(False, f"lid's first layer: not one ring ({len(polys)} pieces)")
        return
    inner, outer = polys[0].interiors[0], polys[0].exterior
    d = []
    for t in np.linspace(0, inner.length, 6000, endpoint=False):
        q = inner.interpolate(t)
        d.append((outer.distance(q), q.x, q.y))
    w, x, y = min(d)
    side = {"left": [a for a, px, py in d if px < 20 and 10 < py < 50],
            "right": [a for a, px, py in d if px > 90 and 10 < py < 50],
            "bottom": [a for a, px, py in d if py < 10 and 15 < px < 85],
            "top": [a for a, px, py in d if py > 50 and 15 < px < 85]}
    report(w >= 2.0, f"lid's first layer, true width (nearest outer edge from each of 6000 points on the inner "
                     f"one): narrowest {w:.2f} mm at x {x:.1f}, y {y:.1f}; along the sides "
                     + ", ".join(f"{k} {min(v):.2f}" for k, v in side.items()) + " mm (want 2.0)")


# ------------------------------------------------------------------ 3
def download_zip():
    dist = os.path.join(ROOT, "dist")
    zips = [f for f in os.listdir(dist) if f.endswith(".zip")]
    if len(zips) != 1:
        report(False, f"download zip: {len(zips)} zip files in dist/")
        return
    z = zipfile.ZipFile(os.path.join(dist, zips[0]))
    names = [n for n in z.namelist() if not n.endswith("/")]
    top = {n.split("/", 1)[0] for n in names}
    rel = {n.split("/", 1)[1]: n for n in names if "/" in n}
    differ = [r for r, n in rel.items() if not os.path.exists(os.path.join(ROOT, r))
              or z.read(n) != open(os.path.join(ROOT, r), "rb").read()]
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    shown = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    promised = ["stl/front_shell_battery.stl", "stl/back_cover_battery.stl", "README.md",
                "preview/renders.png", "preview/owner_measurements.png",
                "docs/assembly_guide_en.pdf", "docs/assembly_guide_bg.pdf"]
    missing = sorted(set(promised + shown) - set(rel))
    row = re.search(r"\| `dist/` \| ([^|]*)\|", readme)
    says = row.group(1) if row else ""
    words_ok = all(w in says for w in ("two STL files", "README", "renders", "measurements", "assembly guides"))
    ok = len(top) == 1 and not differ and not missing and words_ok
    report(ok, f"download zip {zips[0]}: {len(rel)} files in one folder, "
               f"{'all byte for byte the project' if not differ else 'differ from the project: ' + str(differ)}'s; "
               f"the README's pictures ({', '.join(shown)}) and everything its Files table lists "
               f"{'are in it' if not missing else 'are not all in it, missing ' + str(missing)}"
               + ("" if words_ok else "; the README's Files table no longer says what the zip holds"))


if __name__ == "__main__":
    window_with_play()
    pads_and_glass()
    true_band()
    download_zip()
    print(f"\nRound 49: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
