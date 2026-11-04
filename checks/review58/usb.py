"""The round 58 reviewer's USB-C grip test, kept as it wrote it, except that ROOT is found from this file
and the grip size and corner radius can be given on the command line (usb.py W T R; round 59 does).
Grips are pushed into the assembled STLs with 4 and 3 mm standoffs and the board moved along the edge."""
import sys
ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
sys.path.insert(0, ROOT); sys.path.insert(0, ROOT + "/checks"); sys.dont_write_bytecode = True
import numpy as np, case
from round1 import load_assembled, to_manifold
shell, _, cover, _ = load_assembled("battery")
obst = to_manifold(shell) + to_manifold(cover)
def fits(w, t, r, dy, dz):
    zc = case.Z_B + 1.63 + dz
    over = case.prism(case.rrect(w, t, r, case.USB_Y + dy, zc), -0.4 - 25, -0.4).transform([[0,0,1,0],[1,0,0,0],[0,1,0,0]])
    v = (over ^ obst)
    return 0.0 if v.is_empty() else v.volume()
GRIPS = [tuple(map(float, sys.argv[1:3]))] if len(sys.argv) > 2 else [(13.0, 7.0), (12.4, 6.6), (12.4, 7.0), (12.0, 6.9)]
RAD = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
for (w, t) in GRIPS:
    for dz, lab in ((0.0, "4mm"), (1.0, "3mm")):
        for dy in ((-0.3, 0.0, 0.3) if len(sys.argv) > 2 else (0.0, 0.3)):
            print(f"grip {w} x {t} (r {RAD}) {lab} board dy {dy}: overlap {fits(w, t, RAD, dy, dz):.3f} mm3")
