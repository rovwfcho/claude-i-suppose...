#!/usr/bin/env python3
"""Debug round 34 (session 4): methods not used in rounds 1-33.

1. Volume accounting against session 3: the back cover's volume change since session 3's cover (read
   from git) must equal, to 0.5 mm3, what the session-4 features add and remove, worked out by hand
   from their sizes: the new guide bars and speaker brackets added, the three slots cut out, session
   3's guide bars removed and its 28 round grille holes filled in. The screw blocks are left out of
   both (their pilots grew from 1.7 to 1.8 mm). Any change nobody intended would show up as a
   difference.
2. Pictures and the text that points at them: in both guides every picture's markers must all be
   explained in its legend, and every legend entry must have a marker; where the text sends you to a
   marker ("marked 3 in the picture above"), that marker's legend must be about the same thing.
3. Is the measured battery plausible? 1500 mAh at 3.7 V in the measured 61.1 x 40.7 x 4.3 mm is an
   energy density that must fall in the range LiPo pouch cells actually have (300-750 Wh/L); a
   misread thickness or width would show up as an impossible cell.
"""
import contextlib
import io
import json
import math
import os
import re
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


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
def ngon_area(r, n):
    return n / 2 * r * r * math.sin(2 * math.pi / n)


def stadium_area(w, length, n=case.SEG):
    """Area of slot_z's stadium: rrect(w, length, r - 1e-3) with r = w / 2 (a rounded rectangle whose
    round corners are SEG-gons)."""
    r = w / 2 - 1e-3
    core = (w - 2 * r) * (length - 2 * r)
    sides = 2 * r * (w - 2 * r) + 2 * r * (length - 2 * r)
    return core + sides + ngon_area(r, n)


def volume_accounting():
    import trimesh
    from round1 import to_manifold
    old = subprocess.run(["git", "-C", ROOT, "show", "01545f9:stl/back_cover_battery.stl"], capture_output=True)
    if old.returncode != 0 or not old.stdout:
        report(False, "volume accounting: session 3's back cover could not be read from git")
        return
    with tempfile.NamedTemporaryFile(suffix=".stl") as f:
        f.write(old.stdout)
        f.flush()
        tm_old = trimesh.load(f.name)
    tm_new = trimesh.load(os.path.join(ROOT, "stl", "back_cover_battery.stl"))
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    # both are printable STLs (outside face down); put them back in the design frame
    def asm(tm):
        t = tm.copy()
        t.apply_transform(np.diag([1, 1, -1, 1]))
        t.apply_translation([0, 0, z_total])
        return to_manifold(t)
    A, B = asm(tm_old), asm(tm_new)
    blocks = None
    for pos, side in case.SCREWS:                      # leave the screw blocks (and their pilots) out
        p, d, wall = case.screw_frame(pos, side)
        if side == "right":
            b = case.box(case.BW - 8, case.X1 + 1, pos - 3, pos + 3, -1, z_total + 1)
        elif side == "bottom":
            b = case.box(pos - 3, pos + 3, case.Y0 - 1, 8, -1, z_total + 1)
        else:
            b = case.box(pos - 3, pos + 3, case.BH - 8, case.Y1 + 1, -1, z_total + 1)
        blocks = b if blocks is None else blocks + b
    dv = (B - blocks).volume() - (A - blocks).volume()
    z_in = z_total - case.T_BACK
    # what session 4 added and removed (all prisms; heights above the inside face of the back)
    new_guides = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in case.battery_guides()) * case.BATTERY_GUIDE[1]
    from shapely.geometry import box as sbox
    from shapely.ops import unary_union
    brackets = unary_union([sbox(x0, y0, x1, y1) for x0, x1, y0, y1 in case.speaker_brackets()]).area * case.SPK_BRACKET[1]
    gw, gl, _ = case.GRILLE_SLOTS
    slots = 3 * stadium_area(gw, gl) * case.T_BACK
    # session 3: guide bars 1.2 x 12 (ends) and 20 x 1.2 (sides), 1.5 mm tall, round the 5.5-71.5 x 6-50 bay
    old_guides = (2 * 1.2 * 12.0 + 2 * 20.0 * 1.2) * 1.5
    # session 3: round holes r 0.8 (24-gons) on a hex grid inside a 6.0 x 8.6 ellipse round (80, 15.5)
    n_holes = sum(1 for j, yy in enumerate(np.arange(-7.9, 8.0, 2.25))
                  for xx in np.arange(-7.8 + (1.3 if j % 2 else 0.0), 7.9, 2.6)
                  if (xx / 6.0) ** 2 + (yy / 8.6) ** 2 <= 1.0)
    old_holes = n_holes * ngon_area(0.8, 24) * case.T_BACK
    expect = new_guides + brackets - slots - old_guides + old_holes
    report(abs(dv - expect) < 0.5,
           f"back cover volume since session 3 (screw blocks left out): {dv:+.2f} mm3; worked out by hand "
           f"{expect:+.2f} mm3 (guides +{new_guides:.1f}, brackets +{brackets:.1f}, slots -{slots:.1f}, "
           f"old guides -{old_guides:.1f}, {n_holes} old holes filled +{old_holes:.1f})")


# ------------------------------------------------------------------ 2
def figures():
    g = os.path.join(ROOT, "docs", "guide-src")
    build = open(os.path.join(g, "build.py")).read()
    specs = json.load(open(os.path.join(g, "specs.json")))
    calls = re.findall(r"figure\('(\w+)', T\['(\w+)'\](?:, marks=\[([^\]]*)\])?", build)
    calls += [(n, leg, m) for n, leg, m in re.findall(r'figure\("(\w+)", T\["(\w+)"\], marks=\[([^\]]*)\]', build)]
    bad = []
    for lang in ("en", "bg"):
        T = json.load(open(os.path.join(g, f"text_{lang}.json"), encoding="utf-8"))
        for name, legend, marks in calls:
            n = len(specs[name]["labels"])
            mk = re.findall(r"'(\d+)'|\"(\d+)\"", marks) if marks else []
            mk = [a or b for a, b in mk] if mk else [str(i + 1) for i in range(n)]
            if len(mk) != n:
                bad.append(f"{lang} {name}: {len(mk)} marks for {n} markers")
            leg = {k for k, _ in T[legend]}
            if set(mk) != leg:
                bad.append(f"{lang} {name}: markers {sorted(set(mk))} vs legend {sorted(leg)}")
        # text that sends you to a marker
        refs = {"en": (r"marked (\d) in the picture above", "s3", "fig2", "foam"),
                "bg": (r"означени с (\d) на горната снимка", "s3", "fig2", "пяна")}[lang]
        m = re.search(refs[0], T[refs[1]])
        if not m:
            bad.append(f"{lang}: the foam step no longer points at a marker")
        else:
            entry = dict(T[refs[2]]).get(m.group(1), "")
            if refs[3] not in entry.lower():
                bad.append(f"{lang}: '{m.group(0)}' points at legend {m.group(1)}: '{entry}'")
    report(not bad, f"{len(calls)} pictures in each guide: every marker in its legend and back, and the foam step's "
                    f"'marked 3' points at the foam: {bad or 'yes'}")


# ------------------------------------------------------------------ 3
def energy_density():
    import round28
    with contextlib.redirect_stdout(io.StringIO()):
        got = round28.sizes()
    vol_l = got["battery length"] * got["battery width"] * got["battery thickness"] * 1e-6
    wh = 1.5 * 3.7
    d = wh / vol_l
    report(300 <= d <= 750, f"battery: {wh:.2f} Wh in {got['battery length']:.1f} x {got['battery width']:.1f} x "
                            f"{got['battery thickness']:.2f} mm = {vol_l * 1000:.1f} cm3 -> {d:.0f} Wh/L "
                            f"(LiPo pouch cells: 300-750)")


if __name__ == "__main__":
    volume_accounting()
    figures()
    energy_density()
    print(f"\nRound 34: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
