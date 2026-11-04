#!/usr/bin/env python3
"""Debug round 54 (session 5): methods not used in rounds 1-53.

1. Can the newest checks fail? Rounds 33 and 38 made deliberate mistakes to see that the checks of
   their time catch them. The checks added in rounds 44-53 had not been tried that way. In a copy of
   the project each mistake below is made on its own, and the check that should catch it is run on
   the copy and must report a problem. First every one of those checks is run on the unchanged copy,
   and must pass there, so a catch is the mistake's doing and not the copy's.
   In case.py: the window's left edge 0.06 mm further in (rounds 49 and 53), 0.15 mm further in
   (round 52's random builds); the right-hand pads back to 0.5 mm under the PCB (round 49); the
   bottom chamfer back to 0.8 mm (round 49's first-layer band); the buttons standing 2.5 mm out of
   the board (rounds 11 and 53); 2.4 mm standoffs taken as the shortest (round 50); the headers 1 mm
   taller (round 51's clip beams). In the documents: the README's speaker advice back to "stand it
   up" (round 53), its top-edge warning gone (round 11), its window size 0.1 mm off (round 52), its
   screw standard misprinted (round 51), the README changed after the zip was made (round 49). In
   the guides: a text the PDF lacks (round 52), two markers on top of each other and an unbreakable
   word in a table cell (round 52's layout), the pictures at 100 pixels per inch (round 53).
2. Page breaks in the guides: in both PDFs no heading may end a page (its text would be on the
   next), and every picture's legend must be on the same page as the picture, in one piece.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

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
WIN = ("WIN_CX, WIN_CY = 52.0, 29.8", "WIN_W, WIN_H, WIN_R = 88.8, 54.4, 0.4")


# a few catches whose message must name the right thing (target, words in its FAIL line)
WHY = {"headers 1 mm taller": ("r51 beams", "3 mm standoffs: nearest the connectors"),
       "window's left edge 0.06 mm further in": ("r49 window", "light field (your photos): left 0.04"),
       "buttons 2.5 mm out of the board": ("r11 table", "bottom edge"),
       "two markers on top of each other": ("r52 layout", "markers touching: ['"),
       "an unbreakable word in a table cell": ("r52 layout", "WWWW")}


def window_in(dx):
    """case.py edits that move the window's left edge dx further in and keep its right edge."""
    return [(WIN[0], f"WIN_CX, WIN_CY = {52.0 + dx / 2:.3f}, 29.8"), (WIN[1], f"WIN_W, WIN_H, WIN_R = {88.8 - dx:.3f}, 54.4, 0.4")]


PADS = "(BW - 0.3, BW + CLR + 0.1, 5, 12), (BW - 0.3, BW + CLR + 0.1, 45, 55)"
TARGETS = {   # name: (module, call)
    "r49 window": ("round49", "window_with_play()"),
    "r49 pads": ("round49", "pads_and_glass()"),
    "r49 band": ("round49", "true_band()"),
    "r49 zip": ("round49", "download_zip()"),
    "r50 press": ("round50", "press()"),
    "r51 beams": ("round51", "beam_sweep()"),
    "r51 buy list": ("round51", "buy_list()"),
    "r52 random builds": ("round52", "window_monte_carlo()"),
    "r52 README from STL": ("round52", "readme_from_stl()"),
    "r52 texts": ("round52", "texts_in_pdf()"),
    "r52 layout": ("round52", "guide_layout()"),
    "r53 standing": ("round53", "standing()"),
    "r53 temperature": ("round53", "window_temperature()"),
    "r53 print": ("round53", "print_resolution()"),
    "r11 table": ("round11", "table('battery')"),
}
# label, kind, edits, rebuild the STLs?, targets that must catch it
MUTANTS = [
    ("window's left edge 0.06 mm further in", "case.py", window_in(0.06), False, ["r49 window", "r53 temperature"]),
    ("window's left edge 0.15 mm further in", "case.py", window_in(0.15), False, ["r52 random builds"]),
    ("right-hand pads 0.5 mm under the PCB", "case.py", [(PADS, PADS.replace("BW - 0.3", "BW - 0.5"))], True, ["r49 pads"]),
    ("bottom chamfer 0.8 mm", "case.py", [("WIN_CHAMFER_BOTTOM = 0.5 ", "WIN_CHAMFER_BOTTOM = 0.8 ")], True, ["r49 band"]),
    ("buttons 2.5 mm out of the board", "case.py", [("BTN_PROTRUDE = 0.75", "BTN_PROTRUDE = 2.5")], False,
     ["r53 standing", "r11 table"]),
    ("2.4 mm standoffs the shortest", "case.py", [("STANDOFF_H_MIN = 3.0 ", "STANDOFF_H_MIN = 2.4 ")], False, ["r50 press"]),
    ("headers 1 mm taller", "case.py", [("PLUG_Y1, HEADER_H = (2.5, 7.9), 8.7, 3.5", "PLUG_Y1, HEADER_H = (2.5, 7.9), 8.7, 4.5")],
     False, ["r51 beams"]),
    ("README: speaker advice back to \"stand it up\"", "README.md",
     [("muffled: stand it on its bottom edge, or lay", "muffled: stand it up, or lay")], False, ["r53 standing"]),
    ("README: top-edge warning gone", "README.md",
     [(" Don't stand it on its top edge, where the dial would take its weight.", "")], False, ["r11 table"]),
    ("README: window 88.9 mm wide", "README.md", [("Display window:** 88.8 x 54.4 mm", "Display window:** 88.9 x 54.4 mm")],
     False, ["r52 README from STL"]),
    ("README: ISO 7046 for 7045", "README.md", [("7045", "7046")], False, ["r51 buy list"]),
    ("README changed after the zip was made", "README.md", [("\n## ", "\n\n## ")], False, ["r49 zip"]),
    ("a guide text the PDF lacks", "json", None, False, ["r52 texts"]),
    ("two markers on top of each other", "marker", None, False, ["r52 layout"]),
    ("an unbreakable word in a table cell", "word", None, False, ["r52 layout"]),
    ("the guide's pictures at 100 ppi", "pdf", None, False, ["r53 print"]),
]


FAILS = {}


def run_target(d, name):
    mod, call = TARGETS[name]
    code = (f"import sys; sys.path.insert(0, {os.path.join(d, 'checks')!r}); sys.path.insert(0, {d!r}); "
            f"import {mod}; {mod}.{call}")
    # -B and no __pycache__: a mutant and its restore can have the same size and the same second's
    # mtime, and Python would then reuse the other one's compiled case.py
    r = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=d, timeout=1800,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    out = r.stdout
    fails = [ln for ln in out.splitlines() if ln.startswith("  FAIL")]
    FAILS.setdefault(name, []).append(fails[0][7:] if fails else "")
    if r.returncode != 0:
        return "crashed: " + (r.stderr.strip().splitlines() or ["?"])[-1][:120]
    if "  FAIL" in out:
        return "caught"
    if "  SKIP" in out:
        return "skipped"
    return "passed"


def apply(d, kind, edits):
    if kind in ("case.py", "README.md"):
        p = os.path.join(d, kind)
        s = open(p, encoding="utf-8").read()
        for old, new in edits:
            if old not in s:
                return False
            s = s.replace(old, new)
        open(p, "w", encoding="utf-8").write(s)
    elif kind == "json":
        p = os.path.join(d, "docs", "guide-src", "text_en.json")
        t = json.load(open(p, encoding="utf-8"))
        t["tips"].append("Keep the case dry, and wipe it with a soft cloth.")
        json.dump(t, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    elif kind in ("marker", "word"):
        p = os.path.join(d, "docs", "guide-src", "out", "guide_en.html")
        s = open(p, encoding="utf-8").read()
        if kind == "marker":
            m = re.search(r'<span class="mk"[^>]*>[^<]*</span>', s)
            if not m:
                return False
            s = s[:m.end()] + m.group(0) + s[m.end():]
        else:
            if "<td>" not in s:
                return False
            s = s.replace("<td>", "<td>" + "W" * 120, 1)
        open(p, "w", encoding="utf-8").write(s)
    elif kind == "pdf":
        from PIL import Image
        out = os.path.join(d, "docs", "guide-src", "out")
        ims = [Image.open(os.path.join(out, f)).convert("RGB") for f in sorted(os.listdir(out)) if f.endswith(".png")]
        ims[0].save(os.path.join(d, "docs", "assembly_guide_en.pdf"), save_all=True, append_images=ims[1:], resolution=100)
    return True


def mutants():
    rows, missed = [], []
    with tempfile.TemporaryDirectory() as d:
        for f in ("case.py", "verify.py", "README.md", "DEBUG_LOG.md", "make_zips.py"):
            shutil.copy(os.path.join(ROOT, f), d)
        shutil.copytree(HERE, os.path.join(d, "checks"), ignore=shutil.ignore_patterns("__pycache__", ".cache"))
        for sub in ("docs", "stl", "dist", "preview"):
            shutil.copytree(os.path.join(ROOT, sub), os.path.join(d, sub))
        keep = os.path.join(d, ".orig")
        shutil.copytree(d, keep, ignore=shutil.ignore_patterns(".orig"))

        def restore():
            for f in ("case.py", "README.md"):
                shutil.copy(os.path.join(keep, f), os.path.join(d, f))
            for sub in ("docs", "stl"):
                shutil.rmtree(os.path.join(d, sub))
                shutil.copytree(os.path.join(keep, sub), os.path.join(d, sub))
        # the control: every check used below passes on the unchanged copy
        used = sorted({t for m in MUTANTS for t in m[4]})
        control = {t: run_target(d, t) for t in used}
        bad_control = {t: v for t, v in control.items() if v != "passed"}
        for label, kind, edits, rebuild, targets in MUTANTS:
            if not apply(d, kind, edits):
                rows.append(f"{label}: could not be made")
                missed.append(label)
                restore()
                continue
            if rebuild:
                b = subprocess.run([sys.executable, os.path.join(d, "case.py"), os.path.join(d, "stl")], capture_output=True)
                if b.returncode != 0:
                    rows.append(f"{label}: the generator refused it")
                    restore()
                    continue
            got = {t: run_target(d, t) for t in targets}
            why = WHY.get(label)
            if why and got.get(why[0]) == "caught" and why[1] not in FAILS[why[0]][-1]:
                got[why[0]] = f"caught, but not for this ({FAILS[why[0]][-1][:80]})"
            rows.append(f"{label} -> " + ", ".join(f"{t} {v}" for t, v in got.items()))
            if any(v != "caught" for v in got.values()):
                missed.append(label)
            restore()
    report(not missed and not bad_control,
           f"{len(MUTANTS)} deliberate mistakes for the checks of rounds 44-53 (control: the {len(used)} checks "
           + ("all pass on the unchanged copy" if not bad_control else f"do not all pass unchanged: {bad_control}")
           + "): " + "; ".join(rows) + f"; missed: {missed or 'none'}")


# ------------------------------------------------------------------ 2
def squeeze(t):
    import html
    import unicodedata
    t = unicodedata.normalize("NFKC", html.unescape(re.sub(r"<[^>]+>", "", t)))
    return re.sub(r"[\s\-­]+", "", t)


def page_breaks():
    if not (shutil.which("pdftotext") and shutil.which("pdfimages")):
        skip("page breaks: pdftotext or pdfimages is not installed")
        return
    rows, ok = [], True
    for lang in ("en", "bg"):
        T = json.load(open(os.path.join(ROOT, "docs", "guide-src", f"text_{lang}.json"), encoding="utf-8"))
        pdf = os.path.join(ROOT, "docs", f"assembly_guide_{lang}.pdf")
        txt = subprocess.run(["pdftotext", "-raw", pdf, "-"], capture_output=True, text=True).stdout
        pages = txt.split("\f")[:-1] if txt.endswith("\f") else txt.split("\f")
        flat = [squeeze(p) for p in pages]
        heads = [T[k] for k in T if re.fullmatch(r"h_\w+|s\d_h", k)]
        orphans = []
        for i, p in enumerate(pages[:-1]):
            lines = [ln.strip() for ln in p.splitlines() if ln.strip() and not re.fullmatch(r"\d+ / \d+", ln.strip())]
            tail = squeeze(" ".join(lines[-2:]))
            for h in heads:
                if tail.endswith(squeeze(h)):
                    orphans.append(f"'{re.sub(r'<[^>]+>', '', h)}' ends page {i + 1}")
        imgs = []
        for line in subprocess.run(["pdfimages", "-list", pdf], capture_output=True, text=True).stdout.splitlines()[2:]:
            c = line.split()
            if c[2] == "image" and int(c[3]) >= 200:
                imgs.append(int(c[0]))
        figs = ["fig_parts", "fig_print", "fig1", "fig2", "fig3", "fig4a", "fig4b"]
        split = []
        if len(imgs) != len(figs) + 1:
            split.append(f"{len(imgs)} pictures for {len(figs)} legends and the title picture")
        else:
            for k, pg in zip(figs, imgs[1:]):
                where = [next((i + 1 for i, f in enumerate(flat) if squeeze(t) in f), None) for _, t in T[k]]
                if set(where) != {pg}:
                    split.append(f"{k}: picture on page {pg}, legend lines on pages {where}")
        ok &= not orphans and not split
        rows.append(f"{lang.upper()} {len(pages)} pages: " + (", ".join(orphans) if orphans else "no heading ends a page")
                    + "; " + ("; ".join(split) if split else f"all {len(figs)} legends whole, on their picture's page"))
    report(ok, "page breaks in the guides: " + "; ".join(rows))


if __name__ == "__main__":
    page_breaks()
    mutants()
    print(f"\nRound 54: {len(problems)} problem(s), {len(skipped)} skipped")
    for p in problems:
        print("  -", p)
