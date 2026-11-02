#!/usr/bin/env python3
"""Debug round 30 (session 4): methods not used in rounds 1-29.

1. The speaker instruction, by handedness: in your top view of the speaker (photo 8) the sound face
   looks at the camera; the sign of (peg direction x cable direction) there is a property of the part.
   Carried into the case (sound face toward the back, peg toward the top edge), it must put the cable
   on the battery's side, as the README and the guides say, and as the cable route in case.py assumes.
2. Cable lengths from your photo: the battery wire and the speaker cable are traced in photo 8 and
   measured through a perspective transform from the four standoff tops. Each must be longer than its
   route in case.py plus 5 mm of slack, and the speaker cable's spare must fit the loop above the
   speaker (or 10 mm more, tucked along the route).
3. The thin new features in the slicer's output: at 0.1, 0.15 and 0.2 mm layers, PrusaSlicer's
   extrusion lines must cover at least 85 % of every battery guide bar and speaker bracket on each of
   their layers, and must reach to within one layer of their tops (a dropped or half-printed guide
   would show here).
4. The documentation rebuilt from a clean clone: docs/guide-src/build_all.sh runs in a fresh clone of
   the last commit; its preview/renders.png must be pixel-identical to the committed one, and its two
   guides must have the same pages and text as the committed PDFs.
"""
import contextlib
import io
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile

import numpy as np

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
def handedness():
    import round28
    c = np.mean(round28.FRAME, axis=0)
    peg = np.subtract(round28.PEG, c)
    cab = np.subtract(round28.CABLE, c)
    # image axes: x right, y down, z into the picture (right-handed); the sound face's outward normal
    # points at the camera, i.e. -z. So (peg x cable) . normal = -(2-D cross product).
    photo = -(peg[0] * cab[1] - peg[1] * cab[0])
    # in the case (real space seen from the display: x right, y up, z toward you) the sound face points
    # at the back cover (-z) and the peg points up (+y). The cable must then point along d with
    # (y x d) . (-z) having the same sign as in the photo.
    candidates = {"toward the battery (-x)": np.array([-1.0, 0, 0]), "toward the antenna (+x)": np.array([1.0, 0, 0])}
    n = np.array([0, 0, -1.0])
    side = [k for k, d in candidates.items() if np.sign(np.dot(np.cross([0, 1.0, 0], d), n)) == np.sign(photo)]
    pts, _ = case.speaker_wire_route()
    route_left = pts[0][0] < case.SPEAKER["battery"][0]
    readme = open(os.path.join(ROOT, "README.md")).read()
    says = "with its white peg pointing to the top edge" in readme and "comes out on the side facing the battery" in readme
    report(side == ["toward the battery (-x)"] and route_left and says,
           f"speaker handedness from photo 8: (peg x cable) . face normal = {photo:+.0f} px2, so with the sound "
           f"face to the back and the peg up, the cable points {side[0] if side else '?'}; case.py's route leaves "
           f"on the battery side: {route_left}; the README says so: {says}")


# ------------------------------------------------------------------ 2
# photo 8, full-photo px: the four brass standoff tops (circle centres from 8x zooms) and the two cables,
# traced from the plug's exit to where the wire enters the battery's tape / the speaker
STANDOFF_TOPS_8 = {(310.3, 340.0): case.POSTS[0], (1209.5, 320.5): case.POSTS[1],
                   (335.0, 859.5): case.POSTS[2], (1214.0, 840.5): case.POSTS[3]}
BATTERY_WIRE_8 = [(597.5, 387.5), (600, 445), (615, 495), (640, 545), (665, 600), (682.5, 645), (685, 695),
                  (675, 745), (662.5, 795), (652.5, 845), (647.5, 880)]
SPEAKER_CABLE_8 = [(825, 382.5), (835, 430), (860, 470), (900, 515), (950, 550), (995, 575), (1040, 590),
                   (1110, 580), (1185, 560), (1240, 530), (1310, 495), (1385, 455), (1460, 415), (1535, 375),
                   (1565, 355), (1585, 335), (1605, 322), (1607, 303)]


def cable_lengths():
    import round28
    import round13
    src = list(STANDOFF_TOPS_8)
    h = round28.homography(src, [STANDOFF_TOPS_8[k] for k in src])

    def length(poly):
        q = np.array([round28.apply(h, p) for p in poly])
        return float(np.linalg.norm(np.diff(q, axis=0), axis=1).sum())
    lb, ls = length(BATTERY_WIRE_8), length(SPEAKER_CABLE_8)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        round13.wires()
    out = buf.getvalue()
    rb, rs = (int(v) for v in re.findall(r"about (\d+) mm long", out)[:2])
    loop = int(re.search(r"holds about (\d+) mm of cable", out).group(1))
    spare = ls - rs
    report(lb >= rb + 5 and ls >= rs + 5 and spare <= loop + 10,
           f"cables traced in photo 8: battery wire {lb:.0f} mm for a {rb} mm route; speaker cable {ls:.0f} mm for a "
           f"{rs} mm route, {spare:.0f} mm spare for a loop that holds {loop} mm")
    with open(os.path.join(ROOT, "README.md")) as f:
        readme = f.read()
    m = re.search(r"room for about (\d+) cm", readme)
    report(m is not None and abs(int(m.group(1)) * 10 - loop) <= 10,
           f"README gives the loop's room as {m.group(0) if m else 'nothing'}; it holds {loop} mm")


# ------------------------------------------------------------------ 3
def extrusions_w(gcode):
    """{layer z: array of [x0, y0, x1, y1, line width]} from PrusaSlicer G-code (its ;WIDTH: notes)."""
    rel = "\nM83" in gcode
    out, z, x, y, e, w, cur = {}, 0.0, 0.0, 0.0, 0.0, 0.45, []
    for line in gcode.splitlines():
        if line.startswith(";Z:"):
            if cur:
                out.setdefault(z, []).extend(cur)
            z, cur = round(float(line[3:]), 3), []
        elif line.startswith(";WIDTH:"):
            w = float(line[7:])
        elif line.startswith("G92") and " E" in line:
            e = 0.0
        elif line.startswith(("G1 ", "G0 ")):
            p = dict((m[0], float(m[1:])) for m in line.split(";")[0].split()[1:] if m[0] in "XYZE")
            nx, ny = p.get("X", x), p.get("Y", y)
            if "E" in p:
                de = p["E"] if rel else p["E"] - e
                if not rel:
                    e = p["E"]
                if de > 0 and (nx, ny) != (x, y):
                    cur.append((x, y, nx, ny, w))
            x, y = nx, ny
    if cur:
        out.setdefault(z, []).extend(cur)
    return {k: np.array(v) for k, v in out.items()}


def thin_features():
    exe = shutil.which("prusa-slicer")
    if not exe:
        skip("thin features in G-code: PrusaSlicer not installed")
        return
    import trimesh
    from shapely import affinity
    from shapely.geometry import LineString, box as sbox
    from shapely.ops import unary_union
    from round19 import SETTINGS
    stl = os.path.join(ROOT, "stl", "back_cover_battery.stl")
    tm = trimesh.load(stl)
    lo, hi = tm.bounds
    shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    base = z_total - (case.Z_B + case.CAVITY["battery"])          # the inner face, in print height
    feats = [("guide", sbox(b[0], b[2], b[1], b[3]), case.BATTERY_GUIDE[1]) for b in case.battery_guides()]
    br = case.speaker_brackets()                                  # two boxes per corner make one L
    feats += [("bracket", sbox(br[k][0], br[k][2], br[k][1], br[k][3]).union(
        sbox(br[k + 1][0], br[k + 1][2], br[k + 1][1], br[k + 1][3])), case.SPK_BRACKET[1]) for k in range(0, len(br), 2)]
    worst = []
    for lh in (0.1, 0.15, 0.2):
        settings = list(SETTINGS)
        i = settings.index("--layer-height")
        settings[i + 1] = str(lh)
        with tempfile.TemporaryDirectory() as d:
            g = os.path.join(d, "out.gcode")
            subprocess.run([exe, "--export-gcode", *settings, "--support-material=0", "-o", g, stl],
                           capture_output=True, text=True, timeout=900, check=True)
            ex = extrusions_w(open(g).read())
        layers = sorted(ex)
        for kind, shape, height in feats:
            fp = affinity.translate(shape, shift[0], shift[1])
            bx = fp.bounds
            top = base + height
            mids = [z for z in layers if base + 1.5 * lh < z <= top + 1e-6]
            covers = []
            for z in mids:
                segs = ex[z]
                near = segs[(np.maximum(segs[:, 0], segs[:, 2]) >= bx[0] - 1) & (np.minimum(segs[:, 0], segs[:, 2]) <= bx[2] + 1)
                            & (np.maximum(segs[:, 1], segs[:, 3]) >= bx[1] - 1) & (np.minimum(segs[:, 1], segs[:, 3]) <= bx[3] + 1)]
                # each line as wide as the slicer made it, with round ends like a real bead of plastic
                lines = [LineString([(a, b), (c, e)]).buffer(w / 2) for a, b, c, e, w in near if (a, b) != (c, e)]
                covers.append(unary_union(lines).intersection(fp).area / fp.area if lines else 0.0)
            printed = [z for z, cv in zip(mids, covers) if cv > 0.3]
            reach = max(printed) if printed else base
            worst.append((min(covers) if covers else 0.0, top - reach, lh, kind, round(bx[0] - shift[0], 1),
                          round(bx[1] - shift[1], 1)))
    low = [w for w in worst if w[0] < 0.85 or w[1] > max(w[2], 0.2) + 1e-6]
    mc = min(w[0] for w in worst)
    mr = max(w[1] for w in worst)
    report(not low, f"{len(worst) // 3} guide bars and L brackets at 0.1 / 0.15 / 0.2 mm layers: the slicer's lines cover at "
                    f"least {100 * mc:.0f} % of every layer and reach within {max(mr, 0):.2f} mm of the tops; short: {low[:4] or 'none'}")


# ------------------------------------------------------------------ 4
def clean_docs():
    node = shutil.which("node")
    if not node or subprocess.run([node, "-e", "require('playwright')"], capture_output=True).returncode != 0:
        skip("clean-clone documentation build: node with playwright is not installed")
        return
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8766)) == 0:
            skip("clean-clone documentation build: port 8766 is busy")
            return
    if not shutil.which("pdftotext"):
        skip("clean-clone documentation build: pdftotext is not installed")
        return
    top = subprocess.run(["git", "-C", ROOT, "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                         check=True).stdout.strip()
    sub = os.path.relpath(ROOT, top)
    from PIL import Image, ImageChops
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", top, os.path.join(d, "repo")], check=True)
        proj = os.path.join(d, "repo", sub)
        r = subprocess.run(["sh", os.path.join(proj, "docs", "guide-src", "build_all.sh")], capture_output=True,
                           text=True, timeout=1800)
        if r.returncode != 0:
            report(False, f"clean-clone documentation build failed: {(r.stdout + r.stderr)[-400:]}")
            return
        a = Image.open(os.path.join(proj, "preview", "renders.png")).convert("RGB")
        b = Image.open(os.path.join(ROOT, "preview", "renders.png")).convert("RGB")
        same_png = a.size == b.size and ImageChops.difference(a, b).getbbox() is None
        texts = []
        for lang in ("en", "bg"):
            got = subprocess.run(["pdftotext", "-layout", os.path.join(proj, "docs", f"assembly_guide_{lang}.pdf"), "-"],
                                 capture_output=True, text=True).stdout
            have = subprocess.run(["pdftotext", "-layout", os.path.join(ROOT, "docs", f"assembly_guide_{lang}.pdf"), "-"],
                                  capture_output=True, text=True).stdout
            texts.append((lang, got == have, got.count("\f"), have.count("\f")))
        ok = same_png and all(t[1] and t[2] == t[3] for t in texts)
        report(ok, f"clean clone rebuilds the docs: renders.png pixel-identical {same_png}; guides "
                   f"{[(t[0], 'same text' if t[1] else 'TEXT DIFFERS', f'{t[2]} pages') for t in texts]}")


if __name__ == "__main__":
    handedness()
    cable_lengths()
    thin_features()
    clean_docs()
    print(f"\nRound 30: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
