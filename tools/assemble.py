#!/usr/bin/env python3
"""Step 4: join the clips of each chapter with natural pauses, level the voices,
master the loudness and package the audiobook.

  assemble.py --chapters 1-32          chapter files + Snowmoon.m4b with chapter marks
  assemble.py --excerpt ch01_sample    one work file -> audio/samples/<name>.mp3

Run with the Kokoro environment's python (needs numpy + soundfile); encoding uses ffmpeg.
"""
import argparse
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "audio" / "work"
RATE = 24000
# silence after a line, by what ends there
GAP = {"run": 0.22, "para": 0.55, "block": 0.8, "heading": 1.1}
SPEAKER_CHANGE = 0.1
SCENE_BREAK = 1.7
NARRATOR_NAME = "Narrator"
MASTER = "highpass=f=60,acompressor=threshold=-21dB:ratio=2.5:attack=12:release=220:makeup=2," \
         "loudnorm=I=-19:TP=-2:LRA=9,aresample=44100"


FX = {  # ffmpeg filter chains, applied to single clips
    "device": "highpass=f=320,lowpass=f=3300,acrusher=bits=9:mode=log:mix=0.25,"
              "aecho=0.8:0.6:14|23:0.28|0.18,volume=1.15",
    "pa": "highpass=f=260,lowpass=f=4200,aecho=0.85:0.7:95|190|310:0.38|0.24|0.13,volume=0.95",
    "message": "highpass=f=180,lowpass=f=5200,aecho=0.9:0.5:22:0.12",
    "child": "rubberband=pitch=1.16,atempo=1.04",
    "excl": "volume=1.3",
}


def with_fx(clip, fx):
    """Processed copy of a clip, cached next to the original."""
    out = Path(clip).with_suffix(f".{fx}.flac")
    if not out.exists():
        chain = ",".join(FX[part] for part in fx.split("+"))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-af", chain, "-ar", str(RATE),
                        str(out)], check=True)
    return out


def tone(freq, dur, decay, partials=((1, 1.0), (2.01, 0.35), (3.02, 0.12))):
    t = np.arange(int(dur * RATE)) / RATE
    wave = sum(a * np.sin(2 * np.pi * freq * k * t) for k, a in partials)
    return (wave * np.exp(-t / decay)).astype(np.float32)


def chime():
    """Scene change: two soft bell notes."""
    out = np.zeros(int(2.4 * RATE), dtype=np.float32)
    for start, freq in ((0.0, 880.0), (0.38, 1318.5)):
        n = tone(freq, 2.0, 0.55)
        i = int(start * RATE)
        out[i:i + len(n)] += n
    return out * 0.05


def notify():
    """Incoming message: a short double buzz, like a watch on a wrist."""
    t = np.arange(int(0.11 * RATE)) / RATE
    buzz = np.sin(2 * np.pi * 155 * t) * (1 + 0.6 * np.sin(2 * np.pi * 31 * t)) * np.hanning(len(t))
    gap = np.zeros(int(0.09 * RATE))
    return (np.concatenate([buzz, gap, buzz, np.zeros(int(0.35 * RATE))]) * 0.09).astype(np.float32)


def chapter_music_synth(dur=9.0):
    """Chapter opening: a slow, cold pad (D - A - E, an open fifth stack) with a few bell notes on top."""
    t = np.arange(int(dur * RATE)) / RATE
    pad = np.zeros_like(t)
    for f in (146.83, 220.0, 293.66, 329.63, 440.0):
        for detune in (-0.6, 0.0, 0.7):
            pad += np.sin(2 * np.pi * (f + detune) * t + np.random.default_rng(int(f)).uniform(0, 6.28))
    env = np.minimum(1, t / 2.2) * np.minimum(1, (dur - t) / 4.5)
    pad = pad / 15 * env * (0.85 + 0.15 * np.sin(2 * np.pi * 0.21 * t))
    bells = np.zeros_like(t)
    for start, f in ((0.6, 587.33), (1.9, 880.0), (3.1, 659.25), (4.6, 1174.66)):
        n = tone(f, 3.2, 0.9)
        i = int(start * RATE)
        bells[i:i + len(n)] += n[: len(bells) - i]
    return ((pad * 0.11 + bells * 0.035)).astype(np.float32)


SFX = ROOT / "audio" / "sfx"
SCENES = ROOT / "script" / "scenes"
BED_LEVEL, BED_SECONDS, BED_FADE_IN, BED_FADE_OUT = 0.11, 26.0, 2.5, 7.0
SPOT_LEVEL = {"watch_buzz": 0.5, "alarm": 0.35, "crowd_cheer": 0.3, "crowd_gasp": 0.3, "explosion_distant": 0.4,
              "drones_flyby": 0.35, "door_knock": 0.45, "door_open": 0.4, "data_transfer": 0.35,
              "footsteps_stairs": 0.4}
MUSIC_LEVEL = 0.16
# A: glassy and cold (Veridia's civic chapters); B: pulse and tension (tournaments, war);
# C: icy and serene (the emotional and reflective chapters)
CHAPTER_THEME = {1: "A", 2: "B", 3: "A", 4: "B", 5: "C", 6: "A", 7: "B", 8: "A", 9: "C", 10: "A", 11: "A",
                 12: "B", 13: "A", 14: "B", 15: "C", 16: "A", 17: "A", 18: "B", 19: "C", 20: "B", 21: "C",
                 22: "B", 23: "C", 24: "C", 25: "A", 26: "B", 27: "A", 28: "A", 29: "B", 30: "B", 31: "C", 32: "C"}
THEME_FILE = {"A": "theme_A_granular", "B": "theme_B_subpulse", "C": "theme_C_icy"}
THEME_GAIN = {"A": 1.0, "B": 0.45, "C": 1.0}  # B is generated much louder than the other two
# effects for things the text shows but cannot be read: the omitted key lists
EXTRA_SPOTS = {"30:6": "data_transfer", "30:33": "data_transfer", "19:115": "data_transfer"}


def asset(name):
    f = SFX / f"{name}.flac"
    if not f.exists():
        return None
    audio, _ = sf.read(f, dtype="float32")
    return audio


def fade(audio, fade_in=0.0, fade_out=0.0):
    out = audio.copy()
    n_in, n_out = int(fade_in * RATE), int(fade_out * RATE)
    if n_in:
        out[:n_in] *= np.linspace(0, 1, n_in, dtype=np.float32)
    if n_out:
        out[-n_out:] *= np.linspace(1, 0, n_out, dtype=np.float32)
    return out


def bed(name, seconds=BED_SECONDS):
    """A loopable ambience, trimmed to the wanted length with fades."""
    audio = asset(name)
    if audio is None:
        return None
    need = int(seconds * RATE)
    reps = need // len(audio) + 1
    return fade(np.tile(audio, reps)[:need] * BED_LEVEL, BED_FADE_IN, BED_FADE_OUT)


def scene_plan(chapter):
    f = SCENES / f"ch{chapter:02d}.json"
    if not f.exists():
        return {}, {}
    d = json.loads(f.read_text())
    beds = {sc["start"]: sc["ambience"] for sc in d.get("scenes", []) if sc.get("ambience")}
    spots = {sp["id"]: sp["sound"] for sp in d.get("spots", [])}
    return beds, spots


def voice_gains(files):
    """One fixed gain per voice so that all voices sit at the narrator's level."""
    energy, weight = collections.Counter(), collections.Counter()
    for f in files:
        for u in json.loads(f.read_text()):
            if u.get("rms"):
                energy[u["voice"]] += u["rms"] ** 2 * u["seconds"]
                weight[u["voice"]] += u["seconds"]
    level = {v: (energy[v] / weight[v]) ** 0.5 for v in energy}
    target = max(level.items(), key=lambda kv: weight[kv[0]])[1]  # the most-heard voice: the narrator
    return {v: float(np.clip(target / lv, 0.5, 2.5)) for v, lv in level.items()}


def render(lines, gains, sound=True, chapter=None):
    beds, spots = scene_plan(chapter) if (sound and chapter) else ({}, {})
    spots = {**spots, **{k: v for k, v in EXTRA_SPOTS.items() if k.startswith(f"{chapter}:")}} if sound else {}
    out, prev = [], None
    overlays = []  # (sample offset, audio) mixed in afterwards
    timeline = []  # (item id or "pause", seconds from chapter start)
    pos = lambda: sum(len(x) for x in out)
    key = CHAPTER_THEME.get(chapter, "A")
    chapter_music = asset(THEME_FILE[key])
    if chapter_music is not None:
        chapter_music = chapter_music * THEME_GAIN[key]
    for u in lines:
        if "pause" in u:
            timeline.append(("pause", (pos() + int(0.6 * RATE)) / RATE))
            if sound:
                out.append(chime())
            else:
                out.append(np.zeros(int((SCENE_BREAK - GAP["para"]) * RATE), dtype=np.float32))
            continue
        if "clip" not in u:
            continue
        clip = u["clip"]
        if sound and u.get("fx"):
            clip = with_fx(clip, u["fx"])
        audio, _ = sf.read(clip, dtype="float32")
        if prev is not None and prev != u["speaker"]:
            out.append(np.zeros(int(SPEAKER_CHANGE * RATE), dtype=np.float32))
        if sound and u.get("cue") == "notify":
            buzz = asset("watch_buzz")
            out.append(buzz * SPOT_LEVEL["watch_buzz"] if buzz is not None else notify())
        if sound and u.get("cue") == "chapter":
            if chapter_music is not None:
                overlays.append((pos(), fade(chapter_music * MUSIC_LEVEL, 0.3, 9.0)))
            else:
                overlays.append((pos(), chapter_music_fallback()))
            out.append(np.zeros(int(3.4 * RATE), dtype=np.float32))  # music alone, then the title over it
        if sound and u.get("cue") == "ending":
            theme = asset("ending_theme")
            if theme is not None:
                overlays.append((pos(), fade(theme * MUSIC_LEVEL, 1.0, 8.0)))
        if u["id"] in beds:
            b = bed(beds[u["id"]])
            if b is not None:
                overlays.append((pos() + int((10.0 if u.get("cue") == "chapter" else 0.0) * RATE), b))
        timeline.append((u["id"], (pos() + int(0.6 * RATE)) / RATE))  # the voice really starts here
        out.append(audio * gains.get(u["voice"], 1.0))
        if u["id"] in spots and (u["speaker"] == NARRATOR_NAME or u["speaker"] == "mix"):
            sp = asset(spots[u["id"]])
            if sp is not None:
                out.append(np.zeros(int(0.25 * RATE), dtype=np.float32))
                overlays.append((pos(), fade(sp * SPOT_LEVEL.get(spots[u["id"]], 0.4), 0.05, 0.8)))
                out.append(np.zeros(int(min(len(sp) / RATE, 2.2) * RATE), dtype=np.float32))
                spots.pop(u["id"])
        out.append(np.zeros(int(GAP[u["end"]] * RATE), dtype=np.float32))
        prev = u["speaker"]
    lead = np.zeros(int(0.6 * RATE), dtype=np.float32)
    mix = np.concatenate([lead, *out, np.zeros(int(1.5 * RATE), dtype=np.float32)])
    for at, layer in overlays:
        at += len(lead)
        end = min(len(mix), at + len(layer))
        mix[at:end] += layer[: end - at]
    render.timeline = timeline
    return mix


def chapter_music_fallback():
    return chapter_music_synth()


def encode(wav, out, codec):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", MASTER, *codec, str(out)], check=True)


def seconds(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


def chapters(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chapters")
    ap.add_argument("--excerpt")
    ap.add_argument("--plain", action="store_true", help="voices only: no music, chimes, buzzes or voice effects")
    ap.add_argument("--out", default="book", help="output folder under audio/ (also names the .m4b)")
    ap.add_argument("--timelines-only", action="store_true", help="rewrite audio/work/timeline_chNN.json without re-encoding")
    args = ap.parse_args()
    sound = not args.plain
    book = sorted(WORK.glob("ch[0-9][0-9].json"))
    tmp = WORK / "tmp.wav"

    if args.excerpt:
        f = WORK / f"{args.excerpt}.json"
        gains = voice_gains(book or [f])
        ch_no = int(re.match(r"ch(\d+)", args.excerpt).group(1))
        sf.write(tmp, render(json.loads(f.read_text()), gains, sound, ch_no), RATE, subtype="PCM_16")
        out = ROOT / "audio" / "samples" / f"{args.excerpt}.mp3"
        out.parent.mkdir(parents=True, exist_ok=True)
        encode(tmp, out, ["-c:a", "libmp3lame", "-b:a", "128k"])
        print(out, f"{seconds(out):.0f}s")
        tmp.unlink()
        return

    gains = voice_gains(book)
    outdir = ROOT / "audio" / args.out
    outdir.mkdir(parents=True, exist_ok=True)
    made = []
    for ch in chapters(args.chapters):
        f = WORK / f"ch{ch:02d}.json"
        if not f.exists():
            sys.exit(f"chapter {ch} has not been synthesised yet")
        out = outdir / f"Snowmoon - Chapter {ch:02d}.m4a"
        mix = render(json.loads(f.read_text()), gains, sound, ch)
        (WORK / f"timeline_ch{ch:02d}.json").write_text(json.dumps(render.timeline))
        if args.timelines_only:
            print(f"chapter {ch}: timeline rewritten", flush=True)
            continue
        sf.write(tmp, mix, RATE, subtype="PCM_16")
        encode(tmp, out, ["-c:a", "aac", "-b:a", "80k", "-ac", "1"])
        made.append((ch, out, seconds(out)))
        print(f"chapter {ch}: {made[-1][2] / 60:.1f} min", flush=True)
    tmp.unlink(missing_ok=True)
    if args.timelines_only:
        return

    # one .m4b with chapter marks, from every chapter file present (a partial run re-joins the rest)
    made = [(ch, p, seconds(p)) for ch in range(1, 33) for p in [outdir / f"Snowmoon - Chapter {ch:02d}.m4a"] if p.exists()]
    engine = "ElevenLabs" if args.out == "eleven" else "Kokoro-82M"
    meta = [";FFMETADATA1", "title=Snowmoon", "artist=Vitalik Buterin", "album=Snowmoon", "genre=Audiobook",
            f"comment=Text released under GPL v3 at vitalik.eth.limo/snowmoon. Synthetic voices ({engine})."]
    start = 0.0
    for ch, _, dur in made:
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(start * 1000)}", f"END={int((start + dur) * 1000)}",
                 f"title=Chapter {ch}"]
        start += dur
    (WORK / "chapters.txt").write_text("\n".join(meta) + "\n")
    (WORK / "concat.txt").write_text("".join(f"file '{p}'\n" for _, p, _ in made))
    m4b = ROOT / "audio" / f"Snowmoon{'' if args.out == 'book' else '-' + args.out}.m4b"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(WORK / "concat.txt"),
                    "-i", str(WORK / "chapters.txt"), "-map_metadata", "1", "-map_chapters", "1", "-c", "copy",
                    "-movflags", "+faststart", str(m4b)], check=True)
    print(f"{m4b}  {start / 3600:.2f} h, {m4b.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
