"""Render a Draw.io file in solution/ to a PNG with a white background, in solution/diagrams/.

Uses headless Google Chrome and the diagrams.net viewer script, which is fetched from the network;
the diagram itself is rendered locally. Renders the first page only.

    python diagrams/render.py okf-extension-overview
"""
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

from PIL import Image, ImageChops

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HERE = Path(__file__).resolve().parent


def render(name: str) -> Path:
    source, out = HERE.parent / f"{name}.drawio", HERE / f"{name}.png"
    model = ET.parse(source).find(".//mxGraphModel")
    width, height = int(model.get("pageWidth")), int(model.get("pageHeight"))
    config = {"highlight": "none", "nav": False, "resize": False, "toolbar": None, "edit": None, "lightbox": False,
              "auto-fit": False, "auto-crop": False, "border": 0, "zoom": 1, "xml": source.read_text()}
    with tempfile.TemporaryDirectory() as tmp:
        page, shot = Path(tmp) / "view.html", Path(tmp) / "shot.png"
        page.write_text(f"""<!doctype html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:#fff}} .mxgraph{{border:0!important}}</style></head><body>
<div class="mxgraph" style="width:{width}px" data-mxgraph="{escape(json.dumps(config), quote=True)}"></div>
<script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script></body></html>""")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={width + 80},{height + 80}",
                        "--force-device-scale-factor=2", "--virtual-time-budget=20000", f"--screenshot={shot}", page.as_uri()],
                       check=True, capture_output=True)
        image = Image.open(shot).convert("RGB")
    box = ImageChops.difference(image, Image.new("RGB", image.size, "white")).getbbox()
    margin = 40
    image.crop((max(box[0] - margin, 0), max(box[1] - margin, 0), min(box[2] + margin, image.width),
                min(box[3] + margin, image.height))).save(out, optimize=True)
    return out


if __name__ == "__main__":
    for diagram in sys.argv[1:]:
        print(render(diagram))
