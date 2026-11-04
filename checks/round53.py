#!/usr/bin/env python3
"""Debug round 53 (session 5): methods not used in rounds 1-52.

1. Standing it up. Round 51 tells you to stand the case up, or lay it face down, to hear the speaker.
   Here the closed case is put on a table on each of its six faces. The whole device's centre of
   mass is worked out from the parts: the two printed parts from their STLs (PLA, 1.24 g/cm3), the
   board's parts from the board model (glass-epoxy 1.85, the display's glass 2.5, the other parts
   2.0), the battery (a pouch cell, about 2.1 g/cm3, tried from 1.8 to 2.4) and the speaker (3 g).
   On each edge the angle it tips over at is found, and how near the table the board's parts come
   (the buttons, the dial, the USB-C socket; the board can sit up to 0.3 mm nearer an edge). On its
   bottom edge the case must tip over only past 5 degrees either way (a phone on its edge tips at
   about 2), with no board part within the board's play of the table; lying on its back or front, no
   board part and no screw head may touch the table; and the speaker advice in the README and both
   guides must name the edge that works.
2. The window from 0 to 50 degC. Round 41 checked the board's clearances in heat and cold, round 49
   the window with the board anywhere in its play, at room temperature. Once screwed in, the board
   stays where it was put, while the window, in PLA (about 68 um per metre per degree), grows and
   shrinks about the lid's middle more than the board's glass-epoxy (about 14). At 0 and 50 degC,
   with the board in each of round 49's nine positions, the window must still hide nothing of the
   light field; and with round 52's random builds at 10 degC (a cold room), fewer than 1 in 100 may
   hide a whole row or column of pixels.
3. The guides on paper. Each picture in the two PDFs, at the size it is printed, must have at least
   150 pixels per inch (below that a print looks soft or blocky).
"""
import contextlib
import io
import math
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402

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
def mass_parts(bat_density=2.1):
    import trimesh
    from round1 import load_assembled
    shell, _, cover, zt = load_assembled("battery")
    out = [("lid", shell.volume / 1000 * 1.24, shell.center_mass), ("cover", cover.volume / 1000 * 1.24, cover.center_mass)]
    for k, m in case.board_model().items():
        if m.volume() <= 0:
            continue
        g = m.to_mesh()
        tm = trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts))
        out.append((k, m.volume() / 1000 * {"pcb": 1.85, "panel": 2.5}.get(k, 2.0), tm.center_mass))
    z_in = case.Z_B + case.CAVITY["battery"]
    x0, x1, y0, y1 = case.BATTERY_BAY
    bx, by, bz = case.BATTERY_SIZE
    out.append(("battery", bx * by * bz / 1000 * bat_density, np.array([(x0 + x1) / 2, (y0 + y1) / 2, z_in - bz / 2])))
    sx, sy = case.SPEAKER["battery"]
    out.append(("speaker", 3.0, np.array([sx, sy, z_in - case.SPEAKER_SIZE[2] / 2])))
    return out, shell, cover, zt


def screws(zt):
    """The four screw heads, seated in their recesses: (x0, x1, y0, y1, z0, z1) boxes."""
    seat = zt - case.SCREW_HEAD_DEPTH
    return [(px - 2.5, px + 2.5, py - 2.5, py + 2.5, seat, seat + case.SCREW_HEAD_K) for px, py in case.POSTS]


def standing():
    import json
    import re
    rows, ok = [], True
    parts, shell, cover, zt = mass_parts()
    V = np.vstack([shell.vertices, cover.vertices])
    lo, hi = V.min(0), V.max(0)
    total = sum(m for _, m, _ in parts)
    cgs = []
    for d in (1.8, 2.1, 2.4):
        p = mass_parts(d)[0] if d != 2.1 else parts
        cgs.append(sum(m * c for _, m, c in p) / sum(m for _, m, c in p))
    cg = cgs[1]
    boxes = {k: m.bounding_box() for k, m in case.board_model().items()}       # x0 y0 z0 x1 y1 z1
    sc = screws(zt)
    for face, ax, sgn in (("bottom edge", 1, -1), ("top edge", 1, 1), ("left end", 0, -1), ("right end", 0, 1),
                          ("back", 2, 1), ("front", 2, -1)):
        t = lo[ax] if sgn < 0 else hi[ax]
        # how far inside the table's plane each board part and the screw heads stop (negative: past it)
        reach = min([(sgn * (t - (b[ax] if sgn < 0 else b[3 + ax])), k) for k, b in boxes.items()]
                    + [(sgn * (t - (s[2 * ax] if sgn < 0 else s[2 * ax + 1])), "screw heads") for s in sc])
        name = reach[1].replace("_", " ")
        if ax == 2:
            # front and back: the screws hold the board in depth, so only 0.05 mm is asked
            ok &= reach[0] > 0.05
            rows.append(f"lying on its {face}: nearest the table the {name}, {reach[0]:.2f} mm in")
            continue
        on = V[np.abs(V[:, ax] - t) < 0.05]
        za, zb = on[:, 2].min(), on[:, 2].max()
        tips = []
        for c in cgs:
            h = abs(c[ax] - t)
            tips.append((math.degrees(math.atan2(c[2] - za, h)), math.degrees(math.atan2(zb - c[2], h))))
        fwd, back = min(f for f, _ in tips), min(b for _, b in tips)
        # on an edge the board can sit up to CLR nearer the table, so a board part must stop further in than that
        clear = reach[0] > case.CLR
        txt = (f"on its {face}: tips over past {fwd:.1f}° forward and {back:.1f}° back; nearest the table the {name}, "
               f"{reach[0]:.2f} mm in" + ("" if clear else f", so with the board {case.CLR} mm that way it takes the weight"))
        if face == "bottom edge":
            ok &= fwd >= 5.0 and back >= 5.0 and clear
        rows.append(txt)
    # the advice must name the edge that works
    readme = re.sub(r"\s+", " ", open(os.path.join(ROOT, "README.md"), encoding="utf-8").read())
    gd = os.path.join(ROOT, "docs", "guide-src")
    en = " ".join(json.load(open(os.path.join(gd, "text_en.json"), encoding="utf-8"))["tips"])
    bg = " ".join(json.load(open(os.path.join(gd, "text_bg.json"), encoding="utf-8"))["tips"])
    said = {"README": bool(re.search(r"muffled: stand it on its bottom edge", readme)),
            "EN guide": "muffled: stand it on its bottom edge" in en,
            "BG guide": "приглушен: изправете я на долния ѝ ръб" in bg}
    ok &= all(said.values())
    report(ok, f"standing it up: {total:.0f} g in all, centre of mass {cg[2]:.1f} mm behind the front face "
               f"({min(c[2] for c in cgs):.1f}-{max(c[2] for c in cgs):.1f} with the battery 1.8-2.4 g/cm3), "
               f"{cg[1] - lo[1]:.1f} mm above the bottom edge; " + "; ".join(rows)
               + "; the speaker advice names the bottom edge in " + ", ".join(k for k, v in said.items() if v)
               + ("" if all(said.values()) else f", not in {[k for k, v in said.items() if not v]}")
               + " (want the bottom edge to tip only past 5° either way with no board part within the board's play "
                 "of the table, and the advice to say so)")


# ------------------------------------------------------------------ 2
A_PLA, A_BOARD = 68e-6, 14e-6


def window_temperature():
    import round45
    with contextlib.redirect_stdout(io.StringIO()):
        round45.across_photos()
    field = np.array([8.0, 95.2, *round45.LIGHT_Y])
    centre = np.array([case.BW / 2, case.BW / 2, case.BH / 2, case.BH / 2])
    win = np.array([case.WIN_CX - case.WIN_W / 2, case.WIN_CX + case.WIN_W / 2,
                    case.WIN_CY - case.WIN_H / 2, case.WIN_CY + case.WIN_H / 2])
    p = case.CLR
    rows, ok = [], True
    for T in (0.0, 50.0):
        dT = T - 20.0
        w = centre + (win - centre) * (1 + A_PLA * dT)
        worst = np.full(4, 9.0)
        for dx in (-p, 0.0, p):
            for dy in (-p, 0.0, p):
                f = centre + np.array([dx, dx, dy, dy]) + (field - centre) * (1 + A_BOARD * dT)
                worst = np.minimum(worst, [f[0] - w[0], w[1] - f[1], f[2] - w[2], w[3] - f[3]])
        ok &= worst.min() > 0
        rows.append(f"at {T:.0f} °C " + ", ".join(f"{k} {v:.2f}" for k, v in zip(("left", "right", "bottom", "top"), worst)))

    def random_builds(T, n=200_000, seed=53):
        rng = np.random.default_rng(seed)
        half = np.array([case.BW / 2 + case.CLR, case.BH / 2 + case.CLR])
        s = rng.uniform(0.002, 0.004, n)
        play = np.maximum(case.CLR - s[:, None] * half[None], 0.0)
        off = rng.uniform(-1, 1, (n, 2)) * play
        dT = T - 20.0
        w = centre + (win - centre) * (1 - s[:, None]) * (1 + A_PLA * dT) + rng.normal(0, 0.05, (n, 4))
        f = (centre + (field - centre) * (1 + A_BOARD * dT) + rng.normal(0, 0.1, (n, 4))
             + np.column_stack([off[:, 0], off[:, 0], off[:, 1], off[:, 1]]))
        hidden = np.column_stack([w[:, 0] - f[:, 0], f[:, 1] - w[:, 1], w[:, 2] - f[:, 2], f[:, 3] - w[:, 3]])
        return float((hidden.max(1) > 86.4 / 800).mean())
    p10, p0 = random_builds(10.0), random_builds(0.0)
    ok &= p10 < 0.01
    report(ok, "window from 0 to 50 °C (the PLA lid against the board), worst of round 49's nine board positions, mm "
               "to spare: " + "; ".join(rows) + f"; round 52's random builds at 10 °C hide a whole pixel row or column "
               f"in {p10 * 100:.2f} % ({p0 * 100:.2f} % at 0 °C) (want nothing hidden at 0 and 50 °C, under 1 % at 10 °C)")


# ------------------------------------------------------------------ 3
def print_resolution():
    if not shutil.which("pdfimages"):
        skip("guides on paper: pdfimages is not installed")
        return
    rows, ok = [], True
    for lang in ("en", "bg"):
        out = subprocess.run(["pdfimages", "-list", os.path.join(ROOT, "docs", f"assembly_guide_{lang}.pdf")],
                             capture_output=True, text=True).stdout.splitlines()[2:]
        pics = []
        for line in out:
            c = line.split()
            if c[2] != "image" or int(c[3]) < 200:      # the small grey images are the markers' shadows
                continue
            pics.append((min(float(c[12]), float(c[13])), int(c[0]), int(c[3]), int(c[4])))
        low = min(pics)
        ok &= low[0] >= 150 and len(pics) >= 8
        rows.append(f"{lang.upper()} {len(pics)} pictures, the softest {low[0]:.0f} ppi ({low[2]} x {low[3]} px on page {low[1]})")
    report(ok, "guides on paper, each picture at its printed size: " + "; ".join(rows) + " (want 150 ppi)")


if __name__ == "__main__":
    standing()
    window_temperature()
    print_resolution()
    print(f"\nRound 53: {len(problems)} problem(s), {len(skipped)} skipped")
    for p in problems:
        print("  -", p)
