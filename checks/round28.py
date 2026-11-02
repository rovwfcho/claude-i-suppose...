#!/usr/bin/env python3
"""Debug round 28 (session 4: the owner's own battery and speaker). Methods not used in rounds 1-27.

The owner photographed their battery, speaker and board next to a ruler. Crops of those photos are in
checks/owner_photos/ (crops.json says where each crop sits in its photo; every position below is in
full-photo pixels).

1. Ruler scale, read automatically: the ruler's dark tick marks are found along one row of each photo
   and a straight line is fitted through tick number against position, so the pixels per mm come
   from 15-45 ticks, not from two numbers read by eye. Ticks more than 4 px off the line are dropped.
2. Part edges: from a position marked by eye, the strongest colour step within 8 px along the
   measuring line, taken on several rows (median). Size = edge-to-edge distance / scale. The sizes in
   case.py (BATTERY_SIZE, SPEAKER_SIZE) must match within 0.3 mm, and the bay and the speaker pocket
   must give each measured part 0.4-1.2 mm of room on every side (it fits, and can't rattle).
3. Speaker membrane, peg and cable: the four corners of the speaker's white frame in the top view
   (photo 8) and its measured size give a perspective transform. The membrane must match
   SPEAKER_WINDOW within 0.5 mm, the cable exit must match SPK_CABLE_EXIT within 0.5 mm, and the peg
   and the cable must clear the pocket's corner brackets wherever the speaker sits in the pocket.
4. The owner's board: the four brass standoff tops in photo 9 give a perspective transform to board
   coordinates; the USB-C, both buttons, the dial and the board's top edge must land within 0.8 mm of
   case.py's board model (a different board revision would show up here).
5. A review image, preview/owner_measurements.png, with every tick, edge and landmark drawn on.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import case  # noqa: E402

PHOTOS = os.path.join(HERE, "owner_photos")
META = json.load(open(os.path.join(PHOTOS, "crops.json")))
problems = []
marks = {}   # crop name -> list of drawing instructions for the review image


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def load(name):
    return np.asarray(Image.open(os.path.join(PHOTOS, name + ".jpg")).convert("RGB")).astype(float)


def to_crop(name, x, y):
    ox, oy = META[name]["offset"]
    return x - ox, y - oy


# ------------------------------------------------------------------ 1
def ruler_scale(name, row, x0, x1, band=5):
    """Pixels per mm from the ruler's tick marks along one image row (full-photo coordinates)."""
    a = load(name).mean(2)
    r, c0, c1 = (int(round(v)) for v in (to_crop(name, x0, row)[1], to_crop(name, x0, row)[0], to_crop(name, x1, row)[0]))
    prof = gaussian_filter1d(a[r - band:r + band + 1, c0:c1].mean(0), 1.0)
    dark = gaussian_filter1d(prof, 8) - prof       # ticks are darker than their surroundings
    pk = []
    for i in range(2, len(dark) - 2):
        if dark[i] >= dark[i - 1] and dark[i] >= dark[i + 1] and dark[i] > 8:
            den = dark[i - 1] - 2 * dark[i] + dark[i + 1]
            pk.append(c0 + i + (0.5 * (dark[i - 1] - dark[i + 1]) / den if den else 0.0))
    t = np.array(pk)
    keep = np.ones(len(t), bool)
    for _ in range(4):
        step = np.median(np.diff(t[keep]))
        k = np.round((t - t[keep][0]) / step)
        fit = np.polyfit(k[keep], t[keep], 1)
        res = t - np.polyval(fit, k)
        keep = np.abs(res) < 4.0
    ox = META[name]["offset"][0]
    marks.setdefault(name, []).extend(("tick", x - ox, r) for x in t[keep])
    return float(fit[0]), int(keep.sum()), float(np.std(res[keep]))


def edge(name, rows, guess, side, axis="x", win=8):
    """Median position (full-photo px) of the part's outline near `guess` on several rows: of the
    colour steps in the window at least half as strong as the strongest, the outermost one (side -1:
    the part lies on the high side of the edge, +1: on the low side), so a bright rim round the
    part's edge can't pull the edge inward."""
    a = load(name)
    ox, oy = META[name]["offset"]
    found = []
    for row in rows:
        if axis == "x":
            line = a[int(row - oy), :, :]
            g0 = guess - ox
        else:
            line = a[:, int(row - ox), :]
            g0 = guess - oy
        sm = gaussian_filter1d(line, 1.2, axis=0)
        grad = np.sqrt((np.diff(sm, axis=0) ** 2).sum(1))
        lo, hi = int(g0 - win), int(g0 + win)
        seg = grad[lo:hi]
        peaks = [j for j in range(1, len(seg) - 1) if seg[j] >= seg[j - 1] and seg[j] >= seg[j + 1]
                 and seg[j] >= 0.5 * seg.max()]
        i = lo + (min(peaks) if side < 0 else max(peaks))
        den = grad[i - 1] - 2 * grad[i] + grad[i + 1]
        found.append(i + 0.5 + (0.5 * (grad[i - 1] - grad[i + 1]) / den if den else 0.0))
    pos = float(np.median(found))
    for row, f in zip(rows, found):
        marks.setdefault(name, []).append(("edge", f, row - oy) if axis == "x" else ("edge", row - ox, f))
    return pos + (ox if axis == "x" else oy), float(np.std(found))


# measuring lines: crop, tick row and x range, edge rows, the two edges' starting guesses (by eye)
MEASURES = {
    "battery length": ("battery_length", (985, 140, 1450), range(885, 960, 5), (132.0, 1287.0)),
    "battery width": ("battery_width", (1048, 250, 1340), range(965, 1020, 5), (318.5, 1185.0)),
    "battery thickness": ("battery_thickness", (1000, 560, 1480), range(865, 940, 5), (540.0, 670.0)),
    "speaker length": ("speaker_length", (1345, 400, 1480), range(1130, 1200, 5), (388.0, 852.5)),
    "speaker width": ("speaker_width", (1268, 560, 1300), range(1100, 1225, 5), (565.0, 897.5)),
    "speaker thickness": ("speaker_thickness", (1352, 560, 1300), list(range(1140, 1186, 5)) + list(range(1280, 1311, 5)),
                          (595.0, 730.0)),
}


def sizes():
    got = {}
    for label, (name, (row, x0, x1), rows, (g1, g2)) in MEASURES.items():
        pxmm, n, sd = ruler_scale(name, row, x0, x1)
        e1, s1 = edge(name, rows, g1, -1)
        e2, s2 = edge(name, rows, g2, +1)
        mm = (e2 - e1) / pxmm
        got[label] = mm
        report(n >= 12 and sd < 2.0 and max(s1, s2) / pxmm <= 0.2,
               f"{label}: ruler {pxmm:.2f} px/mm from {n} ticks (scatter {sd:.2f} px); edges at {e1:.1f} and {e2:.1f} px "
               f"(scatter along the edge {s1 / pxmm:.2f} / {s2 / pxmm:.2f} mm) -> {mm:.2f} mm")
    L, W, T = case.BATTERY_SIZE
    bx0, bx1, by0, by1 = case.BATTERY_BAY
    for label, model in (("battery length", L), ("battery width", W), ("battery thickness", T)):
        report(abs(got[label] - model) <= 0.3, f"case.py has the {label} as {model} mm; photo says {got[label]:.2f} mm")
    room = ((bx1 - bx0) - got["battery length"]) / 2, ((by1 - by0) - got["battery width"]) / 2
    report(all(0.4 <= r <= 1.2 for r in room), f"battery bay {bx1 - bx0:.1f} x {by1 - by0:.1f} mm leaves "
                                                f"{room[0]:.2f} / {room[1]:.2f} mm each side of the measured cell (want 0.4-1.2)")
    report(case.BATTERY_SPACE - got["battery thickness"] >= 0.5,
           f"battery room {case.BATTERY_SPACE} mm deep for a {got['battery thickness']:.2f} mm cell (0.5 mm for swelling and tape)")
    a, b, c = case.SPEAKER_SIZE
    for label, model in (("speaker width", a), ("speaker length", b), ("speaker thickness", c)):
        report(abs(got[label] - model) <= 0.3, f"case.py has the {label} as {model} mm; photo says {got[label]:.2f} mm")
    pw, ph, pt = case.SPEAKER_BOX["battery"]
    room = (pw - got["speaker width"]) / 2, (ph - got["speaker length"]) / 2
    report(all(0.4 <= r <= 1.2 for r in room), f"speaker pocket {pw} x {ph} mm leaves {room[0]:.2f} / {room[1]:.2f} mm "
                                                f"each side of the measured speaker (want 0.4-1.2)")
    report(case.BATTERY_SPACE - got["speaker thickness"] >= 0.3,
           f"speaker {got['speaker thickness']:.2f} mm thick in the {case.BATTERY_SPACE} mm battery layer")
    return got


# ------------------------------------------------------------------ 3
def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    h = np.linalg.svd(np.array(A))[2][-1].reshape(3, 3)
    return h / h[2, 2]


def apply(h, p):
    q = h @ np.array([p[0], p[1], 1.0])
    return q[:2] / q[2]


# the speaker seen from its sound face in photo 8 (full-photo px, marked by eye on a 6x zoom):
# corners of the white frame (going round: the two ends of the long side nearest the camera's top
# first), corners of the membrane in the same order, the peg's middle and the cable's exit
FRAME = [(1590.0, 156.7), (1705.0, 218.3), (1641.7, 304.2), (1527.5, 235.0)]
MEMBRANE = [(1590.0, 185.0), (1670.0, 226.7), (1641.7, 278.3), (1555.8, 230.8)]
PEG = (1694.0, 260.0)
CABLE = (1607.0, 303.0)


def speaker_face(got):
    L, W = got["speaker length"], got["speaker width"]
    h = homography(FRAME, [(0, 0), (L, 0), (L, W), (0, W)])
    m = np.array([apply(h, p) for p in MEMBRANE])
    ml = (np.linalg.norm(m[1] - m[0]) + np.linalg.norm(m[2] - m[3])) / 2
    mw = (np.linalg.norm(m[3] - m[0]) + np.linalg.norm(m[2] - m[1])) / 2
    off = m.mean(0) - np.array([L / 2, W / 2])
    sw, sl = case.SPEAKER_WINDOW
    report(abs(ml - sl) <= 0.5 and abs(mw - sw) <= 0.5 and np.abs(off).max() <= 0.5,
           f"speaker membrane {ml:.2f} x {mw:.2f} mm, centre {np.round(off, 2).tolist()} mm off the frame's "
           f"(case.py: {sl} x {sw}, centred)")
    # grille slots under the measured membrane wherever this speaker can sit in its pocket: the open
    # area left uncovered at the worst position (a slot edge under the gasket ring) must be under 10 %
    gw, glen, pitch = case.GRILLE_SLOTS
    half_x, half_y = pitch + gw / 2, glen / 2
    pw, ph, _ = case.SPEAKER_BOX["battery"]
    rx, ry = (pw - W) / 2, (ph - L) / 2
    ux = max(0.0, half_x + rx + abs(off[1]) - mw / 2)          # strip of the outer slot past the membrane
    uy = max(0.0, half_y + ry + abs(off[0]) - ml / 2)
    slot_area = 3 * (gw * (glen - gw) + np.pi * gw ** 2 / 4)
    lost = (min(ux, gw) * (glen - gw) + 3 * min(uy, glen / 2) * gw) / slot_area
    report(lost <= 0.10, f"grille {2 * half_x:.1f} x {2 * half_y:.1f} mm under this membrane with the speaker pushed "
                         f"{rx:.2f} / {ry:.2f} mm to the side: {100 * lost:.1f} % of the open area under the gasket "
                         f"ring at worst (want under 10 %)")
    pu, pv = apply(h, PEG)
    cu, cv = apply(h, CABLE)
    # in the pocket (front view): long side along y, peg toward the top, cable on the left long side,
    # so the peg's distance from the cable's side is pv measured from the far long side (v = 0)
    from_end = L - cu
    report(abs(from_end - case.SPK_CABLE_EXIT) <= 0.5,
           f"cable leaves the long side {from_end:.2f} mm from the peg's end (case.py {case.SPK_CABLE_EXIT}); "
           f"peg sticks out {pu - L:.2f} mm, its middle {pv:.2f} mm from the far long side")
    # clearances to the brackets, worst case over the speaker's play in the pocket
    wall, _, leg_x, leg_y = case.SPK_BRACKET
    cable_half = 1.0                                  # the flat flex is about 2 mm wide
    gap_cable = (ph / 2 - leg_y) - (L / 2 - from_end + cable_half) - ry
    peg_half = 1.3
    peg_x = W / 2 - pv                                # peg middle from the speaker's centre line, toward the far side
    gap_peg = (pw / 2 - leg_x) - (abs(peg_x) + peg_half) - rx
    report(gap_cable >= 0.2 and gap_peg >= 0.2,
           f"cable clears the bracket leg by {gap_cable:.2f} mm, the peg by {gap_peg:.2f} mm, with the speaker "
           f"pushed the wrong way (want 0.2)")
    ox, oy = META["speaker_face"]["offset"]
    for p in FRAME + MEMBRANE + [PEG, CABLE]:
        marks.setdefault("speaker_face", []).append(("dot", p[0] - ox, p[1] - oy))


# ------------------------------------------------------------------ 4
# the owner's board, back side (photo 9 shows it with x as seen from the front and y flipped): the
# brass standoff tops (circle centres, from 6x zooms), and the landmarks to check, all full-photo px
STANDOFFS = {(277.1, 174.6): case.POSTS[0], (1590.8, 189.6): case.POSTS[1],
             (267.5, 936.5): case.POSTS[2], (1584.5, 945.5): case.POSTS[3]}
LANDMARKS = [
    ("USB-C centre (y)", (290.0, 553.1), 1, case.USB_Y),
    ("BOOT actuator (x)", (1275.6, 170.0), 0, case.BUTTONS["BOOT"]),
    ("PWR actuator (x)", (1411.9, 170.0), 0, case.BUTTONS["PWR"]),
    ("dial centre (x)", (1335.0, 900.0), 0, case.WHEEL[0]),
    ("board top edge at x 25 (y)", (600.0, 145.0), 1, 0.0),
    ("board top edge at x 54 (y)", (1000.0, 150.0), 1, 0.0),
]


def board():
    src = list(STANDOFFS)
    # photo 9 is flipped top to bottom relative to the front view; standoff 0 is front (2.2, 2.85)
    dst = [STANDOFFS[k] for k in src]
    h = homography(src, dst)
    worst = 0.0
    lines = []
    for label, p, k, model in LANDMARKS:
        v = apply(h, p)[k]
        worst = max(worst, abs(v - model))
        lines.append(f"{label} {v:.2f} (model {model})")
    report(worst <= 0.8, "owner's board vs the board model: " + "; ".join(lines) + f"; worst {worst:.2f} mm")
    ox, oy = META["board_back"]["offset"]
    for p in list(STANDOFFS) + [q[1] for q in LANDMARKS]:
        marks.setdefault("board_back", []).append(("dot", p[0] - ox, p[1] - oy))


# ------------------------------------------------------------------ 5
def review(out_path):
    tiles = []
    for name in ("battery_length", "battery_width", "battery_thickness", "speaker_length", "speaker_width",
                 "speaker_thickness", "speaker_face", "board_back"):
        im = Image.open(os.path.join(PHOTOS, name + ".jpg")).convert("RGB")
        d = ImageDraw.Draw(im)
        for kind, x, y in marks.get(name, []):
            if kind == "tick":
                d.line([(x, y - 9), (x, y + 9)], fill=(0, 120, 255), width=2)
            elif kind == "edge":
                d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(255, 0, 0), width=2)
            else:
                d.ellipse([x - 5, y - 5, x + 5, y + 5], outline=(255, 0, 255), width=3)
        scale = 900 / im.width if name == "board_back" else min(900 / im.width, 1.0)
        im = im.resize((int(im.width * scale), int(im.height * scale)))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 260, 18], fill=(255, 255, 255))
        d.text((4, 3), f"{name} (photo {META[name]['photo']})", fill=(0, 0, 0))
        tiles.append(im)
    W = 1820
    rows, row, x = [], [], 0
    for t in tiles:
        if x + t.width > W and row:
            rows.append(row)
            row, x = [], 0
        row.append(t)
        x += t.width + 20
    rows.append(row)
    H = sum(max(t.height for t in r) + 20 for r in rows) + 40
    sheet = Image.new("RGB", (W, H), "white")
    ImageDraw.Draw(sheet).text((10, 10), "Owner's photos: blue = ruler ticks found, red = part edges found, "
                                         "magenta = landmarks marked by eye (round 28)", fill=(0, 0, 0))
    y = 40
    for r in rows:
        x = 0
        for t in r:
            sheet.paste(t, (x, y))
            x += t.width + 20
        y += max(t.height for t in r) + 20
    sheet.save(out_path)
    print(f"  ..   review image written to {out_path} (inspect by eye)")


if __name__ == "__main__":
    got = sizes()
    speaker_face(got)
    board()
    review(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "preview", "owner_measurements.png"))
    print(f"\nRound 28: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
