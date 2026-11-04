"""The round 58 reviewer's window test, kept as it wrote it, except that ROOT is found from this file:
the board anywhere the cavity lets it sit (a 61 x 61 grid, kept where the board fits), PLA shrinkage 0-0.4 %,
and the light field's worst corner margin inside the rounded window."""
import sys
ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
sys.path.insert(0, ROOT); sys.dont_write_bytecode = True
import numpy as np, case
from shapely.geometry import Polygon, Point, box as sbox
from shapely import affinity
def rr(w,h,r,cx,cy):
    return sbox(cx-w/2+r, cy-h/2+r, cx+w/2-r, cy+h/2-r).buffer(r, quad_segs=64)
board = rr(case.BW, case.BH, case.BR, case.BW/2, case.BH/2)
cav = rr(case.BW+2*case.CLR, case.BH+2*case.CLR, case.BR+case.CLR, case.BW/2, case.BH/2)
win = rr(case.WIN_W, case.WIN_H, case.WIN_R, case.WIN_CX, case.WIN_CY)
for (name, lf) in (("measured", (8.0, 95.2, 3.036, 56.424)), ("nominal", (8.0, 95.2, 3.0, 56.4))):
  for s in (0.0, 0.002, 0.003, 0.004):
    c = affinity.scale(cav, 1-s, 1-s, origin=(case.BW/2, case.BH/2))
    w = affinity.scale(win, 1-s, 1-s, origin=(case.BW/2, case.BH/2))
    wb = w.exterior
    worst = (9, None)
    for dx in np.linspace(-0.3, 0.3, 61):
        for dy in np.linspace(-0.3, 0.3, 61):
            b = affinity.translate(board, dx, dy)
            if not c.buffer(1e-6).contains(b): continue
            x0,x1,y0,y1 = lf
            for (x,y) in ((x0,y0),(x1,y0),(x0,y1),(x1,y1)):
                p = Point(x+dx, y+dy)
                m = wb.distance(p) * (1 if w.contains(p) else -1)
                if m < worst[0]: worst = (m, (round(dx,3), round(dy,3), x, y))
    print(name, "shrink", s, "worst light-field corner margin", round(worst[0],3), worst[1])
