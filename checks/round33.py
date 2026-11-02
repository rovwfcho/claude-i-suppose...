#!/usr/bin/env python3
"""Debug round 33 (session 4): methods not used in rounds 1-32.

1. Can the new checks fail? (mutation testing of the checks themselves.) In a copy of the project,
   each of these deliberate mistakes is made in case.py, the STLs are rebuilt there, and the session-4
   check that should catch it is run on the copy; it must report a problem:
   a bay 1.5 mm too short; a speaker pocket 1 mm too narrow; the grille slots 2 mm off the membrane;
   bracket legs 3 mm long (over the cable); the spare-cable loop moved over the antenna end.
2. The two guides side by side: every field of the English and the Bulgarian text must have the same
   shape (the same number of table rows, bullets and picture legends) and the same numbers in the same
   order (decimal commas read as points), so neither language has a step, a size or a warning the
   other lacks.
3. Margins against small changes: each new dimension (bay, pocket, bracket legs, slot pitch and
   length, cable exit) moved by +/-0.1 mm; every session-4 margin (room for the parts, slots under the
   membrane, cable and peg clear of the legs, antenna distance) must stay positive, so the design does
   not sit on the edge of any limit.
"""
import contextlib
import io
import json
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


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
MUTANTS = [
    ("bay 1.5 mm too short", "BATTERY_BAY = (5.5, 68.0, 6.5, 49.0)", "BATTERY_BAY = (5.5, 66.5, 6.5, 49.0)",
     "round28.py", None),
    ("pocket 1 mm too narrow", 'SPEAKER_BOX = {"battery": (11.2, 15.3, 4.5)}', 'SPEAKER_BOX = {"battery": (10.2, 15.3, 4.5)}',
     "round13.py", None),
    ("grille slots 2 mm off the membrane", "def grille_slots(variant=\"battery\"):\n    \"\"\"Speaker grille: three stadium slots (x0, x1, y0, y1) along y, centred under the speaker.\"\"\"\n    sx, sy = SPEAKER[variant]",
     "def grille_slots(variant=\"battery\"):\n    \"\"\"Speaker grille: three stadium slots (x0, x1, y0, y1) along y, centred under the speaker.\"\"\"\n    sx, sy = SPEAKER[variant]\n    sx += 2.0",
     "round13.py", None),
    ("bracket legs 3 mm long", "SPK_BRACKET = (1.2, 2.0, 2.0, 1.2)", "SPK_BRACKET = (1.2, 2.0, 3.0, 3.0)", "round28.py", None),
    ("cable loop next to the antenna (clear of everything else)", "cx, cy, a, b, rc = sx - 0.5, 40.5, 7.5, 13.5, 4.0",
     "cx, cy, a, b, rc = sx + 4.0, 40.5, 7.5, 12.0, 4.0", "round14.py", None),
]


def mutants():
    caught = []
    with tempfile.TemporaryDirectory() as d:
        for f in ("case.py", "README.md"):
            shutil.copy(os.path.join(ROOT, f), d)
        shutil.copytree(HERE, os.path.join(d, "checks"), ignore=shutil.ignore_patterns("__pycache__", ".cache"))
        shutil.copytree(os.path.join(ROOT, "docs"), os.path.join(d, "docs"),
                        ignore=shutil.ignore_patterns("*.stl", "*.png", "out", "three.module.js", "STLLoader.js"))
        src = open(os.path.join(ROOT, "case.py")).read()
        for label, old, new, check, _ in MUTANTS:
            if src.count(old) != 1:
                caught.append((label, "could not apply"))
                continue
            open(os.path.join(d, "case.py"), "w").write(src.replace(old, new))
            os.makedirs(os.path.join(d, "stl"), exist_ok=True)
            os.makedirs(os.path.join(d, "preview"), exist_ok=True)   # round 28 draws its review image there
            subprocess.run([sys.executable, os.path.join(d, "case.py"), os.path.join(d, "stl")], check=True,
                           capture_output=True)
            r = subprocess.run([sys.executable, os.path.join(d, "checks", check)], capture_output=True, text=True,
                               timeout=1800, cwd=d)
            m = re.search(r"Round \d+: (\d+) problem", r.stdout)
            n = int(m.group(1)) if m else -1
            caught.append((label, f"{check}: {n} problem(s)" if n >= 0 else f"{check} crashed"))
        open(os.path.join(d, "case.py"), "w").write(src)
    missed = [c for c in caught if not re.search(r": [1-9]\d* problem", c[1])]
    report(not missed, f"{len(MUTANTS)} deliberate mistakes, each caught by its check: "
                       f"{[f'{a} -> {b}' for a, b in caught]}; missed: {missed or 'none'}")


# ------------------------------------------------------------------ 2
def numbers_in(x):
    s = json.dumps(x, ensure_ascii=False)
    s = re.sub(r"<code>.*?</code>", "", s)                 # file names, constants
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)                  # Bulgarian decimal commas
    s = re.sub(r"ESP32-S3-ePaper-3\.97|SKU \d+|M2|PH\d|ESP32|3\.97", "", s)
    return re.findall(r"\d+(?:\.\d+)?", s)


def shape(x):
    if isinstance(x, list):
        return [shape(v) for v in x]
    if isinstance(x, tuple):
        return tuple(shape(v) for v in x)
    return "s"


def parity():
    g = os.path.join(ROOT, "docs", "guide-src")
    en = json.load(open(os.path.join(g, "text_en.json"), encoding="utf-8"))
    bg = json.load(open(os.path.join(g, "text_bg.json"), encoding="utf-8"))
    diff = []
    if set(en) != set(bg):
        diff.append(f"fields only in one: {sorted(set(en) ^ set(bg))}")
    for k in sorted(set(en) & set(bg)):
        if k == "lang":
            continue
        if shape(en[k]) != shape(bg[k]):
            diff.append(f"{k}: shape differs")
            continue
        a, b = numbers_in(en[k]), numbers_in(bg[k])
        if a != b:
            diff.append(f"{k}: {a} vs {b}")
    report(not diff, f"English and Bulgarian guides, field by field ({len(en) - 1} fields): same shape and the same "
                     f"numbers in the same order: {diff or 'yes'}")


# ------------------------------------------------------------------ 3
def margins(bay_dx=0.0, pocket_dx=0.0, pocket_dy=0.0, leg=0.0, pitch=0.0, slot=0.0, exit_=0.0):
    """The session-4 margins (mm) for one set of small changes, from the measured parts (round 28)."""
    got = MEASURED
    x0, x1, y0, y1 = case.BATTERY_BAY
    pw, ph, _ = case.SPEAKER_BOX["battery"]
    pw, ph = pw + pocket_dx, ph + pocket_dy
    wall, _, leg_x, leg_y = case.SPK_BRACKET
    leg_x, leg_y = leg_x + leg, leg_y + leg
    gw, gl, gp = case.GRILLE_SLOTS
    gp, gl = gp + pitch, gl + slot
    L, W = got["speaker length"], got["speaker width"]
    rx, ry = (pw - W) / 2, (ph - L) / 2
    out = {
        "battery room": min((x1 - x0 + bay_dx) - got["battery length"], (y1 - y0 + bay_dx) - got["battery width"]) / 2 - 0.3,
        "speaker room": min(rx, ry) - 0.3,
        "slots under membrane x": MEMBRANE[1] / 2 - (gp + gw / 2) - rx,
        "slots under membrane y": MEMBRANE[0] / 2 - gl / 2 - ry,
        "slot webs": gp - gw - 0.8 + 1e-9,
        "cable to leg": (ph / 2 - leg_y) - (L / 2 - (case.SPK_CABLE_EXIT + exit_) + 1.0) - ry,
        "peg to leg": (pw / 2 - leg_x) - (abs(W / 2 - PEG_V) + 1.3) - rx,
        "antenna": case.ANTENNA[0] - (case.SPEAKER["battery"][0] + pw / 2 + wall) - 6.0,
    }
    return out


def sensitivity():
    import round28
    global MEASURED, MEMBRANE, PEG_V
    with contextlib.redirect_stdout(io.StringIO()):
        MEASURED = round28.sizes()
    L, W = MEASURED["speaker length"], MEASURED["speaker width"]
    h = round28.homography(round28.FRAME, [(0, 0), (L, 0), (L, W), (0, W)])
    m = np.array([round28.apply(h, p) for p in round28.MEMBRANE])
    MEMBRANE = ((np.linalg.norm(m[1] - m[0]) + np.linalg.norm(m[2] - m[3])) / 2,
                (np.linalg.norm(m[3] - m[0]) + np.linalg.norm(m[2] - m[1])) / 2)
    PEG_V = round28.apply(h, round28.PEG)[1]
    base = margins()
    worst = dict(base)
    for k in ("bay_dx", "pocket_dx", "pocket_dy", "leg", "pitch", "slot", "exit_"):
        for d in (-0.1, 0.1):
            for name, v in margins(**{k: d}).items():
                worst[name] = min(worst[name], v)
    neg = {k: round(v, 3) for k, v in worst.items() if v < 0}
    report(not neg, "margins with every new dimension moved 0.1 mm either way (mm past each limit, worst case): "
                    + ", ".join(f"{k} {v:+.2f}" for k, v in worst.items()) + f"; below zero: {neg or 'none'}")


if __name__ == "__main__":
    parity()
    sensitivity()
    mutants()
    print(f"\nRound 33: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
