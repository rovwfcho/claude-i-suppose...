#!/usr/bin/env python3
"""Debug round 12: methods not used in rounds 1-11.

1. Capsule finger: a 14 mm wide finger modelled as a cylinder with a round tip, pushed onto each
   switch and the dial straight and tilted (round 1-4 used spheres)
2. Rounded edges measured: circles fitted to sections of the outer corners and edges
3. Board pocket measured wall to wall in sections (must be the PCB plus 0.3 mm each side)
4. README: every file it names exists, every link resolves
"""
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402
from manifold3d import Manifold  # noqa: E402
from round1 import load_assembled, to_manifold  # noqa: E402

problems = []


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


# ------------------------------------------------------------------ 1
def capsule(r, length):
    """Finger along +y with its round tip at the origin."""
    tip = Manifold.sphere(r, 64)
    body = Manifold.cylinder(length, r, r, 64).rotate([90, 0, 0])  # from y=0 to y=-length
    return tip + body


def capsule_fingers(variant):
    shell, _, cover_asm, _ = load_assembled(variant)
    obst = to_manifold(shell) + to_manifold(cover_asm)
    r = 7.0
    finger = capsule(r, 40)

    def stop(target, ang_x, ang_z, travel=20.0):
        rot = finger.rotate([ang_z, 0, ang_x])  # tilt about x (front/back) and z (sideways)
        d = np.array([math.sin(math.radians(-ang_x)), math.cos(math.radians(ang_x)) * math.cos(math.radians(ang_z)),
                      math.sin(math.radians(ang_z))])
        d /= np.linalg.norm(d)
        start = np.asarray(target) - d * (r + travel)
        hit = lambda t: not (rot.translate(list(start + d * t)) ^ obst).is_empty()
        if not hit(travel):
            return 0.0
        lo, hi = 0.0, travel
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if not hit(mid) else (lo, mid)
        return travel - lo

    for name, bx in case.BUTTONS.items():
        tip = [bx, -case.BTN_PROTRUDE, case.Z_B + 0.9]
        for label, ax, az in (("straight", 0, 0), ("15 deg toward the front", 0, -15), ("15 deg toward the back", 0, 15)):
            s = stop(tip, ax, az)
            report(s <= 0.6, f"{variant} {name} capsule finger {label}: stops {s:.2f} mm before the switch tip")
    # dial: finger coming down onto the top edge (flip the finger to point along -y)
    wx, wy, wr = case.WHEEL
    global finger_down
    rim = np.array([wx, case.BH + 2.0, case.Z_B + 1.5])  # smaller protrusion from the drawing
    f2 = finger.rotate([0, 0, 180])
    d = np.array([0, -1.0, 0])
    start = rim - d * (r + 20)
    hit = lambda t: not (f2.translate(list(start + d * t)) ^ obst).is_empty()
    lo, hi = 0.0, 20.0
    if hit(hi):
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if not hit(mid) else (lo, mid)
        s = 20.0 - lo
    else:
        s = 0.0
    report(s <= 0.5, f"{variant} dial capsule finger straight: stops {s:.2f} mm before the rim (2.0 mm protrusion)")


# ------------------------------------------------------------------ 2
def fit_circle(pts):
    A = np.column_stack([2 * pts[:, 0], 2 * pts[:, 1], np.ones(len(pts))])
    b = (pts ** 2).sum(1)
    cx, cy, c = np.linalg.lstsq(A, b, rcond=None)[0]
    return np.array([cx, cy]), math.sqrt(c + cx ** 2 + cy ** 2)


def outer_loop(sec, axes):
    """Points of the section loop with the largest enclosed area (the outside of the part)."""
    best, area = None, -1.0
    for e in sec.discrete:
        p = e[:, list(axes)]
        a = 0.5 * abs(np.dot(p[:-1, 0], p[1:, 1]) - np.dot(p[1:, 0], p[:-1, 1]))
        if a > area:
            best, area = p, a
    return best


def rounded_edges(variant):
    shell, _, cover_asm, z_total = load_assembled(variant)
    # plan corner radius: section at mid-wall height, points of the outer outline near a corner
    z = case.RE + 0.5
    sec = shell.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    pts = np.concatenate([e[:, :2] for e in sec.discrete])  # openings split the outline into pieces
    cx0, cy0 = case.X1 - case.RP, case.Y1 - case.RP
    # keep only points on the outer arc of the top-right corner (the inner pocket's corner is
    # much closer to this centre)
    rr = np.hypot(pts[:, 0] - cx0, pts[:, 1] - cy0)
    sel = (pts[:, 0] > cx0 + 0.3) & (pts[:, 1] > cy0 + 0.3) & (rr > case.RP - 1.0)
    c, r = fit_circle(pts[sel])
    expect = case.RP - case.surface_inset(z, z_total)
    report(abs(r - expect) < 0.1, f"{variant} plan corner radius measured {r:.2f} mm at z={z:.1f} "
                                  f"(designed {case.RP}, {expect:.2f} at this height) from {sel.sum()} points")
    # edge rounding: vertical section across the middle of the left wall, outer profile near the front
    # y = 50: no openings in the left wall there (USB-C is at 30, the mic holes at 42-46)
    sec = shell.section(plane_origin=[0, 50.0, 0], plane_normal=[0, 1, 0])
    pts = outer_loop(sec, (0, 2))
    x0 = case.X0
    arc = pts[(pts[:, 0] < x0 + 0.3 * case.RE) & (pts[:, 1] > 0.3 * case.RE) & (pts[:, 1] < case.RE)]
    c, r = fit_circle(arc)
    report(abs(r - case.RE) < 0.15, f"{variant} front edge rounding radius measured {r:.2f} mm (designed {case.RE}) "
                                   f"from {len(arc)} outline points")


# ------------------------------------------------------------------ 3
def pocket(variant):
    shell, _, _, _ = load_assembled(variant)
    z = (case.Z_PF + case.Z_B) / 2
    for label, o, d, expect in (("width", [-10, 22.0, z], [1, 0, 0], case.BW + 2 * case.CLR),
                                ("height", [52.0, -10, z], [0, 1, 0], case.BH + 2 * case.CLR)):
        locs, _, _ = shell.ray.intersects_location([o], [d], multiple_hits=True)
        s = np.sort((locs - np.array(o)) @ np.array(d, float))
        # crossings: outer wall in, inner wall out ... inner wall in, outer wall out
        inner = s[2] - s[1] if len(s) >= 4 else -1
        report(abs(inner - expect) < 0.02, f"{variant} board pocket {label} measured {inner:.3f} mm "
                                           f"(PCB {expect - 2 * case.CLR} + 2 x {case.CLR})")


# ------------------------------------------------------------------ 4
def readme_links():
    text = open(os.path.join(ROOT, "README.md")).read()
    names = set(re.findall(r"`((?:stl|checks|preview)/[^`]+|[\w./-]+\.(?:py|md|png|sh))`", text))
    names |= set(re.findall(r"\]\(([^)#]+)\)", text))
    missing = [n for n in sorted(names) if not os.path.exists(os.path.join(ROOT, n))]
    report(not missing, f"README names {len(names)} files/links; missing: {missing or 'none'}")


if __name__ == "__main__":
    readme_links()
    for v in case.CAVITY:
        print(f"\n### {v}")
        pocket(v)
        rounded_edges(v)
        capsule_fingers(v)
    print(f"\nRound 12: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
