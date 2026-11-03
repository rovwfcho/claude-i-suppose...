"""Build the assembly guide (English and Bulgarian) as HTML pages, ready to print to PDF."""
import json
import os
import sys

from PIL import Image, ImageChops

G = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(G, "out")
labels = json.load(open(os.path.join(G, "labels.json")))


def crop(name, margin=30):
    """Crop a render to its content; return the file name, its size and the shifted marker positions."""
    im = Image.open(os.path.join(G, name + ".png")).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    x0, y0, x1, y1 = ImageChops.difference(im, bg).getbbox()
    pts = labels.get(name, {}).get("labels", [])
    for x, y in pts:  # keep every marker inside the picture
        x0, y0, x1, y1 = min(x0, x - 20), min(y0, y - 20), max(x1, x + 20), max(y1, y + 20)
    x0, y0 = max(int(x0) - margin, 0), max(int(y0) - margin, 0)
    x1, y1 = min(int(x1) + margin, im.width), min(int(y1) + margin, im.height)
    im.crop((x0, y0, x1, y1)).save(os.path.join(OUT, name + ".png"))
    return name + ".png", (x1 - x0, y1 - y0), [(x - x0, y - y0) for x, y in pts]


IMG = {n: crop(n) for n in ("hero", "parts", "step1", "step2", "step3", "step4a", "step4b", "print")}


def figure(name, legend, marks=None, width=100, max_h=85, box=170):
    """width: % of the column; the picture is also kept under max_h mm tall in a box mm wide column."""
    f, (w, h), pts = IMG[name]
    width = min(width, 100 * max_h * w / h / box)
    marks = marks or [str(i + 1) for i in range(len(pts))]
    dots = "".join(f'<span class="mk" style="left:{100 * x / w:.2f}%;top:{100 * y / h:.2f}%">{m}</span>'
                   for (x, y), m in zip(pts, marks))
    leg = "".join(f"<li><b>{m}</b> {t}</li>" for m, t in legend) if legend else ""
    return (f'<figure><div class="pic" style="width:{width:.1f}%;margin:0 auto"><img src="{f}">{dots}</div>'
            + (f'<ol class="legend">{leg}</ol>' if leg else "") + "</figure>")


CSS = """
@page { size: A4; margin: 14mm 14mm 16mm 14mm; }
:root { --ink:#1d1d1f; --mute:#5a5a60; --acc:#e05a00; --line:#e3e1dc; --soft:#f6f4f0; }
* { box-sizing: border-box; }
body { font-family: Inter, 'DejaVu Sans', sans-serif; color: var(--ink); font-size: 10.5pt; line-height: 1.45; margin: 0; }
h1 { font-size: 22pt; margin: 0 0 2mm; letter-spacing: -0.01em; }
h2 { font-size: 14pt; margin: 7mm 0 2.5mm; padding-bottom: 1.5mm; border-bottom: 2px solid var(--acc); break-after: avoid; }
h3 { font-size: 11.5pt; margin: 5mm 0 1.5mm; break-after: avoid; }
p { margin: 1.5mm 0; }
.sub { color: var(--mute); font-size: 11pt; margin-bottom: 4mm; }
figure { margin: 2mm auto 3mm; break-inside: avoid; }
.pic { position: relative; }
.pic img { width: 100%; display: block; }
.mk { position: absolute; transform: translate(-50%, -50%); width: 6.2mm; height: 6.2mm; border-radius: 50%;
      background: var(--acc); color: #fff; font-weight: 700; font-size: 9pt; display: flex; align-items: center;
      justify-content: center; border: 1.5px solid #fff; box-shadow: 0 0.3mm 1mm rgba(0,0,0,.35); }
.legend { list-style: none; padding: 0; margin: 2mm 0 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(55mm, 1fr)); gap: 1mm 6mm; font-size: 9.5pt; }
.legend li b { display: inline-block; min-width: 5mm; height: 5mm; border-radius: 50%; background: var(--acc); color: #fff;
               text-align: center; font-size: 8pt; line-height: 5mm; margin-right: 1.5mm; }
table { width: 100%; border-collapse: collapse; font-size: 9.5pt; break-inside: auto; }
th, td { text-align: left; vertical-align: top; padding: 1.6mm 2mm; border-bottom: 1px solid var(--line); }
th { background: var(--soft); font-weight: 600; }
tr { break-inside: avoid; }
.step { display: grid; grid-template-columns: 9mm 1fr; gap: 3mm; margin-top: 5mm; break-inside: avoid; }
.num { width: 9mm; height: 9mm; border-radius: 50%; background: var(--ink); color: #fff; font-weight: 700; font-size: 13pt;
       display: flex; align-items: center; justify-content: center; }
.step h3 { margin-top: 1.5mm; }
.note { background: var(--soft); border-left: 3px solid var(--acc); padding: 2mm 3mm; margin: 2.5mm 0; font-size: 9.5pt; break-inside: avoid; }
.warn { border-left-color: #c62828; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; align-items: start; }
ul { margin: 1mm 0; padding-left: 5mm; } li { margin: 0.6mm 0; }
.pb { break-before: page; }
.foot { color: var(--mute); font-size: 8.5pt; margin-top: 6mm; }
"""


def page(T):

    body = f"""
<h1>{T['title']}</h1>
<div class="sub">{T['subtitle']}</div>
{figure('hero', None, max_h=44)}
<p>{T['intro']}</p>

<h2>{T['h_buy']}</h2>
<table><tr><th>{T['col_item']}</th><th>{T['col_qty']}</th><th>{T['col_notes']}</th></tr>
{''.join(f'<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>' for a, b, c in T['buy'])}</table>
<h3>{T['h_tools']}</h3><ul>{''.join(f'<li>{t}</li>' for t in T['tools'])}</ul>

<h2>{T['h_parts']}</h2>
<p>{T['parts_text']}</p>
{figure('parts', T['fig_parts'], max_h=60)}

<h2>{T['h_print']}</h2>
<div class="two"><div><ul>{''.join(f'<li>{t}</li>' for t in T['print'])}</ul></div>
<div>{figure('print', T['fig_print'], box=85)}</div></div>
<div class="note">{T['print_note']}</div>

<h2>{T['h_assembly']}</h2>
<div class="step"><div class="num">1</div><div><h3>{T['s1_h']}</h3><p>{T['s1']}</p>{figure('step1', T['fig1'])}</div></div>
<div class="step"><div class="num">2</div><div><h3>{T['s2_h']}</h3><p>{T['s2']}</p>
<div class="note warn">{T['s2_warn']}</div>{figure('step2', T['fig2'], marks=['1', '2', '3', '3', '3', '3', '4', '5', '6', '7', '8'])}</div></div>
<div class="step"><div class="num">3</div><div><h3>{T['s3_h']}</h3><p>{T['s3']}</p>{figure('step3', T['fig3'], marks=['1', '2', '3', '4', '4', '4', '4'], max_h=80)}</div></div>
<div class="step"><div class="num">4</div><div><h3>{T['s4_h']}</h3><p>{T['s4']}</p>
<div class="note">{T['s4_note']}</div>{figure('step4a', T['fig4a'], max_h=80)}</div></div>

<h2 class="pb">{T['h_open']}</h2>{figure('step4b', T['fig4b'], max_h=55)}<ul>{''.join(f'<li>{t}</li>' for t in T['open'])}</ul>
<h2>{T['h_tips']}</h2><ul>{''.join(f'<li>{t}</li>' for t in T['tips'])}</ul>
<p class="foot">{T['foot']}</p>
"""
    return f'<!doctype html><html lang="{T["lang"]}"><head><meta charset="utf-8"><title>{T["title"]}</title><style>{CSS}</style></head><body>{body}</body></html>'


if __name__ == "__main__":
    for lang in sys.argv[1:]:
        T = json.load(open(os.path.join(G, f"text_{lang}.json")))
        open(os.path.join(OUT, f"guide_{lang}.html"), "w").write(page(T))
        print("wrote", lang)
