#!/usr/bin/env python3
"""Render the book's inline SVG figures (game boards, maps, charts) to PNG for the video.

Pulls every <svg> out of source/html/chapter-N.html with the page's own stylesheet,
and rasterises it with inkscape -> audio/figures/chNN_<element index>.png. An animated
figure (SMIL <animate>, which inkscape would show at its empty first instant) is instead
photographed in headless Chromium a few seconds into the animation.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from bs4 import BeautifulSoup, Tag
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio" / "figures"
CHROMIUM = "chromium"
PAGE_BG = (0x1A, 0x1A, 0x2E)
ANIMATION_AT_MS = 7000   # the moment of an animation to show


def chromium_frame(svg_markup, css, png):
    work = Path.home() / "snowmoon-screens-tmp"   # snap-confined Chromium can only use visible folders under $HOME
    work.mkdir(parents=True, exist_ok=True)
    src = work / (png.stem + ".html")
    src.write_text(f'<!doctype html><html class="dark"><head><meta charset="utf-8"><style>{css}'
                   f"html,body{{background:#1a1a2e;margin:0;padding:24px}}</style></head><body>{svg_markup}</body></html>",
                   encoding="utf-8")
    shot = work / png.name
    subprocess.run([CHROMIUM, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                    "--force-device-scale-factor=3", f"--virtual-time-budget={ANIMATION_AT_MS}", "--window-size=700,700",
                    f"--screenshot={shot}", f"file://{src}"], check=True, capture_output=True, timeout=120)
    im = Image.open(shot).convert("RGB")
    diff = np.abs(np.asarray(im).astype(int) - np.array(PAGE_BG)).sum(axis=2) > 18
    ys, xs = np.where(diff)
    im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)).save(png)
    src.unlink()
    shot.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    chapters = [int(a) for a in sys.argv[1:]] or range(1, 33)
    with tempfile.TemporaryDirectory() as tmp:
        for ch in chapters:
            html = (ROOT / "source" / "html" / f"chapter-{ch}.html").read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html5lib")   # keeps SVG attribute case (viewBox, patternUnits); lxml would lowercase it
            css = "\n".join(s.get_text() for s in soup.find_all("style")).replace("<", "")
            kids = [c for c in soup.find("div", class_="document-page").children if isinstance(c, Tag)]
            for n, el in enumerate(kids):
                if el.name == "nav":
                    continue
                for svg in el.find_all("svg"):
                    png = OUT / f"ch{ch:02d}_{n}.png"
                    if svg.find("animate"):
                        chromium_frame(str(svg), css, png)
                        print(png.name, "(animation frame)")
                        continue
                    svg["xmlns"] = "http://www.w3.org/2000/svg"
                    src = re.sub(r"(<svg[^>]*>)", lambda m: m.group(1) + f"<style>{css}</style>"
                                 '<rect width="100%" height="100%" fill="#1b1b2f"/>', str(svg), count=1)
                    svg_path = Path(tmp) / f"ch{ch:02d}_{n}.svg"
                    svg_path.write_text(src, encoding="utf-8")
                    subprocess.run(["inkscape", "--export-type=png", "--export-width=1000",
                                    f"--export-filename={png}", str(svg_path)], check=True, capture_output=True)
                    print(png.name)


if __name__ == "__main__":
    main()
