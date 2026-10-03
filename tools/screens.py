#!/usr/bin/env python3
"""Render the book's device screens, messages, signs and quotes exactly as the page shows
them (its own CSS, dark mode) -> audio/screens/chNN_<element index>.png, for the video.

Uses headless Chromium. Each block is placed alone on a page of the book's width, animations
off, screenshot at 2x, cropped to the block.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from bs4 import BeautifulSoup, Tag
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio" / "screens"
KINDS = ("device-view", "dz-card")
CHROMIUM = "chromium"
PAGE_BG = (0x1A, 0x1A, 0x2E)


def wrap(styles, element):
    return f"""<!doctype html><html class="dark"><head><meta charset="utf-8">{styles}
<style>
 *{{animation:none!important;transition:none!important}}
 html,body{{background:#1a1a2e;margin:0;padding:0}}
 body{{padding:16px 20px}}
 .document-page{{background:transparent;box-shadow:none;padding:0;margin:0;min-height:0;width:600px;animation:none}}
 .device-view{{margin:0 auto}} blockquote{{margin:0}} center{{margin:0}}
 table.tight-last td:last-child,table.tight-last th:last-child{{white-space:nowrap}}
</style></head><body><div class="document-page">{element}</div></body></html>"""


def crop(png):
    im = Image.open(png).convert("RGB")
    a = np.asarray(im).astype(int)
    diff = np.abs(a - np.array(PAGE_BG)).sum(axis=2) > 18
    ys, xs = np.where(diff)
    if not len(ys):
        return
    pad = 28
    box = (max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.width, xs.max() + pad), min(im.height, ys.max() + pad))
    im.crop(box).save(png)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path.home() / "snowmoon-screens-tmp"   # snap-confined Chromium can only use visible folders under $HOME
    work.mkdir(parents=True, exist_ok=True)
    chapters = [int(a) for a in sys.argv[1:]] or range(1, 33)
    for ch in chapters:
        html = (ROOT / "source" / "html" / f"chapter-{ch}.html").read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "lxml")
        styles = "".join(str(s) for s in soup.find_all("style"))
        kids = [c for c in soup.find("div", class_="document-page").children if isinstance(c, Tag)]
        for n, el in enumerate(kids):
            cls = el.get("class", [])
            is_block = ("device-view" in cls) or el.name in ("blockquote", "center")
            if not is_block or el.find("svg"):
                continue
            png = OUT / f"ch{ch:02d}_{n}.png"
            if png.exists():
                continue
            for table in el.find_all("table"):   # a short last column (a time, a rate, a button) stays on one line
                last = [tr.find_all(["td", "th"])[-1].get_text(" ", strip=True) for tr in table.find_all("tr") if tr.find_all(["td", "th"])]
                if last and max(len(t) for t in last) <= 12:
                    table["class"] = table.get("class", []) + ["tight-last"]
            src = work / f"ch{ch:02d}_{n}.html"
            src.write_text(wrap(styles, str(el)), encoding="utf-8")
            shot = work / png.name
            subprocess.run([CHROMIUM, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                            "--force-device-scale-factor=2", "--virtual-time-budget=1500", "--window-size=660,1400",
                            f"--screenshot={shot}", f"file://{src}"], check=True, capture_output=True, timeout=120)
            crop(shot)
            shot.replace(png)
            src.unlink()
            print(png.name, flush=True)
    for leftover in work.glob("*"):
        leftover.unlink()
    work.rmdir()


if __name__ == "__main__":
    main()
