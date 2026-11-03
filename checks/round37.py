#!/usr/bin/env python3
"""Debug round 37 (session 5): methods not used in rounds 1-36.

1. The log's own numbers, recomputed: every figure the session-5 entries of DEBUG_LOG.md give for the
   new closure (screw hole and recess, how far the screw goes in, the glass and pad gaps, the wall at
   the corners, the clip beams, their bend and forces, the standoff estimate) is found in the log by
   its wording and recomputed from case.py or from the check that measures it; each must agree to
   the precision the log writes it with.
2. Mistakes a person could make while assembling, each answered in all three documents: the battery
   in the wrong connector or the wrong way round, the speaker upside down or turned, tape over the
   membrane, the cable near the antenna, wires over the posts or under the clips, the cover turned
   over the wrong edge, the screws tried before the lid is on, M2 standoffs, screws of the wrong
   length or too tight, 0.3 mm layers, PLA in the sun, and how to open it: the README, the English
   guide and the Bulgarian guide must each say what to do.
3. Markdown that renders: in README.md and DEBUG_LOG.md every paragraph has its ** and ` in pairs,
   every table row has as many cells as its header, and every link and image has a target.
"""
import contextlib
import io
import json
import os
import re
import sys

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


def quiet(fn, *a):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn(*a)
    return r, buf.getvalue()


# ------------------------------------------------------------------ 1
def log_numbers():
    log = open(os.path.join(ROOT, "DEBUG_LOG.md"), encoding="utf-8").read()
    log = log.split("## Session 5", 1)[1]
    import round22
    import round36
    _, o22 = quiet(round22.clips)
    _, o36 = quiet(round36.closing)
    eps = float(re.search(r"([\d.]+) % strain at full bend", o22).group(1))
    close_n, pull_n = (int(v) for v in re.search(r"about (\d+) N to close, (\d+) N to pull", o22).groups())
    worst = float(re.search(r"bend up to [\d.]+ mm while closing \(([\d.]+) % strain", o36).group(1))
    z_total = case.Z_B + case.CAVITY["battery"] + case.T_BACK
    seat = z_total - case.SCREW_HEAD_DEPTH
    into = case.SCREW_LEN - (seat - case.POST_Z)
    glass = case.PANEL_SPACE - case.PANEL_T + case.GLASS_RELIEF
    claims = [
        (r"A ([\d.]+) mm hole and a ([\d.]+) x ([\d.]+) mm recess take an M2\.5 x (\d+) screw",
         (2 * case.SCREW_HOLE_R, 2 * case.SCREW_HEAD_R, case.SCREW_HEAD_DEPTH, case.SCREW_LEN)),
        (r"which then goes (\d+) mm into the standoff", (into,)),
        (r"with 3 mm ones the board sits (\d+) mm further back", (case.STANDOFF_H - case.STANDOFF_H_MIN,)),
        (r"\(x ([\d.]+) / ([\d.]+), y ([\d.]+) / ([\d.]+)\)",
         (case.POSTS[0][0], case.POSTS[3][0], case.POSTS[0][1], case.POSTS[3][1])),
        (r"four (\d+) mm stretches of the back cover's skirt", (case.CLIP_L,)),
        (r"freed from the cover by a ([\d.]+) mm slot", (case.CLIP_SLOT,)),
        (r"\(([\d.]+) mm undercut, (\d+)° catch\)", (case.CLIP_UNDERCUT, case.CLIP_CATCH)),
        (r"a (\d+)° chamfer inside the lid's rim", (case.RIM_CHAMFER[1],)),
        (r"each beam stays bent ([\d.]+) mm", (case.CLIP_PRELOAD,)),
        (r"About (\d+) N closes the lid and (\d+) N pulls it straight off", (close_n, pull_n)),
        (r"the beams bend at most ([\d.]+) %", (eps,)),
        (r"the plate is ([\d.]+) mm thinner over the glass \(([\d.]+) mm clear with 4 mm standoffs, ([\d.]+) mm with 3 mm\)",
         (case.GLASS_RELIEF, glass, glass + case.STANDOFF_H - case.STANDOFF_H_MIN)),
        (r"the pads stop ([\d.]+) mm short of the PCB", (case.PAD_GAP,)),
        (r"Back edge rounding ([\d.]+) → ([\d.]+) mm", (case.RE, case.RE_BACK)),
        (r"bend it up to ([\d.]+) % while closing", (worst,)),
    ]
    bad, n = [], 0
    for rx, want in claims:
        m = re.search(rx, log)
        if not m:
            bad.append(f"not found: {rx}")
            continue
        for s, w in zip(m.groups(), want):
            n += 1
            dec = len(s.split(".")[1]) if "." in s else 0
            if abs(float(s) - w) > 0.5 * 10 ** -dec + 1e-9:
                bad.append(f"'{m.group(0)}': {s} vs recomputed {w:.{dec + 1}f}")
    report(not bad, f"{n} numbers the session-5 log gives for the new closure, recomputed: {bad or 'all agree'}")


# ------------------------------------------------------------------ 2
SLIPS = [  # (slip, README regex, English guide regex, Bulgarian guide regex)
    ("battery in the wrong connector", r"into \*\*BAT\*\*", r"goes into <b>BAT</b> only", r"само в BAT"),
    ("battery the wrong way round", r"taped end \(with the wire\) toward the USB-C end", r"taped end \(with the wire\) toward the USB-C end",
     r"облепения край \(с кабела\) към страната с USB-C"),
    ("battery wire at the far corner", r"turn the cell over", r"turn the cell over", r"обърнете батерията"),
    ("speaker upside down", r"membrane side down", r"membrane side down", r"с мембраната надолу"),
    ("speaker turned round", r"white peg pointing to the top edge", r"white peg toward the top edge", r"бялото щифтче към горния ръб"),
    ("tape over the membrane", r"membrane stays uncovered", r"leaving the membrane uncovered", r"мембраната остава открита"),
    ("cable near the antenna", r"where the ESP32's antenna is", r"where the antenna is", r"където е антената"),
    ("wires over the posts or under the clips", r"away from the four corner posts and the long edges", r"off the 4 corner posts",
     r"далеч от 4-те ъглови стълбчета"),
    ("cover turned over the wrong edge", r"page of a book along the bottom edge", r"page of a book along the bottom edge",
     r"страница на книга около долния ръб"),
    ("screws before the lid", r"The lid has already lined the board up", r"until <b>all 4 clips click</b>", r"и 4-те щипки щракнат"),
    ("M2 standoffs", r"your standoffs are M2: use the M2 screws with a washer", r"your standoffs are M2:</b> use the M2",
     r"втулките ви са M2:</b> използвайте"),
    ("screws of the wrong length", r"Don't use other lengths", r"Use only 8 mm screws", r"Използвайте само винтове от 8 мм"),
    ("screws too tight", r"Don't over-tighten", r"Don't over-tighten", r"Не ги затягайте прекалено"),
    ("0.3 mm layers", r"Don't use 0\.3 mm layers", r"Don't use 0\.3 mm", r"Не използвайте 0,3 мм"),
    ("PLA in the sun", r"Keep the case out of direct sun", r"keep the case out of direct sun", r"пазете кутията от пряко слънце"),
    ("how to open it", r"fingernail or a guitar pick into the notch in the right-hand end",
     r"fingernail or a guitar pick into the <b>notch in the right-hand end", r"перце за китара във <b>вдлъбнатината в десния край"),
]


def slips():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    g = os.path.join(ROOT, "docs", "guide-src")
    en = json.dumps(json.load(open(os.path.join(g, "text_en.json"), encoding="utf-8")), ensure_ascii=False)
    bg = json.dumps(json.load(open(os.path.join(g, "text_bg.json"), encoding="utf-8")), ensure_ascii=False)
    missing = []
    for slip, r_, e_, b_ in SLIPS:
        for doc, text, rx in (("README", readme, r_), ("EN", en, e_), ("BG", bg, b_)):
            if not re.search(rx, text):
                missing.append(f"{doc}: {slip}")
    report(not missing, f"{len(SLIPS)} likely assembly slips, each answered in the README and both guides: "
                        f"{missing or 'all'}")


# ------------------------------------------------------------------ 3
def markdown():
    bad = []
    for name in ("README.md", "DEBUG_LOG.md"):
        text = open(os.path.join(ROOT, name), encoding="utf-8").read()
        in_code = False
        para = []
        lines = text.split("\n") + [""]
        for i, line in enumerate(lines, 1):
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if line.strip() == "" or re.match(r"(- |\||#|\d+\. |\s+- )", line):
                if para:
                    p = " ".join(para)
                    if p.count("**") % 2:
                        bad.append(f"{name} line {i - len(para)}: unpaired **")
                    if p.count("`") % 2:
                        bad.append(f"{name} line {i - len(para)}: unpaired `")
                para = []
            if line.strip():
                para.append(line)
        tables, cur = [], []
        for line in text.split("\n"):
            if line.startswith("|"):
                cur.append(line)
            elif cur:
                tables.append(cur)
                cur = []
        if cur:
            tables.append(cur)
        for t in tables:
            n = t[0].count("|")
            bad += [f"{name}: table row with {r.count('|') - 1} cells: {r[:40]}" for r in t if r.count("|") != n]
        bad += [f"{name}: empty link '{m}'" for m in re.findall(r"\]\(\s*\)", text)]
    report(not bad, f"README.md and DEBUG_LOG.md: bold and code marks in pairs, tables square, links with targets: "
                    f"{bad or 'yes'}")


if __name__ == "__main__":
    markdown()
    slips()
    log_numbers()
    print(f"\nRound 37: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
