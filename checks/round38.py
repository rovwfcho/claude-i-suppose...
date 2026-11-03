#!/usr/bin/env python3
"""Debug round 38 (session 5): methods not used in rounds 1-37.

1. Can the session-5 checks fail? In a copy of the project, each of these deliberate mistakes is made
   in case.py, the STLs are rebuilt there, and the check that should catch it is run on the copy; it
   must report a problem: a corner post 0.8 mm off its standoff; the clip slots closed (beams glued to
   the cover); hooks that only reach 0.1 mm past the lid's wall; screw recesses 1.0 mm deep (heads
   standing proud); pads touching the PCB; posts built for 6 mm standoffs (screws not reaching).
2. Margins against small changes: each new dimension (hole and recess radius, post end, pad gap,
   glass relief, clip length, undercut, slot; for the hole and the recess, their diameter) moved 0.1 mm
   either way; every session-5 margin (screw
   play, head room, wall at the corners, pad and glass gaps, clip strain with print errors, hook reach
   with print errors, screw engagement) must stay at or above its limit.
"""
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

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
    ("a corner post 0.8 mm off its standoff", "POSTS = [(2.45, 2.725),", "POSTS = [(3.25, 2.725),", "verify.py"),
    ("clip slots closed", "CLIP_SLOT = 0.6 ", "CLIP_SLOT = 0.0 ", "checks/round35.py"),
    ("hooks reaching only 0.1 mm", "CLIP_UNDERCUT = 0.55 ", "CLIP_UNDERCUT = 0.1 ", "checks/round36.py"),
    ("screw recesses 1.0 mm deep", "SCREW_HEAD_DEPTH = T_BACK ", "SCREW_HEAD_DEPTH = 1.0 ", "verify.py"),
    ("pads touching the PCB", "PAD_GAP = 0.5 ", "PAD_GAP = 0.0 ", "checks/round23.py"),
    ("posts built for 6 mm standoffs", "POST_STANDOFF = 4.0 ", "POST_STANDOFF = 6.0 ", "checks/round4.py"),
]


def caught(out, script):
    if script == "verify.py":
        return "SOME CHECKS FAILED" in out
    m = re.search(r"Round \d+: (\d+) problem", out)
    return bool(m) and int(m.group(1)) > 0


def mutants():
    src = open(os.path.join(ROOT, "case.py")).read()
    rows, missed = [], []
    with tempfile.TemporaryDirectory() as d:
        for f in ("case.py", "verify.py", "README.md", "DEBUG_LOG.md"):
            shutil.copy(os.path.join(ROOT, f), d)
        shutil.copytree(HERE, os.path.join(d, "checks"), ignore=shutil.ignore_patterns("__pycache__", ".cache"))
        shutil.copytree(os.path.join(ROOT, "docs"), os.path.join(d, "docs"),
                        ignore=shutil.ignore_patterns("*.stl", "*.png", "out", "three.module.js", "STLLoader.js"))
        os.makedirs(os.path.join(d, "preview"), exist_ok=True)
        for label, old, new, script in MUTANTS:
            if src.count(old) != 1:
                rows.append((label, "could not apply"))
                missed.append(label)
                continue
            open(os.path.join(d, "case.py"), "w").write(src.replace(old, new))
            os.makedirs(os.path.join(d, "stl"), exist_ok=True)
            b = subprocess.run([sys.executable, os.path.join(d, "case.py"), os.path.join(d, "stl")], capture_output=True)
            if b.returncode != 0:
                rows.append((label, "the generator refused it"))   # also a catch: an assert in case.py
                continue
            args = [os.path.join(d, script)] + ([os.path.join(d, "stl")] if script == "verify.py" else [])
            r = subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=2400, cwd=d)
            hit = caught(r.stdout, script)
            rows.append((label, f"{script}: {'caught' if hit else 'MISSED'}"))
            if not hit:
                missed.append(label)
        open(os.path.join(d, "case.py"), "w").write(src)
    report(not missed, f"{len(MUTANTS)} deliberate mistakes in the new closure: "
                       + "; ".join(f"{a} -> {b}" for a, b in rows) + f"; missed: {missed or 'none'}")


# ------------------------------------------------------------------ 2
E = 0.37   # how far off centre a screw may sit: the holes' play as designed (round 35 needs 0.29 at most)


def margins(hole=0.0, recess=0.0, post=0.0, pad=0.0, relief=0.0, length=0.0, under=0.0, slot=0.0):
    """Session-5 margins (mm, or % for strain) for one set of small changes; >= 0 means within limits.
    hole and recess are diameters (their radii move half as much)."""
    r_h, r_r = case.SCREW_HOLE_R + hole / 2, case.SCREW_HEAD_R + recess / 2
    post_z = case.POST_Z + post
    L, u = case.CLIP_L + length, case.CLIP_UNDERCUT + under
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    seat = z_total - case.SCREW_HEAD_DEPTH
    err = 0.3                                                  # both parts' print errors (round 36)
    corner = 4.57 - 0.586 * case.RE_BACK - r_r                 # wall at the corner, back face (round 6)
    into = case.SCREW_LEN - (seat - post_z)
    pcb_front_hi = post_z - case.STANDOFF_H - (case.PCB_T + 0.16) # thickest PCB, 4 mm standoffs
    out = {
        "screw play vs 0.29 needed (round 35)": (r_h - 0.075 - 1.25) - 0.29,
        "5 mm head 0.37 mm off centre in the recess": (r_r - 0.075) - (2.5 + E),
        "4.7 mm head 0.37 mm off centre bears 0.2 mm": (2.35 - E) - (r_h - 0.075) - 0.2,
        "wall at the corner": corner - 0.8,
        "screw 1.5-2.5 mm into a standoff": min(into - 1.5, 2.5 - into),
        "pads off a 1.76 mm PCB": pcb_front_hi - (case.Z_PF - (case.PAD_GAP + pad)) - 0.05,
        "glass off the lid, 1.4 mm panel": (pcb_front_hi - 1.4) - (case.T_FRONT - (case.GLASS_RELIEF + relief)) - 0.1,
        "clip strain with print errors, % under 1.8": 1.8 - 100 * 12 * (u + err) * case.SKIRT_T / L ** 2,
        "hook reach with print errors": (u - err) - 0.1,
        # (a deeper undercut that no longer fits is refused by case.py itself, so only the slot varies here)
        "hook fits on the beam": (case.Z_SPLIT - (case.CLIP_SLOT + slot) - 0.08)
        - (case.Z_SPLIT - case.SKIRT_H + 0.08 + (case.SKIRT_CLR + case.CLIP_UNDERCUT)
           * (1 / math.tan(math.radians(case.CLIP_LEAD)) + 1 / math.tan(math.radians(case.CLIP_CATCH))) + 0.05),
    }
    return out


def sensitivity():
    base = margins()
    worst = dict(base)
    for k in ("hole", "recess", "post", "pad", "relief", "length", "under", "slot"):
        for d in (-0.1, 0.1):
            for name, v in margins(**{k: d}).items():
                worst[name] = min(worst[name], v)
    neg = {k: round(v, 3) for k, v in worst.items() if v < 0}
    report(not neg, "session-5 margins with every new dimension moved 0.1 mm either way (worst case past each limit): "
                    + ", ".join(f"{k} {v:+.2f}" for k, v in worst.items()) + f"; below zero: {neg or 'none'}")


if __name__ == "__main__":
    sensitivity()
    mutants()
    print(f"\nRound 38: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
