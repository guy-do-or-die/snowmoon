#!/usr/bin/env python3
"""Step 2: resolve every line to a character and a voice, and make the text speakable.

Input:  script/raw/chNN.json   (from extract.py)
        script/cast/chNN.json  (who speaks each lettered line, per chapter)
Output: script/final/chNN.json - list of utterances {id, speaker, voice, text, end}
                                 and {"pause": "scene" | "heading"} markers
        script/voices.json     - character -> voice, with the reasoning inputs
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from voicesets import ENGINES, NARRATOR  # noqa: E402

ACRONYMS = {"AI", "GPH", "UVC", "API", "VNU", "LLM", "GDP", "DU", "KAG", "XOR", "PM", "CO", "II", "III"}
PA_VOICES = {"loud automated voice", "loud automated voice (Sadzu Du)", "flight announcer", "news reporter",
             "lecture narrator"}
DZEGOBAN_CAPS = {"loud automated voice", "loud automated voice (Sadzu Du)", "group (countdown chant)"}


def speakable(text, lower_caps=False):
    t = text
    t = t.replace("→", "").replace("✓", "").replace("≥", "at least ").replace("Δv", "delta-v")
    t = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", t)
    t = re.sub(r"\bSt\b\.?(?= #| number)", "Street,", t)
    t = re.sub(r"\bAve\b\.?(?= #| number)", "Avenue,", t)
    t = re.sub(r"#(\d)", r"number \1", t)
    t = re.sub(r"\bCO ?2\b", "C O 2", t)
    t = re.sub(r"\bPM ?2\.5\b", "P M 2.5", t)
    t = re.sub(r"(\d) ?zc\b", r"\1 zipcoins", t)
    t = re.sub(r"(\d+)\.(\d*?)0+%", lambda m: (m.group(1) + ("." + m.group(2) if m.group(2) else "")) + "%", t)
    t = re.sub(r"(\d)%", r"\1 percent", t)
    t = re.sub(r"\b(\d+)x gain", r"\1-fold gain", t)
    t = re.sub(r"\b(\d+(?:\.\d+)?)x\b", r"\1 times", t)
    t = re.sub(r"(\d)\.\.\.(\d)", r"\1 to \2", t)
    t = re.sub(r"\b(ages|Tier) (\d+)-(\d+)", r"\1 \2 to \3", t)
    t = re.sub(r"\b50/50\b", "fifty-fifty", t)
    t = re.sub(r"\b(\d+)nm\b", r"\1 nanometer", t)
    t = t.replace("i'th", "i-th").replace("XOR", "X-or")
    t = re.sub(r"_([^_]+)_", r"\1", t)
    t = re.sub(r"\?{2,}!", "?!", t)
    t = re.sub(r"^\* ", "", t).replace(" * ", " ")
    if lower_caps:
        t = re.sub(r"\b[A-Z]{2,}\b", lambda m: m.group(0) if m.group(0) in ACRONYMS else m.group(0).lower(), t)
        t = t[:1].upper() + t[1:]
    t = re.sub(r"\bGPL v3\b", "GPL version 3", t)
    t = re.sub(r"^[.,;:]\s*", "", t)  # narration left over after a quote that ended the sentence
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"\.\"\.", ".\"", t)
    return re.sub(r"\s+", " ", t).strip()


def resolver(ch):
    cast = json.loads((ROOT / "script" / "cast" / f"ch{ch:02d}.json").read_text())
    meta = {c["name"]: c for c in cast["characters"]}
    exc = {(e["id"], e["letter"], e.get("run")): e["speaker"] for e in cast.get("exceptions", [])}
    narr = {(e["id"], e.get("run", 0)): e["speaker"] for e in cast.get("narrator_exceptions", [])}

    def who(item_id, run_index, letter):
        return exc.get((item_id, letter, run_index)) or exc.get((item_id, letter, None)) or cast["letters"][letter]

    return who, narr, meta


def split_quoted(text, speaker):
    """A narrator-coded run that contains spoken words: quotes -> speaker, rest -> narrator."""
    if '"' not in text:
        return [(speaker, text)]
    out = []
    for i, part in enumerate(text.split('"')):
        part = re.sub(r"^[,;]\s*", "", part.strip())
        if part and part not in ".,":
            out.append((speaker if i % 2 else NARRATOR, part))
    return out


def chapter_lines(ch, people):
    items = json.loads((ROOT / "script" / "raw" / f"ch{ch:02d}.json").read_text())
    who, narr, meta = resolver(ch)
    for name, m in meta.items():
        people[name]["meta"] = m
        people[name]["chapters"].add(ch)
    out = []
    for it in items:
        if it["kind"] == "break":
            out.append({"pause": "scene"})
            continue
        for ri, r in enumerate(it["runs"]):
            spk = r["spk"]
            if spk == "N":
                pieces = split_quoted(r["text"], narr[(it["id"], ri)]) if (it["id"], ri) in narr else [(NARRATOR, r["text"])]
            elif spk.startswith("@"):
                pieces = [(spk[1:], r["text"])]
            else:
                pieces = [(who(it["id"], ri, spk), r["text"])]
            letter = spk if len(spk) == 1 and spk != "N" else None  # the page's colour key for this run
            for name, text in pieces:
                kind = people[name]["meta"].get("kind") if name in people and people[name]["meta"] else None
                if kind == "crowd":
                    name = NARRATOR  # unison shouts are read by the narrator
                text = speakable(text, lower_caps=name in DZEGOBAN_CAPS or it["id"] == "2:26")
                if text:
                    u = {"id": it["id"], "speaker": name, "text": text, "end": "run"}
                    if name != NARRATOR:
                        u["letter"] = letter or name[0].upper()
                    if name in PA_VOICES or kind == "announcer":
                        u["fx"] = "pa"            # public-address echo
                    elif kind in ("ai", "robot", "device"):
                        u["fx"] = "device"        # synthetic, band-limited
                    elif it["kind"] == "message" and name != NARRATOR:
                        u["fx"] = "message"       # written message, slightly "on a screen"
                    if it["kind"] == "message" and ri == 0:
                        u["cue"] = "notify"       # a soft buzz before "Message from ..."
                    meta = people[name]["meta"] or {}
                    extra = []
                    if meta.get("kind") == "human" and ("child" in (meta.get("age") or "") or name == "Lily"):
                        extra.append("child")     # Kokoro has no child voices: pitch an adult one up
                    if text.endswith("!") and name != NARRATOR and not u.get("fx"):
                        extra.append("excl")      # shouted lines get a little more level
                    if extra:
                        u["fx"] = "+".join(([u["fx"]] if u.get("fx") else []) + extra)
                    out.append(u)
        if it["kind"] == "heading" and out:
            out[-1]["cue"] = "chapter"            # music under the chapter title
        if out and "pause" not in out[-1]:
            out[-1]["end"] = "heading" if it["kind"] in ("heading", "dateline") else \
                             "block" if it["kind"] != "para" else "para"
    return out


def credits():
    """Opening title, and the author's own declarations from the index page as end credits."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup((ROOT / "source" / "index.html").read_text(encoding="utf-8"), "lxml")

    def line(text, end="para"):
        return {"id": "credits", "speaker": NARRATOR, "text": speakable(text), "end": end}

    opening = [line("Snowmoon. By Vitalik Buterin.", "heading")]
    closing = [{"pause": "scene"}, line("The end.", "heading"), line("From the author.", "block")]
    closing[1]["cue"] = "ending"
    for d in soup.find_all("div", class_="declaration"):
        label = d.find(class_="decl-label").get_text(strip=True).replace("爱", "Ai")
        closing.append(line(label, "run"))
        closing += [line(re.sub(r"\s+", " ", para.get_text(" ", strip=True))) for para in d.find_all("p")]
        closing[-1]["end"] = "block"
    closing.append(line("This audio edition was made with synthetic voices. "
                        "The scripts used to make it are published at github.com/guy-do-or-die/snowmoon-audiobook, "
                        "under the same license."))
    return opening, closing


def cast_voices(people, lines_by_ch, voiceset):
    VOICES, PRINCIPALS = voiceset["voices"], voiceset["principals"]
    reserved = {PRINCIPALS[n] for n in voiceset["exclusive"]}
    load = collections.Counter()
    for ch, lines in lines_by_ch.items():
        for u in lines:
            if "speaker" in u:
                people[u["speaker"]]["chars"] += len(u["text"])
                people[u["speaker"]]["chapters"].add(ch)
    assigned = {}
    for name, voice in PRINCIPALS.items():
        if name in people:
            assigned[name] = voice
            load[voice] += people[name]["chars"]
    rest = sorted((n for n in people if n not in assigned and people[n]["chars"]), key=lambda n: -people[n]["chars"])
    for name in rest:
        m = people[name]["meta"] or {}
        gender, kind, age = m.get("gender", "unknown"), m.get("kind", "human"), m.get("age", "")
        if kind in ("ai", "robot", "device", "written") or gender == "none":
            assigned[name] = voiceset["device"]
            continue
        if gender == "female" or age.startswith("child"):
            pool = [v for v, (_, g) in VOICES.items() if g == "f"]
        elif gender == "male":
            pool = [v for v, (_, g) in VOICES.items() if g == "m"]
        else:
            pool = [v for v, (_, g) in VOICES.items() if g in "mf"]
        pool = [v for v in pool if v not in reserved]
        together = {assigned[o] for o in assigned if o != name and people[o]["chapters"] & people[name]["chapters"]}
        choice = min(pool, key=lambda v: (v in together, load[v]))
        assigned[name] = choice
        load[choice] += people[name]["chars"]
    return assigned


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--engine", choices=sorted(ENGINES), default="kokoro")
    ap.add_argument("--narrator", help="voice name for the narrator (default: the engine's)")
    args = ap.parse_args()
    engine = args.engine
    voiceset = ENGINES[engine]
    if args.narrator:
        if args.narrator not in voiceset["voices"]:
            sys.exit(f"unknown voice {args.narrator}; choose from {', '.join(voiceset['voices'])}")
        # whoever had that voice is re-cast automatically
        principals = {n: v for n, v in voiceset["principals"].items() if v != args.narrator}
        voiceset = {**voiceset, "principals": {**principals, NARRATOR: args.narrator}}
    VOICES = voiceset["voices"]
    people = collections.defaultdict(lambda: {"meta": None, "chapters": set(), "chars": 0})
    lines_by_ch = {ch: chapter_lines(ch, people) for ch in range(1, 33)}
    opening, closing = credits()
    for u in lines_by_ch[1]:
        u.pop("cue", None) if u.get("cue") == "chapter" else None
    opening[0]["cue"] = "chapter"  # the book opens with music under its title
    lines_by_ch[1] = opening + lines_by_ch[1]
    lines_by_ch[32] = lines_by_ch[32] + closing
    voices = cast_voices(people, lines_by_ch, voiceset)
    (ROOT / "script" / "final").mkdir(parents=True, exist_ok=True)
    total = 0
    clashes = []
    for ch, lines in lines_by_ch.items():
        seen = {}
        for u in lines:
            if "speaker" in u:
                u["voice"] = voices[u["speaker"]]
                total += len(u["text"])
                other = seen.setdefault(u["voice"], u["speaker"])
                if other != u["speaker"] and (ch, u["voice"], *sorted((other, u["speaker"]))) not in clashes:
                    clashes.append((ch, u["voice"], *sorted((other, u["speaker"]))))
        (ROOT / "script" / "final" / f"ch{ch:02d}.json").write_text(
            json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    table = {n: {"voice": voices[n], "voice_id": VOICES[voices[n]][0], "characters": p["chars"],
                 "chapters": sorted(p["chapters"]),
                 **{k: (p["meta"] or {}).get(k) for k in ("gender", "age", "kind", "origin", "voice_notes")}}
             for n, p in sorted(people.items(), key=lambda kv: -kv[1]["chars"]) if n in voices}
    table = {"engine": engine, "cast": table}
    (ROOT / "script" / "voices.json").write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{engine}: {total:,} characters to speak, {len(table['cast'])} speakers, {len(set(voices.values()))} voices")
    print(f"voice shared by two people in the same chapter: {len(clashes)}")
    for c in clashes:
        print("  ch%d %s: %s / %s" % c)


if __name__ == "__main__":
    main()
