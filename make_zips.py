#!/usr/bin/env python3
"""Pack the STL files, the README and the preview renders into dist/<name>.zip."""
import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PACKS = {
    "esp32-s3-epaper-3.97-case-battery-16.7mm": ["stl/front_shell_battery.stl", "stl/back_cover_battery.stl"],
}
COMMON = ["README.md", "preview/renders.png", "preview/explained.png",
          "docs/assembly_guide_en.pdf", "docs/assembly_guide_bg.pdf"]

if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    for top, files in PACKS.items():
        path = os.path.join(ROOT, "dist", top + ".zip")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files + COMMON:
                zi = zipfile.ZipInfo(f"{top}/{f}", date_time=(2026, 10, 30, 0, 0, 0))  # fixed date: same bytes every run
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16
                z.writestr(zi, open(os.path.join(ROOT, f), "rb").read())
        print(f"{path}: {os.path.getsize(path) / 1e6:.2f} MB")
