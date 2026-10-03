#!/usr/bin/env python3
"""Step 6: a video track for the audiobook (YouTube).

A slow cellular automaton in ASCII - the book's game Minpentai is a Life-like
game of gliders and symbols - on the page's own dark-mode gradient, with the
chapter's mood in its colours and glyphs. Chapter cards in the page's heading
style, scene datelines, the book's own figures at the moment they are described,
device screens as the page's consoles, and word-synced captions coloured by
speaker exactly as the page colours speech.

  video.py --chapters 1-32 --workers 4     per-chapter videos (with audio) -> audio/video/chNN.mp4
  video.py --join                          Snowmoon.mp4 and youtube_chapters.txt
  video.py --chapters 1 --preview 40       a 40 s preview -> audio/video/ch01_preview.mp4

Needs numpy, Pillow, ffmpeg, the assembled chapters in audio/eleven with their
timelines in audio/work, and the word alignments audio/work/words_chNN.json.
"""
import argparse
import concurrent.futures
import json
import math
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from descriptions import DESCRIPTIONS  # noqa: E402

W, H, FPS = 1920, 1080, 24
CW, CH = 10, 20                        # cell size in pixels -> 192 x 54 cells
COLS, ROWS = W // CW, H // CH
AUDIO_DIR = ROOT / "audio" / "eleven"
OUT_DIR = ROOT / "audio" / "video"
FIGURES = ROOT / "audio" / "figures"
SCREENS = ROOT / "audio" / "screens"      # the page's device screens, messages, signs and quotes, rendered as shown
SCREEN_MAX_H = 760                        # taller screens stay text pages (the image would be too small to read)
MONO = "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf"       # automaton glyphs
SANS = str(Path.home() / ".local/share/fonts/Inter-VariableFont_opsz,wght.ttf")  # closest to the page's system sans
CONSOLE = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"   # the page's device screens use Courier
CONSOLE_BOLD = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"
SERIF_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"      # stand-in for the signs' cursive face

# straight from the page's stylesheet (dark mode)
PAGE_BG = (0x1A, 0x1A, 0x2E)              # .document-page
GRADIENT = ((0x0F, 0x0C, 0x29), (0x30, 0x2B, 0x63), (0x24, 0x24, 0x3E))  # html.dark --bg-gradient
TEXT = (0xE0, 0xE0, 0xE0)                 # body text
TITLE = (0xF0, 0xF0, 0xF0)                # h1
MUTED = (0xA4, 0x9D, 0xC4)
DATE_PLACE, DATE_DOT, DATE_DATE = (0xB3, 0xAE, 0xD0), (0x5F, 0x5A, 0x80), (0x8B, 0x83, 0xC3)
RULE = ((0x8B, 0x83, 0xC3), (0x6B, 0x5B, 0xA0))  # hr gradient / h1 underline
CONSOLE_BG, CONSOLE_BORDER = (0x05, 0x05, 0x10), (0x1A, 0x1A, 0x40)       # .device-view
CONSOLE_HEAD, CONSOLE_CELL = (0x88, 0xBB, 0xEE), (0xB8, 0xD8, 0xFF)
QUOTE_INK, QUOTE_BAR = (0xB0, 0xB0, 0xB0), (0x8B, 0x83, 0xC3)             # blockquote
SIGN_BG, SIGN_INK = (0x1B, 0x2B, 0x36), (0xE6, 0xF4, 0xFF)                # .dz-card
BG = np.array(PAGE_BG, dtype=np.float32)

# chapter moods, matching the music: A glassy, B pulse/tension, C icy
MOOD = {1: "A", 2: "B", 3: "A", 4: "B", 5: "C", 6: "A", 7: "B", 8: "A", 9: "C", 10: "A", 11: "A", 12: "B",
        13: "A", 14: "B", 15: "C", 16: "A", 17: "A", 18: "B", 19: "C", 20: "B", 21: "C", 22: "B", 23: "C",
        24: "C", 25: "A", 26: "B", 27: "A", 28: "A", 29: "B", 30: "B", 31: "C", 32: "C"}
PALETTE = {  # accent for living cells, highlight for new births, glyphs - all from the page's own colours
    "A": ((0x8B, 0x83, 0xC3), (0xE3, 0xDE, 0xF0), "∘•∘•○"),   # the purple of its rules and links
    "B": ((0x7F, 0xBC, 0xFF), (0xF0, 0xE6, 0x8C), "+▲■+×"),   # the console blue, with its highlight yellow
    "C": ((0xB8, 0xD8, 0xFF), (0xE6, 0xF4, 0xFF), "·•∘·◦"),   # the pale console blues
}
DOT_GLYPH, DOT_LEVEL = "·", 0.10

# Scene settings (script/scenes) -> hue of the page's speech-colour formula, base energy, glyphs.
# Energy drives the automaton's pace, density and brightness; 0 is still and dim, 1 is restless.
SCENE_MOOD = {
    "forest_path": (146, 0.25, "∘•∘·○"), "city_street": (253, 0.45, "∘•○•·"), "concert_crowd": (26, 0.85, "+×▲+■"),
    "classroom": (173, 0.30, "∘•·•∘"), "restaurant": (80, 0.35, "∘•○·•"), "stadium_crowd": (53, 0.80, "▲+■×+"),
    "home_interior": (66, 0.30, "∘•·∘•"), "aircraft_cabin": (240, 0.35, "·•∘·•"), "winter_wind": (213, 0.40, "·∘·•·"),
    "library": (280, 0.20, "·∘·•·"), "war_room": (346, 0.60, "+■×+▲"), "battlefield_distant": (13, 0.95, "×▲×■+"),
    "vehicle_interior": (226, 0.45, "∘•∘·•"), "rain": (240, 0.40, "·•·∘·"),
}
# delivery directions -> energy pulse while the line is spoken
DIRECTION_ENERGY = {"[shouting]": 0.7, "[angry]": 0.6, "[urgent]": 0.6, "[calling out]": 0.5, "[frightened]": 0.5,
                    "[crying]": 0.4, "[excited]": 0.4, "[surprised]": 0.3, "[nervous]": 0.3, "[announcing]": 0.3,
                    "[cheerful]": 0.2, "[laughs]": 0.2, "[whispers]": -0.35, "[softly]": -0.3, "[tender]": -0.3,
                    "[sad]": -0.25, "[dejected]": -0.25, "[solemn]": -0.2, "[tired]": -0.2, "[gently]": -0.2,
                    "[mumbling]": -0.15}


class MoodTrack:
    """Energy and colour as a function of chapter time."""

    def __init__(self, ch, words, default_mood):
        starts, ends = {}, {}
        for w in words:
            starts.setdefault(w["line"], w["t0"])
            ends[w["line"]] = w["t1"]
        acc_hue = {"A": 280, "B": 253, "C": 213}[default_mood]
        self.default = (acc_hue, {"A": 0.35, "B": 0.5, "C": 0.3}[default_mood], PALETTE[default_mood][2])
        self.scenes = []  # (t, hue, energy, glyphs)
        f = ROOT / "script" / "scenes" / f"ch{ch:02d}.json"
        if f.exists():
            for sc in json.loads(f.read_text()).get("scenes", []):
                t = starts.get(sc["start"])
                if t is None:
                    later = [v for k, v in starts.items() if int(k.split(":")[1]) >= int(sc["start"].split(":")[1])]
                    t = min(later) if later else None
                if t is None:
                    continue
                mood = SCENE_MOOD.get(sc.get("ambience") or "", self.default)
                self.scenes.append((t, *mood))
        self.scenes.sort()
        self.pulses = []  # (t0, t1, delta)
        f = ROOT / "script" / "directions" / f"ch{ch:02d}.json"
        if f.exists():
            for key, tag in json.loads(f.read_text()).items():
                line = key.split("/")[0]
                if line not in starts:
                    continue
                delta = sum(v for k, v in DIRECTION_ENERGY.items() if k in tag)
                if delta:
                    self.pulses.append((starts[line], ends[line], delta))

    def at(self, t):
        hue, energy, glyphs = self.default
        prev = None
        for i, sc in enumerate(self.scenes):
            if sc[0] <= t:
                prev = sc
                hue, energy, glyphs = sc[1], sc[2], sc[3]
                nxt = self.scenes[i + 1] if i + 1 < len(self.scenes) else None
            else:
                break
        # cross-fade the colour and energy over the first 4 s of a scene
        if prev is not None and t - prev[0] < 4.0:
            k = (t - prev[0]) / 4.0
            i = self.scenes.index(prev)
            before = self.scenes[i - 1] if i > 0 else (0, *self.default)
            hue = before[1] + (hue - before[1]) * k if abs(hue - before[1]) <= 180 else hue
            energy = before[2] + (energy - before[2]) * k
        for t0, t1, delta in self.pulses:
            if t0 - 1.0 <= t <= t1 + 1.5:
                ramp = min(1.0, (t - (t0 - 1.0)) / 1.0, ((t1 + 1.5) - t) / 1.5)
                energy += delta * max(0.0, ramp)
        return hue % 360, max(0.0, min(1.0, energy)), glyphs
CAP_FONT, LABEL_FONT = 50, 28
CAP_Y, CAP_H = H - 180, 180          # caption strip at the bottom
STAGE_H = H - CAP_H                  # the area above the captions


def oklch_to_rgb(L, C, h):
    """The page colours speech with oklch(0.7 0.15 hue); reproduce it exactly."""
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s3 = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s3
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s3
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s3
    out = []
    for v in (r, g, bb):
        v = max(0.0, min(1.0, v))
        v = 1.055 * v ** (1 / 2.4) - 0.055 if v > 0.0031308 else 12.92 * v
        out.append(int(round(max(0.0, min(1.0, v)) * 255)))
    return tuple(out)


def speaker_rgb(letter):
    """Hue from the speaker's letter, the page's own rule (A = 1/27 of the circle)."""
    if not letter:
        return TEXT
    hue = ((ord(letter.upper()) - ord("A") + 1) * 360 / 27) % 360
    return oklch_to_rgb(0.7, 0.15, hue)


# --- background ------------------------------------------------------------------------

class Atlas:
    """Glyph masks so a whole frame of characters is one numpy gather."""

    def __init__(self, glyphs):
        self.glyphs = list(dict.fromkeys(glyphs))
        self.index = {g: i for i, g in enumerate(self.glyphs)}
        fnt = ImageFont.truetype(MONO, 17)
        masks = []
        for g in self.glyphs:
            im = Image.new("L", (CW, CH), 0)
            d = ImageDraw.Draw(im)
            bbox = d.textbbox((0, 0), g, font=fnt)
            d.text(((CW - (bbox[2] - bbox[0])) // 2 - bbox[0], (CH - (bbox[3] - bbox[1])) // 2 - bbox[1]), g,
                   font=fnt, fill=255)
            masks.append(np.asarray(im, dtype=np.float32) / 255.0)
        self.masks = np.stack(masks)  # (G, CH, CW)


class Life:
    """Conway's Life on a torus, fed with gliders so it never goes quiet."""

    GLIDER = np.array([[0, 1, 0], [0, 0, 1], [1, 1, 1]], dtype=np.uint8)

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.cells = (self.rng.random((ROWS, COLS)) < 0.045).astype(np.uint8)
        self.age = np.zeros((ROWS, COLS), dtype=np.int32)

    def inject(self):
        g = self.GLIDER
        for _ in range(self.rng.integers(1, 3)):
            g = np.rot90(g)
        r, c = self.rng.integers(0, ROWS - 3), self.rng.integers(0, COLS - 3)
        self.cells[r:r + 3, c:c + 3] = g

    def step(self, energy=0.4):
        c = self.cells
        n = sum(np.roll(np.roll(c, dr, 0), dc, 1) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)
        born = (c == 0) & (n == 3)
        alive = (c == 1) & ((n == 2) | (n == 3))
        self.cells = (born | alive).astype(np.uint8)
        self.age = np.where(self.cells == 1, self.age + 1, 0)
        if self.rng.random() < 0.1 + 0.8 * energy:
            self.inject()
        if energy > 0.7 and self.rng.random() < energy - 0.5:
            self.inject()
        floor = 0.012 + 0.04 * energy
        if self.cells.mean() < floor:
            self.cells |= (self.rng.random((ROWS, COLS)) < 0.006 + 0.02 * energy).astype(np.uint8)


def gradient_field():
    """The page's 135-degree background gradient, dimmed to sit behind the glyphs."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    t = ((x / W) + (y / H)) / 2.0
    c0, c1, c2 = (np.array(c, dtype=np.float32) for c in GRADIENT)
    first = c0[None, None] * (1 - t * 2)[..., None] + c1[None, None] * (t * 2)[..., None]
    second = c1[None, None] * (2 - t * 2)[..., None] + c2[None, None] * (t * 2 - 1)[..., None]
    field = np.where((t < 0.5)[..., None], first, second)
    return 0.55 * field + 0.45 * BG


GRADIENT_FIELD = gradient_field()


def background(life, atlas, mood, phase, hue=None, energy=0.4, glyphs=None):
    """One frame of the automaton as uint8 RGB; colour and brightness follow the scene's energy."""
    if hue is None:
        accent = np.array(PALETTE[mood][0], dtype=np.float32)
        bright = np.array(PALETTE[mood][1], dtype=np.float32)
    else:
        accent = np.array(oklch_to_rgb(0.62 + 0.1 * energy, 0.10 + 0.07 * energy, hue), dtype=np.float32)
        bright = np.array(oklch_to_rgb(0.88, 0.06 + 0.06 * energy, hue), dtype=np.float32)
    glyphs = glyphs or PALETTE[mood][2]
    idx = np.full((ROWS, COLS), atlas.index[DOT_GLYPH], dtype=np.int32)
    live = life.cells == 1
    # the glyph of a living cell follows its position, so structures look like the game's symbols
    choice = (np.arange(ROWS)[:, None] // 9 + np.arange(COLS)[None, :] // 16 + phase) % len(glyphs)
    lut = np.array([atlas.index[g] for g in glyphs])
    idx[live] = lut[choice[live]]
    level = np.full((ROWS, COLS), DOT_LEVEL, dtype=np.float32)
    young = np.clip(1.0 - life.age / 14.0, 0, 1)
    level[live] = (0.38 + 0.4 * energy) + 0.3 * young[live]
    color = np.empty((ROWS, COLS, 3), dtype=np.float32)
    color[:] = accent * 0.9
    color[live] = accent * (1 - young[live, None]) + bright * young[live, None]
    mask = atlas.masks[idx].transpose(0, 2, 1, 3).reshape(H, W)  # (H, W)
    lv = np.repeat(np.repeat(level, CH, 0), CW, 1)
    col = np.repeat(np.repeat(color, CH, 0), CW, 1)
    frame = GRADIENT_FIELD + mask[..., None] * lv[..., None] * col
    return np.clip(frame, 0, 255).astype(np.uint8)


# --- overlays ----------------------------------------------------------------------------

def font(size, bold=False, sans=True, serif=False):
    if serif:
        return ImageFont.truetype(SERIF_ITALIC, size)
    if sans:
        f = ImageFont.truetype(SANS, size)
        try:
            f.set_variation_by_axes([size if size < 32 else 28, 600 if bold else 400])
        except Exception:
            pass
        return f
    return ImageFont.truetype(CONSOLE_BOLD if bold else CONSOLE, size)


def gradient_line(d, x0, x1, y, thick=3):
    for x in range(x0, x1):
        k = (x - x0) / max(1, x1 - x0)
        c = tuple(int(RULE[0][j] * (1 - k) + RULE[1][j] * k) for j in range(3))
        d.line((x, y, x, y + thick), fill=c + (255,))


def card(title, dateline=None, subtitle=None, small=None):
    """A centred card: h1 with the page's purple underline, a dateline in the page's style, or plain lines."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f1, f_place, f_date, f3 = font(96, True), font(28, True), font(24, True), font(30)
    y = STAGE_H // 2 - 70
    if title:
        w = d.textlength(title, font=f1)
        d.text(((W - w) / 2, y), title, font=f1, fill=TITLE + (255,))
        span = max(w, 420)
        gradient_line(d, int((W - span) / 2), int((W + span) / 2), y + 128)
        y_sub = y + 150
    else:
        y_sub = y + 40
    if dateline:
        place, _, date = dateline.partition("  ·  ")
        if not date:
            place, date = "", place
        date_txt = " ".join(date.upper())  # letter-spaced capitals, as on the page
        parts = [(place, f_place, DATE_PLACE)] + ([("·", f_place, DATE_DOT)] if place else []) + [(date_txt, f_date, DATE_DATE)]
        parts = [p for p in parts if p[0]]
        widths = [d.textlength(t, font=f) for t, f, _ in parts]
        x = (W - sum(widths) - 28 * (len(parts) - 1)) / 2
        for (t, f, c), ww in zip(parts, widths):
            d.text((x, y_sub + (2 if f is f_date else 0)), t, font=f, fill=c + (255,))
            x += ww + 28
    if subtitle:
        w = d.textlength(subtitle, font=f3)
        d.text(((W - w) / 2, y_sub), subtitle, font=f3, fill=TEXT + (255,))
    if small:
        w = d.textlength(small, font=f3)
        d.text(((W - w) / 2, y_sub + 50), small, font=f3, fill=MUTED + (255,))
    return im


def rule_card():
    """Scene break: the page's gradient rule."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gradient_line(ImageDraw.Draw(im), W // 2 - 220, W // 2 + 220, STAGE_H // 2)
    return im


def panel_pages(lines, kind):
    """Wrap a screen's lines and split them into pages that fit above the captions."""
    console = kind in ("device", "message", "override")
    width_chars = 74 if console else 60 if kind == "sign" else 70
    lh = 32 if console else 40
    max_lines = (STAGE_H - 120 - 68) // lh
    wrapped, prev_spk = [], None
    for spk, txt in lines:
        label = spk if (console and spk not in ("N", "Narrator") and spk != prev_spk) else None
        first_width = width_chars - (len(label) + 2 if label else 0)
        parts = textwrap.wrap(txt, first_width) or [""]
        rest = textwrap.wrap(" ".join(parts[1:]), width_chars) if len(parts) > 1 else []
        wrapped.append((label, parts[0]))
        wrapped += [(None, ln) for ln in rest]
        if console and spk not in ("N", "Narrator"):
            prev_spk = spk
    return [wrapped[i:i + max_lines] for i in range(0, len(wrapped), max_lines)]


def panel_text(page, kind):
    """One page of a device screen (console), a quote (purple bar) or a sign (slate card), as on the page."""
    console = kind in ("device", "message", "override")
    if console:
        f, fb = font(23, sans=False), font(23, True, sans=False)
        ink, head, fill, border, width_chars, lh = CONSOLE_CELL, CONSOLE_HEAD, CONSOLE_BG + (235,), CONSOLE_BORDER, 74, 32
    elif kind == "sign":
        f = fb = font(30, serif=True)
        ink, head, fill, border, width_chars, lh = SIGN_INK, SIGN_INK, SIGN_BG + (235,), SIGN_BG, 60, 40
    else:
        f = fb = font(26, serif=True)
        ink, head, fill, border, width_chars, lh = QUOTE_INK, QUOTE_INK, (255, 255, 255, 14), None, 70, 40
    pad = 34
    pw = min(W - 240, int(width_chars * (14 if console else 15)) + 2 * pad + 60)
    ph = len(page) * lh + 2 * pad
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0 = (W - pw) // 2, max(60, (STAGE_H - ph) // 2)
    if console or kind == "sign":
        d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), 15, fill=fill, outline=border + (255,), width=2)
    else:
        d.rectangle((x0, y0, x0 + pw, y0 + ph), fill=(PAGE_BG[0] + 10, PAGE_BG[1] + 10, PAGE_BG[2] + 14, 225))
        d.rectangle((x0, y0, x0 + 5, y0 + ph), fill=QUOTE_BAR + (255,))
    y = y0 + pad
    for label, ln in page:
        x = x0 + pad + (0 if console or kind == "sign" else 8)
        if label:
            d.text((x, y), label + ":", font=fb, fill=head + (255,))
            x += d.textlength(label + ": ", font=fb)
        if console and (ln.endswith(":") or ln.startswith("Message ")):
            d.text((x, y), ln, font=fb, fill=head + (255,))
        else:
            d.text((x, y), ln, font=f, fill=ink + (255,))
        y += lh
    return im


def panel_figure(png, framed=True):
    """The book's own figure in a console frame, or one of its screens as the page renders it."""
    fig = Image.open(png).convert("RGBA")
    scale = min(1000 / fig.width, 560 / fig.height, 1.0 if framed else 0.82)
    fig = fig.resize((int(fig.width * scale), int(fig.height * scale)), Image.LANCZOS)
    if framed:
        fig = fig.filter(ImageFilter.GaussianBlur(0.6))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0 = (W - fig.width) // 2, (STAGE_H - fig.height) // 2
    if framed:
        d.rounded_rectangle((x0 - 24, y0 - 24, x0 + fig.width + 24, y0 + fig.height + 24), 15,
                            fill=CONSOLE_BG + (235,), outline=CONSOLE_BORDER + (255,), width=2)
    else:
        d.rounded_rectangle((x0 - 6, y0 - 6, x0 + fig.width + 6, y0 + fig.height + 6), 18, fill=PAGE_BG + (230,))
    im.alpha_composite(fig, (x0, y0))
    return im


# --- captions ----------------------------------------------------------------------------

def caption_units(words, max_chars=64):
    """Group aligned words into caption lines: same speaker, sentence-aware, at most max_chars."""
    units, cur = [], []

    def flush():
        if cur:
            units.append(cur[:])
            cur.clear()

    for w in words:
        if cur and (w["speaker"] != cur[-1]["speaker"] or w["t0"] - cur[-1]["t1"] > 2.5):
            flush()
        cand = len(" ".join(x["word"] for x in cur + [w]))
        ends = w["word"][-1] in ".!?"
        if cur and cand > max_chars and not (ends and cand <= max_chars + 8):
            flush()
        cur.append(w)
        if ends and len(" ".join(x["word"] for x in cur)) > 36:
            flush()
    flush()
    out = []
    for i, u in enumerate(units):
        t0 = u[0]["t0"] - 0.25
        t1 = u[-1]["t1"] + 0.6
        if out:
            t0 = max(t0, out[-1]["t1"])
        if i + 1 < len(units):
            t1 = min(t1, units[i + 1][0]["t0"] - 0.25)
        out.append({"t0": t0, "t1": max(t1, t0 + 0.4), "words": u, "speaker": u[0]["speaker"],
                    "letter": u[0].get("letter")})
    return out


class Captions:
    def __init__(self, units):
        self.units = units
        self.font = font(CAP_FONT)
        self.label = font(LABEL_FONT, True)
        self.cache = {}
        self.i = 0

    def layout(self, i):
        if i in self.cache:
            return self.cache[i]
        unit = self.units[i]
        strip = Image.new("RGBA", (W, CAP_H), (0, 0, 0, 0))
        d = ImageDraw.Draw(strip)
        rgb = speaker_rgb(unit["letter"]) if unit["speaker"] != "Narrator" else TEXT
        dim = tuple(int(c * 0.62) for c in rgb)
        text = " ".join(w["word"] for w in unit["words"])
        total = d.textlength(text, font=self.font)
        x = (W - total) / 2
        y = 74
        d.text((x + 2, y + 2), text, font=self.font, fill=(0, 0, 0, 160))  # soft shadow for legibility
        positions = []
        for w in unit["words"]:
            ww = d.textlength(w["word"], font=self.font)
            d.text((x, y), w["word"], font=self.font, fill=dim + (255,))
            positions.append((x, ww))
            x += ww + d.textlength(" ", font=self.font)
        if unit["speaker"] not in ("Narrator", "mix"):
            lw = d.textlength(unit["speaker"], font=self.label)
            d.text(((W - lw) / 2 + 1, 30 + 1), unit["speaker"], font=self.label, fill=(0, 0, 0, 150))
            d.text(((W - lw) / 2, 30), unit["speaker"], font=self.label, fill=rgb + (255,))
        if len(self.cache) > 6:
            self.cache = {k: v for k, v in self.cache.items() if k >= i - 1}
        self.cache[i] = (strip, positions, rgb)
        return self.cache[i]

    def frame(self, t):
        """RGBA strip for time t, or None."""
        while self.i < len(self.units) and self.units[self.i]["t1"] < t:
            self.i += 1
        if self.i >= len(self.units):
            return None
        unit = self.units[self.i]
        if t < unit["t0"]:
            return None
        strip, positions, rgb = self.layout(self.i)
        a = min(1.0, (t - unit["t0"]) / 0.3, (unit["t1"] - t) / 0.3)
        out = strip.copy()
        d = ImageDraw.Draw(out)
        for w, (x, ww) in zip(unit["words"], positions):
            if w["t0"] - 0.05 <= t <= w["t1"] + 0.12:
                d.text((x, 74), w["word"], font=self.font, fill=rgb + (255,))
                break
        if a < 1.0:
            out.putalpha(out.getchannel("A").point(lambda v, a=a: int(v * max(a, 0))))
        return out


# --- timing ------------------------------------------------------------------------------

def dateline_text(spoken):
    """'Meldan, Veridia. Snowmoon 3, thirty-seven twenty-four.' -> 'Meldan, Veridia  ·  Snowmoon 3, 3724'."""
    t = spoken.rstrip(".").replace("thirty-seven twenty-four", "3724").replace("thirty-seven twenty-five", "3725")
    return "  ·  ".join(part.strip() for part in t.split(". ") if part.strip())


def say_time(s):
    s = int(s)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def events(ch, words):
    """What to show when: (start, end, kind, payload). Line times come from the aligned words."""
    timeline = json.loads((ROOT / "audio" / "work" / f"timeline_ch{ch:02d}.json").read_text())
    final = json.loads((ROOT / "script" / "final" / f"ch{ch:02d}.json").read_text())
    raw = {it["id"]: it for it in json.loads((ROOT / "script" / "raw" / f"ch{ch:02d}.json").read_text())}
    by_id = {}
    for u in final:
        if "id" in u:
            by_id.setdefault(u["id"], []).append(u)
    starts, ends = {}, {}
    for w in words:
        starts.setdefault(w["line"], w["t0"])
        ends[w["line"]] = w["t1"]
    pauses = [t for k, t in timeline if k == "pause"]
    ev = []
    first_chapter_word = next((w["t0"] for w in words if w["word"].startswith("Chapter")), 3.5)
    dateline = next((u for u in final if "id" in u and raw.get(u["id"], {}).get("kind") == "dateline"), None)
    sub = dateline_text(dateline["text"]) if dateline else ""
    if ch == 1:
        ev.append((0.3, first_chapter_word - 0.4, "card", ("Snowmoon", None, "by Vitalik Buterin", "an audiobook")))
        ev.append((first_chapter_word - 0.3, first_chapter_word + 8.5, "card", (f"Chapter {ch}", sub, None, None)))
    else:
        ev.append((max(0.3, first_chapter_word - 2.5), first_chapter_word + 8.0, "card", (f"Chapter {ch}", sub, None, None)))
    for t in pauses:
        ev.append((t + 0.1, t + 2.4, "rule", None))
    for iid, it in raw.items():
        if iid not in starts:
            continue
        t = starts[iid]
        if it["kind"] == "dateline" and not it.get("opening"):
            ev.append((t - 0.5, t + 7.0, "card", ("", dateline_text(it["runs"][0]["text"]), None, None)))
        elif iid in DESCRIPTIONS and (FIGURES / f"ch{ch:02d}_{iid.split(':')[1]}.png").exists():
            ev.append((t - 1.0, max(t + 22.0, ends.get(iid, t) + 2.0), "figure",
                       str(FIGURES / f"ch{ch:02d}_{iid.split(':')[1]}.png")))
        elif it["kind"] in ("device", "message", "sign", "quote", "override") and "svg" not in it:
            t_end = max(ends.get(iid, t) + 1.5, t + 4.0)
            shot = SCREENS / f"ch{ch:02d}_{iid.split(':')[1]}.png"
            if shot.exists() and Image.open(shot).height <= SCREEN_MAX_H:
                ev.append((t - 0.5, t_end, "screen", str(shot)))   # the page's own rendering
                continue
            lines = [(u["speaker"], u["text"]) for u in by_id.get(iid, [])]
            pages = panel_pages(lines, it["kind"])
            share = (t_end - (t - 0.5)) / len(pages)
            for k, page in enumerate(pages):
                ev.append((t - 0.5 + k * share, t - 0.5 + (k + 1) * share, "panel", (page, it["kind"])))
    if ch == 32:
        end = next((starts[u["id"]] for u in final if u.get("cue") == "ending" and u["id"] in starts), None)
        if end:
            ev.append((end + 1.0, end + 14.0, "card", ("The end", None, "Snowmoon  ·  Vitalik Buterin",
                                                     "GPL v3  ·  github.com/guy-do-or-die/snowmoon-audiobook")))
    ev.sort(key=lambda e: e[0])
    return ev


def alpha_at(t, start, end, fade):
    if t < start or t > end:
        return 0.0
    return float(min(1.0, (t - start) / fade, (end - t) / fade, 1.0))


FADE = {"card": 1.2, "figure": 1.2, "screen": 1.0, "panel": 1.0, "rule": 0.5}


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


# --- rendering ---------------------------------------------------------------------------

def inputs_mtime(ch):
    files = [ROOT / "audio" / "work" / f"words_ch{ch:02d}.json", ROOT / "audio" / "work" / f"timeline_ch{ch:02d}.json",
             ROOT / "script" / "final" / f"ch{ch:02d}.json", AUDIO_DIR / f"Snowmoon - Chapter {ch:02d}.m4a",
             Path(__file__), *SCREENS.glob(f"ch{ch:02d}_*.png")]
    return max(f.stat().st_mtime for f in files if f.exists())


def render_chapter(ch, preview=None, start=0.0):
    audio = AUDIO_DIR / f"Snowmoon - Chapter {ch:02d}.m4a"
    words_file = ROOT / "audio" / "work" / f"words_ch{ch:02d}.json"
    if not words_file.exists():
        raise RuntimeError(f"chapter {ch}: no word alignment (run align.py first)")
    secs = duration(audio)
    if preview:
        secs = min(secs, start + preview)
    out = OUT_DIR / (f"ch{ch:02d}_preview_{int(start)}.mp4" if preview else f"ch{ch:02d}.mp4")
    if out.exists() and not preview and abs(duration(out) - secs) < 0.5 and out.stat().st_mtime > inputs_mtime(ch):
        return out
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mood = MOOD[ch]
    atlas = Atlas(DOT_GLYPH + "".join(v[2] for v in PALETTE.values()))
    life = Life(seed=ch)
    words = json.loads(words_file.read_text())
    ev = events(ch, words)
    caps = Captions(caption_units(words))
    track = MoodTrack(ch, words, mood)
    rendered = {}
    tmp = out.with_suffix(".tmp.mp4")
    n_frames = math.ceil(secs * FPS)
    first_frame = int(round(start * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-ss", f"{first_frame / FPS:.3f}", "-i", str(audio), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-threads", "3",
           "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(tmp)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    base = None
    if first_frame:
        for _ in range(120):   # let the automaton settle as it would have by then
            life.step(track.at(start)[1])
        caps.frame(start)
    try:
        for n in range(first_frame, n_frames):
            t = n / FPS
            hue, energy, glyphs = track.at(t)
            every = max(1, int(round(4.5 - 3.5 * energy)))   # calm: a step every 4 frames; restless: every frame
            if n % every == 0:
                life.step(energy)
            if n % 2 == 0 or base is None:
                base = background(life, atlas, mood, n // 240, hue, energy, glyphs)
            active = [(e, alpha_at(t, e[0], e[1], FADE[e[2]])) for e in ev if e[0] <= t <= e[1]]
            strip = caps.frame(t)
            if active:
                im = Image.fromarray(base, "RGB").convert("RGBA")
                for e, a in active:
                    if a <= 0:
                        continue
                    key = (e[2], e[0])
                    if key not in rendered:
                        if e[2] == "card":
                            rendered[key] = card(*e[3])
                        elif e[2] == "figure":
                            rendered[key] = panel_figure(e[3])
                        elif e[2] == "screen":
                            rendered[key] = panel_figure(e[3], framed=False)
                        elif e[2] == "rule":
                            rendered[key] = rule_card()
                        else:
                            rendered[key] = panel_text(*e[3])
                    layer = rendered[key]
                    if a < 1.0:
                        layer = layer.copy()
                        layer.putalpha(layer.getchannel("A").point(lambda v, a=a: int(v * a)))
                    im.alpha_composite(layer)
                if strip is not None:
                    im.alpha_composite(strip, (0, CAP_Y))
                ff.stdin.write(im.convert("RGB").tobytes())
            elif strip is not None:
                im = Image.fromarray(base, "RGB")
                im.paste(strip.convert("RGB"), (0, CAP_Y), strip.getchannel("A"))
                ff.stdin.write(im.tobytes())
            else:
                ff.stdin.write(base.tobytes())
            if len(rendered) > 12:
                rendered = {k: v for k, v in rendered.items() if any(k == (e[2], e[0]) for e, _ in active)}
    except BrokenPipeError:
        pass
    finally:
        try:
            ff.stdin.close()
        except Exception:
            pass
        rc = ff.wait()
    if rc != 0:
        err = ff.stderr.read().decode(errors="replace")[-800:]
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed for chapter {ch} (exit {rc}): {err}")
    if abs(duration(tmp) - (secs - first_frame / FPS)) > 0.5:
        raise RuntimeError(f"chapter {ch}: rendered {duration(tmp):.1f}s, expected {secs - first_frame / FPS:.1f}s")
    tmp.rename(out)
    return out


def join():
    vids = [OUT_DIR / f"ch{ch:02d}.mp4" for ch in range(1, 33)]
    auds = [AUDIO_DIR / f"Snowmoon - Chapter {ch:02d}.m4a" for ch in range(1, 33)]
    chapters, start = [], 0.0
    for ch, (v, a) in enumerate(zip(vids, auds), 1):
        if not v.exists():
            raise RuntimeError(f"chapter {ch} video missing")
        dv, da = duration(v), duration(a)
        if abs(dv - da) > 0.5:
            raise RuntimeError(f"chapter {ch}: video {dv:.1f}s vs audio {da:.1f}s")
        chapters.append(f"{say_time(start)} Chapter {ch}")
        start += dv
    (OUT_DIR / "videos.txt").write_text("".join(f"file '{p}'\n" for p in vids))
    (ROOT / "audio" / "youtube_chapters.txt").write_text("\n".join(chapters) + "\n")
    final = ROOT / "audio" / "Snowmoon.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT_DIR / "videos.txt"),
                    "-c", "copy", "-movflags", "+faststart", str(final)], check=True)
    print(final, f"{duration(final) / 3600:.2f} h", f"{final.stat().st_size / 1e9:.2f} GB")


def chapters_arg(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chapters", default="1-32")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--join", action="store_true")
    ap.add_argument("--preview", type=float, help="render only N seconds of the first chapter given")
    ap.add_argument("--start", type=float, default=0.0, help="with --preview: start at this second")
    args = ap.parse_args()
    if args.join:
        join()
        return
    if args.preview:
        print(render_chapter(chapters_arg(args.chapters)[0], preview=args.preview, start=args.start))
        return
    with concurrent.futures.ProcessPoolExecutor(args.workers) as pool:
        for path in pool.map(render_chapter, chapters_arg(args.chapters)):
            print(path, flush=True)


if __name__ == "__main__":
    main()
