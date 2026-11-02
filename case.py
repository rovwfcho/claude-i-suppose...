#!/usr/bin/env python3
"""Parametric two-piece case for the Waveshare ESP32-S3-ePaper-3.97 board.

Generates STL files for a rounded front shell and a back cover with room for Waveshare's
454261 LiPo and the speaker side by side, plus a simplified board model used to check fit.
The battery bay and the speaker pocket are sized from the owner's own battery and speaker, measured
with a ruler in their photos (see README.md, "Where the numbers come from").

Requires: pip install manifold3d trimesh numpy

Coordinate system (all mm), as seen looking at the display:
  x to the right, y up, origin at the bottom-left corner of the PCB outline.
  z goes INTO the device: z = 0 is the outer front face of the case.
  Seen from the front with z pointing away from you, this frame is a mirror image of real space (a
  right-handed frame has +x on your left when you look along +z). Every exported STL therefore gets
  exactly one mirroring (front_for_print, flip_for_print), so the printed parts have the real
  board's handedness. Checks undo it again (checks/round1.py, load_assembled).

Board facts (Waveshare outline drawing): PCB 99.5 x 60, corner R2,
active area 86.40 x 51.84. Every other position below was measured from
Waveshare's 1600 x 1200 product photos (~10 px/mm) and is an estimate
(about +/-0.5 mm). See README.md for the list of assumptions.
"""
import math
import os
import sys

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold

SEG = 96  # circle resolution

# ---------------------------------------------------------------- board
BW, BH, BR = 99.5, 60.0, 2.0     # PCB outline (official)
PCB_T = 1.6                      # assumed standard PCB thickness
PANEL_T = 1.2                    # e-paper glass + adhesive, estimated from photos

# display window (active area 86.40 x 51.84 plus margin)
# Waveshare's dimension drawing puts the active area at x 9.3-95.7, y 4.1-55.9; the photos put the
# grey field at x 7.4-96.5, y 3.6-58.1. This window covers the drawing's area with >= 0.7 mm to spare.
WIN_CX, WIN_CY = 52.4, 30.2
WIN_W, WIN_H, WIN_R = 88.0, 53.6, 1.0
TAIL_X1 = 7.0                    # panel tail / driver-IC strip on the left

# brass standoffs on the back (front-view coordinates)
POSTS = [(2.2, 2.85), (96.7, 2.85), (2.2, 57.4), (96.7, 57.4)]
STANDOFF_D = 4.5                 # measured outer diameter incl. photo blur
STANDOFF_H = 4.0                 # estimate (photos suggest 3-4 mm)
POST_RIN = STANDOFF_D / 2 + 1.3  # pads keep 1.3 mm off the measured standoff edge (position is +/-0.5)
POST_ROUT = POST_RIN + 1.1
# ring sector (degrees from +x) facing the board centre; the bottom-left one is narrowed to stay off
# the microSD socket and the 5V header pad, the top two to clear the top-left and right-hand screw
# blocks. Edges are kept off the circle vertices (every 360/SEG = 3.75 deg) so no zero-area
# triangles appear.
POST_SECTORS = [(1, 40), (91, 179), (271, 329.5), (181, 224.5)]
# The board is pressed against the front pads by a piece of 1 mm double-sided foam tape on each ring:
# the ring faces stay FOAM_GAP behind the PCB, so the foam is squeezed to about 60 % and keeps
# pushing (it takes up print, layer-height and PCB-thickness tolerance; no plastic has to bend)
FOAM_T, FOAM_GAP = 1.0, 0.6

USB_Y = 30.0                     # USB-C on the left edge, back side
SD_Y = 13.95                     # microSD slot on the left edge, back side
WHEEL = (79.0, 56.96, 5.65)      # dial wheel centre x, y and radius (top edge)
BUTTONS = {"BOOT": 74.0, "PWR": 84.0}  # side buttons on the bottom edge
BTN_PROTRUDE = 0.75
MIC = (2.5, 43.8)                # MEMS mic, back side
DHT = (97.8, 48.5)               # temperature / humidity sensor, back side
# Speaker: the owner's speaker, measured against a ruler in their photos (round 28): a box
# 14.2 x 10.2-10.3 x 4.5 mm (+/-0.3), with a white peg about 2.6 mm wide sticking out about 1.6 mm from one
# short side (1 mm off its middle), and its cable leaving a long side about 2.9 mm from the peg's end.
# Its sound face (a white membrane about 10 x 6 mm inside a black gasket ring) lies face down on the
# grille, peg toward the top edge, so the cable leaves on the side facing the battery. It sits turned
# lengthways in a pocket with about 0.45-0.55 mm clearance all round, located by four corner brackets whose
# short legs leave the middle of every side open for the peg and the cable. The grille is three slots
# under the membrane, well inside the speaker's sealed face, so no sound leaks round its edge. The
# pocket is 7.9 mm (the brackets 6.7 mm) from the ESP32 module's antenna end (right-hand end of the
# board, about x 93.5-99.5), so the magnet won't detune it.
SPEAKER_SIZE = (10.3, 14.2, 4.5)          # turned lengthways: x, y, z
SPEAKER_WINDOW = (5.8, 10.0)              # membrane on the sound face, turned (x, y), centred
SPEAKER_BOX = {"battery": (11.2, 15.3, 4.5)}   # the pocket inside the brackets (x, y, height kept)
SPK_ROOM = tuple((b - s) / 2 for b, s in zip(SPEAKER_BOX["battery"][:2], SPEAKER_SIZE[:2]))  # play each way
SPEAKER = {"battery": (80.0, 15.5)}       # pocket centre
SPK_BRACKET = (1.2, 2.0, 2.0, 1.2)        # corner brackets: wall, height, leg along the short / long sides
SPK_CABLE_EXIT = 2.9                      # cable centre from the peg's end, along the long side
GRILLE_SLOTS = (1.0, 7.0, 1.8)            # three slots along y: width, length, pitch (0.8 mm webs)
ANTENNA = (93.5, 99.5, 14.0, 40.0)       # x0, x1, y0, y1 of the module's antenna end (estimate)
# Battery: the owner's Waveshare 3.7 V 1500 mAh LiPo (model 454261), measured against a ruler in their
# photos (round 28): 61.1 x 40.7 x 4.3 mm including its taped protection-board end (+/-0.3). Its wires
# leave that end at one corner. The bay is 62.5 x 42.5 mm (1.4 and 1.8 mm more than the cell, so it
# can only shift about 0.7-0.9 mm each way) and 5 mm deep, with guide bars on all four sides; the
# corners stay open so the wire can leave from either corner.
BATTERY_SIZE = (61.1, 40.7, 4.3)
BATTERY_MAX = (62.3, 42.2, 4.8)          # largest it could plausibly be (ruler error, tape, swelling)
BATTERY_BAY = (5.5, 68.0, 6.5, 49.0)     # x0, x1, y0, y1
BATTERY_GUIDE = (1.2, 2.0)               # guide bar thickness and height
BATTERY_SPACE = 5.0                      # height kept for it (4.3 mm cell + swelling/tape)
PARTS_SPACE = 5.0                        # room above the PCB for its parts and wires

# ---------------------------------------------------------------- case
CLR = 0.3                        # board edge to inner wall
FLEX_RELIEF = 0.3                # extra wall clearance beside the display flex (left edge)
WALL = 2.4
T_FRONT = 1.6
PANEL_SPACE = PANEL_T + 0.5      # room for the panel; lip floats above the glass
T_BACK = 1.8
RP = 7.0                         # plan-view corner radius
RE = 4.5                         # edge rounding radius (front and back)
CAVITY = {"battery": PARTS_SPACE + BATTERY_SPACE}  # clear depth behind the PCB

Z_PF = T_FRONT + PANEL_SPACE     # PCB front face
Z_B = Z_PF + PCB_T               # PCB back face
Z_SPLIT = Z_B + 7.5              # shell / back-cover parting plane
SKIRT_H, SKIRT_T, SKIRT_CLR = 2.5, 1.2, 0.35  # rigid parts: room for +/-0.15 mm print error on each
Z_COMP = Z_B + 4.0               # assumed top of the tallest parts on the PCB back

# side buttons: the bottom wall is left out between these x values, from the front face to 2.5 mm
# past the seam, so nothing covers the switches and a finger reaches them straight or tilted 15 deg.
# The display lip above the opening stays whole.
BTN_NOTCH = (min(BUTTONS.values()) - 6.0, max(BUTTONS.values()) + 6.0)
BTN_NOTCH_TOP = Z_SPLIT + 2.5
TAB_CLR = 0.35                           # side gap of the back-cover tab in the dial notch
BTN_BEVEL = 1.2                          # outer edges of the opening bevelled so a tilted finger fits

# no-flex closure: M2 screws through the long walls into blocks on the back cover
# (position along the wall, wall). The top-left one sits near the corner and the fourth goes in the
# right-hand wall, so the dial's thumb scoop has room; the bottom ones sit beside the battery bay.
SCREWS = [(20.0, "bottom"), (64.0, "bottom"), (8.5, "top"), (52.4, "right")]
SCREW_Z = Z_SPLIT - 3.1            # keeps the counterbore 1.0 mm below the parting line
BLOCK_Z0 = Z_B + 2.7               # screw blocks sit where only low parts are (see README)
# The M2 screws pass a clearance hole in the shell wall and cut their own thread in the cover's block.
# The wall hole is set SCREW_DRAW toward the front, so with the case shut the screw shank already
# rests on its back edge: the foam can't push the cover back (a "drawbore"). The pilot has a lead-in
# so the tip finds it.
SCREW_WALL_R, SCREW_PILOT_R, SCREW_DRAW = 1.15, 0.9, 0.05  # pilot 1.8 mm for PLA: forming the thread
# strains the thin block walls about a third less than a 1.7 mm pilot (PLA cracks sooner than PETG, and
# small sideways holes print a little undersize); draw 0.05: hole top on the 0.1/0.2 mm layer grid
SCREW_HEAD_R, SCREW_HEAD_DEPTH = 2.1, 1.4  # counterbore for a pan or button head
BLOCK_DEPTH = 5.5

X0, Y0 = -CLR - WALL, -CLR - WALL
X1, Y1 = BW + CLR + WALL, BH + CLR + WALL


# ---------------------------------------------------------------- helpers
def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def rrect(w, h, r, cx=0.0, cy=0.0):
    base = CrossSection.square([w - 2 * r, h - 2 * r], True)
    return base.offset(r, JoinType.Round, 2.0, SEG).translate([cx, cy])


def prism(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def cyl_x(y, z, r, x0, x1):
    return Manifold.cylinder(x1 - x0, r, r, SEG).rotate([0, 90, 0]).translate([x0, y, z])


def cyl_y(x, z, r, y0, y1):
    return Manifold.cylinder(y1 - y0, r, r, SEG).rotate([-90, 0, 0]).translate([x, y0, z])


def cyl_z(x, y, r, z0, z1, seg=SEG):
    return Manifold.cylinder(z1 - z0, r, r, seg).translate([x, y, z0])


def slot_x(y0, y1, zc, h, x0, x1):
    """Stadium hole through an x-facing wall, long axis along y."""
    r = h / 2
    return Manifold.hull(cyl_x(y0 + r, zc, r, x0, x1) + cyl_x(y1 - r, zc, r, x0, x1))


def slot_z(x0, x1, y0, y1, z0, z1):
    """Stadium hole through the back wall."""
    w, h = x1 - x0, y1 - y0
    r = min(w, h) / 2
    return prism(rrect(w, h, r - 1e-3, (x0 + x1) / 2, (y0 + y1) / 2), z0, z1)


def slab_xz(x0, x1, z0, z1, r, y0, y1):
    """Rounded rectangle in the x-z plane, extruded along y from y0 to y1."""
    cs = rrect(x1 - x0, z1 - z0, r, (x0 + x1) / 2, (z0 + z1) / 2)
    return prism(cs, 0, y1 - y0).rotate([90, 0, 0]).translate([0, y1, 0])


def button_notch():
    """Opening in the bottom wall (outside the cavity only) that exposes the PWR/BOOT switches."""
    x0, x1 = BTN_NOTCH
    b = BTN_BEVEL
    inner = slab_xz(x0, x1, -3.0, BTN_NOTCH_TOP, 2.0, Y0 + b, -CLR + 0.01)
    bevel = Manifold.hull(slab_xz(x0, x1, -3.0, BTN_NOTCH_TOP, 2.0, Y0 + b - 0.01, Y0 + b)
                          + slab_xz(x0 - b, x1 + b, -3.0 - b, BTN_NOTCH_TOP + b, 2.0 + b, Y0 - 3, Y0))
    return inner + bevel


def dial_scoop():
    """Thumb dish over the dial; wide enough for a thumb rolling the wheel at an angle."""
    return ellipsoid([WHEEL[0], Y1 + 0.9, Z_B + 1.5], [14.0, 2.8, 4.5])


def screw_frame(pos, side):
    """(point where the screw axis meets the outer wall plane, unit vector pointing into the case,
    coordinate of the cavity wall along that axis)."""
    if side == "bottom":
        return np.array([pos, Y0, SCREW_Z]), np.array([0.0, 1.0, 0.0]), -CLR
    if side == "top":
        return np.array([pos, Y1, SCREW_Z]), np.array([0.0, -1.0, 0.0]), BH + CLR
    if side == "right":
        return np.array([X1, pos, SCREW_Z]), np.array([-1.0, 0.0, 0.0]), BW + CLR
    raise ValueError(side)


def cyl_along(p, d, t0, t1, r):
    """Cylinder of radius r on the axis p + t*d (d along x or y), from t0 to t1."""
    a, b = p + d * t0, p + d * t1
    if d[0] != 0:
        x0, x1 = sorted((a[0], b[0]))
        return cyl_x(p[1], p[2], r, x0, x1)
    y0, y1 = sorted((a[1], b[1]))
    return cyl_y(p[0], p[2], r, y0, y1)


def ellipsoid(c, r):
    return Manifold.sphere(1.0, SEG).scale(r).translate(c)


def edge_profile(r, n=12):
    """(inset, height) points of a print-friendly round: arc to 45 deg, then a 45 deg chamfer."""
    pts = [(r - r * math.cos(a), r - r * math.sin(a))
           for a in np.linspace(0, math.pi / 4, n)]
    pts.append((0.586 * r, 0.0))
    return pts


def body(z_total):
    pts = []
    prof = edge_profile(RE)
    corners = [(X1 - RP, Y1 - RP, 0), (X0 + RP, Y1 - RP, 90),
               (X0 + RP, Y0 + RP, 180), (X1 - RP, Y0 + RP, 270)]
    for cx, cy, a0 in corners:
        for t in np.linspace(math.radians(a0), math.radians(a0 + 90), 49):
            ct, st = math.cos(t), math.sin(t)
            for d, h in prof:
                rr = RP - d
                pts.append((cx + rr * ct, cy + rr * st, h))
                pts.append((cx + rr * ct, cy + rr * st, z_total - h))
    return Manifold.hull_points(pts)


def surface_inset(z, z_total):
    """How far the rounded outer surface sits inside the straight wall at height z."""
    h = min(z, z_total - z)
    prof = edge_profile(RE, 200)
    if h >= RE:
        return 0.0
    return float(np.interp(h, [p[1] for p in prof][::-1], [p[0] for p in prof][::-1]))


def pry_notch(z_total):
    """Shallow dish across the parting line on the right side, for opening the case."""
    x = X1 - surface_inset(Z_SPLIT, z_total)
    return ellipsoid([x + 0.6, 30.0, Z_SPLIT], [1.4, 5.0, 1.8])


def cavity_cs(extra=0.0):
    return rrect(BW + 2 * CLR + 2 * extra, BH + 2 * CLR + 2 * extra,
                 BR + CLR + extra, BW / 2, BH / 2)


# ---------------------------------------------------------------- parts
def front_shell(z_total):
    outer = body(z_total) ^ box(-50, 150, -50, 150, -1, Z_SPLIT)
    s = outer - prism(cavity_cs(), T_FRONT, Z_SPLIT + 1)

    # display window, 45 deg chamfer on the outside
    c = 0.8
    big = rrect(WIN_W + 2 * c, WIN_H + 2 * c, WIN_R + c)
    sc = (WIN_W / (WIN_W + 2 * c), WIN_H / (WIN_H + 2 * c))
    s -= Manifold.extrude(big, c, 0, 0, sc).translate([WIN_CX, WIN_CY, -0.001])
    s -= prism(rrect(WIN_W, WIN_H, WIN_R, WIN_CX, WIN_CY), c - 0.01, T_FRONT + 0.1)

    # extra room for the display flex where it wraps round the left PCB edge (0.1 mm proud of it), so
    # normal plastic shrinkage (0.2-0.4 %) can't make it rub; the PCB itself keeps its CLR
    s -= box(-CLR - FLEX_RELIEF, 0.5, 18.4, 41.3, T_FRONT, Z_PF + 0.1)  # any panel thickness

    # relief over the panel tail (driver IC, sealant)
    # (starts 0.7 mm in from the board edge: the tail does too, and the rounded corners stay solid)
    s -= box(0.7, TAIL_X1, 1.0, BH - 1.0, T_FRONT - 0.5, T_FRONT + 0.1)

    # ledge pads: clamp the PCB front face at its rim, panel never loaded. None on the left end: the
    # glass edge is only about 0.75 mm in from the PCB edge there
    pads = [
        (6, 18, -CLR - 0.1, 0.5), (40, 58, -CLR - 0.1, 0.5), (86, 94, -CLR - 0.1, 0.5),
        (6, 18, BH - 0.5, BH + CLR + 0.1), (35, 60, BH - 0.5, BH + CLR + 0.1),
        (88, 94, BH - 0.5, BH + CLR + 0.1),
        (BW - 0.5, BW + CLR + 0.1, 5, 12), (BW - 0.5, BW + CLR + 0.1, 45, 55),
    ]
    for x0, x1, y0, y1 in pads:
        s += box(x0, x1, y0, y1, T_FRONT - 0.1, Z_PF)

    # side screws: clearance hole (drawn SCREW_DRAW toward the front) + counterbore for the head
    for pos, side in SCREWS:
        p, d, _ = screw_frame(pos, side)
        s -= cyl_along(p - np.array([0, 0, SCREW_DRAW]), d, -1.0, WALL + 0.01, SCREW_WALL_R)
        s -= cyl_along(p, d, -3.0, SCREW_HEAD_DEPTH, SCREW_HEAD_R)

    # USB-C: rounded-rectangle opening sized for common cable overmolds (13 x 7)
    usb_zc = Z_B + 1.6
    usb = rrect(13.0, 7.0, 1.2, USB_Y, usb_zc)
    s -= prism(usb, X0 - 1, 0.5).transform([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0]])  # (y, z, x) -> (x, y, z)
    s -= box(-CLR - 0.3, 0.5, USB_Y - 5.0, USB_Y + 5.0, Z_B - 0.3, Z_SPLIT + 0.1)  # insertion channel

    # microSD: opening + fingernail scoop
    sd_zc = Z_B + 1.1
    s -= slot_x(SD_Y - 6.5, SD_Y + 6.5, sd_zc, 3.2, X0 - 1, 0.5)
    s -= ellipsoid([X0 - 1.0, SD_Y, sd_zc], [2.4, 8.0, 3.6])

    # microphone and sensor vents
    for dy in (-2.0, 0.0, 2.0):  # >= 0.8 mm between holes so the webs print
        s -= cyl_x(MIC[1] + dy, Z_B + 1.0, 0.55, X0 - 1, 0.5)
    s -= dht_slots_x(BW - 0.5, X1 + 1)
    s -= pry_notch(z_total)

    # dial wheel: notch open to the rim (back cover tab closes it) + thumb scoop
    wx, wy, wr = WHEEL
    s -= box(wx - 7.5, wx + 7.5, BH - 1.0, Y1 + 1, Z_B - 0.6, Z_SPLIT + 0.1)
    s -= dial_scoop()

    # side buttons: open notch, switches fully exposed
    s -= button_notch()
    return s


def dht_slots_x(x0, x1):
    """Vertical vent slots through the right-hand wall near the DHT sensor."""
    out = Manifold()
    for y in (40.0, 42.5, 45.0, 47.5):
        zc = Z_B + 1.8
        a = cyl_x(y, zc - 0.9, 0.6, x0, x1)
        b = cyl_x(y, zc + 0.9, 0.6, x0, x1)
        out += Manifold.hull(a + b)
    return out


def grille_slots(variant="battery"):
    """Speaker grille: three stadium slots (x0, x1, y0, y1) along y, centred under the speaker."""
    sx, sy = SPEAKER[variant]
    w, length, pitch = GRILLE_SLOTS
    return [(sx + k * pitch - w / 2, sx + k * pitch + w / 2, sy - length / 2, sy + length / 2)
            for k in (-1, 0, 1)]


def speaker_brackets(variant="battery"):
    """Four L-shaped brackets at the corners of the speaker pocket, as (x0, x1, y0, y1) boxes (two
    per corner, overlapping in the corner square). The legs run SPK_BRACKET[2] along the short sides
    and SPK_BRACKET[3] along the long ones, so the peg and the cable both get out."""
    sx, sy = SPEAKER[variant]
    w, h, _ = SPEAKER_BOX[variant]
    wall, _, leg_x, leg_y = SPK_BRACKET
    out = []
    for cx in (-1, 1):
        for cy in (-1, 1):
            xi, yi = sx + cx * w / 2, sy + cy * h / 2          # inner corner of the pocket
            xo, yo = xi + cx * wall, yi + cy * wall            # outer corner of the bracket
            xl, yl = xi - cx * leg_x, yi - cy * leg_y          # ends of the two legs
            out.append((min(xo, xl), max(xo, xl), min(yi, yo), max(yi, yo)))   # leg along x
            out.append((min(xi, xo), max(xi, xo), min(yo, yl), max(yo, yl)))   # leg along y
    return out


def battery_guides():
    """Guide bars round the battery bay, as (x0, x1, y0, y1) boxes. Each end gets a 14 mm bar in its
    middle; each long side gets bars from 10 mm in from the corners, broken where a screw block
    stands. So the four corners stay open for the battery's wire."""
    x0, x1, y0, y1 = BATTERY_BAY
    th = BATTERY_GUIDE[0]
    ym = (y0 + y1) / 2
    bars = [(x0 - th, x0, ym - 7.0, ym + 7.0), (x1, x1 + th, ym - 7.0, ym + 7.0)]
    for side, ya, yb in (("bottom", y0 - th, y0), ("top", y1, y1 + th)):
        spans = [(x0 + 10.0, x1 - 10.0)]
        for pos, s in SCREWS:
            if s == side:   # keep 1.5 mm off the 4 mm wide block
                a, b = pos - 3.5, pos + 3.5
                spans = [p for lo, hi in spans for p in ((lo, min(hi, a)), (max(lo, b), hi)) if p[1] - p[0] >= 6.0]
        bars += [(lo, hi, ya, yb) for lo, hi in spans]
    return bars


# ---------------------------------------------------------------- wires (assembly advice)
# Where the wires go: centre lines (x, y, z) and wire radius. Not part of the printed geometry: the
# checks (rounds 13, 29 and 31) prove each route is free in the closed case with bends the cables can
# take, and the guide draws them.
def battery_wire_route():
    """Battery wire: leaves the taped end at its bottom corner, drops beside the bay, runs along the
    bottom of the board over the microSD socket and under the battery, and ends in front of BAT."""
    x0, x1, y0, y1 = BATTERY_BAY
    z_in = Z_B + CAVITY["battery"]
    zs = Z_B + 1.9 + 1.25             # resting on top of the microSD socket (1.9 mm tall)
    return [(x0 - 1.4, y0 + 3.5, z_in - BATTERY_SPACE / 2), (3.5, y0 + 3.5, zs), (3.5, 7.6, zs),
            (34.0, 7.6, zs), (34.0, 6.4, zs)], 1.25


def speaker_wire_route():
    """Speaker cable (2.8 mm thick where it is sleeved): its thin leads leave the speaker's long side
    facing the battery (peg toward the top edge) and turn down the gap between the bay and the pocket;
    the sleeved part slopes down under the battery (no bend tighter than 3 mm) and runs to the front
    of SPK (x 52.5-61.5)."""
    sx, sy = SPEAKER["battery"]
    w, h, t = SPEAKER_BOX["battery"]
    z_in = Z_B + CAVITY["battery"]
    r = 1.4
    zl = Z_B + 1.45 + r               # above the board's low parts (1.4 mm), under the battery
    xg = (BATTERY_BAY[1] + sx - w / 2 - SPK_BRACKET[0]) / 2   # middle of the gap between bay and pocket
    ye = sy + SPEAKER_SIZE[1] / 2 - SPK_CABLE_EXIT             # where the cable leaves the speaker
    return [(sx - w / 2 - r - 0.05, ye, z_in - t / 2), (xg, ye, z_in - t / 2), (xg, 9.5, zl),
            (57.0, 9.5, zl), (57.0, 6.4, zl)], r


def speaker_cable_coil():
    """Where the spare speaker cable goes: one loop lying on the back cover above the speaker pocket,
    kept 5 mm from the antenna end and clear of the dial tab. About 77 mm of cable."""
    sx, sy = SPEAKER["battery"]
    z_in = Z_B + CAVITY["battery"]
    r = 1.4
    cx, cy, a, b, rc = sx - 0.5, 40.5, 7.5, 13.5, 4.0   # centre, half sizes, corner radius
    pts = []
    for (qx, qy), a0 in (((cx + a - rc, cy + b - rc), 0), ((cx - a + rc, cy + b - rc), 90),
                         ((cx - a + rc, cy - b + rc), 180), ((cx + a - rc, cy - b + rc), 270)):
        for ang in np.radians(np.linspace(a0, a0 + 90, 7)):
            pts.append((qx + rc * math.cos(ang), qy + rc * math.sin(ang), z_in - r - 0.05))
    pts.append(pts[0])
    return pts, r


def back_cover(z_total, variant):
    outer = body(z_total)
    z_in = z_total - T_BACK
    t = (outer ^ box(-50, 150, -50, 150, Z_SPLIT, z_total + 1)) - prism(cavity_cs(), Z_SPLIT - 1, z_in)

    # skirt that slides inside the shell rim (locating only, nothing has to flex).
    # It stops short of the corners so it never meets the standoff posts.
    sk = prism(cavity_cs(-SKIRT_CLR), Z_SPLIT - SKIRT_H, Z_SPLIT + 0.01) - \
        prism(cavity_cs(-SKIRT_CLR - SKIRT_T), Z_SPLIT - SKIRT_H - 1, Z_SPLIT + 1)
    # join it to the cover wall with a 45 deg slope (a flat ledge would print in mid-air)
    w = SKIRT_CLR + SKIRT_T
    cone = Manifold.hull(prism(cavity_cs(-w), Z_SPLIT - 0.01, Z_SPLIT)
                         + prism(cavity_cs(0.01), Z_SPLIT + w + 0.01, Z_SPLIT + w + 0.02))
    sk += prism(cavity_cs(), Z_SPLIT, Z_SPLIT + w) - cone
    sk ^= box(8.0, 91.0, -5, BH + 5, 0, 50) + box(-5, BW + 5, 8.5, 51.5, 0, 50)
    sk -= box(-5, 6, USB_Y - 7.5, USB_Y + 7.5, 0, 50)             # USB-C
    sk -= box(WHEEL[0] - 8.5, WHEEL[0] + 8.5, BH - 6, BH + 5, 0, 50)  # wheel
    sk -= box(BTN_NOTCH[0] - BTN_BEVEL - 0.5, BTN_NOTCH[1] + BTN_BEVEL + 0.5, -5, 3, 0, 50)  # button opening
    t += sk

    # posts: a sector of a ring beside each standoff; foam tape on it presses the PCB; the standoff stays clear
    for (px, py), (a0, a1) in zip(POSTS, POST_SECTORS):
        ring = cyl_z(px, py, POST_ROUT, Z_B + FOAM_GAP, z_in + 0.05) - cyl_z(px, py, POST_RIN, Z_B - 1, z_in + 1)
        pts = [(px, py)] + [(px + 6 * math.cos(math.radians(a)), py + 6 * math.sin(math.radians(a)))
                            for a in np.linspace(a0, a1, 12)]
        t += ring ^ prism(CrossSection([pts]), Z_B - 1, z_in + 1)

    # tab that closes the top of the wheel notch
    wx = WHEEL[0]
    tab = (outer ^ box(wx - 7.5 + TAB_CLR, wx + 7.5 - TAB_CLR, BH + CLR, Y1 + 1, Z_B + 4.0, Z_SPLIT + 0.05))
    tab -= dial_scoop()
    t += tab

    # the button opening continues 2.5 mm into the cover so a finger can come in tilted
    t -= button_notch()

    # screw blocks with pilot holes
    for pos, side in SCREWS:
        p, d, wall = screw_frame(pos, side)
        a = wall + (SKIRT_CLR if side == "bottom" else -SKIRT_CLR)   # block face against the wall
        b = wall + (BLOCK_DEPTH if side == "bottom" else -BLOCK_DEPTH)
        lo, hi = sorted((a, b))
        if side == "right":
            t += box(lo, hi, pos - 2.0, pos + 2.0, BLOCK_Z0, z_in + 0.05)
        else:
            t += box(pos - 2.0, pos + 2.0, lo, hi, BLOCK_Z0, z_in + 0.05)
        depth = abs(b - (p @ np.abs(d)))  # outer wall plane to the far face of the block
        t -= cyl_along(p, d, 0.0, depth + 0.5, SCREW_PILOT_R)  # through the block: no bottoming out
        face = abs(a - (p @ np.abs(d)))   # outer wall plane to the block face
        t -= Manifold.hull(cyl_along(p, d, face - 0.05, face, SCREW_PILOT_R + 0.35)
                           + cyl_along(p, d, face + 0.35, face + 0.36, SCREW_PILOT_R))  # 45 deg lead-in

    t -= pry_notch(z_total)

    # speaker grille: three slots under the speaker's membrane (none outside it, so the sound from the
    # back of the cone can't leak out round the speaker and cancel the front)
    for x0, x1, y0, y1 in grille_slots(variant):
        t -= slot_z(x0, x1, y0, y1, z_in - 1, z_total + 1)

    # speaker pocket: four L-shaped corner brackets; the middle of every side stays open for the
    # speaker's peg and cable
    for x0, x1, y0, y1 in speaker_brackets(variant):
        t += box(x0, x1, y0, y1, z_in - SPK_BRACKET[1], z_in + 0.05)

    # battery: guide bars on all four sides of its bay. The corners stay open so its wire can leave
    # from either corner of the taped end.
    if variant == "battery":
        for gx0, gx1, gy0, gy1 in battery_guides():
            t += box(gx0, gx1, gy0, gy1, z_in - BATTERY_GUIDE[1], z_in + 0.05)

    # mic holes, DHT vents, drill marks for optional screws into the standoffs
    for dy in (-2.0, 0.0, 2.0):  # >= 0.8 mm between holes so the webs print
        t -= cyl_z(4.6, MIC[1] + dy, 0.6, z_in - 1, z_total + 1, 24)
    for x in (93.0, 95.2):
        t -= slot_z(x - 0.6, x + 0.6, 40.5, 47.5, z_in - 1, z_total + 1)
    for px, py in POSTS:
        t -= Manifold.cylinder(0.45, 0.05, 0.75, 24).translate([px, py, z_total - 0.449])
    return t


def board_model():
    """Simplified board with the parts that matter for fit."""
    zb = Z_B
    parts = {
        "pcb": prism(rrect(BW, BH, BR, BW / 2, BH / 2), Z_PF, zb),
        "panel": box(0.75, 98.5, 1.5, 58.5, Z_PF - PANEL_T, Z_PF),  # glass edges measured on the front photo
        "fpc_fold": box(-0.1, 1.0, 19.4, 40.3, Z_PF - PANEL_T, Z_PF),
        "usb_c": box(-0.4, 7.0, USB_Y - 4.47, USB_Y + 4.47, zb, zb + 3.26),
        "sd_socket": box(1.5, 15.5, 6.5, 21.4, zb, zb + 1.9),
        "esp32_module": box(81.5, 99.5, 14.0, 40.0, zb, zb + 3.3),
        "connectors": box(29.5, 38.5, 0.5, 5.0, zb, zb + 3.5) + box(40.5, 49.5, 0.5, 5.0, zb, zb + 3.5)
        + box(52.5, 61.5, 0.5, 5.0, zb, zb + 3.5),
        "wheel": cyl_z(WHEEL[0], WHEEL[1], WHEEL[2], zb + 0.2, zb + 2.8),
        "wheel_body": box(WHEEL[0] - 6.5, WHEEL[0] + 6.5, 50.5, 58.5, zb, zb + 3.0),
    }
    so = Manifold()
    for px, py in POSTS:
        so += cyl_z(px, py, STANDOFF_D / 2, zb, zb + STANDOFF_H)
    parts["standoffs"] = so
    btn = Manifold()
    for bx in BUTTONS.values():
        btn += box(bx - 2.0, bx + 2.0, 0.0, 3.5, zb, zb + 1.8)
        btn += box(bx - 0.8, bx + 0.8, -BTN_PROTRUDE, 0.01, zb + 0.4, zb + 1.4)
    parts["buttons"] = btn
    return parts


# ---------------------------------------------------------------- output
def to_trimesh(m):
    import trimesh
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)


def write_stl(m, path):
    """Binary STL with triangles in a fixed order, so the same geometry always gives the same file."""
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties, np.float64)[:, :3]
    tri = v[np.asarray(mesh.tri_verts)]
    # rotate each triangle so its lexicographically smallest corner comes first (winding kept)
    keys = tri[:, :, 0] * 1e6 + tri[:, :, 1] * 1e3 + tri[:, :, 2]
    k = np.argmin(keys, axis=1)
    tri = np.stack([tri[np.arange(len(tri)), (k + i) % 3] for i in range(3)], axis=1)
    order = np.lexsort(tri.reshape(len(tri), 9).T[::-1])
    tri = tri[order].astype(np.float32)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(tri), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as f:
        f.write(b"ESP32-S3-ePaper-3.97 case".ljust(80, b" "))
        f.write(np.uint32(len(tri)).tobytes())
        f.write(rec.tobytes())


def flip_for_print(m, z_total):
    """Back cover: outer back face down on the bed. The z mirror is also the one mirroring that
    turns the design frame into real space (see the module notes)."""
    return m.mirror([0, 0, 1]).translate([0, 0, z_total])


def front_for_print(m):
    """Front shell: the display face is already on the bed; mirrored left to right (about the board
    centre) so the printed part has the real board's handedness (see the module notes)."""
    return m.mirror([1, 0, 0]).translate([BW, 0, 0])


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    result = {}
    # the outer rounding follows the total thickness, so each depth gets its own matching shell
    for name, cav in CAVITY.items():
        z_total = Z_B + cav + T_BACK
        shell = front_shell(z_total)
        bc = back_cover(z_total, name)
        result[name] = (shell, bc, z_total)
        write_stl(front_for_print(shell), os.path.join(out_dir, f"front_shell_{name}.stl"))
        write_stl(flip_for_print(bc, z_total), os.path.join(out_dir, f"back_cover_{name}.stl"))
    return result


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "stl")
    for name, (shell, bc, z_total) in build(out).items():
        for part, m in (("front_shell", shell), ("back_cover", bc)):
            print(f"{part}_{name}: {m.volume() / 1000:.1f} cm3, status {m.status()}, total depth {z_total:.1f} mm")
