"""Render Draw.io pages to PNG with a white background.

Uses headless Google Chrome and the diagrams.net viewer script, which is fetched from the network;
the diagram itself is rendered locally.

    python diagrams/render.py okf-extension-overview    first page of solution/<name>.drawio, to solution/diagrams/
    python diagrams/render.py --model                   every page of the ontology diagram, to model/diagrams/
"""
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

from PIL import Image, ImageChops

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HERE = Path(__file__).resolve().parent


MODEL = HERE.parents[1] / "model"


def render(source: Path, out: Path, page: int = 0) -> Path:
    model = ET.parse(source).findall(".//mxGraphModel")[page]
    width, height = int(model.get("pageWidth")), int(model.get("pageHeight"))
    config = {"highlight": "none", "nav": False, "resize": False, "toolbar": None, "edit": None, "lightbox": False,
              "auto-fit": False, "auto-crop": False, "border": 0, "zoom": 1, "page": page, "xml": source.read_text()}
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
    if sys.argv[1:] == ["--model"]:
        source = MODEL / "xb-pei-model.drawio"
        for page, diagram in enumerate(ET.parse(source).getroot().findall("diagram")):
            out = render(source, MODEL / "diagrams" / (re.sub(r"[^a-z0-9]+", "-", diagram.get("name").lower()).strip("-") + ".png"), page)
            image = Image.open(out)  # the ontology pages are kept at half the rendered size
            image.resize((image.width // 2, image.height // 2), Image.LANCZOS).save(out, optimize=True)
            print(out)
    else:
        for name in sys.argv[1:]:
            print(render(HERE.parent / f"{name}.drawio", HERE / f"{name}.png"))
