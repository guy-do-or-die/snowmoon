#!/usr/bin/env python3
"""Step 3 (ElevenLabs): voice the final script with the Text to Dialogue API.

Lines are grouped into chunks (default 1,900 characters, at most 10 voices) that
the model performs in one pass, so turn-taking sounds natural. Lines that get a
sound effect (devices, public address) are generated on their own so the effect
can be applied. Delivery directions from script/directions are inserted as tags.

  synth_eleven.py --chapters 1 --dry-run        count chunks and characters, spend nothing
  synth_eleven.py --chapters 1-32               generate (cached: re-runs cost nothing)

Writes audio/work/chNN.json for assemble.py. Run with the Kokoro environment's python.
"""
import argparse
import concurrent.futures
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import eleven  # noqa: E402
from voicesets import ELEVEN, NARRATOR  # noqa: E402

CLIPS = Path.home() / ".cache" / "snowmoon-audiobook" / "clips_eleven"
RATE = 24000
SOLO_FX = {"device", "pa"}  # effects that need a clip of their own
VOICE_ID = {name: vid for name, (vid, _) in ELEVEN["voices"].items()}


def directed(ch):
    f = ROOT / "script" / "directions" / f"ch{ch:02d}.json"
    return json.loads(f.read_text()) if f.exists() else {}


def apply_direction(u, run_index, directions):
    d = directions.get(f"{u['id']}/{run_index}")
    if not d:
        return u["text"]
    if d.startswith("INLINE:"):
        return d[len("INLINE:"):].strip()
    return f"{d} {u['text']}"


def chunk_lines(lines, directions, limit):
    """Yield work items: {'turns': [(voice_id, text), ...], 'lines': [line, ...]} or pause markers."""
    run_index = {}
    cur = None

    def close():
        nonlocal cur
        if cur:
            yield cur
        cur = None

    for u in lines:
        if "pause" in u:
            yield from close()
            yield u
            continue
        n = run_index[u["id"]] = run_index.get(u["id"], -1) + 1
        text = apply_direction(u, n, directions)
        fx = "+".join(p for p in (u.get("fx") or "").split("+") if p in SOLO_FX)
        if fx:
            yield from close()
            yield {"turns": [(VOICE_ID[u["voice"]], text)], "lines": [u], "fx": fx}
            continue
        voices = {VOICE_ID[u["voice"]]} | ({t[0] for t in cur["turns"]} if cur else set())
        size = len(text) + (sum(len(t[1]) for t in cur["turns"]) if cur else 0)
        if cur and (u.get("cue") or size > limit or len(voices) > 10):
            yield from close()
        if cur is None:
            cur = {"turns": [], "lines": []}
        cur["turns"].append((VOICE_ID[u["voice"]], text))
        cur["lines"].append(u)
    yield from close()


def to_flac(mp3):
    out = CLIPS / (Path(mp3).stem + ".flac")
    if not out.exists():
        CLIPS.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", str(RATE),
                        str(out)], check=True)
    return out


def measure(path):
    audio, _ = sf.read(path, dtype="float32")
    active = audio[np.abs(audio) > 0.01]
    return len(audio) / RATE, float(np.sqrt(np.mean(active ** 2))) if len(active) else 0.0


def generate(item, model):
    if len(item["turns"]) == 1:
        voice, text = item["turns"][0]
        mp3 = eleven.speak(text, voice, model)
    else:
        mp3 = eleven.dialogue(item["turns"], model=model)
    return to_flac(mp3)


def quota():
    try:
        r = requests.get(f"{eleven.BASE}/v1/user/subscription", headers={"xi-api-key": eleven._key()}, timeout=30)
        if r.ok:
            s = r.json()
            return f"{s['character_count']:,} of {s['character_limit']:,} characters used this period"
    except requests.RequestException:
        pass
    return "quota unknown (key lacks user_read)"


def chapters(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chapters", default="1-32")
    ap.add_argument("--model", default="eleven_v4")
    ap.add_argument("--chunk", type=int, default=1900, help="max characters per dialogue request")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--first")
    ap.add_argument("--last")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    if json.loads((ROOT / "script" / "voices.json").read_text())["engine"] != "eleven":
        sys.exit("script/final was built for another engine; run: tools/build.py --engine eleven")
    eleven.OUTPUT_FORMAT = "mp3_44100_192"
    work = ROOT / "audio" / "work"
    work.mkdir(parents=True, exist_ok=True)
    grand = 0
    for ch in chapters(args.chapters):
        lines = json.loads((ROOT / "script" / "final" / f"ch{ch:02d}.json").read_text())
        if args.first:
            ids = [u.get("id") for u in lines]
            lines = lines[ids.index(args.first): len(ids) - ids[::-1].index(args.last)]
        items = list(chunk_lines(lines, directed(ch), args.chunk))
        jobs = [it for it in items if "turns" in it]
        chars = sum(len(t[1]) for it in jobs for t in it["turns"])
        grand += chars
        print(f"ch{ch:02d}: {len(jobs)} requests, {chars:,} characters"
              f"{' (' + str(sum(1 for j in jobs if len(j['turns']) == 1)) + ' single-line)' if not args.dry_run else ''}",
              flush=True)
        if args.dry_run:
            continue
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
            clips = list(pool.map(lambda it: generate(it, args.model), jobs))
        out = []
        k = 0
        for it in items:
            if "pause" in it:
                out.append(it)
                continue
            first, last = it["lines"][0], it["lines"][-1]
            seconds, rms = measure(clips[k])
            rec = {"id": first["id"], "speaker": first["speaker"] if len(it["lines"]) == 1 else "mix",
                   "voice": first["voice"] if len(it["lines"]) == 1 else "mix",
                   "text": " ".join(t[1] for t in it["turns"]), "clip": str(clips[k]),
                   "seconds": seconds, "rms": rms, "end": last["end"]}
            if first.get("cue"):
                rec["cue"] = first["cue"]
            if it.get("fx"):
                rec["fx"] = it["fx"]
            out.append(rec)
            k += 1
        (work / f"ch{ch:02d}{args.tag}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(f"       {sum(r.get('seconds', 0) for r in out) / 60:.1f} min of audio in "
              f"{(time.time() - t0) / 60:.1f} min; {quota()}", flush=True)
    print(f"total {grand:,} characters")


if __name__ == "__main__":
    main()
