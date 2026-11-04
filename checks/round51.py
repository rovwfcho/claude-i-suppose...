#!/usr/bin/env python3
"""Debug round 51 (session 5): methods not used in rounds 1-50.

1. Where the clip beams go while the lid closes. Round 36 found how far each hook must bend inward
   to pass the lid's rim, but not what the bending beam could hit inside the case. Each beam is held
   at both ends, so pushed in at its hook it bends in the shape of a beam fixed at both ends under a
   middle load, w(x) = w_max * 4 s^2 (3 - 4 s) for s = x / L up to the middle. With w_max the most
   it bends with print errors the worst way round (the hook's reach plus 0.3 mm), the space the
   beam's inner face sweeps is cut into 0.5 mm slices along the beam, and every part inside the
   case (the board's parts with 4 mm and with 3 mm standoffs, both wires, the spare-cable loop, the
   battery and the speaker) must keep at least 0.3 mm from it.
2. The buy list, item by item: each row of the guide's buy table (English) is matched with what the
   README asks for, and the quantity and every number in the row must be in the README too.
3. A read-through of the README passages rounds 49 and 50 changed (the window, the battery wire),
   by me.
4. The case as it will be used (by me, not a script): lying on its back on a desk, lying face down,
   standing on each edge, held in a hand, with the USB-C cable in. What each does to the speaker,
   the vents, the buttons, the dial and the display.
"""
import os
import re
import sys
import json

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


def box_gap(a, b):
    """Distance between two axis-aligned boxes (x0, x1, y0, y1, z0, z1); 0 if they touch or overlap."""
    d = [max(0.0, max(a[2 * i], b[2 * i]) - min(a[2 * i + 1], b[2 * i + 1])) for i in range(3)]
    return float(np.sqrt(sum(v * v for v in d)))


def obstacles(sh):
    out = []
    d = case.STANDOFF_H - sh
    for k, m in case.board_model(standoff_h=sh).items():
        b = m.bounding_box()
        out.append((k.replace("_", " "), (b[0], b[3], b[1], b[4], b[2], b[5])))
    for label, (pts, r) in (("battery wire", case.battery_wire_route()), ("speaker cable", case.speaker_wire_route())):
        for p, q in zip(pts, pts[1:]):
            out.append((label, (min(p[0], q[0]) - r, max(p[0], q[0]) + r, min(p[1], q[1]) - r, max(p[1], q[1]) + r,
                                min(p[2], q[2]) - r + d, max(p[2], q[2]) + r + d)))
    coil, rc = case.speaker_cable_coil()
    c = np.array(coil)
    out.append(("spare-cable loop", (c[:, 0].min() - rc, c[:, 0].max() + rc, c[:, 1].min() - rc, c[:, 1].max() + rc,
                                     c[:, 2].min() - rc, c[:, 2].max() + rc)))
    z_in = case.Z_B + case.CAVITY["battery"]
    x0, x1, y0, y1 = case.BATTERY_BAY
    out.append(("battery", (x0, x1, y0, y1, z_in - case.BATTERY_SIZE[2] - 0.2, z_in)))
    sx, sy = case.SPEAKER["battery"]
    w, h, _ = case.SPEAKER_BOX["battery"]
    out.append(("speaker", (sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2, z_in - case.SPEAKER_SIZE[2] - 0.2, z_in)))
    return out


def beam_sweep():
    p, za, zb, zc, zd = case.clip_levels()
    w_max = p + 0.3                                           # round 36: errors the worst way round
    z0, z1 = case.Z_SPLIT - case.SKIRT_H, case.Z_SPLIT - case.CLIP_SLOT
    y_in = -case.CLR + case.SKIRT_CLR + case.SKIRT_T          # the skirt's inner face, bottom wall
    L = case.CLIP_L
    rows, worst = [], 9.0
    for sh in (case.STANDOFF_H, case.STANDOFF_H_MIN):
        obs = obstacles(sh)
        best = (9.0, "", 0)
        for cx, side in case.CLIPS:
            for x in np.arange(0, L, 0.5):
                s = min(x + 0.25, L - x - 0.25) / L
                w = w_max * 4 * s * s * (3 - 4 * s)
                if side == "bottom":
                    sl = (cx - L / 2 + x, cx - L / 2 + x + 0.5, y_in, y_in + w, z0, z1)
                else:
                    sl = (cx - L / 2 + x, cx - L / 2 + x + 0.5, case.BH - y_in - w, case.BH - y_in, z0, z1)
                for name, b in obs:
                    g = box_gap(sl, b)
                    if g < best[0]:
                        best = (g, name, cx, side)
        worst = min(worst, best[0])
        rows.append(f"{sh:.0f} mm standoffs: nearest the {best[1]}, {best[0]:.2f} mm from the {best[3]} beam at x {best[2]:.0f}")
    report(worst >= 0.3, f"clip beams bending in while the lid closes (up to {w_max:.2f} mm at the hook, z "
                         f"{z0:.1f}-{z1:.1f}): " + "; ".join(rows) + " (want 0.3)")


def buy_list():
    en = json.load(open(os.path.join(ROOT, "docs", "guide-src", "text_en.json"), encoding="utf-8"))
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    flat = re.sub(r"\s+", " ", readme.replace("×", "x"))
    missing = []
    for item, qty, notes in en["buy"]:
        row = re.sub(r"<[^>]+>", "", f"{item} {notes}").replace("×", "x")
        nums = re.findall(r"(?<![\w.,])\d+(?:\.\d+)?(?:–\d+(?:\.\d+)?)?", row)
        lost = [n for n in nums if n not in flat]
        q = re.sub(r"<[^>]+>", "", qty)
        if q.split()[0].isdigit() and q.split()[0] != "1" and not re.search(rf"\b{re.escape(q.split()[0])} x ", flat) \
                and q not in flat:
            lost.append(f"quantity {q}")
        if lost:
            missing.append(f"{item[:40]}: {lost}")
    report(not missing, f"buy list: all {len(en['buy'])} rows of the guide's table, with their quantities and "
                        f"numbers, are in the README" + (": missing " + "; ".join(missing) if missing else ""))


if __name__ == "__main__":
    beam_sweep()
    buy_list()
    print("  ..   read-through of the README's window and battery-wire passages: see DEBUG_LOG.md, round 51")
    print(f"\nRound 51: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
