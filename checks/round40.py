#!/usr/bin/env python3
"""Debug round 40 (session 5): methods not used in rounds 1-39.

1. The closing force from the meshes: round 36's bend curve (how far each hook is bent at each point
   of the lid's travel, found on the STLs) times the beam's stiffness gives the side force; the slope
   of the curve gives the angle the lid presses at, and so the push needed (friction 0.3). Its peak,
   for all four clips, must be what the README says to within 25 %, and so must the pull-off force
   (from the catch face's slope on the curve).
2. The same words for the same parts, in all three documents: the README and the English guide call
   the front part the lid (front lid) and never the old "front shell" outside file names; the
   Bulgarian guide calls it the front cover ("преден капак") and never the old "предна част"; the
   standoffs, posts and clips have one name each per language.
3. Lying on its back: the case rests on its back face, the screw heads sunk in their recesses (none
   proud of the back face with the tallest head allowed, 2.1 mm), and nothing else below that plane.
"""
import json
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


# ------------------------------------------------------------------ 1
def forces():
    from round1 import load_assembled, to_manifold
    from round36 import bend_curve
    shell, _, _, _ = load_assembled("battery")
    lid = to_manifold(shell)
    E, L, t = 3000.0, case.CLIP_L, case.SKIRT_T
    h = case.SKIRT_H - case.CLIP_SLOT
    k = 192 * E * (h * t ** 3 / 12) / L ** 3          # N per mm of bend, fixed-fixed beam, load in the middle
    mu = 0.3
    push_peak, pull_peak = 0.0, 0.0
    for x, side in case.CLIPS:
        d, b = bend_curve(lid, x, side)
        slope = np.diff(b) / np.diff(-d)              # bend per mm of travel toward closed (+: bending more)
        mid = (b[:-1] + b[1:]) / 2
        push = []
        for s, bb in zip(slope, mid):
            if s > 0:                                  # riding up: push = side force x (tan + mu) / (1 - mu tan)
                push.append(k * bb * (s + mu) / max(1 - mu * s, 1e-6))
        push_peak = max(push_peak, max(push, default=0.0))
        # pulling off from closed: the catch face's slope where the bend falls toward closed
        catch = [(-s, bb) for s, bb in zip(slope, mid) if s < 0]
        if catch:
            tan_c = max(c[0] for c in catch)
            pull_peak = max(pull_peak, k * case.CLIP_UNDERCUT * (tan_c + mu) / max(1 - mu * tan_c, 1e-6))
    n = len(case.CLIPS)
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    m = re.search(r"Pressing the lid on takes about (\d+) N.*?pulling it straight off takes about (\d+) N", text)
    said = tuple(int(v) for v in m.groups()) if m else (None, None)
    ok = m and abs(n * push_peak - said[0]) <= 0.25 * said[0] and abs(n * pull_peak - said[1]) <= 0.25 * said[1]
    report(bool(ok), f"forces from the meshes' bend curves ({n} clips): about {n * push_peak:.0f} N at the hardest point "
                     f"of closing, {n * pull_peak:.0f} N to pull the lid straight off; the README says {said[0]} and "
                     f"{said[1]} N (want within 25 %)")


# ------------------------------------------------------------------ 2
def words():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    g = os.path.join(ROOT, "docs", "guide-src")
    en = json.dumps(json.load(open(os.path.join(g, "text_en.json"), encoding="utf-8")), ensure_ascii=False)
    bg = json.dumps(json.load(open(os.path.join(g, "text_bg.json"), encoding="utf-8")), ensure_ascii=False)
    strip = lambda t: re.sub(r"`[^`]*`|<code>.*?</code>", "", t)   # noqa: E731  file names may keep "front_shell"
    bad = []
    for doc, t in (("README", strip(readme)), ("EN guide", strip(en))):
        for old in ("front shell", "foam", "side screw", "pilot"):
            if old in t.lower():
                bad.append(f"{doc}: '{old}'")
        for need in ("front lid", "standoff", "corner post", "clip"):
            if need not in t.lower():
                bad.append(f"{doc}: no '{need}'")
    t = strip(bg)
    for old in ("предна част", "пяна", "пилот"):
        if old in t.lower():
            bad.append(f"BG guide: '{old}'")
    for need in ("преден капак", "втулк", "стълбче", "щипк"):
        if need not in t.lower():
            bad.append(f"BG guide: no '{need}'")
    # one Bulgarian word each: the clips are "щипки", never "клипс"; the standoffs "втулки", never "дистанционни" alone
    for other in ("клипс", "щракалк", "стойк"):
        if other in t.lower():
            bad.append(f"BG guide: second name '{other}'")
    report(not bad, f"the same words for the same parts in the README and both guides: {bad or 'yes'}")


# ------------------------------------------------------------------ 3
def lying_flat():
    from round1 import load_assembled
    _, _, cover, z_total = load_assembled("battery")
    zmax = cover.bounds[1][2]
    seat = z_total - case.SCREW_HEAD_DEPTH
    head_top = seat + case.SCREW_HEAD_K                # the tallest head the README allows
    # the back face is the cover's highest plane; its area there (it rests on that)
    v = cover.vertices
    on_face = v[np.abs(v[:, 2] - zmax) < 1e-3]
    span = on_face[:, :2].max(0) - on_face[:, :2].min(0)
    report(abs(zmax - z_total) < 1e-3 and head_top <= z_total + 1e-9 and span[0] > 90 and span[1] > 55,
           f"lying on its back: the back face is the lowest plane (z {zmax:.2f}, {span[0]:.1f} x {span[1]:.1f} mm across); "
           f"a {case.SCREW_HEAD_K} mm head (ISO 7045) sits {z_total - head_top:.2f} mm inside it "
           f"({z_total - head_top - 0.2:.2f} mm with the slicer's thick bridges)")


if __name__ == "__main__":
    words()
    lying_flat()
    forces()
    print(f"\nRound 40: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
