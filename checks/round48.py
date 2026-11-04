#!/usr/bin/env python3
"""Debug round 48 (session 5): methods not used in rounds 1-47.

1. The two guides side by side. Every text in the English guide has its Bulgarian twin (same key in
   text_en.json and text_bg.json). For each pair, the numbers must be the same ones in the same order
   (decimal commas read as points, a range like 3-4 read as two numbers), and the bold phrases must be
   as many, so a number changed in one language and not the other, or a warning that lost its bold,
   is found. Rounds 37 and 43 compared each guide with the README and the log; this compares the two
   guides with each other.
2. First-layer squish ("elephant's foot"): the first layer on the bed often spreads 0.1-0.2 mm
   sideways unless the slicer compensates for it. Each part's first layer is cut from its STL, every
   opening in it is shrunk by 0.2 mm all round, and what is left must still be open and at least
   0.4 mm wide: the speaker slots, the microphone and sensor holes and the screw recesses on the back,
   and on the lid every opening that reaches its front face. Each recess must still take a 5.0 mm
   head with 0.3 mm to spare.
3. Read through (by me, not a script): the README, and both guides' texts side by side, as the owner
   will read them. What it found is in DEBUG_LOG.md.
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
NUM = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?")   # not the 2.5 of M2.5 (or M2,5)


def flat(v):
    if isinstance(v, str):
        return [v]
    if isinstance(v, (list, tuple)):
        return [s for x in v for s in flat(x)]
    if isinstance(v, dict):
        return [s for x in v.values() for s in flat(x)]
    return []


def numbers(texts):
    out = []
    for t in texts:
        t = re.sub(r"<[^>]+>", " ", t)
        t = t.replace(" ", " ").replace(" ", " ")
        out += [n.replace(",", ".") for n in NUM.findall(t)]
    return out


def bold(texts):
    return sum(t.count("<b>") for t in texts)


def guides_side_by_side():
    gd = os.path.join(ROOT, "docs", "guide-src")
    en = json.load(open(os.path.join(gd, "text_en.json"), encoding="utf-8"))
    bg = json.load(open(os.path.join(gd, "text_bg.json"), encoding="utf-8"))
    missing = sorted(set(en) ^ set(bg))
    report(not missing, f"guides: the same {len(en)} texts in English and Bulgarian"
                        + (f"; only in one: {missing}" if missing else ""))
    num_bad, bold_bad, total = [], [], 0
    for k in sorted(set(en) & set(bg)):
        if k == "lang":
            continue
        e, b = flat(en[k]), flat(bg[k])
        ne, nb = numbers(e), numbers(b)
        total += len(ne)
        if ne != nb:
            # show where they part
            i = next((j for j, (x, y) in enumerate(zip(ne, nb)) if x != y), min(len(ne), len(nb)))
            num_bad.append(f"{k}: EN {ne[max(0, i - 2):i + 3]} / BG {nb[max(0, i - 2):i + 3]}")
        if bold(e) != bold(b):
            bold_bad.append(f"{k}: {bold(e)} bold in EN, {bold(b)} in BG")
    report(not num_bad, f"guides: {total} numbers in the English texts, the same ones in the same order in "
                        f"the Bulgarian" + (": " + "; ".join(num_bad) if num_bad else ""))
    report(not bold_bad, "guides: as many bold phrases in each Bulgarian text as in its English twin"
                         + (": " + "; ".join(bold_bad) if bold_bad else ""))


# ------------------------------------------------------------------ 2
def stl_polys(mesh, z):
    import trimesh
    from shapely.geometry import Polygon
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    planar, tf = sec.to_2D()
    pts = lambda r: trimesh.transform_points(np.column_stack([np.asarray(r.coords), np.zeros(len(r.coords))]), tf)[:, :2]  # noqa: E731
    return [Polygon(pts(p.exterior), [pts(r) for r in p.interiors]) for p in planar.polygons_full]


def recess_centres(polys):
    """Centres of the round openings about as wide as the recess, in a section through the recesses."""
    out = []
    for p in polys:
        for r in p.interiors:
            from shapely.geometry import Polygon
            h = Polygon(r)
            d = 2 * math.sqrt(h.area / math.pi)
            if abs(d - 2 * case.SCREW_HEAD_R) < 0.3:
                out.append((h.centroid.x, h.centroid.y))
    return sorted(out)


def first_layer():
    import trimesh
    from shapely.geometry import Point, Polygon
    squish, left = 0.2, 0.4
    rows, ok = [], True
    for label, f in (("back cover", "back_cover_battery.stl"), ("lid", "front_shell_battery.stl")):
        m = trimesh.load(os.path.join(ROOT, "stl", f))
        m.apply_translation([0, 0, -m.bounds[0][2]])
        polys = stl_polys(m, 0.1)
        holes = [Polygon(r) for p in polys for r in p.interiors]
        narrow = []
        for h in holes:
            still = h.buffer(-(squish + left / 2))
            if still.is_empty:
                c = h.representative_point()
                narrow.append(f"({c.x:.1f}, {c.y:.1f}), {h.area:.2f} mm2")
        ok &= not narrow
        txt = f"{label}: {len(holes)} opening{'s' if len(holes) != 1 else ''} in the first layer"
        if label == "back cover":
            centres = recess_centres(polys)
            spare = min(h.buffer(-squish).intersection(Point(c).buffer(2.5 + 0.3, 128)).area
                        / Point(c).buffer(2.5 + 0.3, 128).area for h in holes for c in centres
                        if h.contains(Point(c)))
            ok &= len(centres) == 4 and spare > 0.999
            txt += (f", the {len(centres)} recesses still take a 5.0 mm head with 0.3 mm to spare"
                    if spare > 0.999 else ", a recess too small for a 5.0 mm head")
        rows.append(txt + (f"; too narrow: {narrow}" if narrow else ", every one still open and 0.4 mm wide"))
    report(ok, f"first layer spread {squish} mm sideways into every opening: " + "; ".join(rows))


if __name__ == "__main__":
    guides_side_by_side()
    first_layer()
    print(f"\nRound 48: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
