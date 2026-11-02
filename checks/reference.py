"""Waveshare reference images used by the photo checks, downloaded on first use into checks/.cache.

They are not stored in the repository: they are Waveshare's product photos and drawing. If the
download fails (no network, or the host is blocked where the checks run), `path` raises Unavailable and
the checks that need these images report themselves as SKIPPED, never as passed.
"""
import base64
import os
import re
import urllib.request

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
PHOTO = "https://www.waveshare.com/media/catalog/product/e/s/esp32-s3-epaper-3.97-{n}_1.jpg"
DOCS = "https://docs.waveshare.com/ESP32-S3-ePaper-3.97"


class Unavailable(RuntimeError):
    """The reference image is not cached and could not be downloaded."""


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except OSError as e:  # URLError, HTTP errors, timeouts
        raise Unavailable(f"{url}: {e}") from e


def path(name):
    """'front' (photo 2), 'back' (photo 3) or 'drawing' (the outline drawing on the docs page)."""
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, {"front": "big2.jpg", "back": "big3.jpg", "drawing": "dim0.png"}[name])
    if os.path.exists(out):
        return out
    if name in ("front", "back"):
        data = _get(PHOTO.format(n=2 if name == "front" else 3))
        open(out, "wb").write(data)
    else:
        html = _get(DOCS).decode("utf-8", "replace")
        sect = html[html.find("id=dimensions"):]
        m = re.search(r'src="data:image/(\w+);base64,([^"]+)"', sect)
        raw = base64.b64decode(m.group(2))
        from io import BytesIO
        from PIL import Image
        Image.open(BytesIO(raw)).convert("RGB").save(out)
    return out
