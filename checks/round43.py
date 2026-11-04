#!/usr/bin/env python3
"""Debug round 43 (session 5): methods not used in rounds 1-42.

1. Every new number in the guides accounted for: the numbers in the English and Bulgarian guide texts
   now that were not in session 4's (commit 13d2cbf, decimal commas read as points) are listed, and
   each must come from case.py, a check's result or a measurement, as round 31 does for the README.
2. The zip as you will open it: unpacked into an empty folder, every file must open the way you would
   use it: both STLs load as single watertight solids of the right size, every PNG decodes, both PDFs
   have their pages with the guide's title and step headings in their text, and the README's
   pictures resolve inside the zip.
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
import zipfile

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
def numbers(text):
    t = re.sub(r"<code>.*?</code>", "", text)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    t = re.sub(r"ESP32-S3-ePaper-3\.97|SKU \d+|ESP32|3\.97", "", t)
    return set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?", t))


def guides_inventory():
    g = os.path.join(ROOT, "docs", "guide-src")
    old, new = set(), set()
    for lang in ("en", "bg"):
        src = subprocess.run(["git", "-C", ROOT, "show", f"13d2cbf:docs/guide-src/text_{lang}.py"],
                             capture_output=True, text=True).stdout
        if not src:
            report(False, "guides inventory: session 4's guide texts could not be read from git")
            return
        old |= numbers(src)
        new |= numbers(json.dumps(json.load(open(os.path.join(g, f"text_{lang}.json"), encoding="utf-8")), ensure_ascii=False))
    fresh = sorted(new - old, key=float)
    import trimesh
    back = trimesh.load(os.path.join(ROOT, "stl", "back_cover_battery.stl")).volume / 1000
    m = re.search(r"about (\d+) g", json.dumps(json.load(open(os.path.join(g, "text_en.json"), encoding="utf-8"))))
    explain = {
        f"{case.SCREW_HOLE_R - 1.25:.1f}"[:3]: "the holes' play (SCREW_HOLE_R - 1.25 = 0.45, 'allow 0.4')",
        f"{case.SCREW_HEAD_K:.1f}": "tallest head (SCREW_HEAD_K, DIN 7985 M2.5)",
        f"{case.PAD_GAP + case.STANDOFF_H - case.STANDOFF_H_MIN:.1f}": "board to the posts before screwing, 3 mm standoffs",
        f"{2 * 2.5:.1f}": "largest head, 5.0 mm (the checks' head model)",
        f"{back:.0f}": f"back cover volume ({back:.1f} cm3 in the STL)",
        "7045": "ISO 7045", "7985": "DIN 7985", "7089": "ISO 7089", "125": "DIN 125",
        "0.7": "the standoff estimates' spread (round 35: Waveshare's photos vs yours, up to 0.7 mm)",
    }
    if m:
        explain[m.group(1)] = "PLA estimate (round 19 checks it against the slicer)"
    for label, (pts, _) in (("battery wire", case.battery_wire_route()), ("speaker cable", case.speaker_wire_route())):
        length = sum(math.dist(p, q) for p, q in zip(pts, pts[1:]))
        explain.setdefault(f"{length:.0f}", f"{label} route in case.py (round 13 checks it)")
    unexplained = [v for v in fresh if v not in explain]
    report(not unexplained, f"guides: {len(fresh)} numbers new since session 4 ({', '.join(fresh)}), each traced to "
                            f"case.py, a check or a measurement; unexplained: {unexplained or 'none'}")


# ------------------------------------------------------------------ 2
def zip_as_opened():
    import trimesh
    from PIL import Image
    zips = [f for f in os.listdir(os.path.join(ROOT, "dist")) if f.endswith(".zip")]
    bad, notes = [], []
    for zname in zips:
        with tempfile.TemporaryDirectory() as d:
            with zipfile.ZipFile(os.path.join(ROOT, "dist", zname)) as z:
                z.extractall(d)
            top = os.path.join(d, os.listdir(d)[0])
            for dirpath, _, files in os.walk(top):
                for f in files:
                    p = os.path.join(dirpath, f)
                    rel = os.path.relpath(p, top)
                    try:
                        if f.endswith(".stl"):
                            m = trimesh.load(p)
                            size = m.bounds[1] - m.bounds[0]
                            if not (m.is_watertight and len(m.split(only_watertight=False)) == 1
                                    and abs(size[0] - (case.X1 - case.X0)) < 0.05 and abs(size[1] - (case.Y1 - case.Y0)) < 0.05):
                                bad.append(f"{rel}: not one watertight {case.X1 - case.X0:.1f} x {case.Y1 - case.Y0:.1f} mm part")
                            notes.append(f"{rel} {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f}")
                        elif f.endswith(".png"):
                            with Image.open(p) as im:
                                im.load()
                                if min(im.size) < 200:
                                    bad.append(f"{rel}: only {im.size}")
                        elif f.endswith(".pdf"):
                            txt = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True).stdout
                            pages = txt.count("\f")
                            lang = "bg" if "_bg" in f else "en"
                            T = json.load(open(os.path.join(ROOT, "docs", "guide-src", f"text_{lang}.json"), encoding="utf-8"))
                            heads = [T["title"].split(":")[0]] + [re.sub(r"<[^>]+>", "", T[k]) for k in ("s1_h", "s2_h", "s3_h", "s4_h", "h_open")]
                            flat = re.sub(r"\s+", " ", txt)
                            missing = [h for h in heads if re.sub(r"\s+", " ", h) not in flat]
                            if pages < 4 or missing:
                                bad.append(f"{rel}: {pages} pages, headings missing {missing}")
                            notes.append(f"{rel} {pages} pages")
                        elif f.endswith(".md"):
                            text = open(p, encoding="utf-8").read()
                            for img in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
                                if not os.path.exists(os.path.join(top, img)):
                                    bad.append(f"{rel}: picture {img} not in the zip")
                    except Exception as e:  # noqa: BLE001
                        bad.append(f"{rel}: {e}")
    report(zips and not bad, f"{len(zips)} zip(s) unpacked and every file opened: {'; '.join(notes)}"
                             f"{'; problems: ' + str(bad) if bad else ''}")


if __name__ == "__main__":
    guides_inventory()
    zip_as_opened()
    print(f"\nRound 43: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
