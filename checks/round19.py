#!/usr/bin/env python3
"""Debug round 19: methods not used in rounds 1-18.

1. A real slicer: PrusaSlicer's own mesh check (--info) on each STL: manifold, one part, the size
2. Each part sliced by PrusaSlicer with the README's settings (0.2 mm layers, 3 perimeters, 20 %
   infill) and supports OFF; the slicer's own warnings (support spots, floating parts, bed adhesion)
   must stay silent, and every G-code layer must print something
3. Material and time from the slicer, for the README

Needs PrusaSlicer on the PATH (prusa-slicer); skipped with a note if it isn't installed.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

problems = []
PARTS = ["front_shell_battery", "back_cover_battery"]
PLA_DENSITY = 1.24  # g/cm3
SETTINGS = ["--layer-height", "0.2", "--first-layer-height", "0.2", "--perimeters", "3", "--fill-density", "20%",
            "--nozzle-diameter", "0.4", "--filament-diameter", "1.75", "--temperature", "210",
            "--bed-temperature", "60", "--bed-shape", "0x0,250x0,250x210,0x210", "--center", "125,105"]


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def main():
    exe = shutil.which("prusa-slicer")
    if not exe:
        print("  ..   PrusaSlicer not installed; round 19 skipped")
        return
    total_g, total_min = 0.0, 0.0
    for name in PARTS:
        stl = os.path.join(ROOT, "stl", name + ".stl")
        info = subprocess.run([exe, "--info", stl], capture_output=True, text=True).stdout
        kv = dict(re.findall(r"^(\w+) = +(\S+)", info, re.M))
        report(kv.get("manifold") == "yes" and kv.get("number_of_parts") == "1",
               f"{name}: PrusaSlicer reads it as manifold={kv.get('manifold')}, parts={kv.get('number_of_parts')}, "
               f"{float(kv['size_x']):.1f} x {float(kv['size_y']):.1f} x {float(kv['size_z']):.1f} mm")
        with tempfile.TemporaryDirectory() as d:
            g = os.path.join(d, "out.gcode")
            r = subprocess.run([exe, "--export-gcode", *SETTINGS, "--support-material=0", "-o", g, stl],
                               capture_output=True, text=True, timeout=900)
            log = r.stdout + r.stderr
            warn = [ln.strip() for ln in log.splitlines()
                    if re.search(r"warning|detected|floating|adhesion|unsupported|collaps|error", ln, re.I)]
            report(r.returncode == 0 and not warn, f"{name}: sliced without supports, exit {r.returncode}, "
                                                    f"slicer warnings {warn or 'none'}")
            if r.returncode != 0:
                continue
            gcode = open(g).read()
            # layers that print nothing would mean a part of the model starts in mid-air or vanished
            layers = re.split(r"\n;LAYER_CHANGE\n", gcode)[1:]
            empty = [i for i, ly in enumerate(layers) if not re.search(r"^G1 [^\n]*E[\d.]+", ly, re.M)]
            zmax = float(kv["size_z"])
            report(not empty and abs(len(layers) * 0.2 - zmax) < 0.25,
                   f"{name}: {len(layers)} layers for {zmax:.1f} mm, layers with no extrusion: {empty or 'none'}")
            cm3 = float(re.search(r"filament used \[cm3\] = ([\d.]+)", gcode).group(1))
            t = re.search(r"estimated printing time \(normal mode\) = ((?:\d+h )?(?:\d+m )?\d+s)", gcode).group(1)
            mins = sum(int(v) * {"h": 60, "m": 1, "s": 1 / 60}[u] for v, u in re.findall(r"(\d+)([hms])", t))
            total_g += cm3 * PLA_DENSITY
            total_min += mins
            print(f"  ..   {name}: {cm3:.1f} cm3 of filament (about {cm3 * PLA_DENSITY:.0f} g of PLA), "
                  f"about {t} on PrusaSlicer's generic machine profile")
    text = open(os.path.join(ROOT, "README.md")).read()
    m = re.search(r"about (\d+) g of PLA", text)
    report(m is not None and abs(int(m.group(1)) - total_g) <= 2,
           f"both parts: about {total_g:.0f} g of PLA, {total_min / 60:.1f} h; README says "
           f"{m.group(0) if m else 'nothing'}")


if __name__ == "__main__":
    main()
    print(f"\nRound 19: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
