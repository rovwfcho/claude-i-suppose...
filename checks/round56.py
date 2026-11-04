#!/usr/bin/env python3
"""Debug round 56 (session 5): methods not used in rounds 1-55.

1. The project with its history, as you will get it: the last commit packed the way the delivery
   zip is (git archive of HEAD and a git bundle of the history), unpacked into an empty folder, the
   bundle cloned into another one as the zip's HOW-TO-USE.txt says. The clone must check out this
   branch at this commit, hold every commit of it, and have exactly the files of the archive, byte
   for byte; and verify.py must pass in the clone.
2. No dead constants: every named constant at the top of case.py must be used, by case.py's own
   code or by a check, a guide script or verify.py. A constant nothing reads would mislead whoever
   edits it (the README's "If something doesn't fit" sends you to these constants).
3. The README's Files table, the other way round: round 12 checks that every file it names exists;
   here every file and folder in the project (as committed) must be named in it, apart from the
   README itself and the tools' own settings (.claude/, .gitignore).
"""
import ast
import glob
import os
import re
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

problems = []
skipped = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def skip(msg):
    print("  SKIP " + msg)
    skipped.append(msg)


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


# ------------------------------------------------------------------ 1
def with_history():
    top = git("rev-parse", "--show-toplevel")
    if top.returncode != 0:
        skip("project with its history: not a git checkout")
        return
    head = git("rev-parse", "HEAD").stdout.strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    n_commits = int(git("rev-list", "--count", "HEAD").stdout.strip())
    sub = os.path.relpath(ROOT, top.stdout.strip())
    with tempfile.TemporaryDirectory() as d:
        z = os.path.join(d, "everything.zip")
        git("archive", "--format=zip", "--prefix=case/", "-o", z, "HEAD", "--", ".")
        b = os.path.join(d, "history.bundle")
        r = git("bundle", "create", b, "--all")
        if r.returncode != 0:
            report(False, f"project with its history: git bundle failed: {r.stderr[-200:]}")
            return
        unpacked = os.path.join(d, "unpacked")
        zipfile.ZipFile(z).extractall(unpacked)
        clone = os.path.join(d, "esp32-case")
        r = subprocess.run(["git", "clone", "-q", b, clone], capture_output=True, text=True)
        if r.returncode != 0:
            report(False, f"project with its history: git clone of the bundle failed: {r.stderr[-200:]}")
            return
        c_head = git("rev-parse", "HEAD", cwd=clone).stdout.strip()
        c_branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=clone).stdout.strip()
        c_n = int(git("rev-list", "--count", "HEAD", cwd=clone).stdout.strip())
        base = os.path.join(unpacked, "case")
        files = sorted(os.path.relpath(os.path.join(p, f), base) for p, _, fs in os.walk(base) for f in fs)
        cdir = os.path.join(clone, sub) if sub != "." else clone
        differ = [f for f in files if not os.path.exists(os.path.join(cdir, f))
                  or open(os.path.join(base, f), "rb").read() != open(os.path.join(cdir, f), "rb").read()]
        tracked = sorted(git("ls-files", cwd=cdir).stdout.split())
        extra = sorted(set(tracked) - set(files))
        v = subprocess.run([sys.executable, "-B", os.path.join(cdir, "verify.py")], cwd=cdir, capture_output=True,
                           text=True, timeout=1200)
        v_ok = v.returncode == 0 and "SOME CHECKS FAILED" not in v.stdout
        size = os.path.getsize(b) / 1e6
    ok = c_head == head and c_branch == branch and c_n == n_commits and not differ and not extra and v_ok
    report(ok, f"project with its history: the bundle ({size:.1f} MB) clones to branch {c_branch} at "
               f"{c_head[:7]} with {c_n} commits (the project: {branch} at {head[:7]}, {n_commits}); the clone's "
               f"{len(files)} files are "
               + ("byte for byte the archive's" if not differ and not extra else f"not the archive's: differ {differ[:5]}, extra {extra[:5]}")
               + f"; verify.py in the clone: {'passes' if v_ok else 'FAILS: ' + v.stdout[-200:]}")


# ------------------------------------------------------------------ 2
def dead_constants():
    src = open(os.path.join(ROOT, "case.py"), encoding="utf-8").read()
    names = []
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ([t] if isinstance(t, ast.Name) else getattr(t, "elts", [])):
                    if isinstance(n, ast.Name) and n.id.isupper():
                        names.append(n.id)
    code = re.sub(r"#.*", "", src)
    others = "".join(open(f, encoding="utf-8").read() for f in
                     glob.glob(os.path.join(HERE, "*.py")) + glob.glob(os.path.join(ROOT, "docs", "guide-src", "*.py"))
                     + [os.path.join(ROOT, "verify.py"), os.path.join(ROOT, "make_zips.py")])
    own = {n: len(re.findall(rf"\b{n}\b", code)) - 1 for n in names}
    ext = {n: len(re.findall(rf"\bcase\.{n}\b", others)) for n in names}
    dead = [n for n in names if own[n] <= 0 and ext[n] == 0]
    report(not dead, f"case.py's {len(names)} named constants: {sum(1 for n in names if own[n] > 0)} used by its own "
                     f"code, {sum(1 for n in names if own[n] <= 0 and ext[n] > 0)} only by the checks or guide scripts "
                     f"({', '.join(n for n in names if own[n] <= 0 and ext[n] > 0)}), dead: {dead or 'none'}")


# ------------------------------------------------------------------ 3
def files_table():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    table = readme.split("## Files", 1)[1].split("\n## ", 1)[0]
    r = git("ls-files")
    if r.returncode != 0:
        skip("README's Files table: not a git checkout")
        return
    tops = sorted({f.split("/", 1)[0] + ("/" if "/" in f else "") for f in r.stdout.split()})
    tooling = {".claude/", ".gitignore"}
    tops = [t for t in tops if t != "README.md"]             # the table's own file
    unnamed = [t for t in tops if t not in tooling and f"`{t}" not in table and f"]({t}" not in table
               and t.rstrip("/") not in table]
    report(not unnamed, f"README's Files table names every part of the project: {len(tops)} top-level entries besides the README, "
                        f"{len(tooling & set(tops))} of them the tools' settings; not named: {unnamed or 'none'}")


if __name__ == "__main__":
    with_history()
    dead_constants()
    files_table()
    print(f"\nRound 56: {len(problems)} problem(s), {len(skipped)} skipped")
    for p in problems:
        print("  -", p)
