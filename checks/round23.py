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

Also the foam that presses the board against the front pads, as printed: both parts are sliced by
PrusaSlicer at several layer heights, and the heights the slicer really gives the pad tops, the seam
and the ring faces are read from the G-code (the slicer rounds every face to a layer). From those,
the gap the foam tape fills is worked out. The screw's position is read the same way: the top of
the wall hole and the axis of the block's pilot as printed give how far the foam can push the cover
back before the M2 shank meets the hole's edge (and whether the shank would have to cut into it).
Foam of 1.0 and 1.2 mm (the README's range) must stay squeezed (at least 10 %, at most 75 %) with
the PCB 0.16 mm thinner or thicker than assumed and that back-off, and the shank must not cut more
than 0.05 mm into the wall hole.
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


def foam_as_printed():
    exe = shutil.which("prusa-slicer")
    if not exe:
        print("  ..   PrusaSlicer not installed; as-printed foam gap skipped")
        return
    import trimesh
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK

    def open_layers(ex, pt, z0, z1):
        """Layers between z0 and z1 with no extrusion within 0.25 mm of the point (a hole there)."""
        return sorted(z for z, segs in ex.items() if z0 <= z <= z1 and len(segs)
                      and seg_dist(np.array([pt]), segs)[0] > 0.25)
    meshes = {n: trimesh.load(os.path.join(ROOT, "stl", n + ".stl")) for n in ("front_shell_battery", "back_cover_battery")}
    px, py = case.POSTS[1]
    ring_pt = (px + 4.1 * math.cos(math.radians(135)), py + 4.1 * math.sin(math.radians(135)))
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
                hole = open_layers(ex, np.array(mirror(20.0, -0.8)) + shift, case.SCREW_Z - 1.6, case.SCREW_Z + 1.6)
                tops["hole_top"] = max(hole)              # bottom screw at x = 20, inside the wall
            else:
                tops["rim"] = top_at(ex, np.array([30.0, -2.0]) + shift)
                tops["ring"] = top_at(ex, np.array(ring_pt) + shift)
                zp = z_total - case.SCREW_Z                # the pilot axis in print height
                pil = open_layers(ex, np.array([20.0, 3.0]) + shift, zp - 1.2, zp + 1.2)  # stay inside the block
                tops["pilot"] = (min(pil) - lh + max(pil)) / 2
        ring_z = tops["seam"] - (tops["ring"] - tops["rim"])
        pilot_z = tops["seam"] - (tops["pilot"] - tops["rim"])     # assembled height of the screw axis
        slack = tops["hole_top"] - (pilot_z + 0.97)              # room before an M2 shank (r 0.97-1.0) meets it
        cut = (pilot_z + 1.0) - tops["hole_top"]                 # how far the shank would cut into the hole
        gap = ring_z - (tops["pad"] + case.PCB_T)
        g_max, g_min = gap + 0.16 + max(slack, 0.0), gap - 0.16
        c_min, c_max = 1 - g_max / 1.0, 1 - g_min / 1.2          # thinnest foam at the widest gap, and v.v.
        ok = c_min >= 0.10 and c_max <= 0.75 and cut <= 0.05
        msg = (f"{lh} mm layers: pad top {tops['pad']}, seam {tops['seam']}, cover rim {tops['rim']}, ring face "
               f"{tops['ring']} -> foam gap {gap:.2f} mm (designed {case.FOAM_GAP}); 1.0-1.2 mm foam squeezed "
               f"{100 * c_min:.0f}-{100 * c_max:.0f} % over PCB +/-0.16; screw: hole top {tops['hole_top']}, axis "
               f"{pilot_z:.2f}, back-off {max(slack, 0):.2f} mm, shank cuts {max(cut, 0):.2f} mm into the hole")
        if lh <= 0.2:
            report(ok, msg)
        else:
            print(("  ..   " if ok else "  ..   NOT RECOMMENDED: ") + msg)


if __name__ == "__main__":
    front_shell()
    back_cover()
    foam_as_printed()
    print(f"\nRound 23: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
