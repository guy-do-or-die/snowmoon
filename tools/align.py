#!/usr/bin/env python3
"""Step 5b: word timestamps for every clip, via ElevenLabs forced alignment.

Reads audio/work/chNN.json, aligns each clip's audio with its text (delivery
tags stripped), caches the result, and writes audio/work/words_chNN.json:
a list of {t0, t1, word, speaker, line} in chapter time, using the chapter's
timeline from assemble.py.

  align.py --chapters 1-32 [--workers 4]
"""
import argparse
import concurrent.futures
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import eleven  # noqa: E402

CACHE = Path.home() / ".cache" / "snowmoon-audiobook" / "align"
TAG = re.compile(r"\s*\[[^\]]+\]\s*")


def spoken(text):
    return re.sub(r"\s+", " ", TAG.sub(" ", text)).strip()


def align(clip, text):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / (Path(clip).stem + ".json")
    if out.exists():
        return json.loads(out.read_text())
    for attempt in range(3):
        with open(clip, "rb") as f:
            r = requests.post(f"{eleven.BASE}/v1/forced-alignment", headers={"xi-api-key": eleven._key()},
                              files={"file": ("clip.flac", f, "audio/flac")}, data={"text": text}, timeout=600)
        if r.ok:
            out.write_text(r.text)
            return r.json()
    raise RuntimeError(f"alignment failed for {clip}: {r.status_code} {r.text[:200]}")


def words_for_chapter(ch):
    work = json.loads((ROOT / "audio" / "work" / f"ch{ch:02d}.json").read_text())
    timeline = json.loads((ROOT / "audio" / "work" / f"timeline_ch{ch:02d}.json").read_text())
    final = json.loads((ROOT / "script" / "final" / f"ch{ch:02d}.json").read_text())
    starts = [t for k, t in timeline if k != "pause"]
    items = [u for u in work if "clip" in u]
    assert len(starts) == len(items), f"ch{ch}: timeline/work mismatch"
    # the chunk's lines, in order, with their speakers
    lines = [u for u in final if "text" in u]
    cursor = 0
    out = []
    for t0, item in zip(starts, items):
        text = spoken(item["text"])
        res = align(item["clip"], text)
        tokens = []
        for w in res["words"]:
            parts = w["text"].split()
            if not parts:
                continue
            if len(parts) == 1:
                tokens.append(w)
                continue
            # a parenthesised phrase comes back as one token: share its span over the words
            span, at = (w["end"] - w["start"]) / len(parts), w["start"]
            for part in parts:
                tokens.append({"text": part, "start": at, "end": at + span})
                at += span
        # consume lines from the script that make up this chunk
        chunk_lines = []
        acc = ""
        while cursor < len(lines) and len(acc) < len(text) - 2:
            chunk_lines.append(lines[cursor])
            acc = (acc + " " + spoken(lines[cursor]["text"])).strip()
            cursor += 1
        # assign tokens to lines by word counts
        k = 0
        for ln in chunk_lines:
            n = len(spoken(ln["text"]).split())
            for w in tokens[k:k + n]:
                out.append({"t0": round(t0 + w["start"], 3), "t1": round(t0 + w["end"], 3), "word": w["text"],
                            "speaker": ln["speaker"], "line": ln["id"], "letter": ln.get("letter")})
            k += n
        if k != len(tokens):
            print(f"ch{ch} {item['id']}: {len(tokens)} aligned words vs {k} script words", file=sys.stderr)
    (ROOT / "audio" / "work" / f"words_ch{ch:02d}.json").write_text(json.dumps(out))
    return ch, len(out)


def chapters(spec):
    r = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        r += range(int(a), int(b or a) + 1)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chapters", default="1-32")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        for ch, n in pool.map(words_for_chapter, chapters(args.chapters)):
            print(f"ch{ch:02d}: {n} words", flush=True)


if __name__ == "__main__":
    main()
