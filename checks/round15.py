#!/usr/bin/env python3
"""Debug round 15: methods not used in rounds 1-14.

1. Battery size cross-check: the 454261 label is read as 4.5 x 42 x 61 mm by the usual naming
   convention; Waveshare's own photo of the battery must show the same length-to-width ratio.
   Since session 4 the bay is sized from the owner's own cell, measured with a ruler (61.3 x 41.0 mm,
   checked in round 28), so Waveshare's photo is only reported for comparison here
2. (Slim version grille: removed with the slim version)
3. Release zips (if present in dist/): they open cleanly and their STLs are byte-identical to stl/
"""
import hashlib
import os
import sys
import urllib.request
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled, to_manifold  # noqa: E402

problems = []
skipped = []
BATTERY_PHOTO = "https://www.waveshare.com/img/devkit/general/3.7V-1500mA-battery.jpg"


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
def battery_photo():
    from PIL import Image
    from scipy import ndimage
    cache = os.path.join(HERE, ".cache")
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, "battery.jpg")
    if not os.path.exists(path):
        req = urllib.request.Request(BATTERY_PHOTO, headers={"User-Agent": "Mozilla/5.0"})
        try:
            data = urllib.request.urlopen(req, timeout=60).read()
        except OSError as e:
            print(f"  SKIP battery photo comparison: Waveshare's battery photo could not be downloaded ({e})")
            skipped.append("battery photo")
            return
        open(path, "wb").write(data)
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # the cell: everything that is neither white background nor red/black wire; its length and width
    # are the spans of columns/rows that are mostly cell
    bg = (r > 235) & (g > 235) & (b > 235)
    wire = ((r > 150) & (g < 90) & (b < 90)) | ((r < 70) & (g < 70) & (b < 70))
    cell = ~bg & ~wire
    cols = np.nonzero(cell[400:880].mean(0) > 0.6)[0]
    rows = np.nonzero(cell[:, 600:1250].mean(1) > 0.6)[0]
    w, h = cols.max() - cols.min(), rows.max() - rows.min()
    ratio = w / h
    L = ratio * case.BATTERY_SIZE[1]
    x0, x1, y0, y1 = case.BATTERY_BAY
    # for comparison only: the owner's cell was measured directly (round 28), and that cell is the one
    # going in this case
    print(f"  ..   Waveshare's battery photo: {w} x {h} px, length/width {ratio:.3f} -> about {L:.1f} mm long "
          f"at the owner's measured width of {case.BATTERY_SIZE[1]:.1f} mm; the owner's cell measures "
          f"{case.BATTERY_SIZE[0]:.1f} mm and the bay is {x1 - x0:.1f} x {y1 - y0:.1f} mm")


# ------------------------------------------------------------------ 3
def zips():
    dist = os.path.join(ROOT, "dist")
    if not os.path.isdir(dist):
        print("  ..   no dist/ folder yet; zip check skipped")
        return
    stl_hash = {f: hashlib.sha256(open(os.path.join(ROOT, "stl", f), "rb").read()).hexdigest()
                for f in os.listdir(os.path.join(ROOT, "stl"))}
    for name in sorted(os.listdir(dist)):
        if not name.endswith(".zip"):
            continue
        with zipfile.ZipFile(os.path.join(dist, name)) as z:
            bad = z.testzip()
            stls = [n for n in z.namelist() if n.endswith(".stl")]
            mism = [n for n in stls if hashlib.sha256(z.read(n)).hexdigest() != stl_hash.get(os.path.basename(n))]
            report(bad is None and stls and not mism, f"{name}: {len(z.namelist())} files, {len(stls)} STLs, "
                                                      f"corrupt entry {bad}, STLs differing from stl/: {mism or 'none'}")


if __name__ == "__main__":
    battery_photo()
    zips()
    print(f"\nRound 15: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
