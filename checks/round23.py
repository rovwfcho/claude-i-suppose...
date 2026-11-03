#!/usr/bin/env python3
"""Debug round 23: methods not used in rounds 1-22.

Handedness (mirror-image) test of the printed parts, in real space, with nothing taken from case.py:
features are found on the STL files as printed and compared with the real board as Waveshare's
photos show it. Looking at the display: the USB-C and microSD ports are on the LEFT end, microSD
BELOW USB-C, the wide inactive glass strip on the LEFT; the mic is on the left and the temperature
sensor on the right, both in the upper half.
For a viewer facing the display (display normal n toward the viewer), left L and up U satisfy
(L x U) . n < 0 in a right-handed frame (STL files and slicers are right-handed). A mirrored part
gives > 0. Every earlier check compared the parts with a board model in the same frame as the
design, so they could not see a mirror image; this one can.

Also the stack-up as printed: both parts are sliced by PrusaSlicer at several layer heights, and the
heights the slicer really gives the lid's rim, its pad tops and the plate over the glass, and the
cover's rim and corner-post ends, are read from the G-code (the slicer rounds every face to a layer).
From those, with the board screwed to the posts on 4 mm standoffs and a PCB 0.16 mm thicker than
assumed and standoffs 0.1 mm taller, the pads must still not press the PCB and the glass must stay
at least 0.4 mm clear of the lid (more with 3 mm standoffs).
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round19 import SETTINGS  # noqa: E402
from round20 import extrusions, holes, seg_dist  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def clusters(ys, gap=0.5):
    ys = np.sort(ys)
    if not len(ys):
        return []
    out, start = [], ys[0]
    for a, b in zip(ys[:-1], ys[1:]):
        if b - a > gap:
            out.append((start, a))
            start = b
    out.append((start, ys[-1]))
    return out


def front_shell():
    import trimesh
    tm = trimesh.load(os.path.join(ROOT, "stl", "front_shell_battery.stl"))
    lo, hi = tm.bounds
    n = np.array([0, 0, -1.0])                    # printed display face down: it faces -z
    # 1. the end wall with the big port openings: rays from outside along x, 6.4 mm above the bed
    #    (port height); a ray that gets more than 5 mm in before hitting anything went through a hole
    z = 6.4
    ys = np.arange(lo[1] + 3, hi[1] - 3, 0.1)
    ends = {}
    for sign, x0 in ((+1, lo[0] - 5), (-1, hi[0] + 5)):
        o = np.column_stack([np.full(len(ys), x0), ys, np.full(len(ys), z)])
        d = np.tile([sign, 0, 0.0], (len(o), 1))
        loc, ray, _ = tm.ray.intersects_location(o, d, multiple_hits=False)
        depth = np.full(len(o), np.inf)
        depth[ray] = np.abs(loc[:, 0] - x0) - 5
        ends[sign] = [c for c in clusters(ys[depth > 5.0]) if c[1] - c[0] > 2.0]
    port_end = max(ends, key=lambda s: sum(b - a for a, b in ends[s]))
    L = np.array([-port_end, 0, 0.0])             # the end the rays came in from
    big = sorted(ends[port_end], key=lambda c: c[1] - c[0], reverse=True)[:2]
    usb, sd = big[0], big[1]                       # USB-C is the widest opening, microSD the next
    U = np.array([0, np.sign((usb[0] + usb[1]) / 2 - (sd[0] + sd[1]) / 2), 0.0])
    h = np.dot(np.cross(L, U), n)
    report(len(big) == 2 and h < 0, f"front shell: port end at {'low' if port_end > 0 else 'high'} x with openings "
                                    f"{[(round(a, 1), round(b, 1)) for a, b in big]} (USB-C, microSD); "
                                    f"(L x U).n = {h:+.0f}: {'real board handedness' if h < 0 else 'MIRROR IMAGE'}")
    # 2. independent of the ports: the wide frame band (inactive glass strip) must be on the same end
    o = np.array([[lo[0] - 5, (lo[1] + hi[1]) / 2, 1.0]])
    s1 = np.sort(tm.ray.intersects_location(o, [[1, 0, 0]], multiple_hits=True)[0][:, 0])
    band_low, band_high = s1[1] - s1[0], s1[-1] - s1[-2]
    wide = +1 if band_low > band_high else -1
    report(wide == port_end, f"front shell: frame band {band_low:.1f} mm at low x, {band_high:.1f} mm at high x; "
                             f"the wide band is on the port end: {wide == port_end}")


def back_cover():
    import trimesh
    tm = trimesh.load(os.path.join(ROOT, "stl", "back_cover_battery.stl"))
    n = np.array([0, 0, 1.0])                     # back face on the bed: the display faces +z
    hs = holes(tm)
    info = []
    for h in hs:
        c = h.mean(0)
        ext = h.max(0) - h.min(0)
        info.append((c, max(ext) / max(min(ext), 0.1)))
    xs = np.array([c[0] for c, _ in info])
    slots = [c for c, asp in info if asp > 2.0]                  # the sensor vents are slots
    mic = [c for c, asp in info if asp <= 2.0 and abs(c[0] - xs.min()) < 3.0 and c[0] < np.median(xs)]
    if not slots or not mic:
        report(False, f"back cover: could not find the mic holes ({len(mic)}) and sensor slots ({len(slots)})")
        return
    mic_c, dht_c = np.mean(mic, 0), np.mean(slots, 0)
    lo, hi = tm.bounds
    centre = (lo[:2] + hi[:2]) / 2
    L = np.append(mic_c - dht_c, 0)
    L = L / np.linalg.norm(L)
    up = (mic_c + dht_c) / 2 - centre
    U = np.append(up - np.dot(up, L[:2]) * L[:2], 0)
    U = U / np.linalg.norm(U)
    h = np.dot(np.cross(L, U), n)
    report(h < 0, f"back cover: {len(mic)} mic holes at {np.round(mic_c, 1).tolist()}, {len(slots)} sensor slots at "
                  f"{np.round(dht_c, 1).tolist()}; (L x U).n = {h:+.2f}: "
                  f"{'real board handedness' if h < 0 else 'MIRROR IMAGE'}")


def top_at(ex, pt, r=0.3):
    """Height of the highest layer that extrudes within r of the point (print coordinates)."""
    best = None
    for z, segs in ex.items():
        if len(segs) and seg_dist(np.array([pt]), segs)[0] < r and (best is None or z > best):
            best = z
    return best


def stack_as_printed():
    exe = shutil.which("prusa-slicer")
    if not exe:
        print("  ..   PrusaSlicer not installed; as-printed stack-up skipped")
        return
    import trimesh
    meshes = {n: trimesh.load(os.path.join(ROOT, "stl", n + ".stl")) for n in ("front_shell_battery", "back_cover_battery")}
    px, py = case.POSTS[1]
    for lh in (0.1, 0.15, 0.2, 0.3):
        tops = {}
        for name, tm in meshes.items():
            with tempfile.TemporaryDirectory() as d:
                g = os.path.join(d, "out.gcode")
                st = list(SETTINGS)
                st[st.index("--layer-height") + 1] = str(lh)
                subprocess.run([exe, "--export-gcode", *st, "--support-material=0", "-o", g, os.path.join(ROOT, "stl", name + ".stl")],
                               capture_output=True, text=True, timeout=900, check=True)
                ex = extrusions(open(g).read())
            lo, hi = tm.bounds
            shift = np.array([125.0, 105.0]) - (lo[:2] + hi[:2]) / 2
            if name.startswith("front"):
                mirror = lambda x, y: (case.BW - x, y)          # front_for_print mirrors x about the board centre
                tops["pad"] = top_at(ex, np.array(mirror(49.0, 0.05)) + shift)
                tops["seam"] = top_at(ex, np.array(mirror(30.0, -2.0)) + shift)
                tops["lip"] = top_at(ex, np.array(mirror(52.0, 2.2)) + shift)     # plate over the glass
            else:
                tops["rim"] = top_at(ex, np.array([30.0, -2.0]) + shift)
                tops["post"] = top_at(ex, np.array([px - 2.6, py + 0.5]) + shift)
        post_z = tops["seam"] - (tops["post"] - tops["rim"])        # post end, in the lid's print heights
        pcb_front = post_z - case.STANDOFF_H - case.PCB_T
        pad_gap = pcb_front - tops["pad"]
        glass_gap = pcb_front - case.PANEL_T - tops["lip"]
        worst_pad, worst_glass = pad_gap - 0.26, glass_gap - 0.26
        ok = worst_pad >= 0.0 and worst_glass >= 0.4
        msg = (f"{lh} mm layers: lid rim {tops['seam']}, pad top {tops['pad']}, plate over the glass {tops['lip']}; cover "
               f"rim {tops['rim']}, post end {tops['post']} -> pads {pad_gap:.2f} mm in front of the PCB (worst "
               f"{worst_pad:.2f}), glass {glass_gap:.2f} mm clear of the lid (worst {worst_glass:.2f})")
        if lh <= 0.2:
            report(ok, msg)
        else:
            print(("  ..   " if ok else "  ..   NOT RECOMMENDED: ") + msg)


if __name__ == "__main__":
    front_shell()
    back_cover()
    stack_as_printed()
    print(f"\nRound 23: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
