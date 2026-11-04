#!/usr/bin/env python3
"""Debug round 17: methods not used in rounds 1-16.

1. Mutation test of the README's "If something doesn't fit" advice: each constant it tells you to
   edit is changed in a copy of case.py, the copy is run the way the README says, and the STL files
   it writes must change (and the change must be the one the README promises)
2. Frame widths measured on the front shell STL with rays across the front face, compared with the
   numbers the README and preview/explained.png give, and with the display's picture area
3. Nothing left over from the removed slim version in the README, the zip, stl/ or dist/
"""
import hashlib
import os
import re
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

MODEL_ONLY = {"STANDOFF_H"}

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def build_copy(src, out):
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "case.py"), "w").write(src)
        subprocess.run([sys.executable, os.path.join(d, "case.py"), out], check=True, capture_output=True)
    return {f: hashlib.sha256(open(os.path.join(out, f), "rb").read()).hexdigest() for f in sorted(os.listdir(out))}


# ------------------------------------------------------------------ 1
def mutation():
    text = open(os.path.join(ROOT, "README.md")).read()
    section = text.split("### If something doesn't fit", 1)[1].split("Then run", 1)[0]
    named = list(dict.fromkeys(re.findall(r"`([A-Z][A-Z0-9_]+)`", section)))
    src = open(os.path.join(ROOT, "case.py")).read()
    edits = {  # one small change per constant, made the way a user would make it
        "WIN_CX": ("WIN_CX, WIN_CY = 52.0, 29.8", "WIN_CX, WIN_CY = 52.5, 29.8"),
        "WIN_CY": ("WIN_CX, WIN_CY = 52.0, 29.8", "WIN_CX, WIN_CY = 52.0, 30.3"),
        "CLR": ("CLR = 0.3 ", "CLR = 0.4 "),
        "PANEL_T": ("PANEL_T = 1.2 ", "PANEL_T = 1.5 "),
        "PCB_T": ("PCB_T = 1.6 ", "PCB_T = 1.7 "),
        "USB_Y": ("USB_Y = 30.0 ", "USB_Y = 30.5 "),
        "SD_Y": ("SD_Y = 13.95 ", "SD_Y = 14.45 "),
        "WHEEL": ("WHEEL = (79.0,", "WHEEL = (79.5,"),
        "BUTTONS": ('BUTTONS = {"BOOT": 74.0,', 'BUTTONS = {"BOOT": 74.5,'),
        "STANDOFF_H": ("STANDOFF_H = 4.0 ", "STANDOFF_H = 3.5 "),
        "POSTS": ("POSTS = [(2.45, 2.725),", "POSTS = [(2.55, 2.725),"),
        "POST_STANDOFF": ("POST_STANDOFF = 4.0 ", "POST_STANDOFF = 4.5 "),
        "PARTS_SPACE": ("PARTS_SPACE = 5.0 ", "PARTS_SPACE = 6.0 "),
        "BATTERY_SPACE": ("BATTERY_SPACE = 5.0 ", "BATTERY_SPACE = 6.0 "),
        "BATTERY_BAY": ("BATTERY_BAY = (5.5, 68.0, 6.5, 49.0)", "BATTERY_BAY = (5.5, 68.5, 6.5, 49.0)"),
        "SPEAKER_BOX": ('SPEAKER_BOX = {"battery": (11.2, 15.3, 4.5)}', 'SPEAKER_BOX = {"battery": (11.5, 15.3, 4.5)}'),
    }
    report(set(named) <= set(edits), f"README names {named}; all have a test edit: {set(named) <= set(edits)}")
    with tempfile.TemporaryDirectory() as base:
        ref = build_copy(src, os.path.join(base, "ref"))
        for name in named:
            old, new = edits[name]
            if src.count(old) != 1:
                report(False, f"{name}: could not find '{old}' in case.py")
                continue
            got = build_copy(src.replace(old, new), os.path.join(base, name))
            changed = [f for f in ref if ref[f] != got.get(f)]
            if name in MODEL_ONLY:  # describes the board for the checks; the README must say so
                said = re.search(rf"`{name}` only describes the board for the checks", section) is not None
                report(not changed and said, f"README: {name} is a check-model number: STLs unchanged "
                                             f"({not changed}), README says so ({said})")
                continue
            report(bool(changed), f"README: editing {name} ({old.strip()} -> {new.split('=')[-1].strip()}) "
                                  f"changes the printed parts: {changed or 'NOTHING'}")
            if name in ("PARTS_SPACE", "BATTERY_SPACE"):
                import trimesh
                m = trimesh.load(os.path.join(base, name, "front_shell_battery.stl"))
                c = trimesh.load(os.path.join(base, name, "back_cover_battery.stl"))
                print(f"  ..   {name} +1 mm: front shell {m.bounds[1][2]:.1f} mm tall, back cover {c.bounds[1][2]:.1f} mm")


# ------------------------------------------------------------------ 2
def frame_widths():
    import trimesh
    from round1 import load_assembled
    shell = load_assembled("battery")[0]  # the STL is mirrored for printing; this puts it back
    z = 1.0  # inside the front skin, past the 0.8 mm window chamfer
    widths = {}
    for label, o, d in (("left", [-20, 30.0, z], [1, 0, 0]), ("right", [130, 30.0, z], [-1, 0, 0]),
                        ("bottom", [49.75, -20, z], [0, 1, 0]), ("top", [49.75, 90, z], [0, -1, 0])):
        locs, _, _ = shell.ray.intersects_location([o], [d], multiple_hits=True)
        s = np.sort((locs - np.array(o)) @ np.array(d, float))
        widths[label] = s[1] - s[0]  # outer surface in, window edge out
    # the edge rounding moves the outer surface in at this depth; the window edge is exact here
    ins = case.surface_inset(z, 16.7)
    ch = 0.0
    expect = {"left": (case.WIN_CX - case.WIN_W / 2) - (-case.CLR - case.WALL) - ins - ch,
              "right": (case.BW + case.CLR + case.WALL) - (case.WIN_CX + case.WIN_W / 2) - ins - ch,
              "bottom": (case.WIN_CY - case.WIN_H / 2) - (-case.CLR - case.WALL) - ins - ch,
              "top": (case.BH + case.CLR + case.WALL) - (case.WIN_CY + case.WIN_H / 2) - ins - ch}
    for k in widths:
        print(f"  ..   {k} frame at z={z}: measured {widths[k]:.2f} mm, from the design numbers {expect[k]:.2f} mm")
    nominal = {"left": (case.WIN_CX - case.WIN_W / 2) + case.CLR + case.WALL,
               "right": case.BW + case.CLR + case.WALL - (case.WIN_CX + case.WIN_W / 2)}
    text = open(os.path.join(ROOT, "README.md")).read()
    ok = all(abs(widths[k] - expect[k]) < 0.15 for k in widths)
    report(ok, f"frame widths on the STL match the design within 0.15 mm: "
               f"{ {k: round(v, 2) for k, v in widths.items()} }")
    left_txt = f"{nominal['left']:.1f} mm vs about 6 mm"
    report(left_txt in text, f"README gives the left frame as '{left_txt}': {left_txt in text}")
    # the picture area from Waveshare's drawing's dimension lines: x 9.3-95.7 (see case.py)
    a0, a1 = 9.3, case.BW - 95.7
    s = f"It starts {a0:.1f} mm from the left PCB edge but ends {a1:.1f} mm from the right one"
    report(s in text, f"README: '{s}': {s in text}")
    m0, m1 = a0 - (case.WIN_CX - case.WIN_W / 2), (case.WIN_CX + case.WIN_W / 2) - 95.7
    said = f"at least 0.7 mm of margin all round, and {m0:.1f} mm on the left" in text
    report(m0 >= 0.7 and m1 >= 0.7 and said,
           f"window margin around the drawing's picture area: {m0:.2f} mm left, {m1:.2f} mm right; the README says so: {said}")


# ------------------------------------------------------------------ 3
def leftovers():
    hits = []
    text = open(os.path.join(ROOT, "README.md")).read()
    # the slim version was 14.2 mm thick; 14.2 alone is now also the speaker's length, so look for the
    # thickness wording
    for word in ("slim", "14.2 mm thick", "14.2mm", "both versions", "same version"):
        if word.lower() in text.lower():
            hits.append(f"README: {word}")
    # nor from the side-screw closure the corner screws replaced (session 5): foam, pilots, blocks
    import json
    g = os.path.join(ROOT, "docs", "guide-src")
    docs = {"README": text}
    for lang in ("en", "bg"):
        docs[f"{lang} guide"] = json.dumps(json.load(open(os.path.join(g, f"text_{lang}.json"), encoding="utf-8")),
                                           ensure_ascii=False)
    for doc, t in docs.items():
        for word in ("foam", "pre-cut", "pilot", "side screw", "screw block", "drawbore", "never longer than 7",
                     "пяна", "нарежете резбите", "предварително"):
            if word.lower() in t.lower():
                hits.append(f"{doc}: {word}")
    for d in ("stl", "dist", "preview"):
        for f in os.listdir(os.path.join(ROOT, d)):
            if "slim" in f or "compare_speaker" in f:
                hits.append(f"{d}/{f}")
    for f in os.listdir(os.path.join(ROOT, "dist")):
        with zipfile.ZipFile(os.path.join(ROOT, "dist", f)) as z:
            for n in z.namelist():
                if "slim" in n:
                    hits.append(f"{f}: {n}")
            readme = [n for n in z.namelist() if n.endswith("README.md")]
            if readme and "slim" in z.read(readme[0]).decode().lower():
                hits.append(f"{f}: README mentions slim")
    report(not hits, f"leftovers of the removed slim version: {hits or 'none'}")


if __name__ == "__main__":
    leftovers()
    frame_widths()
    mutation()
    print(f"\nRound 17: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
