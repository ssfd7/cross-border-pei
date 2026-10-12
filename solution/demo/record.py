"""Record the captioned demo video of the review app.

Run from solution/ with the app up on port 8501:  .venv/bin/python demo/record.py
Writes demo/xb-pei-demo.mp4. Needs playwright (with chromium) and imageio-ffmpeg.
"""
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import Page, sync_playwright

APP = "http://localhost:8501"
OUT = Path(__file__).parent
SIZE = {"width": 1440, "height": 900}

# (page to open or None to stay, heading to scroll to or None for the top, seconds, caption)
SCENES = [
    (None, None, 11, "A cross-border private equity fund: every payment to an investor can carry a withholding consequence."),
    (None, "How the pieces fit", 11, "One ontology gives each business term one meaning, with a steward and a status."),
    (None, "One term, from the business question to the rows", 14, "Trace a term from the business question, through the ontology, to the rows that hold it."),
    ("Clearance workflow", None, 14, "The withholding procedure, step by step. Each step names the governed computations and tools it uses."),
    (None, "Second review and sign-off", 11, "The agent drafts the schedule. Only a person signs it."),
    ("LookThrough analytics", None, 12, "The same ontology and bundle answer analytical questions. Nothing is defined twice."),
    (None, "What the answer rests on", 12, "Each answer shows the computations that produced it."),
    ("Benchmark", "Evidence behind the schedule", 12, "Grounded agent: all 30 schedule lines carry evidence, and all 207 cited facts resolve to the data."),
    (None, "Evidence behind the schedule", 11, "Ungrounded agent: the same 30 lines, with a free-text basis that nothing checks."),
    (None, None, 12, "Synthetic data and illustrative rules. Next: investor onboarding and documentation upkeep on the same ontology."),
]

CAPTION = """
(() => {
  const style = document.createElement('style');
  style.textContent = '[data-testid="stToolbar"]{display:none}';
  document.head.appendChild(style);
  const bar = document.createElement('div');
  bar.id = 'demo-caption';
  bar.style.cssText = 'position:fixed;left:50%;bottom:28px;transform:translateX(-50%);max-width:1100px;padding:14px 26px;'
    + 'background:rgba(20,24,32,.92);color:#fff;font:500 22px/1.35 -apple-system,Helvetica,Arial,sans-serif;'
    + 'border-radius:10px;text-align:center;z-index:999999;box-shadow:0 4px 18px rgba(0,0,0,.3)';
  document.body.appendChild(bar);
})()
"""


def show(page: Page, heading: str | None) -> None:
    if heading:
        page.get_by_role("heading", name=heading, exact=True).first.evaluate("e => e.scrollIntoView({behavior: 'smooth', block: 'start'})")
    else:
        page.get_by_test_id("stMain").evaluate("e => e.scrollTo({top: 0, behavior: 'smooth'})")


def record() -> tuple[Path, float]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport=SIZE, record_video_dir=str(OUT), record_video_size=SIZE)
        started = time.monotonic()
        page = context.new_page()
        page.goto(f"{APP}/?page=Overview&term=xbpei:Clearance")
        page.get_by_role("heading", name="One ontology grounding two products").wait_for()
        page.wait_for_timeout(2500)
        page.evaluate(CAPTION)
        page.evaluate("document.getElementById('demo-caption').style.visibility = 'hidden'")
        lead = time.monotonic() - started  # the loading screen, cut from the video
        for opens, heading, seconds, caption in SCENES:
            if opens:
                page.evaluate("document.getElementById('demo-caption').style.visibility = 'hidden'")
                page.get_by_test_id("stSidebar").get_by_text(opens, exact=True).click()
                page.get_by_role("heading", name=opens).first.wait_for()
                page.wait_for_timeout(1500)
            show(page, heading)
            page.evaluate("t => { const bar = document.getElementById('demo-caption'); bar.textContent = t; bar.style.visibility = 'visible'; }", caption)
            page.wait_for_timeout(seconds * 1000)
        raw = Path(page.video.path())
        context.close()
        browser.close()
    return raw, lead


if __name__ == "__main__":
    raw, lead = record()
    final = OUT / "xb-pei-demo.mp4"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", f"{lead:.2f}", "-i", str(raw),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", str(final)], check=True)
    raw.unlink()
    print(final, f"{final.stat().st_size / 1e6:.1f} MB")
