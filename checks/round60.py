#!/usr/bin/env python3
"""Debug round 60 (session 5): methods not used in rounds 1-59.

1. Every number in the README, accounted for. Round 58's reviewer found two README numbers that no
   check really held to (a stub of 2.4 mm that was 2.5, a USB-C grip that didn't fit everywhere).
   Here every number in the README (its measures, counts and percentages; not names, part numbers,
   round and step numbers) is looked for in what the checks printed in their last run
   (checks/.cache/out/, which run_checks.py writes): it is traced when a line of that output gives the
   same value, to the README's precision, and shares a word with the README's sentence. Every number
   not traced that way must be one of the EXPLAINED list below, where I worked out by hand where it
   comes from (case.py, Waveshare's drawing, a count you can see in the README itself, ...), and no
   entry of that list may be stale (its number no longer in the README). With no saved output (the
   checks never run through run_checks.py here) this part is SKIP.
2. The second independent review: another reviewer, fresh, went through the case as round 58 left
   it. What it found, and what I made of it, is in DEBUG_LOG.md, round 60.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

problems = []
skipped = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def skip(msg):
    print("  SKIP " + msg)
    skipped.append(msg)


STOP = set("with that this from have they their there where which when what into onto than then them each also "
           "more less most only over under same just like your about after before because both does done here "
           "must would could should mm the and for are but not all any can its it's off out per".split())
# names and numbers that aren't measures: product names, part numbers, standards, rounds, steps, photos
NOT_MEASURES = [r"ESP32-S3-ePaper-3\.97", r"SKU \d+", r"model \d+", r"\b454261\b", r"ISO \d+", r"DIN \d+", r"\bM2(?:\.5)?\b",
                r"[Rr]ounds? \d+(?:(?:, | and |–|-)\d+)*", r"[Ss]teps? \d+(?:(?:, | and |–|-)\d+)*",
                r"photos? \d+", r"\bPH\d\b", r"r\d{3}\b", r"^\s*\d+\. ", r"\b20\d\d\b", r"\bx\d\b",
                r"three\.js r\d+", r"0\.\d+\.\d+"]


def readme_numbers():
    """Every number in the README that is a measure, with its sentence and its neighbours (the other
    numbers of a group like 104.9 x 65.4 x 16.7 or 2.45 / 97.05)."""
    t = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    t = re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), t)                  # code and file names
    t = re.sub(r"\]\([^)]*\)", lambda m: " " * len(m.group(0)), t)              # link targets
    for rx in NOT_MEASURES:
        t = re.sub(rx, lambda m: " " * len(m.group(0)), t, flags=re.M)
    found = [(m.group(1), m.start(), m.end()) for m in re.finditer(r"(?<![\w.,/-])(\d+(?:\.\d+)?)(?![\w.]*\d)", t)]
    out = []
    for i, (v, s, e) in enumerate(found):
        a, b = max(0, s - 70), min(len(t), e + 50)
        ctx = " ".join(t[a:b].split())
        near = [w for j, (w, s2, e2) in enumerate(found) if j != i and (0 <= s - e2 <= 4 or 0 <= s2 - e <= 4)]
        out.append((v, ctx, near))
    return out


def words(s):
    return {w for w in re.findall(r"[a-z][a-z'-]{3,}", s.lower()) if w not in STOP}


def account():
    outs = sorted(glob.glob(os.path.join(HERE, ".cache", "out", "*.txt")))
    outs = [f for f in outs if not f.endswith("round60.txt")]
    if len(sys.argv) > 1:
        outs = sys.argv[1:]
    if not outs:
        skip("README numbers: no saved check output (run checks/run_checks.py first)")
        return
    lines = [ln for f in outs for ln in open(f, encoding="utf-8", errors="replace").read().splitlines()]
    index = []
    for ln in lines:
        nums = [(float(v), v) for v in re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", ln)]
        index.append((nums, words(ln)))
    traced, untraced = 0, []

    def close(u, v):
        d = len(v.split(".")[1]) if "." in v else 0
        return abs(u - float(v)) <= 0.5 * 10 ** -d + 1e-9
    for v, ctx, near in readme_numbers():
        kw = words(ctx)
        sig = len(v.replace(".", "").lstrip("0"))
        hit = False
        for nums, w in index:
            if not any(close(u, v) for u, _ in nums):
                continue
            if (kw & w) or any(close(u, n) for n in near for u, _ in nums) \
                    or (sig >= 3 and any(s == v for _, s in nums)):
                hit = True
                break
        if hit:
            traced += 1
        else:
            untraced.append((v, ctx))
    explained, used = [], set()
    for v, ctx in untraced:
        k = next((i for i, (n, snip, _) in enumerate(EXPLAINED) if n == v and snip in ctx), None)
        if k is None:
            explained.append(f"{v} in '...{ctx}...'")
        else:
            used.add(k)
    stale = [f"{n} '{snip}'" for i, (n, snip, _) in enumerate(EXPLAINED) if i not in used]
    for e in explained:
        print("         not traced and not explained:", e)
    report(not explained and not stale,
           f"README numbers: {traced + len(untraced)} in all; {traced} traced to the checks' output "
           f"({len(outs)} rounds), {len(used)} worked out by hand (EXPLAINED); unaccounted for: "
           f"{len(explained)}; stale explanations: {stale or 'none'}")


# number, a piece of its README sentence, where it comes from (worked out by hand, round 60)
EXPLAINED = [
]


if __name__ == "__main__":
    account()
    print("  ..   the second independent review: see DEBUG_LOG.md, round 60")
    print(f"\nRound 60: {len(problems)} problem(s), {len(skipped)} skipped")
    for p in problems:
        print("  -", p)
