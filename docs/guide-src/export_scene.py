#!/usr/bin/env python3
"""Export the STL pieces the 3D scenes are built from (guide and README renders).

Usage: python3 export_scene.py OUT_DIR

Everything is in case.py's design frame (scene.html mirrors z to show real space), except p_front and
p_cover, which are the printable STLs as they lie on the bed.
"""
import math
import os
import sys

import numpy as np
from manifold3d import Manifold

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import case  # noqa: E402


def tube(points, r):
    out = Manifold()
    for a, b in zip(points[:-1], points[1:]):
        out += Manifold.hull(Manifold.sphere(r, 24).translate(list(a)) + Manifold.sphere(r, 24).translate(list(b)))
    return out


def parts():
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    z_in = z_total - case.T_BACK
    b = case.board_model()
    out = {
        "shell": case.front_shell(z_total),
        "cover": case.back_cover(z_total, "battery"),
        "board": b["pcb"] + b["usb_c"] + b["sd_socket"] + b["esp32_module"] + b["connectors"] + b["wheel_body"]
        + b["buttons"] + b["fpc_fold"],
        "panel": b["panel"],
        "wheel": b["wheel"],
        "standoffs": b["standoffs"],
    }
    # the owner's battery, measured: silver pouch with a yellow taped end (the wire end, toward USB-C)
    x0, x1, y0, y1 = case.BATTERY_BAY
    L, W, T = case.BATTERY_SIZE
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bx0, bx1, by0, by1 = cx - L / 2, cx + L / 2, cy - W / 2, cy + W / 2
    out["battery"] = case.box(bx0 + 8.0, bx1, by0, by1, z_in - T, z_in)
    out["battery_end"] = case.box(bx0, bx0 + 8.0, by0, by1, z_in - T, z_in)
    # the owner's speaker, measured, sound face down on the grille; its white peg on the top short side
    sx, sy = case.SPEAKER["battery"]
    w, h, t = case.SPEAKER_SIZE
    out["speaker"] = case.box(sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2, z_in - t, z_in)
    out["speaker_peg"] = case.cyl_y(sx, z_in - 1.5, 1.3, sy + h / 2 - 0.1, sy + h / 2 + 1.8)
    pts, r = case.battery_wire_route()
    out["wire_bat"] = tube(pts, r)
    pts, r = case.speaker_wire_route()
    out["wire_spk"] = tube(pts, r)
    pts, r = case.speaker_cable_coil()
    out["coil_spk"] = tube(pts, r)
    screws = Manifold()
    for px, py in case.POSTS:              # M2.5 x 8 pan heads, seated in their recesses
        seat = z_total - case.SCREW_HEAD_DEPTH
        screws += case.cyl_z(px, py, 2.5, seat, seat + 1.75) + case.cyl_z(px, py, 1.25, seat - case.SCREW_LEN, seat)
    out["screws"] = screws
    out["p_front"] = case.front_for_print(out["shell"])
    out["p_cover"] = case.flip_for_print(out["cover"], z_total)
    return out


if __name__ == "__main__":
    dst = sys.argv[1]
    os.makedirs(dst, exist_ok=True)
    ps = parts()
    for name, m in ps.items():
        case.write_stl(m, os.path.join(dst, name + ".stl"))
    print("wrote", len(ps), "scene STLs to", dst)
