#!/usr/bin/env python3
"""Debug round 32 (session 4): methods not used in rounds 1-31.

1. Calipers on the G-code: the bay and the speaker pocket measured on what the slicer will print, not
   on the STL. At mid-height of the guides and brackets, the inner edge of each guide bar and bracket
   leg is where PrusaSlicer's extrusion lines end (line centre plus half the width it writes for that
   line). From those edges the printed bay and pocket must be within 0.15 mm of the design at 0.1, 0.15
   and 0.2 mm layers, and leave the measured battery and speaker 0.3-1.2 mm on every side.
2. The order of the work: the assembly steps of the README and of both guides are read in order, and
   the actions that must come before others must do so: foam on the rings and the plugs in before the
   cover goes on, threads pre-cut before the cover goes on, the cover turned over along the bottom edge
   before it is lowered, and the screws driven only after that.
3. Sound, a textbook estimate: the grille's open area against the membrane (want 25 % or more), and the
   Helmholtz resonance of the small air space in front of the membrane with the slots as its neck
   (want it above the audible range the speaker can play, 12 kHz), so the grille doesn't muffle it.
"""
import json
import math
import os
import re
import shutil
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
def gcode_calipers():
    exe = shutil.which("prusa-slicer")
    if not exe:
        skip("G-code calipers: PrusaSlicer not installed")
        return
    import contextlib
    import io
    import trimesh
    import round28
    from round19 import SETTINGS
    from round30 import extrusions_w
    with contextlib.redirect_stdout(io.StringIO()):
        got = round28.sizes()
    stl = os.path.join(ROOT, "stl", "back_cover_battery.stl")
    tm = trimesh.load(stl)
    lo, hi = tm.bounds
    shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    base = z_total - (case.Z_B + case.CAVITY["battery"])          # inner face, in print height
    x0, x1, y0, y1 = case.BATTERY_BAY
    ym = (y0 + y1) / 2
    sx, sy = case.SPEAKER["battery"]
    pw, ph, _ = case.SPEAKER_BOX["battery"]
    wall, _, leg_x, leg_y = case.SPK_BRACKET

    def edge(segs, win, axis, side):
        """Inner edge of the material in a window (x0, x1, y0, y1 in design coordinates): the largest
        (side +1) or smallest (side -1) coordinate the lines reach, including their half widths."""
        wx0, wx1, wy0, wy1 = win[0] + shift[0], win[1] + shift[0], win[2] + shift[1], win[3] + shift[1]
        m = ((np.minimum(segs[:, 0], segs[:, 2]) >= wx0) & (np.maximum(segs[:, 0], segs[:, 2]) <= wx1)
             & (np.minimum(segs[:, 1], segs[:, 3]) >= wy0) & (np.maximum(segs[:, 1], segs[:, 3]) <= wy1))
        s = segs[m]
        if not len(s):
            return float("nan")
        c = s[:, [axis, axis + 2]]
        if side > 0:
            return float((c.max(1) + s[:, 4] / 2).max()) - shift[axis]
        return float((c.min(1) - s[:, 4] / 2).min()) - shift[axis]

    rows = []
    for lh in (0.1, 0.15, 0.2):
        settings = list(SETTINGS)
        i = settings.index("--layer-height")
        settings[i + 1] = str(lh)
        with tempfile.TemporaryDirectory() as d:
            g = os.path.join(d, "out.gcode")
            subprocess.run([exe, "--export-gcode", *settings, "--support-material=0", "-o", g, stl],
                           capture_output=True, text=True, timeout=900, check=True)
            ex = extrusions_w(open(g).read())
        z = min(ex, key=lambda k: abs(k - (base + 1.0)))           # half way up the 2 mm guides
        segs = ex[z]
        # battery bay: inner faces of the end bars and the long-side bars; each window holds one whole
        # bar (the slicer's lines run its full length) plus 0.4 mm on the bay side
        bars = case.battery_guides()
        lb = next(b for b in bars if b[1] == x0)
        rb = next(b for b in bars if b[0] == x1)
        bb = next(b for b in bars if b[3] == y0)
        tb = next(b for b in bars if b[2] == y1)
        left = edge(segs, (lb[0] - 0.6, lb[1] + 0.4, lb[2] - 0.6, lb[3] + 0.6), 0, +1)
        right = edge(segs, (rb[0] - 0.4, rb[1] + 0.6, rb[2] - 0.6, rb[3] + 0.6), 0, -1)
        bottom = edge(segs, (bb[0] - 0.6, bb[1] + 0.6, bb[2] - 0.6, bb[3] + 0.4), 1, +1)
        top = edge(segs, (tb[0] - 0.6, tb[1] + 0.6, tb[2] - 0.4, tb[3] + 0.6), 1, -1)
        # speaker pocket: inner faces of the legs along the long sides (x) and the short sides (y)
        pl = edge(segs, (sx - pw / 2 - wall - 0.6, sx - pw / 2 + 0.4, sy - ph / 2 - 0.2, sy - ph / 2 + leg_y), 0, +1)
        pr = edge(segs, (sx + pw / 2 - 0.4, sx + pw / 2 + wall + 0.6, sy - ph / 2 - 0.2, sy - ph / 2 + leg_y), 0, -1)
        pb = edge(segs, (sx - pw / 2 - 0.2, sx - pw / 2 + leg_x, sy - ph / 2 - wall - 0.6, sy - ph / 2 + 0.4), 1, +1)
        pt = edge(segs, (sx - pw / 2 - 0.2, sx - pw / 2 + leg_x, sy + ph / 2 - 0.4, sy + ph / 2 + wall + 0.6), 1, -1)
        rows.append((lh, right - left, top - bottom, pr - pl, pt - pb))
    bad = []
    for lh, bl, bw, kw, kl in rows:
        for label, v, want, part in (("bay length", bl, x1 - x0, got["battery length"]),
                                     ("bay width", bw, y1 - y0, got["battery width"]),
                                     ("pocket width", kw, pw, got["speaker width"]),
                                     ("pocket length", kl, ph, got["speaker length"])):
            room = (v - part) / 2
            if not (abs(v - want) <= 0.15 and 0.3 <= room <= 1.2):
                bad.append((lh, label, round(v, 3), round(room, 2)))
    report(not bad, "as sliced (G-code calipers, layer heights 0.1 / 0.15 / 0.2): " + "; ".join(
        f"{lh} mm: bay {bl:.2f} x {bw:.2f}, pocket {kw:.2f} x {kl:.2f}" for lh, bl, bw, kw, kl in rows)
        + f"; outside 0.15 mm of the design or 0.3-1.2 mm room: {bad or 'none'}")


# ------------------------------------------------------------------ 2
def order():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    sect = readme.split("## Assembly", 1)[1].split("## Where the numbers", 1)[0]
    en = json.load(open(os.path.join(ROOT, "docs", "guide-src", "text_en.json"), encoding="utf-8"))
    bg = json.load(open(os.path.join(ROOT, "docs", "guide-src", "text_bg.json"), encoding="utf-8"))
    steps = ("s1", "s2", "s2_warn", "s3", "s4", "s5", "s5_note")
    docs = {"README": sect,
            "EN guide": "\n".join(en[k] for k in steps),
            "BG guide": "\n".join(bg[k] for k in steps)}
    # (action, regex in English, regex in Bulgarian); the list is the order they must appear in
    actions = [
        ("plug in", r"into \*?\*?<?b?>?BAT|Plug the battery into", r"Включете батерията"),
        ("foam on the rings", r"foam tape, about 1\.5", r"лентата от пяна, около 1,5"),
        ("pre-cut the threads", r"[Pp]re-cut the threads", r"нарежете резбите"),
        ("turn the cover over along the bottom edge", r"page of a book", r"страница на книга"),
        ("lower it straight down", r"lower it straight down|lower it <b>straight down", r"спуснете <b>право надолу|право надолу"),
        ("drive in the screws", r"drive in the 4 screws", r"завийте 4-те винта"),
    ]
    problems_here = []
    for doc, text in docs.items():
        pos = []
        for name, rx_en, rx_bg in actions:
            m = re.search(rx_bg if doc == "BG guide" else rx_en, text)
            pos.append((name, m.start() if m else None))
        missing = [n for n, p in pos if p is None]
        found = [(n, p) for n, p in pos if p is not None]
        wrong = [f"{a} after {b}" for (a, pa), (b, pb) in zip(found[1:], found[:-1]) if pa < pb]
        # foam is in its own step in the guides (step 3) and inside step 2 in the README: both before closing
        if missing or wrong:
            problems_here.append(f"{doc}: missing {missing or 'none'}, out of order {wrong or 'none'}")
    report(not problems_here, f"assembly order in the README and both guides (plugs, foam, pre-cut threads, turn over "
                              f"along the bottom edge, lower straight down, screws): {problems_here or 'right in all three'}")


# ------------------------------------------------------------------ 3
def sound():
    import contextlib
    import io
    import round28
    with contextlib.redirect_stdout(io.StringIO()):
        got = round28.sizes()
    # membrane as measured (round 28's perspective transform), slots from case.py
    h = round28.homography(round28.FRAME, [(0, 0), (got["speaker length"], 0),
                                           (got["speaker length"], got["speaker width"]), (0, got["speaker width"])])
    m = np.array([round28.apply(h, p) for p in round28.MEMBRANE])
    ml = (np.linalg.norm(m[1] - m[0]) + np.linalg.norm(m[2] - m[3])) / 2
    mw = (np.linalg.norm(m[3] - m[0]) + np.linalg.norm(m[2] - m[1])) / 2
    membrane = ml * mw
    gw, gl, _ = case.GRILLE_SLOTS
    slot = gw * (gl - gw) + math.pi * gw ** 2 / 4
    area = 3 * slot
    ratio = area / membrane
    # front air space: membrane area times the gap to the cover (gasket + tape, about 0.4 mm), plus the
    # slots themselves; neck: the slots through the 1.8 mm back with an end correction
    c = 343000.0                                   # mm/s
    V = membrane * 0.4 + area * case.T_BACK
    r_eq = math.sqrt(slot / math.pi)
    L_eff = case.T_BACK + 1.7 * r_eq
    f = c / (2 * math.pi) * math.sqrt(area / (V * L_eff))
    report(ratio >= 0.25 and f >= 12000,
           f"grille: {area:.1f} mm2 open over a {ml:.1f} x {mw:.1f} mm membrane ({100 * ratio:.0f} %); front-cavity "
           f"Helmholtz resonance about {f / 1000:.0f} kHz (neck {L_eff:.1f} mm, volume {V:.0f} mm3), above 12 kHz")


if __name__ == "__main__":
    gcode_calipers()
    order()
    sound()
    print(f"\nRound 32: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
