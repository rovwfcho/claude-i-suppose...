#!/usr/bin/env python3
"""Debug round 59 (session 5): methods not used in rounds 1-58.

1. Every numbered marker in the guide's pictures sits on the thing its legend names. Round 58 found
   two pictures that numbered the screws differently; here every marker of every picture is tried.
   Each scene is rebuilt from the meshes the guide renders (docs/guide-src/*.stl, turned over and
   moved as specs.json says), and for each marker the nearest part is found from the meshes alone.
   It must be the part the legend names (my reading of each legend, written out below), and markers
   for openings, edges and clips must also be in the right place on the case (the top or bottom
   edge, the USB-C end or the far end, at the dial, the buttons or a clip), from case.py's positions
   of those features, not from the code that placed the markers. Each legend must be numbered 1, 2,
   3... in order, every number must have a marker, and the Bulgarian legend must have as many items
   as the English.
2. The words for directions, read in the view each step sets up. Round 58 found "the notch in the
   right-hand end", which holds only with the display facing you. Every "left", "right", "top",
   "bottom", "above", "below", "front", "back", "toward you" and "away from you" in the README's
   assembly and opening text and in both guides' steps is listed with its step and the view that
   step sets up, and I read each one in that view (DEBUG_LOG.md, round 59). The script checks that
   no step where the back faces you (step 4 and the opening, in all three documents) uses "left"
   or "right" at all.
3. The reviewer's own scripts, re-run. The round 58 reviewer wrote its own measurements, separately
   from the checks. Two of them, kept in checks/review58/ as it wrote them (only ROOT and the
   command line changed), are run on the case as it is now: its USB-C grip test with the README's
   grip size, and its window test with the board anywhere the cavity lets it sit. Both must agree
   with the README.
"""
import json
import math
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

G = os.path.join(ROOT, "docs", "guide-src")
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
# Where each legend item should be, by my reading of the legend: the parts it may sit on, and (for
# openings, edges and clips) a test on the marker's x, y in the case's own frame.
NOTCH = (case.WHEEL[0] - 7.5, case.WHEEL[0] + 7.5)
BTN = case.BTN_NOTCH
at_top = lambda x, y, z: y > case.BH - 1.0                                          # noqa: E731
at_bottom = lambda x, y, z: y < 1.0                                                 # noqa: E731
dial = lambda x, y, z: at_top(x, y, z) and NOTCH[0] <= x <= NOTCH[1]                 # noqa: E731
buttons = lambda x, y, z: at_bottom(x, y, z) and BTN[0] <= x <= BTN[1]               # noqa: E731
usb = lambda x, y, z: x < 1.0 and abs(y - case.USB_Y) < 6.5                         # noqa: E731
sd = lambda x, y, z: x < 1.0 and abs(y - case.SD_Y) < 6.0                           # noqa: E731
far_end = lambda x, y, z: x > case.BW - 1.0                                         # noqa: E731
clip = lambda x, y, z: any(abs(x - cx) < 3.0 and (at_bottom(x, y, z) if s == "bottom" else at_top(x, y, z))
                           for cx, s in case.CLIPS)                                 # noqa: E731
post = lambda x, y, z: any(abs(x - px) < 5.0 and abs(y - py) < 5.0 for px, py in case.POSTS)  # noqa: E731
BOARD = {"board", "panel", "standoffs", "wheel"}
EXPECT = {
    "parts": {1: ({"shell"}, None), 2: (BOARD, None), 3: ({"cover"}, None), 4: ({"battery", "battery_end"}, None),
              5: ({"speaker", "speaker_peg"}, None), 6: ({"cover"}, None)},
    "step1": {1: ({"shell"}, dial), 2: ({"shell"}, buttons), 3: ({"shell"}, usb), 4: (BOARD, None), 5: ({"shell"}, sd)},
    "step2": {1: ({"battery", "battery_end"}, None), 2: ({"speaker"}, None), 3: ({"cover"}, post),
              4: ({"wire_bat"}, None), 5: ({"wire_spk"}, None), 6: ({"wire_bat"}, None), 7: ({"coil_spk"}, None),
              8: ({"speaker_peg"}, None)},
    "step3": {1: ({"cover"}, dial), 2: ({"cover"}, None), 3: ({"wheel"}, dial), 4: ({"cover"}, clip)},
    "step4a": {i: ({"screws"}, post) for i in (1, 2, 3, 4)},
    "step4b": {1: ({"shell", "cover"}, far_end)},
    "print": {1: ({"p_front"}, None), 2: ({"p_cover"}, None)},
}
LEGEND = {"parts": "fig_parts", "step1": "fig1", "step2": "fig2", "step3": "fig3", "step4a": "fig4a",
          "step4b": "fig4b", "print": "fig_print"}


def scene(spec):
    import trimesh
    out = {}
    for p in spec["parts"]:
        m = trimesh.load(os.path.join(G, p["f"] + ".stl"), force="mesh")
        if p.get("flip"):
            m.apply_transform(np.diag([1.0, -1.0, -1.0, 1.0]))       # scene.html: rotation.x = pi
        m.apply_translation([p.get("dx", 0), p.get("dy", 0), p.get("dz", 0)])
        out[p["f"]] = (m, p)
    return out


def markers():
    specs = json.load(open(os.path.join(G, "specs.json"), encoding="utf-8"))
    en = json.load(open(os.path.join(G, "text_en.json"), encoding="utf-8"))
    bg = json.load(open(os.path.join(G, "text_bg.json"), encoding="utf-8"))
    build = open(os.path.join(G, "build.py"), encoding="utf-8").read()
    bad, n, rows = [], 0, []
    for name, key in LEGEND.items():
        legend = en[key]
        nums = [int(m) for m, _ in legend]
        if nums != list(range(1, len(legend) + 1)):
            bad.append(f"{name}: legend numbered {nums}")
        if len(bg[key]) != len(legend) or [m for m, _ in bg[key]] != [m for m, _ in legend]:
            bad.append(f"{name}: the Bulgarian legend has {len(bg[key])} items, the English {len(legend)}")
        m = re.search(rf"figure\('{name}', T\['{key}'\], marks=(\[[^\]]*\])", build)
        labels = specs[name]["labels"]
        marks = [int(s) for s in json.loads(m.group(1).replace("'", '"'))] if m else list(range(1, len(labels) + 1))
        if len(marks) != len(labels) or set(marks) != set(nums):
            bad.append(f"{name}: {len(labels)} markers numbered {sorted(set(marks))}, legend {nums}")
            continue
        parts = scene(specs[name])
        for pt, k in zip(labels, marks):
            n += 1
            d = {f: float(abs(mesh.nearest.on_surface([pt])[1][0])) for f, (mesh, _) in parts.items()}
            near = min(d, key=d.get)
            want, where = EXPECT[name][k]
            # the part the legend names may share the nearest spot with another (a plug on its wire)
            on = near in want or min(d[f] for f in want if f in d) <= d[near] + 0.3
            spot = True
            if where is not None:
                mesh, p = parts[sorted(want & set(parts))[0]]
                x, y, z = pt[0] - p.get("dx", 0), pt[1] - p.get("dy", 0), pt[2] - p.get("dz", 0)
                if p.get("flip"):
                    y, z = -y, -z
                spot = where(x, y, z)
            if not (on and spot):
                bad.append(f"{name} marker {k} ('{dict(legend)[str(k)][:40]}'): nearest {near} ({d[near]:.1f} mm)"
                           + ("" if spot else f", not where its legend says ({pt[0]:.1f}, {pt[1]:.1f})"))
        rows.append(f"{name} {len(labels)}")
    report(not bad, f"{n} markers in {len(LEGEND)} pictures ({', '.join(rows)}): each on the part its legend names, "
                    f"in the right place, legends numbered in order and the same length in both languages: "
                    f"{bad or 'all'}")


# ------------------------------------------------------------------ 2
DIRS = r"\b(left|right|top|bottom|above|below|front|back|toward you|away from you)\b"
DIRS_BG = r"(ляв|десн|горн|долн|над |под |пред |отзад|гърб|към вас|далеч от вас)"


def directions():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    asm = readme.split("## Assembly", 1)[1].split("\n## ", 1)[0]
    steps = {f"README step {i}": s for i, s in enumerate(re.split(r"\n(?=\d\. )", asm.strip()), 1)}
    m = re.search(r"\*\*Opening:\*\*[^\n]*", asm)
    if m:
        steps["README opening"] = m.group(0)
    steps["README step 4"] = steps.get("README step 4", "").split("**Opening:**")[0]
    en = json.load(open(os.path.join(G, "text_en.json"), encoding="utf-8"))
    bg = json.load(open(os.path.join(G, "text_bg.json"), encoding="utf-8"))
    for lang, T in (("EN", en), ("BG", bg)):
        for k in ("s1", "s2", "s3", "s4", "s4_note"):
            steps[f"{lang} {k}"] = T[k]
        steps[f"{lang} opening"] = " ".join(T["open"]) + " " + " ".join(t for _, t in T["fig4b"])
    back_faces_you = [k for k in steps if k.endswith(("step 4", "opening", "s4", "s4_note"))]
    listed, bad = 0, []
    print("  ..   direction words, with the view each step sets up:")
    for k, text in steps.items():
        plain = re.sub(r"<[^>]+>|\*\*", "", text)
        rx = DIRS_BG if k.startswith("BG") else DIRS
        for mm in re.finditer(rx, plain, re.I):
            listed += 1
            a, b = max(0, mm.start() - 50), min(len(plain), mm.end() + 40)
            print(f"         {k}: ...{plain[a:b]}...".replace("\n", " "))
        if k in back_faces_you:
            lr = r"(ляв|десн)" if k.startswith("BG") else r"\b(left|right)(-hand)?\b"
            hits = re.findall(lr, plain, re.I)
            if hits:
                bad.append(f"{k}: {hits}")
    report(not bad, f"direction words: {listed} listed in {len(steps)} steps (read in their views: DEBUG_LOG.md, "
                    f"round 59); left or right where the back faces you: {bad or 'none'}")


# ------------------------------------------------------------------ 3
REVIEW = os.path.join(HERE, "review58")


def reviewers_scripts():
    usb, win = os.path.join(REVIEW, "usb.py"), os.path.join(REVIEW, "win2.py")
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    w, t = (float(v) for v in re.search(r"moulded grip is up to about ([\d.]+) x ([\d.]+) mm", readme).groups())
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, "-B", usb, str(w), str(t), "1.0"], capture_output=True, text=True,
                         env=env, timeout=1200).stdout
    vols = [float(v) for v in re.findall(r"overlap ([\d.]+) mm3", out)]
    out2 = subprocess.run([sys.executable, "-B", win], capture_output=True, text=True, env=env, timeout=1200).stdout
    margins = [float(v) for v in re.findall(r"^(?:measured|nominal) shrink [\d.]+ worst light-field corner margin ([-\d.]+)",
                                            out2, re.M)]
    ok = len(vols) == 6 and max(vols) < 1e-3 and len(margins) == 8 and min(margins) >= 0.1 - 1e-3
    report(ok, f"the reviewer's own scripts (checks/review58/) on the case as it is now: its USB-C test with the "
               f"README's {w} x {t} grip (corners 1 mm round, 4 and 3 mm standoffs, the board 0.3 mm either way along "
               f"the edge): overlaps at most {max(vols) if vols else float('nan'):.3f} mm3 in {len(vols)} tries; its "
               f"window test (the board anywhere the cavity lets it sit, 0-0.4 % shrinkage, the light field as "
               f"measured and as y 3.0): its corners at least {min(margins) if margins else float('nan'):.3f} mm "
               f"inside (want 0.1)")


if __name__ == "__main__":
    markers()
    directions()
    reviewers_scripts()
    print(f"\nRound 59: {len(problems)} problem(s), {len(skipped)} skipped")
    for p in problems:
        print("  -", p)
