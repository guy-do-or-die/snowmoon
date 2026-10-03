#!/usr/bin/env python3
"""Make a short audition clip from chapter 1 (the family dinner scene), two ways:

  A  text-to-dialogue with Eleven v3: all voices generated together in one pass
  B  one clip per line with Multilingual v2, stitched with pauses

  D  like A, with delivery directions (whisper, shout, mood) on the lines

  E  like D, with Eleven v4

Usage: tools/sample.py [A|B|both|D|E]
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eleven  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio" / "samples"

# ElevenLabs default voices (usable on every plan)
VOICES = {
    "N": "JBFqnCBsd6RMkjVDRZzb",  # George  - narrator
    "G": "cjVigY5qzO86Huf0OWal",  # Eric    - Gladias
    "S": "EXAVITQu4vr4xnSDxMaL",  # Sarah   - Seila
    "Z": "FGY2WhTYpPnrIDTdsKH5",  # Laura   - Zven (child)
    "F": "TX3LPaxmHKxFdv7VOQHJ",  # Liam    - Febric (teen)
}
FIRST, LAST = "1:113", "1:127"


def scene():
    items = json.loads((ROOT / "script" / "raw" / "ch01.json").read_text())
    ids = [it["id"] for it in items]
    return items[ids.index(FIRST): ids.index(LAST) + 1]


def polish(spk, text):
    if spk == "N" and text[0].islower():
        return text  # "he shouted." continues the sentence the character started
    return text


def turns(items):
    """Merge neighbouring runs of one speaker; keep paragraph ends for pausing."""
    out = []
    for it in items:
        for i, r in enumerate(it["runs"]):
            last = i == len(it["runs"]) - 1
            if out and out[-1]["spk"] == r["spk"] and not out[-1]["para_end"]:
                out[-1]["text"] += " " + r["text"]
            else:
                out.append({"spk": r["spk"], "text": polish(r["spk"], r["text"]), "para_end": False})
            out[-1]["para_end"] = last
    return out


def variant_a(ts):
    merged = []
    for t in ts:
        if merged and merged[-1][0] == VOICES[t["spk"]]:
            merged[-1] = (merged[-1][0], merged[-1][1] + " " + t["text"])
        else:
            merged.append((VOICES[t["spk"]], t["text"]))
    clip = eleven.dialogue(merged, model="eleven_v3")
    out = OUT / "sample_A_v3_dialogue.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-af",
                    "loudnorm=I=-18:TP=-1.5:LRA=11", "-b:a", "128k", str(out)], check=True)
    return out


def variant_b(ts):
    clips = []
    for i, t in enumerate(ts):
        prev = " ".join(x["text"] for x in ts[max(0, i - 2): i]) or None
        nxt = ts[i + 1]["text"] if i + 1 < len(ts) else None
        settings = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True}
        clips.append((eleven.speak(t["text"], VOICES[t["spk"]], "eleven_multilingual_v2",
                                   settings=settings, previous_text=prev, next_text=nxt),
                      0.65 if t["para_end"] else 0.28))
    # per-clip loudness levelling, then silence, then concat
    inputs, filters, labels = [], [], []
    for n, (clip, gap) in enumerate(clips):
        inputs += ["-i", str(clip)]
        filters.append(f"[{n}:a]silenceremove=start_periods=1:start_threshold=-50dB,"
                       f"areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                       f"loudnorm=I=-18:TP=-1.5:LRA=11,aresample=44100,apad=pad_dur={gap}[a{n}]")
        labels.append(f"[a{n}]")
    filters.append("".join(labels) + f"concat=n={len(clips)}:v=0:a=1[out]")
    out = OUT / "sample_B_v2_per_line.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[out]", "-b:a", "128k", str(out)], check=True)
    return out


# Variant D: the same engine as A, plus delivery directions (Eleven v3 audio tags) per line.
# Keyed by (item id, run index); the narrator is left undirected.
ACTED_RANGE = ("1:122", "1:134")
ACTED_VOICES = {**VOICES, "L": "cgSgspJ2msm6clMCkdW9"}  # Jessica - Lily
DIRECTIONS = {
    ("1:123", 0): "[shouting excitedly] {}",
    ("1:125", 0): "[warmly] {}",
    ("1:126", 0): "[eagerly] {}",
    ("1:127", 0): "[shouting, triumphant] {}",
    ("1:129", 0): "[matter-of-fact] Lily's in the bathroom. Hreda will be back from after-school number theory "
                  "in a longhour. [teasing] Come on, you know she always gets the number nine.",
    ("1:131", 1): "[sighs] [gently, concerned] {}",
    ("1:132", 0): "[mumbling, dejected] Sixty percent on the history exam. [sighs] Whatever...",
    ("1:133", 1): "[softly, tenderly] {}.",
}


def variant_d(model="eleven_v3", name="sample_D_v3_acted.mp3"):
    items = json.loads((ROOT / "script" / "raw" / "ch01.json").read_text())
    ids = [it["id"] for it in items]
    merged = []
    for it in items[ids.index(ACTED_RANGE[0]): ids.index(ACTED_RANGE[1]) + 1]:
        for i, r in enumerate(it["runs"]):
            text = DIRECTIONS.get((it["id"], i), "{}").format(r["text"])
            voice = ACTED_VOICES[r["spk"]]
            if merged and merged[-1][0] == voice:
                merged[-1] = (voice, merged[-1][1] + " " + text)
            else:
                merged.append((voice, text))
    print("D:", sum(len(t) for _, t in merged), "characters,", len(merged), "turns")
    clip = eleven.dialogue(merged, model=model)
    out = OUT / name
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-af",
                    "loudnorm=I=-18:TP=-1.5:LRA=11", "-b:a", "128k", str(out)], check=True)
    return out


def main():
    which = (sys.argv[1] if len(sys.argv) > 1 else "both").upper()
    OUT.mkdir(parents=True, exist_ok=True)
    if which == "D":
        print("D ->", variant_d())
        return
    if which == "E":  # same scene and directions, Eleven v4
        print("E ->", variant_d(model="eleven_v4", name="sample_E_v4_acted.mp3"))
        return
    ts = turns(scene())
    chars = sum(len(t["text"]) for t in ts)
    print(f"{len(ts)} turns, {chars} characters per variant")
    for name, fn in (("A", variant_a), ("B", variant_b)):
        if which in (name, "BOTH"):
            try:
                print(name, "->", fn(ts))
            except Exception as e:  # report and carry on with the other variant
                print(name, "FAILED:", type(e).__name__, e)


if __name__ == "__main__":
    main()
