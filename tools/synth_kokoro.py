#!/usr/bin/env python3
"""Step 3 (Kokoro): speak every line of the final script into a cached clip.

Run with the Kokoro environment's python (see README). Clips are cached by
voice + text, so an interrupted run resumes where it stopped and a re-run only
makes what changed.

  synth_kokoro.py --chapters 1-32 [--threads 3]
  synth_kokoro.py --chapters 1 --first 1:113 --last 1:127     (an excerpt)

Writes audio/work/chNN.json: the chapter's lines with clip path, duration and loudness.
"""
import argparse
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import pronounce  # noqa: E402

CLIPS = Path.home() / ".cache" / "snowmoon-audiobook" / "clips"
RATE = 24000
SPEED = 1.0
FORCE_DZEGOBAN = {"19:43"}  # one-word Dzegoban lines that look like English ("be")
_pipes = {}


def pipeline(voice):
    from kokoro import KPipeline
    lang = voice[0]  # a = American, b = British
    if lang not in _pipes:
        shared = next(iter(_pipes.values())).model if _pipes else True
        _pipes[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M", model=shared)
    return _pipes[lang]


def trim(audio, floor=0.004, keep=0.03):
    loud = np.flatnonzero(np.abs(audio) > floor)
    if not len(loud):
        return audio
    pad = int(keep * RATE)
    return audio[max(0, loud[0] - pad): loud[-1] + pad]


def speak(text, voice, force_dz=False):
    marked = pronounce.mark(text, force=force_dz)
    key = hashlib.sha1(f"kokoro-1.0|{voice}|{SPEED}|{marked}".encode()).hexdigest()
    path = CLIPS / key[:2] / f"{key}.flac"
    if not path.exists():
        chunks = [a.numpy() if hasattr(a, "numpy") else np.asarray(a)
                  for _, _, a in pipeline(voice)(marked, voice=voice, speed=SPEED) if a is not None]
        audio = trim(np.concatenate(chunks)) if chunks else np.zeros(int(0.1 * RATE), dtype=np.float32)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp.flac")
        sf.write(tmp, audio, RATE, subtype="PCM_16")
        tmp.rename(path)
    return path


def measure(path):
    audio, _ = sf.read(path, dtype="float32")
    active = audio[np.abs(audio) > 0.01]
    rms = float(np.sqrt(np.mean(active ** 2))) if len(active) else 0.0
    return len(audio) / RATE, rms


def chapters(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chapters", default="1-32")
    ap.add_argument("--first")
    ap.add_argument("--last")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--tag", default="", help="suffix for the work file of an excerpt")
    ap.add_argument("--shard", help="K/N: only make every N-th line starting at K (parallel workers); "
                                    "writes no work file - finish with a run without --shard")
    args = ap.parse_args()
    torch.set_num_threads(args.threads)
    if json.loads((ROOT / "script" / "voices.json").read_text())["engine"] != "kokoro":
        sys.exit("script/final was built for another engine; run: tools/build.py --engine kokoro")
    work = ROOT / "audio" / "work"
    work.mkdir(parents=True, exist_ok=True)
    for ch in chapters(args.chapters):
        lines = json.loads((ROOT / "script" / "final" / f"ch{ch:02d}.json").read_text())
        if args.first:
            ids = [u.get("id") for u in lines]
            lines = lines[ids.index(args.first): len(ids) - ids[::-1].index(args.last)]
        t0, made, seconds = time.time(), 0, 0.0
        shard = [int(x) for x in args.shard.split("/")] if args.shard else None
        for n, u in enumerate(lines):
            if "text" not in u:
                continue
            if shard:
                if n % shard[1] == shard[0]:
                    speak(u["text"], u["voice"], u["id"] in FORCE_DZEGOBAN)
                continue
            path = speak(u["text"], u["voice"], u["id"] in FORCE_DZEGOBAN)
            u["clip"] = str(path)
            u["seconds"], u["rms"] = measure(path)
            seconds += u["seconds"]
            made += 1
        if shard:
            print(f"ch{ch:02d}: shard {args.shard} done in {(time.time() - t0) / 60:.1f} min", flush=True)
            continue
        (work / f"ch{ch:02d}{args.tag}.json").write_text(json.dumps(lines, ensure_ascii=False, indent=1))
        print(f"ch{ch:02d}: {made} lines, {seconds / 60:.1f} min of audio, took {(time.time() - t0) / 60:.1f} min",
              flush=True)


if __name__ == "__main__":
    main()
