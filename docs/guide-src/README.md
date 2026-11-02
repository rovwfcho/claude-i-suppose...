# Assembly guide sources

`assembly_guide_en.pdf` and `assembly_guide_bg.pdf` (one folder up) are built from these files:

- `text_en.py`, `text_bg.py`: all the guide's text (run them to write `text_*.json`)
- `specs.json`: the 3D scenes (parts, camera, numbered marker positions)
- `scene.html` + `shoot.js`: render the scenes with three.js in headless Chromium (needs `three.module.js` and `STLLoader.js` from three.js r160 next to `scene.html`, the scene STLs exported from `case.py`, and a local web server on port 8766)
- `build.py`: crops the renders, places the markers and writes `out/guide_*.html`
- `topdf.js`: prints the HTML to A4 PDF with Chromium
