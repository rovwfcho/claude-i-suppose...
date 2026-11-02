#!/usr/bin/env python3
"""Debug round 18: methods not used in rounds 1-17.

1. Clean clone: the committed project is cloned into an empty folder and rebuilt there; the STL files
   it makes must be byte-identical to the committed ones and to the ones inside the zip
2. Plastic shrinkage: the printed parts are scaled down in x and y the way plastics shrink as they
   cool (PLA/PETG about 0.2-0.4 %, ASA about 0.4-0.7 %), and the board must still go in; where it
   doesn't, the README must say what to do
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled, to_manifold, vol  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------ 1
def clean_clone():
    top = subprocess.run(["git", "-C", ROOT, "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                         check=True).stdout.strip()
    sub = os.path.relpath(ROOT, top)
    dirty = subprocess.run(["git", "-C", top, "status", "--porcelain", "--", sub], capture_output=True, text=True,
                           check=True).stdout.strip()
    if dirty:
        print("  ..   uncommitted changes in the project; the clone check uses the last commit")
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "clone", "-q", "--no-hardlinks", top, os.path.join(d, "repo")], check=True)
        proj = os.path.join(d, "repo", sub)
        out = os.path.join(d, "out")
        subprocess.run([sys.executable, os.path.join(proj, "case.py"), out], check=True, capture_output=True)
        built = {f: sha(open(os.path.join(out, f), "rb").read()) for f in os.listdir(out)}
        committed = {f: sha(open(os.path.join(proj, "stl", f), "rb").read()) for f in os.listdir(os.path.join(proj, "stl"))}
        report(built == committed, f"clean clone rebuild: {sorted(built)} identical to the committed STLs: {built == committed}")
        zips = [f for f in os.listdir(os.path.join(proj, "dist")) if f.endswith(".zip")]
        for zname in zips:
            with zipfile.ZipFile(os.path.join(proj, "dist", zname)) as z:
                inner = {os.path.basename(n): sha(z.read(n)) for n in z.namelist() if n.endswith(".stl")}
            report(inner == built, f"{zname} (committed): its STLs match the clean rebuild: {inner == built}")


# ------------------------------------------------------------------ 2
def shrinkage():
    shell, _, cover_asm, z_total = load_assembled("battery")
    S0, C0 = to_manifold(shell), to_manifold(cover_asm)
    board = case.board_model()
    cx, cy = case.BW / 2, case.BH / 2
    text = open(os.path.join(ROOT, "README.md")).read().lower()
    results = {}
    for pct in (0.2, 0.4, 0.5, 0.7):
        k = 1 - pct / 100
        S = S0.translate([-cx, -cy, 0]).scale([k, k, 1]).translate([cx, cy, 0])
        C = C0.translate([-cx, -cy, 0]).scale([k, k, 1]).translate([cx, cy, 0])
        hits = {n: round(vol(g ^ (S + C)), 3) for n, g in board.items()}
        hits = {n: v for n, v in hits.items() if v > 1e-3}
        results[pct] = hits
        print(f"  ..   parts shrunk {pct} %: pocket {100.1 * k:.2f} x {60.6 * k:.2f} mm for the 99.5 x 60 PCB; "
              f"board parts touching: {hits or 'none'}")
    report(not results[0.2] and not results[0.4] and not results[0.5],
           "PLA/PETG shrinkage (0.2-0.4 %, and 0.5 % for margin): the board still goes in")
    worst = min((p for p in results if results[p]), default=None)
    if worst is not None:
        said = "shrink" in text and "asa" in text
        report(said, f"from {worst} % shrinkage the board no longer fits (ASA range); the README tells you to "
                     f"turn on shrinkage compensation for ASA: {said}")


if __name__ == "__main__":
    clean_clone()
    shrinkage()
    print(f"\nRound 18: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
