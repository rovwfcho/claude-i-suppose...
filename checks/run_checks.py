#!/usr/bin/env python3
"""Run every check round, skipping the ones whose inputs have not changed since they last passed.

A round's inputs are its own script, the check modules it imports, and the parts of the project it
reads, worked out from its source (and its imports'):
  geometry  case.py with comments and docstrings stripped (a comment edit changes nothing), and the
            STL files it writes
  readme    README.md            guides  docs/guide-src and the two PDF guides
  log       DEBUG_LOG.md         photos  checks/owner_photos
  zips      make_zips.py         slicer  the PrusaSlicer version
A round that passed is skipped while all of its inputs hash the same as when it passed; everything
else runs. Results are kept in checks/.cache/passed.json, and each round's last output in
checks/.cache/out/ (round 60 reads them); neither is part of the project.

    python3 checks/run_checks.py            # run what changed
    python3 checks/run_checks.py --all      # run everything
    python3 checks/run_checks.py round13    # just these (always run)
"""
import ast
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, ".cache", "passed.json")
ORDER = ["verify.py"] + [f"checks/round{n}.py" for n in
                         sorted(int(m) for m in (re.findall(r"round(\d+)\.py", " ".join(os.listdir(HERE)))))]


def stripped_source(path):
    """The module's code without comments and docstrings."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def files_hash(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(os.path.relpath(p, ROOT).encode())
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def slicer_version():
    try:
        r = subprocess.run(["prusa-slicer", "--help"], capture_output=True, text=True, timeout=60)
        return (r.stdout or "").splitlines()[0] if r.stdout else "none"
    except (OSError, subprocess.TimeoutExpired):
        return "none"


INPUTS = {
    "geometry": lambda: hashlib.sha256((stripped_source(os.path.join(ROOT, "case.py"))
                                        + files_hash(glob.glob(os.path.join(ROOT, "stl", "*.stl")))).encode()).hexdigest(),
    "readme": lambda: files_hash([os.path.join(ROOT, "README.md")]),
    "guides": lambda: files_hash([p for p in glob.glob(os.path.join(ROOT, "docs", "guide-src", "*"))
                                  if os.path.isfile(p)] + glob.glob(os.path.join(ROOT, "docs", "*.pdf"))),
    "log": lambda: files_hash([os.path.join(ROOT, "DEBUG_LOG.md")]),
    "photos": lambda: files_hash(glob.glob(os.path.join(HERE, "owner_photos", "*"))),
    "zips": lambda: files_hash([os.path.join(ROOT, "make_zips.py")]),
    "slicer": slicer_version,
}
WORDS = {"readme": r"README", "guides": r"guide-src|text_en|text_bg|specs\.json|build\.py",
         "log": r"DEBUG_LOG", "photos": r"owner_photos|round28", "zips": r"make_zips|dist/",
         "slicer": r"prusa-slicer|PrusaSlicer|round19|round30"}


def local_imports(path, seen=None):
    """The script and every check module it imports, directly or not."""
    seen = seen if seen is not None else set()
    if path in seen or not os.path.exists(path):
        return seen
    seen.add(path)
    src = open(path, encoding="utf-8").read()
    for name in set(re.findall(r"(?:^|\s)(?:import|from)\s+(round\d+|reference|verify)\b", src)):
        for d in (HERE, ROOT):
            p = os.path.join(d, name + ".py")
            if os.path.exists(p):
                local_imports(p, seen)
    return seen


def key_for(script, values):
    mods = local_imports(os.path.join(ROOT, script))
    src = "".join(open(m, encoding="utf-8").read() for m in sorted(mods))
    needs = ["geometry"] + [k for k, rx in WORDS.items() if re.search(rx, src)]
    h = hashlib.sha256(files_hash(mods).encode())
    for k in needs:
        h.update(k.encode() + values[k].encode())
    return h.hexdigest(), needs


def main(argv):
    os.chdir(ROOT)
    run_all = "--all" in argv
    only = [a for a in argv if not a.startswith("--")]
    scripts = [s for s in ORDER if not only or any(os.path.basename(s).startswith(o) for o in only)]
    subprocess.run([sys.executable, "case.py"], check=True, capture_output=True)   # STLs first: they are inputs
    values = {k: f() for k, f in INPUTS.items()}
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    ran, cached, bad = 0, 0, []
    t0 = time.time()
    for s in scripts:
        key, needs = key_for(s, values)
        if not run_all and not only and cache.get(s, {}).get("key") == key:
            c = cache[s]
            print(f"=== {s}: passed {c['when']} with the same inputs ({', '.join(needs)}): not run again")
            cached += 1
            continue
        print(f"=== {s}", flush=True)
        r = subprocess.run([sys.executable, s], capture_output=True, text=True)
        sys.stdout.write(r.stdout + r.stderr)
        ran += 1
        out = os.path.join(os.path.dirname(CACHE), "out")      # each round's last output (round 60 reads them)
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, os.path.basename(s)[:-3] + ".txt"), "w", encoding="utf-8").write(r.stdout)
        m = re.search(r"Round \d+: (\d+) problem", r.stdout)
        ok = r.returncode == 0 and ((m and m.group(1) == "0") or (s == "verify.py" and "ALL CHECKS PASSED" in r.stdout))
        if ok:
            cache[s] = {"key": key, "when": time.strftime("%Y-%m-%d %H:%M"), "needs": needs}
        else:
            cache.pop(s, None)
            bad.append(s)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w"), indent=1)
    print(f"\n{ran} run, {cached} not run again (inputs unchanged since they passed), "
          f"{len(bad)} with problems{': ' + ', '.join(bad) if bad else ''} ({(time.time() - t0) / 60:.1f} min)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
