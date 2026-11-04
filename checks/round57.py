#!/usr/bin/env python3
"""Debug round 57 (session 5): methods not used in rounds 1-56.

1. Spelling, by a spell checker (pyspellchecker's English word list): every word of the README, of
   the English guide's texts and of the log's session-5 entries that the list doesn't know must be
   one of a short list of known exceptions (British spellings, units, names). And one spelling
   throughout: no word may appear in both its British and its American form (centre and center).
2. The checks give the same answer twice: rounds 52, 53 and 55 (the ones that draw random numbers or
   lay pages out in Chromium) are each run twice, and their output must be the same, word for word.
3. Enough random builds: rounds 52 and 53 count rare events in 200 000 random builds. Each count's
   statistical error must leave it at least 5 standard errors under its 1 % limit, and the same
   builds drawn with five other seeds must all stay under the limit too.
"""
import contextlib
import io
import json
import math
import os
import re
import subprocess
import sys

import numpy as np

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
KNOWN = {  # British spellings, units, names and tools the word list doesn't have
    "centre", "centred", "centres", "colour", "moulded", "metre", "mm", "px", "ppi", "qty", "stl", "waveshare",
    "waveshare's", "chamfer's", "pdftotext", "preload", "roark", "timestamp", "timestamps", "voxel", "booleans",
    "pyspellchecker's", "txt"}
PAIRS = [("centre", "center"), ("centred", "centered"), ("colour", "color"), ("moulded", "molded"), ("metre", "meter"),
         ("grey", "gray"), ("fibre", "fiber"), ("aluminium", "aluminum"), ("behaviour", "behavior"),
         ("organise", "organize"), ("minimise", "minimize"), ("labelled", "labeled"), ("travelled", "traveled")]


def plain(t):
    t = re.sub(r"`[^`]*`", " ", t)
    t = re.sub(r"\S+\.(?:txt|md|py|json|stl|png|pdf|zip|jpg|sh)\b", " ", t)      # file names
    t = re.sub(r"\]\([^)]*\)", "] ", t)
    t = re.sub(r"https?://\S+", " ", t)
    return re.sub(r"<[^>]+>", " ", t)


def spelling():
    try:
        from spellchecker import SpellChecker
    except ImportError:
        skip("spelling: pyspellchecker is not installed (pip install pyspellchecker)")
        return
    sp = SpellChecker(language="en")

    def flat(v):
        if isinstance(v, str):
            return [v]
        if isinstance(v, (list, tuple)):
            return [s for x in v for s in flat(x)]
        return []
    T = json.load(open(os.path.join(ROOT, "docs", "guide-src", "text_en.json"), encoding="utf-8"))
    log = open(os.path.join(ROOT, "DEBUG_LOG.md"), encoding="utf-8").read()
    texts = {"README": open(os.path.join(ROOT, "README.md"), encoding="utf-8").read(),
             "English guide": " ".join(s for k, v in T.items() for s in flat(v)),
             "log (session 5)": log[log.index("## Session 5"):] if "## Session 5" in log else log}
    rows, ok, every = [], True, set()
    for name, t in texts.items():
        words = [w.lower() for w in re.findall(r"(?<![\w-])[A-Za-z][a-z]+(?:'[a-z]+)?(?![\w-])", plain(t))]
        every |= set(words)
        odd = sorted(sp.unknown(words) - KNOWN)
        ok &= not odd
        rows.append(f"{name} {len(words)} words" + (f", not known: {odd}" if odd else ""))
    both = [f"{b}/{a}" for b, a in PAIRS if b in every and a in every]
    ok &= not both
    report(ok, "spelling: " + "; ".join(rows) + ("; every word known or one of the "
               f"{len(KNOWN)} exceptions" if ok else "") + f"; British and American forms of one word: {both or 'none'}")


# ------------------------------------------------------------------ 2
def twice():
    rows, ok = [], True
    for r in ("round52.py", "round53.py", "round55.py"):
        outs = [subprocess.run([sys.executable, "-B", os.path.join(HERE, r)], capture_output=True, text=True,
                               cwd=ROOT, timeout=1800).stdout for _ in range(2)]
        same = outs[0] == outs[1]
        ok &= same and bool(outs[0])
        rows.append(f"{r[:-3]} {'the same' if same else 'DIFFERENT'} ({outs[0].count(chr(10))} lines)")
    report(ok, "the checks give the same answer twice: " + ", ".join(rows))


# ------------------------------------------------------------------ 3
def enough_builds():
    import round45
    with contextlib.redirect_stdout(io.StringIO()):
        round45.across_photos()
    field = np.array([8.0, 95.2, *round45.LIGHT_Y])
    centre = np.array([case.BW / 2, case.BW / 2, case.BH / 2, case.BH / 2])
    win = np.array([case.WIN_CX - case.WIN_W / 2, case.WIN_CX + case.WIN_W / 2,
                    case.WIN_CY - case.WIN_H / 2, case.WIN_CY + case.WIN_H / 2])

    def builds(seed, T=20.0, n=200_000):      # rounds 52 (T 20) and 53 (T 10), the same model
        rng = np.random.default_rng(seed)
        half = np.array([case.BW / 2 + case.CLR, case.BH / 2 + case.CLR])
        s = rng.uniform(0.002, 0.004, n)
        play = np.maximum(case.CLR - s[:, None] * half[None], 0.0)
        off = rng.uniform(-1, 1, (n, 2)) * play
        dT = T - 20.0
        w = centre + (win - centre) * (1 - s[:, None]) * (1 + 68e-6 * dT) + rng.normal(0, 0.05, (n, 4))
        f = (centre + (field - centre) * (1 + 14e-6 * dT) + rng.normal(0, 0.1, (n, 4))
             + np.column_stack([off[:, 0], off[:, 0], off[:, 1], off[:, 1]]))
        hidden = np.column_stack([w[:, 0] - f[:, 0], f[:, 1] - w[:, 1], w[:, 2] - f[:, 2], f[:, 3] - w[:, 3]])
        return float((hidden.max(1) > 86.4 / 800).mean())
    rows, ok = [], True
    for label, T, seed in (("round 52 (20 °C)", 20.0, 52), ("round 53 (10 °C)", 10.0, 53)):
        p = builds(seed, T)
        se = math.sqrt(p * (1 - p) / 200_000)
        others = [builds(s, T) for s in (1, 2, 3, 4, 5)]
        k = (0.01 - p) / se
        ok &= k >= 5 and max(others) < 0.01
        rows.append(f"{label}: {p * 100:.2f} % ± {se * 100:.3f} (standard error), {k:.0f} standard errors under 1 %; "
                    f"other seeds {min(others) * 100:.2f}-{max(others) * 100:.2f} %")
    report(ok, "enough random builds: " + "; ".join(rows) + " (want 5 standard errors under, and every seed under 1 %)")


if __name__ == "__main__":
    spelling()
    twice()
    enough_builds()
    print(f"\nRound 57: {len(problems)} problem(s), {len(skipped)} skipped")
    for p in problems:
        print("  -", p)
