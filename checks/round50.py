#!/usr/bin/env python3
"""Debug round 50 (session 5): methods not used in rounds 1-49.

1. Pressing on the display. The window leaves the glass open, so a finger can press the board
   straight back, toward the battery and the speaker. The board hangs on its four corner standoffs.
   Its bending under a firm 10 N press in the middle of the window is estimated as a beam across the
   long span between the standoffs (94.6 mm), FR-4 (E about 18 GPa) 1.6 mm thick, counting only half
   the board's width (a plate held at four points bends more than one held along two edges) and
   leaving out the glass bonded to it, which only stiffens it. The room behind the board is measured
   in the models: from the back of every part on the board's back to whatever lies behind it there
   (the battery in its bay on its tape, the speaker in its pocket, the battery wire across the
   battery's bottom edge), with 4 mm and with 3 mm standoffs. The press that closes the smallest
   gap must be more than 10 N; beyond that the battery or the speaker simply takes the load.
2. A read-through of the debug log from round 45 on, as a whole: every figure an entry gives that a
   later round changed must be corrected in a later entry (not silently left standing).
"""
import os
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


def overlap(a, b):
    """Plan overlap of two (x0, x1, y0, y1) boxes."""
    return min(a[1], b[1]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[2], b[2])


def press():
    E, t, P = 18000.0, case.PCB_T, 10.0                      # MPa, mm, N
    xa, xb = case.POSTS[0][0], case.POSTS[1][0]
    L = xb - xa
    I = (case.BH / 2) * t ** 3 / 12
    xm = (xa + xb) / 2

    def bend(x0, x1):
        """Most a part between x0 and x1 is pushed back by 10 N in the middle (beam on two supports)."""
        x = min(max(xm, x0), x1)
        u = min(max(x - xa, 0.0), L - max(x - xa, 0.0))     # distance from the nearer support
        u = max(0.0, min(u, L / 2))
        return P * u * (3 * L ** 2 - 4 * u ** 2) / (48 * E * I)
    tape = 0.2                                               # the thickest tape the README allows
    z_in = case.Z_B + case.CAVITY["battery"]
    bx0, bx1, by0, by1 = case.BATTERY_BAY
    sx, sy = case.SPEAKER["battery"]
    w, h, _ = case.SPEAKER_BOX["battery"]
    behind = [("battery", (bx0, bx1, by0, by1), z_in - case.BATTERY_SIZE[2] - tape),
              ("speaker", (sx - w / 2, sx + w / 2, sy - h / 2, sy + h / 2), z_in - case.SPEAKER_SIZE[2] - tape)]
    rows, ok = [], True
    for sh in (case.STANDOFF_H, case.STANDOFF_H_MIN):
        d = case.STANDOFF_H - sh                             # how much further back the board sits
        bm = case.board_model(standoff_h=sh)
        pcb_back = bm["pcb"].bounding_box()[5]
        hard, soft = [], []
        for k, m in bm.items():
            bb = m.bounding_box()
            if k in ("pcb", "standoffs") or bb[2] < pcb_back - 0.01:
                continue
            for name, box, z in behind:
                if overlap((bb[0], bb[3], bb[1], bb[4]), box):
                    g = z - bb[5]
                    hard.append((P * g / bend(max(bb[0], box[0]), min(bb[3], box[1])), g, k, name))
        # the wires lie on the board's parts: they are soft, and only get squeezed
        for label, (pts, r) in (("battery wire", case.battery_wire_route()), ("speaker cable", case.speaker_wire_route())):
            for p, q in zip(pts, pts[1:]):
                if abs(p[2] - q[2]) > 1e-6:
                    continue
                seg = (min(p[0], q[0]) - r, max(p[0], q[0]) + r, min(p[1], q[1]) - r, max(p[1], q[1]) + r)
                for name, box, z in behind:
                    if overlap(seg, box):
                        g = z - (p[2] + r + d)
                        soft.append((P * g / bend(max(seg[0], box[0]), min(seg[1], box[1])), g, label, name))
        f, g, part, what = min(hard)
        ok &= g > 0 and f > P
        txt = f"{sh:.0f} mm standoffs: {part.replace('_', ' ')} {g:.2f} mm from the {what}, touches it at about {f:.0f} N"
        if soft:
            fs, gs, lab, wh = min(soft)
            txt += f" (the {lab} is squeezed against the {wh} from about {max(fs, 0):.0f} N)"
        rows.append(txt)
    report(ok, f"pressing the display: a 10 N press in the middle bends the board about {bend(xm, xm):.2f} mm there "
               f"(beam estimate, half the board's width, glass left out); " + "; ".join(rows)
               + " (want a board part to reach the battery or the speaker only above 10 N)")


if __name__ == "__main__":
    press()
    print("  ..   read-through of the log from round 45 on: see DEBUG_LOG.md, round 50")
    print(f"\nRound 50: {len(problems)} problem(s)")
    for p in problems:
        print("  -", p)
