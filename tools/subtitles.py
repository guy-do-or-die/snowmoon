#!/usr/bin/env python3
"""Subtitles for the joined video: audio/Snowmoon.srt from the aligned words.

Cues are the caption units of the video (same speaker, sentence-aware, up to 84 characters),
prefixed with the speaker's name for everyone but the narrator; chapter offsets come from the
chapter videos, so run this after video.py --join.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import video  # noqa: E402


def stamp(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    cues, offset = [], 0.0
    for ch in range(1, 33):
        words = json.loads((ROOT / "audio" / "work" / f"words_ch{ch:02d}.json").read_text())
        for u in video.caption_units(words, max_chars=84):
            start = offset + u["words"][0]["t0"]
            end = offset + max(u["words"][-1]["t1"] + 0.4, u["words"][0]["t0"] + 0.8)
            text = " ".join(w["word"] for w in u["words"])
            if u["speaker"] not in ("Narrator", "mix"):
                text = f"{u['speaker']}: {text}"
            cues.append([start, end, text])
        offset += video.duration(video.OUT_DIR / f"ch{ch:02d}.mp4")
    for i in range(len(cues) - 1):   # no overlaps
        if cues[i][1] > cues[i + 1][0] - 0.02:
            cues[i][1] = max(cues[i][0] + 0.3, cues[i + 1][0] - 0.02)
    out = ROOT / "audio" / "Snowmoon.srt"
    out.write_text("".join(f"{n}\n{stamp(a)} --> {stamp(b)}\n{t}\n\n" for n, (a, b, t) in enumerate(cues, 1)), encoding="utf-8")
    print(f"{out.name}: {len(cues)} cues, {offset / 3600:.2f} h")


if __name__ == "__main__":
    main()
