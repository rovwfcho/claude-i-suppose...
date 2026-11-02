#!/usr/bin/env python3
"""Debug round 16: methods not used in rounds 1-15.

1. Mesh orientation by my own code: every directed edge in each STL file must appear exactly once and
   its reverse exactly once, the parts must be one connected body each, and the signed volume
   (divergence theorem) must be positive, so slicers see the outside as the outside
2. Depth map: rays from the inside of the back wall toward the front over the battery bay and the
   speaker space give the real free depth at every point (a z-buffer, not a collision test)
3. Print bed: the area each part touches the bed with, and its centre of mass over that area
4. Release zips unpacked: every file inside (STLs, README, renders) must be byte-identical to the
   project's current copy, so a zip can't carry an old README
5. README numbers from session 2 recomputed from the code and the STL files
"""
import contextlib
import hashlib
import io
import os
import re
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from round1 import load_assembled  # noqa: E402

problems = []
PARTS = ["front_shell_battery", "back_cover_battery"]


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def read_stl(name):
    raw = open(os.path.join(ROOT, "stl", name + ".stl"), "rb").read()
    n = int(np.frombuffer(raw[80:84], "<u4")[0])
    rec = np.frombuffer(raw[84:84 + 50 * n], np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return rec["v"].astype(np.float64)


# ------------------------------------------------------------------ 1
def orientation():
    for name in PARTS:
        tri = read_stl(name)
        verts, idx = np.unique(tri.reshape(-1, 3), axis=0, return_inverse=True)
        f = idx.reshape(-1, 3)
        directed = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
        key = directed[:, 0].astype(np.int64) * len(verts) + directed[:, 1]
        rkey = directed[:, 1].astype(np.int64) * len(verts) + directed[:, 0]
        uniq, counts = np.unique(key, return_counts=True)
        dup = int((counts > 1).sum())
        unmatched = int((~np.isin(rkey, uniq)).sum())
        # connected bodies: union-find over edges
        parent = np.arange(len(verts))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for a, b in directed[::2]:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        for a, b in directed[1::2]:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        bodies = len({find(i) for i in range(len(verts))})
        signed = float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0)
        E = len(uniq) // 2
        genus = (2 - (len(verts) - E + len(f))) // 2
        report(dup == 0 and unmatched == 0 and bodies == 1 and signed > 0,
               f"{name}: {len(f)} triangles, directed edges used twice {dup}, without a reverse {unmatched}, "
               f"{bodies} body, signed volume {signed / 1000:.2f} cm3, genus {genus}")


# ------------------------------------------------------------------ 2
def depth_map():
    shell, _, cover_asm, z_total = load_assembled("battery")
    import trimesh
    board = [case.to_trimesh(g) for g in case.board_model().values()]
    scene = trimesh.util.concatenate([shell, cover_asm] + board)
    z_in = z_total - case.T_BACK

    def free_depth(x0, x1, y0, y1, step=0.5):
        xs, ys = np.meshgrid(np.arange(x0 + 0.1, x1 - 0.1, step), np.arange(y0 + 0.1, y1 - 0.1, step))
        o = np.column_stack([xs.ravel(), ys.ravel(), np.full(xs.size, z_in - 0.02)])
        d = np.tile([0, 0, -1.0], (len(o), 1))
        loc, ray, _ = scene.ray.intersects_location(o, d, multiple_hits=False)
        depth = np.full(len(o), np.inf)
        depth[ray] = o[ray, 2] - loc[:, 2] + 0.02
        return depth, o

    x0, x1, y0, y1 = case.BATTERY_BAY
    depth, o = free_depth(x0, x1, y0, y1)
    i = int(np.argmin(depth))
    report(depth.min() >= case.BATTERY_SPACE + 0.5,
           f"battery bay depth map ({len(depth)} rays): free depth {depth.min():.2f}-{np.median(depth):.2f} mm "
           f"(min at x {o[i, 0]:.1f}, y {o[i, 1]:.1f}); battery room {case.BATTERY_SPACE} mm + 0.5 mm air wanted")
    sx, sy = case.SPEAKER["battery"]
    w, h, t = case.SPEAKER_BOX["battery"]
    depth, o = free_depth(sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2)
    report(depth.min() >= t + 0.5, f"speaker space depth map ({len(depth)} rays): free depth at least "
                                    f"{depth.min():.2f} mm; speaker room {t} mm + 0.5 mm air wanted")


# ------------------------------------------------------------------ 3
def bed():
    from scipy.spatial import ConvexHull
    from matplotlib.path import Path
    for name in PARTS:
        tri = read_stl(name)
        zmin = tri[:, :, 2].min()
        flat = (tri[:, :, 2] < zmin + 0.01).all(1)
        a = 0.5 * np.linalg.norm(np.cross(tri[flat, 1] - tri[flat, 0], tri[flat, 2] - tri[flat, 0]), axis=1).sum()
        # centre of mass from signed tetrahedra
        v6 = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2]))
        com = (v6[:, None] * tri.sum(1)).sum(0) / (4 * v6.sum())
        pts = tri[flat].reshape(-1, 3)[:, :2]
        hull = ConvexHull(pts)
        inside = Path(pts[hull.vertices]).contains_point(com[:2])
        size = tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0)
        report(a > 500 and inside and size[0] <= 180 and size[1] <= 180,
               f"{name}: bed contact {a:.0f} mm2, centre of mass over it: {inside}, "
               f"footprint {size[0]:.1f} x {size[1]:.1f} mm (fits a 180 mm bed)")


# ------------------------------------------------------------------ 4
def zips():
    dist = os.path.join(ROOT, "dist")
    names = sorted(n for n in os.listdir(dist) if n.endswith(".zip")) if os.path.isdir(dist) else []
    report(len(names) == 1, f"dist/ holds {len(names)} zips: {names}")
    for name in names:
        with zipfile.ZipFile(os.path.join(dist, name)) as z:
            stale = []
            for n in z.namelist():
                rel = n.split("/", 1)[1]
                cur = os.path.join(ROOT, rel)
                if not os.path.exists(cur) or hashlib.sha256(open(cur, "rb").read()).digest() != hashlib.sha256(z.read(n)).digest():
                    stale.append(rel)
            own = {"stl/front_shell_battery.stl", "stl/back_cover_battery.stl"}
            got = {n.split("/", 1)[1] for n in z.namelist() if n.endswith(".stl")}
            report(not stale and got == own, f"{name} unpacked: {len(z.namelist())} files, differing from the project: "
                                             f"{stale or 'none'}; STLs {sorted(got)}")


# ------------------------------------------------------------------ 5
def readme_numbers():
    text = open(os.path.join(ROOT, "README.md")).read()
    import round13
    import round14
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        round13.wires()
        round13.battery_drop()
    out = buf.getvalue()
    lb, ls = (int(v) for v in re.findall(r"about (\d+) mm long", out))
    slide = float(re.search(r"slide at most ([\d.]+) mm", out).group(1))
    sx, sy = case.SPEAKER["battery"]
    w, h, _ = case.SPEAKER_BOX["battery"]
    ant = round14.plan_gap((sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2), case.ANTENNA)
    x0, x1, y0, y1 = case.BATTERY_BAY
    shell, _, cover_asm, z_total = load_assembled("battery")
    lo = np.minimum(shell.bounds[0], cover_asm.bounds[0])
    hi = np.maximum(shell.bounds[1], cover_asm.bounds[1])
    size = "%.1f x %.1f x %.1f mm" % tuple(hi - lo)
    tri = read_stl("front_shell_battery")
    vol_front = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6000.0
    want = {
        "size": size,
        "bay": f"{x1 - x0:.1f} x {y1 - y0:.1f} mm",
        "antenna": f"kept {ant:.1f} mm from the ESP32's antenna",
        "wires": f"about {lb} mm and {ls} mm long",
        "slide": f"about {slide:.1f} mm",
        "speaker room": "%.1f x %.1f mm" % case.SPEAKER_BOX["battery"][:2],
        "test print": f"about {vol_front:.0f} cm³",
    }
    for k, s in want.items():
        report(s in text, f"README states the {k} as '{s}': {s in text}")


if __name__ == "__main__":
    orientation()
    bed()
    zips()
    depth_map()
    readme_numbers()
    print(f"\nRound 16: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
