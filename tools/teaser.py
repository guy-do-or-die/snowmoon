#!/usr/bin/env python3
"""A teaser cut from the video edition.

The beats are listed in script/teaser_plan.json: [{"chapter", "first_id", "last_id", "bed"}, ...],
each a span of consecutive lines, and "bed" one of the three chapter textures (A granular, B sub-pulse,
C icy) to play underneath. Beats are word-timed cuts from the chapter videos, separated by a short dip to
black, with the music bed continuous over each run of beats that share a texture. A title card opens, a
slate closes; no chapter numbers anywhere (the beats come from many chapters, out of order).
Nothing is cut mid-word: a span ends strictly after its last word and before any card or scene rule,
and the fades never reach into speech. Output: audio/samples/Snowmoon - teaser.mp4 (1920x1080).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import video  # noqa: E402

from PIL import Image  # noqa: E402

OUT = ROOT / "audio" / "samples" / "Snowmoon - teaser.mp4"
WORK = ROOT / "audio" / "samples" / "teaser-work"
PLAN = ROOT / "script" / "teaser_plan.json"
GAP = 0.45            # dip to black between beats, seconds
LAST_GAP = 1.5        # hold after the last word, before the slate
TITLE_S, SLATE_S = 3.2, 7.0
V_FADE, A_FADE = 0.45, 0.35
BED_LEVEL = {"A": 0.16, "B": 0.07, "C": 0.16}
THEME = {"A": "theme_A_granular", "B": "theme_B_subpulse", "C": "theme_C_icy"}
SIZE = f"{video.W}x{video.H}"


def words(ch):
    return json.loads((ROOT / "audio" / "work" / f"words_ch{ch:02d}.json").read_text())


def span(ch, first, last):
    """Start/end in chapter time, padded into the silence around the lines: never into a word, never
    into a card or a scene rule. Returns (start, end, silence left after the last word)."""
    ws = words(ch)
    a = next(w["t0"] for w in ws if w["line"] == first)
    b = max(w["t1"] for w in ws if w["line"] == last)
    nxt = min((w["t0"] for w in ws if w["t0"] >= b + 0.01), default=b + 3)
    prv = max((w["t1"] for w in ws if w["t1"] <= a - 0.01), default=-1)
    a2 = max(0.0, a - 0.45, prv + 0.08)
    b2 = min(b + 1.1, nxt - 0.12)
    for e0, e1, kind, _ in video.events(ch, ws):
        if kind in ("card", "rule"):
            if b < e0 < b2 + 0.05:
                b2 = max(b + 0.15, e0 - 0.05)
            if a2 - 0.05 < e1 < a:
                a2 = min(a - 0.05, e1 + 0.05)
    stray = [w["word"] for w in ws if (a2 < w["t0"] < b2 < w["t1"]) or (w["t0"] < a2 < w["t1"])]
    assert not stray and b2 > b, (ch, first, last, stray, b, b2)
    return a2, b2, b2 - b


def source_for(ch, a, b):
    """The chapter video if it is rendered, otherwise a preview of just this stretch (cached)."""
    full = video.OUT_DIR / f"ch{ch:02d}.mp4"
    if full.exists():
        return full, 0.0
    start = max(0.0, a - 1.0)
    first_frame = int(round(start * video.FPS))
    length = (b - start) + 1.0
    prev = video.OUT_DIR / f"ch{ch:02d}_preview_{int(start)}.mp4"
    if not (prev.exists() and prev.stat().st_mtime > video.inputs_mtime(ch) and abs(video.duration(prev) - length) < 0.6):
        prev = video.render_chapter(ch, preview=length, start=start)
    return prev, first_frame / video.FPS


def still(name, seconds, fade_in, fade_out, *card_args):
    """A card over the automaton, as a short silent clip."""
    atlas = video.Atlas(video.DOT_GLYPH + "".join(v[2] for v in video.PALETTE.values()) +
                        "".join(m[2] for m in video.SCENE_MOOD.values()))
    life = video.Life(seed=32)
    for _ in range(70):
        life.step(0.3)
    im = Image.fromarray(video.background(life, atlas, "C", 2, 213, 0.3, "·•∘·◦"), "RGB").convert("RGBA")
    im.alpha_composite(video.card(*card_args))
    png = WORK / f"{name}.png"
    im.convert("RGB").save(png)
    mp4 = WORK / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", f"{seconds}", "-i", str(png),
                    "-filter_complex", f"[0:v]fps={video.FPS},format=yuv420p,fade=t=in:st=0:d={fade_in},"
                    f"fade=t=out:st={seconds - fade_out:.2f}:d={fade_out}[v]",
                    "-map", "[v]", "-c:v", "libx264", "-crf", "23", str(mp4)], check=True)
    return mp4


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    plan = json.loads(PLAN.read_text())
    pieces = []  # (src, local start, duration, tail silence, bed)
    for beat in plan:
        ch = beat["chapter"]
        a, b, tail = span(ch, beat["first_id"], beat["last_id"])
        src, off = source_for(ch, a, b)
        pieces.append((src, a - off, b - a, tail, beat["bed"]))
        print(f"ch{ch} {beat['first_id']}-{beat['last_id']}: {a:.2f}-{b:.2f} ({b - a:.1f}s, {tail:.2f}s tail) from {Path(src).name}")
    title = still("title", TITLE_S, 0.7, 0.7, "Snowmoon", None, "by Vitalik Buterin", "a full-cast audiobook")
    slate = still("slate", SLATE_S, 0.8, 1.0, "Snowmoon", None, "by Vitalik Buterin", "a full-cast audiobook  ·  92 voiced characters  ·  10.5 hours")
    # --- picture and speech: title, beats with fades and black gaps between, slate ---------
    inputs, filt, vparts, aparts = [], [], [], []
    inputs += ["-i", str(title)]
    filt.append("[0:v]setpts=PTS-STARTPTS[vtitle]")
    filt.append(f"anullsrc=r=44100:cl=stereo:d={TITLE_S + GAP}[stitle]")
    filt.append(f"color=c=black:s={SIZE}:r={video.FPS}:d={GAP}[gtitle]")
    vparts += ["[vtitle]", "[gtitle]"]; aparts += ["[stitle]"]
    t = TITLE_S + GAP
    runs = []  # (bed, start, end) over consecutive beats sharing a texture; the first run starts under the title
    for i, (src, local, d, tail, bed) in enumerate(pieces):
        k = i + 1
        inputs += ["-ss", f"{local:.3f}", "-t", f"{d:.3f}", "-i", str(src)]
        a_out = min(A_FADE, max(0.15, tail - 0.1))      # the audio fade stays inside the silence
        filt.append(f"[{k}:v]scale={SIZE},fps={video.FPS},format=yuv420p,fade=t=in:st=0:d={V_FADE},"
                    f"fade=t=out:st={d - V_FADE:.3f}:d={V_FADE},setpts=PTS-STARTPTS[v{k}]")
        filt.append(f"[{k}:a]aresample=44100,afade=t=in:st=0:d=0.2,afade=t=out:st={d - a_out:.3f}:d={a_out},"
                    f"asetpts=PTS-STARTPTS[a{k}]")
        vparts.append(f"[v{k}]"); aparts.append(f"[a{k}]")
        gap = GAP if i < len(pieces) - 1 else LAST_GAP
        if runs and runs[-1][0] == bed:
            runs[-1][2] = t + d + gap
        else:
            runs.append([bed, 0.0 if not runs else t, t + d + gap])
        t += d
        filt.append(f"color=c=black:s={SIZE}:r={video.FPS}:d={gap}[g{k}]")
        filt.append(f"anullsrc=r=44100:cl=stereo:d={gap}[s{k}]")
        vparts.append(f"[g{k}]"); aparts.append(f"[s{k}]")
        t += gap
    n = len(pieces) + 1
    inputs += ["-i", str(slate)]
    filt.append(f"[{n}:v]setpts=PTS-STARTPTS[vslate]")
    filt.append(f"anullsrc=r=44100:cl=stereo:d={SLATE_S}[sslate]")
    vparts.append("[vslate]"); aparts.append("[sslate]")
    total = t + SLATE_S
    runs[-1][2] = total                                   # the last texture carries through the slate
    filt.append("".join(vparts) + f"concat=n={len(vparts)}:v=1:a=0[vcat]")
    filt.append("".join(aparts) + f"concat=n={len(aparts)}:v=0:a=1[acat]")
    # --- music bed: one texture per run, faded, mixed under the speech ----------------------
    acur = "acat"
    for j, (bed, lo, hi) in enumerate(runs):
        idx = n + 1 + j
        length = hi - lo
        fade_out = 3.5 if j == len(runs) - 1 else 2.0
        inputs += ["-stream_loop", "-1", "-t", f"{length + 1:.3f}", "-i", str(ROOT / "audio" / "sfx" / f"{THEME[bed]}.flac")]
        filt.append(f"[{idx}:a]aresample=44100,atrim=0:{length:.3f},volume={BED_LEVEL[bed]},"
                    f"afade=t=in:st=0:d=1.5,afade=t=out:st={length - fade_out:.3f}:d={fade_out},"
                    f"adelay={int(lo * 1000)}|{int(lo * 1000)}[bed{j}]")
        filt.append(f"[{acur}][bed{j}]amix=inputs=2:duration=first:normalize=0[am{j}]")
        acur = f"am{j}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
                    "-map", "[vcat]", "-map", f"[{acur}]", "-t", f"{total:.3f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-profile:v", "high", "-level", "4.1", "-r", str(video.FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                    "-movflags", "+faststart", str(OUT)], check=True)
    print(f"{OUT.name}: {video.duration(OUT):.1f}s, {os.path.getsize(OUT) / 1e6:.1f} MB")
    for bed, lo, hi in runs:
        print(f"  bed {bed}: {lo:6.1f}-{hi:6.1f}")


if __name__ == "__main__":
    main()
