#!/usr/bin/env python3
"""Debug round 52 (session 5): methods not used in rounds 1-51.

1. The window, statistically. Round 49 put the board in its nine worst positions with every other
   number at its measured value. Here 200 000 builds are drawn at random, each with: the board
   anywhere in its play (uniform), the lid's shrinkage as it cools (uniform 0.2-0.4 %, which pulls
   the lid's walls and the window toward the lid's middle, so the board has less play but the
   window's edges move in too), each edge of the light field off by its measuring error (normal,
   0.1 mm standard deviation: your two photos across the board agree within 0.14 mm) and each edge
   of the window off by the printer's error (normal, 0.05 mm). In fewer than 1 build in 100 may the
   frame hide a whole row or column of pixels (0.108 mm, 86.4 mm / 800) on any side.
2. Every number in the README's Features list that rounds 49-51 changed, recomputed from the STL
   (the window's size and edges, the left frame), not from case.py.
3. Every text of the guides reaches the PDF. Round 43 looked for the guides' headings in the PDFs;
   here every text in text_en.json and text_bg.json (each sentence, table cell, legend line and tip)
   must be in the PDF's text, so a text the page template leaves out, or one added to the JSON
   (like round 51's new tip) and never laid out, is found.
4. The guide pages as Chromium lays them out for print (A4, the guides' own margins): no line of
   text may stick out of its box (a table cell, a note, a legend line) or out of the page, every
   picture must load, and no two numbered markers on a picture may touch (0.5 mm apart at least), so
   none hides another or reads as one.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import case  # noqa: E402

problems = []
skipped = []


def skip(msg):
    print("  SKIP " + msg)
    skipped.append(msg)


def report(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + msg)
    if not ok:
        problems.append(msg)


def window_monte_carlo(n=200_000, seed=52):
    import contextlib
    import io
    import round45
    with contextlib.redirect_stdout(io.StringIO()):
        round45.across_photos()
    field = np.array([8.0, 95.2, *round45.LIGHT_Y])          # left, right, bottom, top
    rng = np.random.default_rng(seed)
    cx, cy = case.BW / 2, case.BH / 2                       # the lid's middle (the board's, centred)
    half = np.array([case.BW / 2 + case.CLR, case.BH / 2 + case.CLR])
    s = rng.uniform(0.002, 0.004, n)
    play = np.maximum(case.CLR - s[:, None] * half[None], 0.0)     # the walls move in too
    off = rng.uniform(-1, 1, (n, 2)) * play
    win = np.array([case.WIN_CX - case.WIN_W / 2, case.WIN_CX + case.WIN_W / 2,
                    case.WIN_CY - case.WIN_H / 2, case.WIN_CY + case.WIN_H / 2])
    centre = np.array([cx, cx, cy, cy])
    w = centre + (win - centre) * (1 - s[:, None]) + rng.normal(0, 0.05, (n, 4))
    f = field + rng.normal(0, 0.1, (n, 4)) + np.column_stack([off[:, 0], off[:, 0], off[:, 1], off[:, 1]])
    hidden = np.column_stack([w[:, 0] - f[:, 0], f[:, 1] - w[:, 1], w[:, 2] - f[:, 2], f[:, 3] - w[:, 3]])
    row = 86.4 / 800
    worst = hidden.max(1)
    p_row = float((worst > row).mean())
    p_any = float((worst > 0).mean())
    sides = ", ".join(f"{k} {float((hidden[:, i] > row).mean()) * 100:.2f} %"
                      for i, k in enumerate(("left", "right", "bottom", "top")))
    report(p_row < 0.01, f"window, {n} random builds (board play, 0.2-0.4 % shrinkage, measuring and print "
                         f"errors): a whole pixel row or column hidden in {p_row * 100:.2f} % ({sides}), any "
                         f"sliver at all in {p_any * 100:.1f} % (want under 1 % for a whole row)")


def readme_from_stl():
    import trimesh
    from shapely.geometry import Polygon
    from round1 import load_assembled
    shell = load_assembled("battery")[0]
    z = case.T_FRONT - case.GLASS_RELIEF - 0.05               # behind the chamfer, in the straight part
    sec = shell.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    planar, tf = sec.to_2D()
    pts = lambda r: trimesh.transform_points(np.column_stack([np.asarray(r.coords), np.zeros(len(r.coords))]), tf)[:, :2]  # noqa: E731
    holes = [Polygon(pts(r)) for p in planar.polygons_full for r in p.interiors]
    win = max(holes, key=lambda h: h.area)
    x0, y0, x1, y1 = win.bounds
    left_frame = x0 - shell.bounds[0][0]
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    want = {f"{x1 - x0:.1f} x {y1 - y0:.1f} mm": f"Display window:** {x1 - x0:.1f} x {y1 - y0:.1f} mm",
            f"window runs {y0:.1f}-{y1:.1f}": f"(it runs from {y0:.1f} to {y1:.1f})",
            f"starts at {x0:.1f}": f"The window now starts at {x0:.1f} mm",
            f"left frame {left_frame:.1f}": f"({left_frame:.1f} mm vs about 6 mm elsewhere)"}
    missing = [k for k, v in want.items() if v not in text]
    report(not missing, f"README's window numbers recomputed from the lid's STL (section at z {z:.2f}): window "
                        f"x {x0:.2f}-{x1:.2f}, y {y0:.2f}-{y1:.2f} ({x1 - x0:.2f} x {y1 - y0:.2f} mm), left frame "
                        f"{left_frame:.2f} mm; " + ("all as the README says" if not missing else f"not in the README: {missing}"))


def flat(v):
    if isinstance(v, str):
        return [v]
    if isinstance(v, (list, tuple)):
        return [s for x in v for s in flat(x)]
    return []


def squeeze(t):
    t = unicodedata.normalize("NFKC", html.unescape(re.sub(r"<[^>]+>", "", t))).replace("\u00ad", "")
    return re.sub(r"\s+", "", t)


def texts_in_pdf():
    if not shutil.which("pdftotext"):
        skip("guide texts in the PDFs: pdftotext is not installed")
        return
    rows = []
    for lang in ("en", "bg"):
        T = json.load(open(os.path.join(ROOT, "docs", "guide-src", f"text_{lang}.json"), encoding="utf-8"))
        pdf = os.path.join(ROOT, "docs", f"assembly_guide_{lang}.pdf")
        # -raw keeps the PDF's own order, so a table's columns don't interleave; hyphens are left out on both
        # sides because pdftotext joins a word broken after one (ESP32-S3-/ePaper reads ESP32-S3ePaper)
        txt = squeeze(subprocess.run(["pdftotext", "-raw", pdf, "-"], capture_output=True, text=True).stdout).replace("-", "")
        items = [t for k, v in T.items() if k != "lang" for t in flat(v) if squeeze(t)]
        lost = [t for t in items if squeeze(t).replace("-", "") not in txt]
        rows.append((lang, len(items), lost))
    report(all(not r[2] for r in rows), "guide texts in the PDFs: " + "; ".join(
        f"{lang.upper()} {n} texts, " + ("all in the PDF" if not lost else f"not in the PDF: {[t[:60] for t in lost]}")
        for lang, n, lost in rows))


LAYOUT_JS = r"""
const {chromium} = require('playwright');
(async () => {
  const b = await chromium.launch();
  const res = {};
  for (const [lang, file] of JSON.parse(process.argv[1])) {
    const p = await b.newPage({viewport: {width: 688, height: 1100}});   // A4 less 2 x 14 mm, at 96 px/in
    await p.emulateMedia({media: 'print'});
    await p.goto('file://' + file, {waitUntil: 'networkidle'});
    await p.evaluate(() => document.fonts.ready);
    res[lang] = await p.evaluate(() => {
      const W = document.documentElement.clientWidth, out = {width: W, wide: [], sticks: [], imgs: [], overlap: [], lines: 0};
      const boxOf = n => { let e = n.parentElement;
        while (e && getComputedStyle(e).display.startsWith('inline')) e = e.parentElement; return e; };
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n; (n = walk.nextNode());) {
        if (!n.textContent.trim()) continue;
        const box = boxOf(n), br = box.getBoundingClientRect(), cs = getComputedStyle(box);
        const l = br.left + parseFloat(cs.borderLeftWidth), r = br.right - parseFloat(cs.borderRightWidth);
        const rg = document.createRange(); rg.selectNodeContents(n);
        for (const q of rg.getClientRects()) {
          out.lines++;
          if (q.left < l - 1 || q.right > r + 1) out.sticks.push(`${box.tagName}.${box.className}: "${n.textContent.trim().slice(0, 40)}" ${q.left.toFixed(0)}-${q.right.toFixed(0)} in ${l.toFixed(0)}-${r.toFixed(0)}`);
          if (q.left < -0.5 || q.right > W + 0.5) out.wide.push(n.textContent.trim().slice(0, 40));
        }
      }
      for (const e of document.body.querySelectorAll('*')) {
        const q = e.getBoundingClientRect();
        if (q.width && (q.left < -0.5 || q.right > W + 0.5)) out.wide.push(`${e.tagName}.${e.className} ${q.left.toFixed(0)}-${q.right.toFixed(0)}`);
      }
      for (const im of document.images) if (!im.complete || !im.naturalWidth) out.imgs.push(im.getAttribute('src'));
      out.nimgs = document.images.length;
      let nm = 0;
      for (const pic of document.querySelectorAll('.pic')) {
        const mk = [...pic.querySelectorAll('.mk')].map(m => [m.getBoundingClientRect(), m.textContent]);
        nm += mk.length;
        for (let i = 0; i < mk.length; i++) for (let j = i + 1; j < mk.length; j++) {
          const [a, ta] = mk[i], [c, tc] = mk[j];
          const d = Math.hypot((a.left + a.right - c.left - c.right) / 2, (a.top + a.bottom - c.top - c.bottom) / 2);
          if (d < (a.width + c.width) / 2 + 2) out.overlap.push(`${pic.querySelector('img').getAttribute('src')}: ${ta} and ${tc}, ${d.toFixed(1)} px apart`);
        }
      }
      out.nmarks = nm;
      return out;
    });
  }
  console.log(JSON.stringify(res));
  await b.close();
})();
"""


def guide_layout():
    node = shutil.which("node")
    if not node or subprocess.run([node, "-e", "require('playwright')"], capture_output=True).returncode != 0:
        skip("guide layout: node with playwright is not installed")
        return
    out_dir = os.path.join(ROOT, "docs", "guide-src", "out")
    files = [(lang, os.path.join(out_dir, f"guide_{lang}.html")) for lang in ("en", "bg")]
    if not all(os.path.exists(f) for _, f in files):
        skip("guide layout: the guides' HTML pages are not built (docs/guide-src/build_all.sh)")
        return
    r = subprocess.run([node, "-e", LAYOUT_JS, json.dumps(files)], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        report(False, f"guide layout: Chromium failed: {r.stderr[-300:]}")
        return
    res = json.loads(r.stdout)
    ok, rows = True, []
    for lang, o in res.items():
        bad = o["sticks"] + o["wide"] + o["imgs"] + o["overlap"]
        ok &= not bad
        rows.append(f"{lang.upper()}: {o['lines']} lines of text, {o['nimgs']} pictures, {o['nmarks']} markers"
                    + ("" if not bad else f"; out of their box: {o['sticks'][:4]}, past the page: {o['wide'][:4]}, "
                                          f"pictures not loading: {o['imgs']}, markers touching: {o['overlap']}"))
    report(ok, f"guide pages laid out for print ({res['en']['width']} px wide, A4 less the margins): "
               + "; ".join(rows) + ("; every line inside its box and the page, every picture loaded, no markers "
                                    "touching" if ok else ""))


if __name__ == "__main__":
    window_monte_carlo()
    readme_from_stl()
    texts_in_pdf()
    guide_layout()
    print(f"\nRound 52: {len(problems)} problem(s), {len(skipped)} skipped")
    for p in problems:
        print("  -", p)
