#!/usr/bin/env python3
"""Write specs.json, the 3D scenes of the assembly guide, from case.py: which pieces each picture
shows, the camera, and where the numbered markers go (computed from the design, so they follow it)."""
import json
import math
import os
import sys

G = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(G)))
import case  # noqa: E402

Z_TOTAL = case.Z_B + case.CAVITY["battery"] + case.T_BACK
Z_IN = Z_TOTAL - case.T_BACK
FLIP_DY = 137.7                            # parts picture: the cover, turned over, sits below the shell
C = {"shell": "#e9e6df", "cover": "#d9d4ca", "board": "#1d4f91", "panel": "#d8d8d8", "wheel": "#222222",
     "standoffs": "#c9a227", "battery": "#c9ccd1", "battery_end": "#e0b23c", "speaker": "#8f949a",
     "speaker_peg": "#f4f4f4", "foam": "#ff6a00", "wire_bat": "#d62828", "wire_spk": "#2a6fdb",
     "coil_spk": "#2a6fdb", "screws": "#3a3a3a", "p_front": "#e9e6df", "p_cover": "#d9d4ca"}
BOARD = ["board", "panel", "wheel", "standoffs"]
INSIDE = ["battery", "battery_end", "speaker", "speaker_peg", "foam"]
WIRES = ["wire_bat", "wire_spk", "coil_spk"]


def parts(names, **kw):
    return [dict({"f": n, "c": C[n]}, **kw) for n in names]


def flipped(p):
    """Where a design point of the back cover lands in the parts picture (turned over about x)."""
    x, y, z = p
    return [x, -y + FLIP_DY, -z + Z_TOTAL]


def foam_points():
    out = []
    for (px, py), (a0, a1) in zip(case.POSTS, case.POST_SECTORS):
        am = math.radians((a0 + a1) / 2)
        rm = (case.POST_RIN + case.POST_ROUT) / 2
        out.append([px + rm * math.cos(am), py + rm * math.sin(am), case.Z_B + case.FOAM_GAP / 2])
    return out


def specs():
    x0, x1, y0, y1 = case.BATTERY_BAY
    bat = [(x0 + x1) / 2, (y0 + y1) / 2, Z_IN - case.BATTERY_SIZE[2]]
    sx, sy = case.SPEAKER["battery"]
    spk = [sx, sy, Z_IN - case.SPEAKER_SIZE[2]]
    bat_wire, _ = case.battery_wire_route()
    spk_wire, _ = case.speaker_wire_route()
    coil, _ = case.speaker_cable_coil()
    coil_top = max(coil, key=lambda p: p[1])
    foam = foam_points()
    s = {}
    s["hero"] = {"parts": parts(["shell", "cover"] + BOARD), "cam": {"t": [49.75, 30, 8], "o": [-70, -110, 190]},
                 "labels": []}
    s["parts"] = {"w": 1400, "h": 1100,
                  "parts": parts(["shell"]) + parts(BOARD, dx=118)
                  + parts(["cover"] + INSIDE, flip=True, dy=FLIP_DY, dz=Z_TOTAL),
                  "cam": {"t": [108, 68, 8], "o": [0, -70, -440]},
                  "labels": [[49.75, -2.7, 6], [167.75, -0.5, 5], flipped((49.75, -2.7, 14.0)), flipped(bat),
                             flipped(spk), flipped(foam[0])]}
    s["step1"] = {"parts": parts(["shell"]) + parts(BOARD, dz=55), "cam": {"t": [49.75, 30, 26], "o": [90, -230, -190]},
                  "labels": [[79, 62.7, 4], [79, -2.7, 4], [-2.7, 30, 6], [49.75, 30, 59.9], [-2.7, 14, 6]], "h": 1000}
    s["step2"] = {"parts": parts(["cover"] + INSIDE + WIRES), "cam": {"t": [49.75, 30, 12], "o": [-40, -120, 210]},
                  "labels": [bat, spk] + foam + [list(bat_wire[-1]), list(spk_wire[-1]), list(bat_wire[0]),
                                                 list(coil_top), [sx, sy + case.SPEAKER_SIZE[1] / 2 + 1.0, Z_IN - 1.5]]}
    s["step3"] = {"parts": parts(["shell"] + BOARD) + parts(["cover"] + INSIDE + WIRES, dz=22),
                  "cam": {"t": [49.75, 30, 16], "o": [110, 200, -170]},
                  "labels": [[79, 62.7, 36], [49.75, 30, 38.7], [79, 63.5, 7]]}
    shut = parts(["shell", "cover", "screws"] + BOARD)
    s["step4a"] = {"parts": shut, "cam": {"t": [55, 15, 9], "o": [95, -150, -95]},
                   "labels": [[p, case.Y0, case.SCREW_Z] if side == "bottom" else [case.X1, p, case.SCREW_Z]
                              for p, side in case.SCREWS if side in ("bottom", "right")]}
    s["step4b"] = {"parts": shut, "cam": {"t": [15, 50, 9], "o": [-110, 150, -95]},
                   "labels": [[p, case.Y1, case.SCREW_Z] for p, side in case.SCREWS if side == "top"]}
    s["print"] = {"noflip": True, "parts": [{"f": "p_front", "c": C["p_front"]}, {"f": "p_cover", "c": C["p_cover"], "dx": 118}],
                  "cam": {"t": [108, 30, 4], "o": [0, -230, 260]},
                  "labels": [[50, -1.5, case.Z_SPLIT], [168, 30, 12.0]], "w": 1400, "h": 800}
    return s


if __name__ == "__main__":
    json.dump(specs(), open(os.path.join(G, "specs.json"), "w"))
    print("wrote specs.json")
