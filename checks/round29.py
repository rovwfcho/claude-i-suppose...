#!/usr/bin/env python3
"""Debug round 29 (session 4): methods not used in rounds 1-28.

1. Tolerance stack-up, statistically: 100 000 random cases combining the measuring error of your
   photos (0.15 mm standard deviation), printing error (pockets print about 0.1 mm small, +/-0.1 mm)
   and PLA shrinkage (0.2-0.4 %). The battery and the speaker must go in in at least 99.9 % of the
   cases, have no more than 1.2 mm of play per side in at least 99 %, and the speaker's cable and peg
   must clear the corner brackets in at least 99 %; the battery plus tape (and some swelling) must
   fit its 5 mm layer in at least 99.9 %.
2. The guide's pictures, checked by the computer: each picture is rendered again in flat, unlit
   colours, one colour per part (an "ID picture"), and the part each numbered marker names must
   show up within 20 px of the marker.
3. Numbers across three documents: the README, the English guide and the Bulgarian guide (decimal
   commas) must give the same sizes, wire lengths, play, screw lengths and material, and those must be
   the ones from case.py and the checks.
4. Cables with real bends: every corner of the wire routes and the spare-cable loop is rounded, and
   the radius each corner can take is worked out from the straight lengths beside it. The sleeved
   speaker cable needs 3 mm, its thin leads at each end and the battery wires 1 mm. The rounded tubes
   must still clear everything.
5. Calipers on the printed cover: rays between the guide bars and between the speaker brackets of the
   exported back cover measure the bay and the pocket.
6. Heat, a textbook estimate: how warm the closed PLA case gets inside with 1 W of heat (charging and
   Wi-Fi), and in full sun; the README must warn where PLA (softens at about 55 °C) is at risk.
"""
import contextlib
import io
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GUIDE = os.path.join(ROOT, "docs", "guide-src")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, GUIDE)
import case  # noqa: E402
from manifold3d import Manifold  # noqa: E402
from round1 import load_assembled, to_manifold, vol  # noqa: E402

problems = []
skipped = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def skip(msg):
    print("  SKIP " + msg)
    skipped.append(msg)


def measured():
    """The sizes round 28 reads off your photos."""
    import round28
    with contextlib.redirect_stdout(io.StringIO()):
        got = round28.sizes()
    return got


# ------------------------------------------------------------------ 1
def tolerance(got, n=100_000, seed=29):
    rng = np.random.default_rng(seed)

    def part(mean):
        return rng.normal(mean, 0.15, n)

    def pocket(nominal):
        return nominal * (1 - rng.uniform(0.002, 0.004, n)) - rng.normal(0.1, 0.1, n)

    x0, x1, y0, y1 = case.BATTERY_BAY
    pw, ph, _ = case.SPEAKER_BOX["battery"]
    for label, size, room in (("battery length", got["battery length"], x1 - x0),
                              ("battery width", got["battery width"], y1 - y0),
                              ("speaker width", got["speaker width"], pw),
                              ("speaker length", got["speaker length"], ph)):
        gap = pocket(room) - part(size)
        p_stuck = float((gap <= 0).mean())
        p_loose = float((gap / 2 > 1.2).mean())
        report(p_stuck <= 0.001 and p_loose <= 0.01,
               f"{label}: {size:.2f} mm part in a {room} mm space, printed: play per side "
               f"{np.percentile(gap, 0.1) / 2:.2f}-{np.percentile(gap, 99.9) / 2:.2f} mm (0.1-99.9 %); "
               f"won't go in {100 * p_stuck:.3f} %, looser than 1.2 mm {100 * p_loose:.2f} %")
    # thickness: cell + tape (0.08-0.2 mm) + swelling as it ages (0-0.3 mm), against the free depth
    # under the bay: the highest wire or board part beneath it (the 5 mm layer is only the nominal room)
    t = part(got["battery thickness"]) + rng.uniform(0.08, 0.2, n) + rng.uniform(0.0, 0.3, n)
    free = free_depth_under_bay()
    p_over = float((t > free).mean())
    report(p_over <= 0.001, f"battery + tape + swelling {np.percentile(t, 50):.2f} mm (99.9 %: "
                            f"{np.percentile(t, 99.9):.2f}); {free:.2f} mm free above the wires and parts under the "
                            f"bay; reaches them in {100 * p_over:.3f} %; over the nominal {case.BATTERY_SPACE} mm "
                            f"in {100 * float((t > case.BATTERY_SPACE).mean()):.2f} %")
    # cable and peg against the bracket legs
    wall, _, leg_x, leg_y = case.SPK_BRACKET
    L, W = part(got["speaker length"]), part(got["speaker width"])
    exit_ = rng.normal(case.SPK_CABLE_EXIT, 0.15, n)
    half = rng.uniform(0.8, 1.2, n)                     # the flat flex is 1.6-2.4 mm wide
    ry = np.maximum(pocket(ph) - L, 0) / 2
    gap_cable = (pocket(ph) / 2 - leg_y) - (L / 2 - exit_ + half) - ry * rng.uniform(0, 1, n)
    peg_off = rng.normal(1.0, 0.3, n)                   # the peg sits about 1 mm off the side's middle
    rx = np.maximum(pocket(pw) - W, 0) / 2
    gap_peg = (pocket(pw) / 2 - leg_x) - (np.abs(peg_off) + 1.3) - rx * rng.uniform(0, 1, n)
    p_c, p_p = float((gap_cable < 0).mean()), float((gap_peg < 0).mean())
    report(p_c <= 0.01 and p_p <= 0.01, f"speaker cable touches a bracket leg in {100 * p_c:.2f} %, the peg in "
                                        f"{100 * p_p:.2f} % (median clearances {np.median(gap_cable):.2f} / "
                                        f"{np.median(gap_peg):.2f} mm)")


def free_depth_under_bay():
    """From the inside of the back wall down to the highest wire or modelled board part under the bay."""
    from round13 import tube
    z_in = case.Z_B + case.CAVITY["battery"]
    x0, x1, y0, y1 = case.BATTERY_BAY
    under = case.box(x0, x1, y0, y1, case.Z_B, z_in)
    things = Manifold()
    for g in case.board_model().values():
        things += g
    for pts, r in (case.battery_wire_route(), case.speaker_wire_route()):
        things += tube(pts, r)
    top = (things ^ under).bounding_box()[5]
    return z_in - top


# ------------------------------------------------------------------ 2
ID_EXPECT = {
    "parts": [["shell"], ["board", "panel", "standoffs", "wheel"], ["cover"], ["battery", "battery_end"],
              ["speaker", "speaker_peg"], ["cover"]],
    "step1": [["shell", "wheel", "board"], ["shell", "board"], ["shell", "board"],
              ["board", "panel", "standoffs"], ["shell", "board"]],
    "step2": [["battery", "battery_end"], ["speaker"], ["cover"], ["cover"], ["cover"], ["cover"], ["wire_bat"],
              ["wire_spk"], ["wire_bat"], ["coil_spk"], ["speaker_peg"]],
    "step3": [["cover"], ["cover"], ["wheel", "shell"], ["cover"], ["cover"], ["cover"], ["cover"]],
    "step4a": [["screws"], ["screws"], ["screws"], ["screws"]],
    "step4b": [["shell", "cover"]],
    "print": [["p_front"], ["p_cover"]],
}


def free_port(p):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", p)) != 0


def id_pictures():
    node = shutil.which("node")
    if not node or subprocess.run([node, "-e", "require('playwright')"], capture_output=True).returncode != 0:
        skip("ID pictures: node with playwright is not installed")
        return
    if not free_port(8766):
        skip("ID pictures: port 8766 is busy (the guide build may be running)")
        return
    import export_scene
    from PIL import Image
    specs = json.load(open(os.path.join(GUIDE, "specs.json")))
    with tempfile.TemporaryDirectory() as d:
        for f in ("scene.html", "shoot.js"):
            shutil.copy(os.path.join(GUIDE, f), d)
        three = [os.path.join(GUIDE, f) for f in ("three.module.js", "STLLoader.js")]
        if all(os.path.exists(f) for f in three):
            for f in three:
                shutil.copy(f, d)
        else:
            r = subprocess.run(["sh", "-c", "curl -sSf -o three.tgz https://registry.npmjs.org/three/-/three-0.160.0.tgz && "
                                "tar -xzf three.tgz package/build/three.module.js package/examples/jsm/loaders/STLLoader.js && "
                                "cp package/build/three.module.js package/examples/jsm/loaders/STLLoader.js ."],
                               cwd=d, capture_output=True)
            if r.returncode != 0:
                skip("ID pictures: three.js could not be fetched")
                return
        for name, m in export_scene.parts().items():
            case.write_stl(m, os.path.join(d, name + ".stl"))
        names = sorted({p["f"] for s in specs.values() for p in s["parts"]})
        ids = {n: "#%02x%02x%02x" % (40 + 13 * i, 255 - 11 * i, (97 * i) % 256) for i, n in enumerate(names)}
        flat = {}
        for k, s in specs.items():
            if not s["labels"]:
                continue
            s = json.loads(json.dumps(s))
            s["flat"] = True
            for p in s["parts"]:
                p["c"] = ids[p["f"]]
                p.pop("op", None)
            flat[k] = s
        json.dump(flat, open(os.path.join(d, "ids.json"), "w"))
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8766"], cwd=d,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(1.0)
            r = subprocess.run([node, "shoot.js", "ids.json"], cwd=d, capture_output=True, text=True, timeout=600)
        finally:
            srv.terminate()
        if r.returncode != 0:
            report(False, f"ID pictures: renderer failed: {r.stderr[-300:]}")
            return
        labels = json.load(open(os.path.join(d, "labels.json")))
        rgb = {n: np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)]) for n, c in ids.items()}
        names_arr = list(rgb)
        table = np.array([rgb[n] for n in names_arr])
        bad = []
        count = 0
        for k, want in ID_EXPECT.items():
            a = np.asarray(Image.open(os.path.join(d, k + ".png")).convert("RGB")).astype(int)
            pts = labels[k]["labels"]
            if len(pts) != len(want):
                bad.append(f"{k}: {len(pts)} markers, {len(want)} expected")
                continue
            for i, ((x, y), ok_names) in enumerate(zip(pts, want)):
                yy, xx = np.mgrid[-20:21, -20:21]
                m = (xx ** 2 + yy ** 2) <= 400
                xs, ys = (int(round(x)) + xx[m]).clip(0, a.shape[1] - 1), (int(round(y)) + yy[m]).clip(0, a.shape[0] - 1)
                px = a[ys, xs]
                dist = np.abs(px[:, None, :] - table[None, :, :]).sum(2)
                near = dist.min(1) <= 12
                seen = {names_arr[j] for j in dist.argmin(1)[near]}
                count += 1
                if not seen & set(ok_names):
                    bad.append(f"{k} marker {i + 1}: wants {ok_names}, sees {sorted(seen) or 'background only'}")
        report(not bad, f"ID pictures: {count} guide markers checked; every one within 20 px of the part it names: "
                        f"{bad or 'yes'}")


# ------------------------------------------------------------------ 3
def numbers(got):
    readme = open(os.path.join(ROOT, "README.md")).read()
    en = json.dumps(json.load(open(os.path.join(GUIDE, "text_en.json"))), ensure_ascii=False)
    bg = json.dumps(json.load(open(os.path.join(GUIDE, "text_bg.json"))), ensure_ascii=False)
    import round13
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        round13.wires()
        round13.battery_drop()
    out = buf.getvalue()
    lb, ls = (int(v) for v in re.findall(r"about (\d+) mm long", out)[:2])
    slide = float(re.search(r"slide at most ([\d.]+) mm", out).group(1))
    x0, x1, y0, y1 = case.BATTERY_BAY

    def f(v):
        return f"{v:.1f}"

    def trip(a, b, c, sep):
        return sep.join([a, b, c])
    bat = [f(got["battery length"]), f(got["battery width"]), f(got["battery thickness"])]
    spk = [f(got["speaker length"]), f(got["speaker width"]), f(got["speaker thickness"])]
    bay = [f(x1 - x0), f(y1 - y0)]
    L = f"{case.SCREW_LEN:.0f}"
    facts = {
        "battery size": (trip(*bat, " x ") + " mm", trip(*bat, " × ") + " mm", trip(*bat, " × ").replace(".", ",") + " мм"),
        "bay": (" x ".join(bay) + " mm", " × ".join(bay) + " × 5 mm", " × ".join(bay).replace(".", ",") + " × 5 мм"),
        "speaker size": (trip(*spk, " x ") + " mm", trip(*spk, " × ") + " mm", trip(*spk, " × ").replace(".", ",") + " мм"),
        "wire routes": (f"about {lb} mm and {ls} mm", f"about {lb} mm and {ls} mm", f"около {lb} мм и {ls} мм"),
        "play": (f"about {slide:.1f} mm", f"about {slide:.1f} mm", f"около {slide:.1f} мм".replace(".", ",")),
        "screws": (f"4 × M2.5 × {L} mm screws", f"M2.5 × {L} mm screws", f"Винтове M2,5 × {L} мм"),
        "screw length": (f"{L} mm long under the head", f"Exactly {L} mm", f"Точно {L} мм"),
        "screw head": ("5.0 mm across and 1.8 mm tall", "5.0 mm across and 1.8 mm tall", "5,0 мм в диаметър и 1,8 мм висока"),
        "M2 washers": ("5 mm across, 0.3 mm thick", "5 mm across, 0.3 mm thick", "5 мм в диаметър и 0,3 мм дебели"),
        "standoff height": ("3–4 mm tall", "3–4 mm tall", "високи 3–4 мм"),
        "material": ("about 27 g of PLA", "about 27 g", "около 27 г"),
        "speaker cable": ("10–11 cm", "10–11 cm", "10–11 см"),
    }
    missing = []
    for k, (r, e, b) in facts.items():
        for doc, text, s in (("README", readme, r), ("EN guide", en, e), ("BG guide", bg, b)):
            if s not in text:
                missing.append(f"{doc} lacks '{s}' ({k})")
    report(not missing, f"{len(facts)} facts x 3 documents agree with case.py and the checks: {missing or 'yes'}")


# ------------------------------------------------------------------ 4
def fillet(points, radii_min, r_target):
    """Round every corner of a polyline. Returns (rounded points, radius each corner can take)."""
    P = [np.array(p, float) for p in points]
    n = len(P)
    seg = [np.linalg.norm(P[i + 1] - P[i]) for i in range(n - 1)]
    turn = [0.0] * n
    for i in range(1, n - 1):
        a, b = P[i] - P[i - 1], P[i + 1] - P[i]
        c = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        turn[i] = math.acos(max(-1.0, min(1.0, c)))
    # straight length beside each corner is shared with the neighbouring corner in proportion
    can = []
    out = [P[0]]
    for i in range(1, n - 1):
        th = turn[i]
        if th < 1e-6:
            can.append(math.inf)
            out.append(P[i])
            continue
        def share(j_seg, other):
            t_other = math.tan(turn[other] / 2) if 0 < other < n - 1 else 0.0
            t_me = math.tan(th / 2)
            return seg[j_seg] * t_me / (t_me + t_other)
        avail = min(share(i - 1, i - 1), share(i, i + 1))
        r = avail / math.tan(th / 2)
        can.append(r)
        r_use = min(r, r_target)
        t = r_use * math.tan(th / 2)
        a, b = (P[i - 1] - P[i]) / seg[i - 1], (P[i + 1] - P[i]) / seg[i]
        s, e = P[i] + a * t, P[i] + b * t
        # arc from s to e: centre along the bisector
        bis = (a + b) / np.linalg.norm(a + b)
        centre = P[i] + bis * (r_use / math.cos(th / 2))
        u, v = s - centre, e - centre
        k = 8
        for j in range(k + 1):
            w = j / k
            ang = math.acos(max(-1, min(1, np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)))))
            if ang < 1e-9:
                q = s
            else:
                q = centre + (math.sin((1 - w) * ang) * u + math.sin(w * ang) * v) / math.sin(ang)
            out.append(q)
    out.append(P[-1])
    short = [(i + 1, round(r, 2), m) for i, (r, m) in enumerate(zip(can, radii_min)) if r < m]
    return out, can, short


def bends():
    shell, _, cover_asm, z_total = load_assembled("battery")
    S, C = to_manifold(shell), to_manifold(cover_asm)
    z_in = z_total - case.T_BACK
    every = Manifold()
    for g in case.board_model().values():
        every += g
    x0, x1, y0, y1 = case.BATTERY_BAY
    bat = case.box(x0, x1, y0, y1, z_in - case.BATTERY_SPACE, z_in)
    sx, sy = case.SPEAKER["battery"]
    w, h, t = case.SPEAKER_BOX["battery"]
    spk = case.box(sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2, z_in - t, z_in)
    obst = S + C + every + bat + spk
    from round13 import tube
    pts, r = case.battery_wire_route()
    mins = [1.0] * (len(pts) - 2)
    path, can, short = fillet(pts, mins, 2.0)
    hit = vol(tube(path, r) ^ obst)
    report(not short and hit < 1e-3, f"battery wire with rounded bends: tightest corner can take "
                                     f"{min(can):.2f} mm (needs 1); too tight {short or 'none'}; overlap {hit:.4f} mm3")
    pts, r = case.speaker_wire_route()
    mins = [1.0] + [3.0] * (len(pts) - 4) + [1.0]      # thin leads at both ends, sleeve between
    path, can, short = fillet(pts, mins, 4.0)
    hit = vol(tube(path, r) ^ obst)
    report(not short and hit < 1e-3, f"speaker cable with rounded bends: corners can take "
                                     f"{[round(c, 2) for c in can]} mm (sleeve needs 3, thin leads 1); too tight "
                                     f"{short or 'none'}; overlap {hit:.4f} mm3")
    pts, r = case.speaker_cable_coil()
    path, can, short = fillet(pts, [3.0] * (len(pts) - 2), 4.0)
    hit = vol(tube(path, r) ^ obst)
    report(not short and hit < 1e-3, f"spare-cable loop: tightest bend {min(can):.2f} mm (needs 3); overlap {hit:.4f} mm3")


# ------------------------------------------------------------------ 5
def calipers():
    _, _, cover_asm, z_total = load_assembled("battery")
    z = z_total - case.T_BACK - 1.0          # half way up the 2 mm guides and brackets

    def span(o, d):
        o = np.array(o, float)
        d = np.array(d, float)
        l1, _, _ = cover_asm.ray.intersects_location([o], [d], multiple_hits=False)
        l2, _, _ = cover_asm.ray.intersects_location([o], [-d], multiple_hits=False)
        return float(np.linalg.norm(l1[0] - l2[0])) if len(l1) and len(l2) else float("nan")

    x0, x1, y0, y1 = case.BATTERY_BAY
    ym = (y0 + y1) / 2
    bay_l = span([(x0 + x1) / 2, ym, z], [1, 0, 0])
    bay_w = span([40.0, ym, z], [0, 1, 0])
    sx, sy = case.SPEAKER["battery"]
    w, h, _ = case.SPEAKER_BOX["battery"]
    wall, _, leg_x, leg_y = case.SPK_BRACKET
    pk_w = span([sx, sy - h / 2 + leg_y / 2, z], [1, 0, 0])      # through the legs along the long sides
    pk_l = span([sx - w / 2 + leg_x / 2, sy, z], [0, 1, 0])      # through the legs along the short sides
    ok = (abs(bay_l - (x1 - x0)) < 0.02 and abs(bay_w - (y1 - y0)) < 0.02 and abs(pk_w - w) < 0.02
          and abs(pk_l - h) < 0.02)
    report(ok, f"calipers on the back cover STL: bay {bay_l:.3f} x {bay_w:.3f} mm (designed {x1 - x0} x {y1 - y0}), "
               f"speaker pocket {pk_w:.3f} x {pk_l:.3f} mm (designed {w} x {h})")


# ------------------------------------------------------------------ 6
def heat():
    lx, ly = case.X1 - case.X0, case.Y1 - case.Y0
    zt = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    area = 2 * lx * ly + 2 * (lx + ly) * zt                    # mm2, outer surface
    A = area * 1e-6
    h = 8.0                                                   # W/m2K, still air (convection + radiation)
    k_pla, t_wall = 0.13, 1.8e-3
    R = 1 / (h * A) + t_wall / (k_pla * A)
    rise = 1.0 * R
    sun = 0.7 * 1000 * lx * ly * 1e-6                          # W absorbed by one face in full sun
    rise_sun = (sun + 1.0) * R
    text = open(os.path.join(ROOT, "README.md")).read()
    warned = "55 °C" in text and "sun" in text and "car" in text
    print(f"  ..   heat: case surface {area / 100:.0f} cm2, {R:.1f} K/W: 1 W inside -> about {rise:.0f} K over the room; "
          f"in full sun on its face (+{sun:.1f} W) -> about {rise_sun:.0f} K over the air")
    report(rise < 15 and (rise_sun + 25 < 55 or warned),
           f"PLA softens near 55 °C: indoors at 25 °C the case reaches about {25 + rise:.0f} °C; in full sun about "
           f"{25 + rise_sun:.0f} °C, and the README warns about sun and parked cars: {warned}")


if __name__ == "__main__":
    got = measured()
    tolerance(got)
    numbers(got)
    calipers()
    bends()
    heat()
    id_pictures()
    print(f"\nRound 29: {len(problems)} problem(s)" + (f", {len(skipped)} check(s) SKIPPED" if skipped else ""))
    for p in problems:
        print("  -", p)
