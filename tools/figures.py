#!/usr/bin/env python3
"""Render the book's inline SVG figures (game boards, maps, charts) to PNG for the video.

Pulls every <svg> out of source/html/chapter-N.html with the page's own stylesheet,
and rasterises it with inkscape -> audio/figures/chNN_<element index>.png
"""
import re
import subprocess
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio" / "figures"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for ch in range(1, 33):
            html = (ROOT / "source" / "html" / f"chapter-{ch}.html").read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "lxml")
            css = "\n".join(s.get_text() for s in soup.find_all("style")).replace("<", "")
            kids = [c for c in soup.find("div", class_="document-page").children if isinstance(c, Tag)]
            for n, el in enumerate(kids):
                if el.name == "nav":
                    continue
                for svg in el.find_all("svg"):
                    svg["xmlns"] = "http://www.w3.org/2000/svg"
                    src = re.sub(r"(<svg[^>]*>)", lambda m: m.group(1) + f"<style>{css}</style>"
                                 '<rect width="100%" height="100%" fill="#1b1b2f"/>', str(svg), count=1)
                    svg_path = Path(tmp) / f"ch{ch:02d}_{n}.svg"
                    svg_path.write_text(src, encoding="utf-8")
                    png = OUT / f"ch{ch:02d}_{n}.png"
                    subprocess.run(["inkscape", "--export-type=png", "--export-width=1000",
                                    f"--export-filename={png}", str(svg_path)], check=True, capture_output=True)
                    print(png.name)


if __name__ == "__main__":
    main()
