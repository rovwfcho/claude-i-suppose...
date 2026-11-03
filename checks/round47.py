#!/usr/bin/env python3
"""Debug round 47 (session 5): methods not used in rounds 1-46.

1. The guide's steps 2 and 3, done to the STL files as printed. Both parts come off the printer inside
   up, as step 2 lays them. Their ends and edges are found on the meshes themselves, not from case.py:
   the lid's dial notch (the shorter of the two gaps in its long walls; the PWR/BOOT opening is the
   longer), the cover's dial tab (the only solid stretch on a long wall's centre line above its rim),
   and each part's USB-C end (the lid's widest gap in a short wall; the cover's skirt cut-out).
   Step 2: the cover is turned in the table's plane until its tab is away from you, and the README's
   "the USB-C end is on your left" must then hold; the lid is turned until its dial notch is toward
   you, and laid just in front, the two bottom edges together and the ends lined up. Only turns in the
   table's plane are allowed (a printed part can't be mirrored). Step 3: the cover is turned over like
   a page about the shared bottom edge and lowered straight down. It must land exactly where the
   assembled case has it relative to the lid (the STLs put back together the way round 1 does), with
   the same overlap with the lid as there (the hooks' preload, nothing else). As a control, the same
   motions with the lid's dial notch away from you must not close.
2. The wires with the parts laid open as step 2 says, before the page turn: the battery is plugged
   into BAT and the speaker into SPK while the board lies face down in the lid, in front of the cover.
   Each wire's shortest path, from where it leaves its part on the cover, over the cover's skirt and
   both rims, to its connector on the board (the board resting on the lid's pads), must be at least
   5 mm shorter than the wire measured in your photo (round 30). The path is found in the plane across
   the shared edge (the upper hull over the rims and the skirt) and unrolled along the edge.
3. The BAT, RTC and SPK headers in your back photo (photo 9): each white housing's edges are found as
   the strongest brightness steps near a starting guess (its sides along rows through its middle, its
   ends along a column), and mapped onto the board's plane with round 35's homography, pulled toward
   the camera's axis for their 3 mm height. The board model's headers must contain each housing, at
   most 0.6 mm larger, and the plugs' faces must be inside the modelled plugs.
"""
import contextlib
import io
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


def gaps(mesh, line, z, step=0.25):
    """Length of the stretches of `line` (a list of (x, y)) at height z that are not inside the mesh."""
    pts = np.array([(x, y, z) for x, y in line])
    return float((~mesh.contains(pts)).sum() * step)


# ------------------------------------------------------------------ 1
def page_turn():
    import trimesh
    from manifold3d import Manifold, Mesh
    from round1 import load_assembled, vol
    lid = trimesh.load(os.path.join(ROOT, "stl", "front_shell_battery.stl"))
    cov = trimesh.load(os.path.join(ROOT, "stl", "back_cover_battery.stl"))
    (lx0, ly0, _), (lx1, ly1, lz1) = lid.bounds
    (cx0, cy0, _), (cx1, cy1, cz1) = cov.bounds
    w = case.WALL / 2                                     # the walls' centre lines
    xs = lambda a, b: np.arange(a + 3, b - 3, 0.25)       # noqa: E731
    # the lid: its long walls' gaps, and its short walls' gaps, at mid-height
    zl = lz1 / 2
    lid_lo = gaps(lid, [(x, ly0 + w) for x in xs(lx0, lx1)], zl)
    lid_hi = gaps(lid, [(x, ly1 - w) for x in xs(lx0, lx1)], zl)
    notch_side = "hi" if lid_hi < lid_lo else "lo"        # the dial notch is the shorter gap
    lid_xlo = gaps(lid, [(lx0 + w, y) for y in xs(ly0, ly1)], zl)
    lid_xhi = gaps(lid, [(lx1 - w, y) for y in xs(ly0, ly1)], zl)
    lid_usb = "hi" if lid_xhi > lid_xlo else "lo"
    # the cover, above its rim: the wall's centre line is solid only where the dial tab is; the USB-C
    # end is where the skirt is cut away
    zc = (cz1 + (case.Z_B + case.CAVITY["battery"] + case.T_BACK - case.Z_SPLIT)) / 2
    tab_lo = len(xs(cx0, cx1)) * 0.25 - gaps(cov, [(x, cy0 + w) for x in xs(cx0, cx1)], zc)
    tab_hi = len(xs(cx0, cx1)) * 0.25 - gaps(cov, [(x, cy1 - w) for x in xs(cx0, cx1)], zc)
    tab_side = "hi" if tab_hi > tab_lo else "lo"
    sk = case.WALL + case.SKIRT_CLR + case.SKIRT_T / 2   # the skirt's centre line, from the outside
    cov_xlo = gaps(cov, [(cx0 + sk, y) for y in xs(cy0, cy1)], zc)
    cov_xhi = gaps(cov, [(cx1 - sk, y) for y in xs(cy0, cy1)], zc)
    cov_usb = "lo" if cov_xlo > cov_xhi else "hi"
    print(f"  ..   found on the meshes: lid wall gaps {lid_lo:.1f} / {lid_hi:.1f} mm (dial notch on its y-{notch_side} "
          f"side), short-wall gaps {lid_xlo:.1f} / {lid_xhi:.1f} mm (USB-C end x-{lid_usb}); cover tab "
          f"{tab_lo:.1f} / {tab_hi:.1f} mm of wall (y-{tab_side}), skirt cut-outs {cov_xlo:.1f} / {cov_xhi:.1f} mm "
          f"(USB-C end x-{cov_usb})")

    def turn_z(flip, x0, x1, y0, y1):
        """A turn in the table's plane: 0 or 180 degrees, about the part's own centre."""
        if not flip:
            return np.eye(4)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return np.array([[-1, 0, 0, 2 * cx], [0, -1, 0, 2 * cy], [0, 0, 1, 0], [0, 0, 0, 1.0]])

    # step 2: the cover's tab away from you (+y)
    Tc = turn_z(tab_side == "lo", cx0, cx1, cy0, cy1)
    usb_c_left = (cov_usb == "lo") != (tab_side == "lo")
    # the lid's dial notch toward you (-y), the lid in front, bottom edges together, ends lined up
    results = {}
    shell, _, cover_asm, z_total = load_assembled("battery")

    def mf(tm):
        return Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    true_overlap = vol(mf(shell) ^ mf(cover_asm))
    for label, notch_toward_you in (("as the guide says", True), ("control: dial notch away from you", False)):
        flip = (notch_side == "hi") == notch_toward_you
        Tl = turn_z(flip, lx0, lx1, ly0, ly1)
        L = lid.copy()
        L.apply_transform(Tl)
        C = cov.copy()
        C.apply_transform(Tc)
        (a0, b0, _), (a1, b1, _) = L.bounds
        (c0, d0, _), (c1, d1, _) = C.bounds
        L.apply_translation([c0 - a0, d0 - b1, 0])          # in front: its far edge on the cover's near edge
        usb_l_left = (lid_usb == "lo") != flip
        # step 3: turn the cover over like a page about the shared edge (y = d0, on the table), then
        # lower it straight down until its rim (the parting plane) is on the lid's
        rim_c = z_total - case.Z_SPLIT
        page = np.array([[1, 0, 0, 0], [0, -1, 0, 2 * d0], [0, 0, -1, 0], [0, 0, 0, 1.0]])
        C.apply_transform(page)
        C.apply_translation([0, 0, L.bounds[1][2] + rim_c])
        # where the assembled case has the cover: round 1's assembly, carried into the lid's pose
        Ltrue = shell.copy()
        Ltrue.apply_transform(np.diag([-1, 1, 1, 1]))
        Ltrue.apply_translation([case.BW, 0, 0])          # back into the lid STL's frame (it is mirrored)
        Ctrue = cover_asm.copy()
        Ctrue.apply_transform(np.diag([-1, 1, 1, 1]))
        Ctrue.apply_translation([case.BW, 0, 0])
        for m in (Ltrue, Ctrue):
            m.apply_transform(Tl)
            m.apply_translation([c0 - a0, d0 - b1, 0])
        # the lid put back from round 1's assembly is the lid as laid out (a check of this check)
        lid_off = float(np.abs(Ltrue.vertices - L.vertices).max())
        # the turned cover against the assembled one: the same vertices, in the same order
        off = max(float(np.abs(C.vertices - Ctrue.vertices).max()), lid_off)
        overlap = vol(mf(L) ^ mf(C))
        results[label] = (usb_l_left, off, overlap)
    ok_l, off, ov = results["as the guide says"]
    _, off_c, ov_c = results["control: dial notch away from you"]
    ok = (usb_c_left and ok_l and off < 0.01 and abs(ov - true_overlap) < 0.05 and (off_c > 1.0 and ov_c > 10 * true_overlap + 1))
    report(ok, f"steps 2-3 done to the STLs: cover tab away from you -> its USB-C end on the "
               f"{'left' if usb_c_left else 'RIGHT'}; lid dial notch toward you -> its USB-C end on the "
               f"{'left' if ok_l else 'RIGHT'}; after the page turn the cover lands {off:.4f} mm from its assembled place, "
               f"overlapping the lid by {ov:.2f} mm3 (assembled: {true_overlap:.2f}, the hooks' preload); control with the "
               f"notch away: {off_c:.1f} mm off, {ov_c:.0f} mm3 of overlap")


# ------------------------------------------------------------------ 2
def upper_hull(pts):
    """Upper convex chain from the first point to the last (points sorted by s)."""
    pts = sorted(pts)
    out = []
    for p in pts:
        while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (p[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0]) >= 0:
            out.pop()
        out.append(p)
    return out


def open_reach():
    import round30
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        round30.cable_lengths()
    out = buf.getvalue()
    lb = float(re.search(r"battery wire (\d+) mm", out).group(1))
    ls = float(re.search(r"speaker cable (\d+) mm", out).group(1))
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    Y0 = -case.CLR - case.WALL
    rest = case.PAD_GAP                                   # the board lies on the pads, this much forward
    yf = -case.CLR + case.SKIRT_CLR
    # obstacles across the shared edge, as (s, height): s < 0 in the lid (face down, height = z),
    # s > 0 in the cover (back down, height = z_total - z); s = distance from the shared edge
    corners = [(-(-case.CLR - Y0), case.Z_SPLIT), (0.0, case.Z_SPLIT),                      # lid's wall
               (0.0, z_total - case.Z_SPLIT), (case.WALL, z_total - case.Z_SPLIT),           # cover's rim
               (yf - Y0, z_total - (case.Z_SPLIT - case.SKIRT_H)),                            # cover's skirt
               (yf + case.SKIRT_T - Y0, z_total - (case.Z_SPLIT - case.SKIRT_H))]
    rows, ok = [], True
    for label, (pts, r), have in (("battery wire", case.battery_wire_route(), lb),
                                  ("speaker cable", case.speaker_wire_route(), ls)):
        bx, by, bz = pts[0]                               # where it leaves its part, on the cover
        px, py, pz = pts[-1]                              # in front of its connector, on the board
        P = (-(py - Y0), pz - rest)
        B = (by - Y0, z_total - bz)
        chain = upper_hull([P, B] + corners)
        plane = sum(np.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(chain, chain[1:]))
        need = float(np.hypot(plane, px - bx))
        rows.append(f"{label} needs {need:.0f} mm (has {have:.0f})")
        ok &= need <= have - 5
    report(ok, "wires with the parts laid open as step 2 says (board face down in the lid, the lid in front of the "
               "cover): " + "; ".join(rows) + " (want 5 mm to spare)")


# ------------------------------------------------------------------ 3
GUESS = {"BAT": (496.7, 618.3), "RTC": (656.7, 778.3), "SPK": (815.0, 936.7)}   # housing sides, crop px


def headers():
    import round35 as r
    from PIL import Image
    from scipy import ndimage as ndi
    ph = r.Photo()
    left = r.fit_line(ph.edge("x", list(range(448, 494, 3)) + list(range(612, 732, 3)), 244), "x")
    right = r.fit_line(ph.edge("x", list(range(232, 340, 3)) + list(range(380, 700, 4)), 1618), "x")
    top = r.fit_line(ph.edge("y", list(range(420, 560, 4)) + list(range(680, 1240, 4)) + list(range(1300, 1500, 4)), 146), "y")
    tl, tr = r.cross(left[:2], top[:2]), r.cross(right[:2], top[:2])
    rings = np.array([ph.ring(c) for c in r.RINGS])
    beta = (np.linalg.norm(rings[3] - rings[2]) / np.linalg.norm(rings[1] - rings[0]) - 1) \
        / (rings[2:, 1].mean() - rings[:2, 1].mean())
    sx = np.linalg.norm(tr - tl) / case.BW

    def down(p, edge):
        d = np.array([edge[0], 1.0])
        d /= np.linalg.norm(d)
        L = case.BH * sx
        for _ in range(5):
            L = case.BH * sx * (1 + beta * d[1] * L / 2)
        return p + d * L
    H = r.homography([tl, tr, down(tr, right[:2]), down(tl, left[:2])],
                     [(0, 0), (case.BW, 0), (case.BW, case.BH), (0, case.BH)])
    ox, oy = r.OFFSET
    N = r.apply(H, r.CENTRE)
    k = 1 - 3.0 / 300.0                    # their tops about 3 mm nearer a camera about 300 mm away (round 35)
    to_mm = lambda x, y: N + (r.apply(H, (x + ox, y + oy)) - N) * k   # noqa: E731
    g = ndi.gaussian_filter(np.asarray(Image.open(os.path.join(HERE, "owner_photos", "board_back.jpg")).convert("L"))
                            .astype(float), 1.0)
    d = np.diff(g[120:150].mean(0))
    rows, bad = [], []
    for name, (x0, x1) in GUESS.items():
        i0 = int(x0) - 8 + int(np.argmax(d[int(x0) - 8:int(x0) + 8])) + 0.5      # dark board -> white housing
        i1 = int(x1) - 8 + int(np.argmin(d[int(x1) - 8:int(x1) + 8])) + 0.5
        cx = (i0 + i1) / 2
        dc = np.diff(g[80:200, int(cx) - 20:int(cx) - 10].mean(1))
        j0 = 90 + int(np.argmax(dc[10:35])) + 0.5
        j1 = 160 + int(np.argmin(dc[80:115])) + 0.5
        (mx0, my0), (mx1, my1) = to_mm(i0, j0), to_mm(i1, j1)
        hx0, hx1 = case.HEADERS[name]
        hy1 = case.PLUG_Y1 if name != "RTC" else case.HEADER_Y[1]
        inside = hx0 <= mx0 and mx1 <= hx1 and case.HEADER_Y[0] <= my0 and my1 <= hy1
        snug = (mx0 - hx0) <= 0.6 and (hx1 - mx1) <= 0.6 and (my0 - case.HEADER_Y[0]) <= 0.6 and (hy1 - my1) <= 0.6
        if not (inside and snug):
            bad.append(name)
        rows.append(f"{name} x {mx0:.1f}-{mx1:.1f}, y {my0:.1f}-{my1:.1f} (model {hx0}-{hx1}, {case.HEADER_Y[0]}-{hy1})")
    report(not bad, "headers in your back photo (BAT and SPK with their plugs in, to the plug's face): "
                    + "; ".join(rows) + (f"; not matched: {bad}" if bad else ""))


if __name__ == "__main__":
    page_turn()
    open_reach()
    headers()
    print(f"\nRound 47: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
