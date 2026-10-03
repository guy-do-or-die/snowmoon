#!/usr/bin/env python3
"""Pronunciation for the book's invented names and for Dzegoban, the constructed language.

Kokoro's G2P accepts inline phonemes as [word](/phonemes/). Without this it spells
"Dzego" as "D-Z-ego" and reads Dzegoban syllables as English words.

Dzegoban is written as space-separated syllables: optional onset, vowel or diphthong,
optional final n. The book gives no pronunciation guide, so the reading here is a
choice: vowels as in Italian/pinyin, c = "ts", j = English j, dz and sh as written.
"""
import re
from pathlib import Path

NAMES = {
    "Zei": "zˈA", "Dzego": "dzˈɛɡO", "Dzegoban": "dzˈɛɡObˌɑn", "Dzegojan": "dzˈɛɡOʤˌɑn",
    "Dza": "dzˈɑ", "Dzingo": "dzˈɪŋɡO", "Zven": "zvˈɛn", "Minpentai": "mˌɪnpɛntˈI",
    "Pafogai": "pˌɑfOɡˈI", "Kungaupei": "kˌuŋɡWpˈA", "Bansunpei": "bˌɑnsunpˈA",
    "Sadzu": "sˈɑdzu", "Mu": "mˈu", "Munbau": "mˈunbW", "Jahen": "ʤˈɑhɛn", "Caibai": "tsˈIbI",
    "Deluin": "dˈɛluɪn", "Evelor": "ˈɛvəlˌɔɹ", "Thaldur": "θˈɑldʊɹ", "Telpo": "tˈɛlpO",
    "Balme": "bˈɑlm", "Pelae": "pɛlˈA", "Grapetime": "ɡɹˈAptˌIm", "Mistime": "mˈɪstˌIm",
    "Inglewore": "ˈɪŋɡəlwˌɔɹ", "Arturia": "ɑɹtˈʊɹiə", "Arturian": "ɑɹtˈʊɹiən",
    "Tafindel": "tˈæfɪndˌɛl", "Gelebor": "ɡˈɛlɛbˌɔɹ", "Mabuli": "mɑbˈuli", "Caeron": "kˈɛɹən",
    "Devanvil": "dˈɛvənvˌɪl", "Imber": "ˈɪmbəɹ", "autobus": "ˈɔTObˌʌs", "Gladias": "ɡlˈædiəs",
    "Daia": "dˈIə", "Ai": "ˈI", "Buterin": "bjˈutəɹɪn", "Vitalik": "vɪtˈɑlɪk", "Leimin": "lˈAmin", "Belpaki": "bɛlpˈɑki", "Utaku": "utˈɑku",
}

ONSET = {"b": "b", "c": "ts", "d": "d", "dz": "dz", "f": "f", "g": "ɡ", "h": "h", "j": "ʤ", "k": "k",
         "l": "l", "m": "m", "n": "n", "p": "p", "s": "s", "sh": "ʃ", "t": "t", "z": "z", "": ""}
NUCLEUS = {"a": "ɑ", "e": "ɛ", "i": "i", "o": "O", "u": "u", "ai": "I", "ei": "A", "au": "W", "ou": "O",
           "ia": "jɑ", "ie": "jɛ", "iu": "ju", "io": "jO", "ui": "wA", "ua": "wɑ", "ue": "wɛ",
           "iau": "jW", "uai": "wI"}
SYLLABLE = re.compile(r"^(dz|sh|[bcdfghjklmnpstz])?(iau|uai|ai|ei|au|ou|ia|ie|iu|io|ui|ua|ue|a|e|i|o|u)(n)?$")
# English words that are also shaped like Dzegoban syllables: never Dzegoban on their own
REAL_ENGLISH = {"a", "i", "be", "he", "me", "to", "go", "no", "so", "do", "ha", "an", "in", "on", "hi",
                "man", "can", "fan", "sun", "fun", "gun", "pin", "ten", "men", "pen", "den", "hen", "tin",
                "sin", "lie", "die", "tie", "pie", "she", "son", "ban", "tan", "pan", "bun", "fin", "bin",
                "kin", "zen", "la", "pa", "ma", "pi", "de", "bio", "non", "un", "cue", "lion", "pain", "gain"}
ROOT = Path(__file__).resolve().parent.parent


def _inventory():
    """Syllables that occur in the book's pure-Dzegoban blocks (signs, announcements, screens)."""
    import json
    pure = {"23:23", "18:92", "19:16", "19:20", "19:40", "19:71", "19:144", "12:38", "18:51", "2:26", "4:64"}
    found = set()
    for f in sorted((ROOT / "script" / "raw").glob("ch*.json")):
        for it in json.loads(f.read_text()):
            if it["kind"] == "sign" or it["id"] in pure or (it["kind"] == "quote" and it["id"].startswith("26:")):
                for r in it["runs"]:
                    found |= {w for w in re.findall(r"[a-z]+", r["text"]) if SYLLABLE.match(w)}
    return found


INVENTORY = _inventory() | {
    # numerals and words that only appear inside dialogue or narration
    "pa", "gu", "so", "bi", "ze", "ha", "mu", "fo", "shi", "le", "fi", "hui", "ziu", "tau", "fa", "gei",
    "mun", "gui", "tei", "giu", "mo", "jia", "dzu", "lie", "gie", "kiu", "kai", "bin", "hu", "ba", "fau",
    "dia", "lau", "shau", "hei", "ja", "ma", "da", "cu", "hen", "be", "lu", "hin", "dze", "lin", "pan",
}
TOKEN = re.compile(r"[A-Za-z]+(?:'s\b)?|[^A-Za-z]+")
WORDLIST = Path("/usr/share/dict/american-english")
DICTIONARY = {w.strip().lower() for w in WORDLIST.read_text().split()} if WORDLIST.exists() else set()


def syllable(tok):
    m = SYLLABLE.match(tok.lower())
    if not m or tok.lower() not in INVENTORY:
        return None
    onset, nucleus, n = m.groups()
    return ONSET[onset or ""] + "ˈ" + NUCLEUS[nucleus] + ("n" if n else "")


def _link(word, phonemes):
    return f"[{word}](/{phonemes}/)"


def mark(text, force=False):
    """Wrap names and Dzegoban syllable runs in inline-phoneme links.

    force=True treats every syllable-shaped word as Dzegoban (for lines known to be Dzegoban).
    """
    parts = TOKEN.findall(text)
    words = [i for i, p in enumerate(parts) if p[0].isalpha()]
    shaped_all = [i for i in words if syllable(parts[i])]
    # a line that is (almost) all Dzegoban syllables is Dzegoban, English look-alikes included
    if words and len(shaped_all) >= 0.8 * len(words) and any(parts[i].lower() not in REAL_ENGLISH for i in shaped_all):
        force = True
    is_dz = {}
    run = []

    def flush():
        while not force and run and parts[run[-1]].lower() in REAL_ENGLISH:
            run.pop()
        while not force and run and parts[run[0]].lower() in REAL_ENGLISH:
            run.pop(0)
        toks = [parts[i] for i in run]
        if not toks:
            return
        foreign = [t for t in toks if t.lower() not in REAL_ENGLISH]
        if len(toks) == 1:
            i, t = run[0], toks[0]
            quoted = i > 0 and i + 1 < len(parts) and parts[i - 1][-1] in "'\"" and parts[i + 1][0] in "'\""
            ok = force or (t.islower() and t not in REAL_ENGLISH and
                           (quoted or (len(t) >= 3 and t not in DICTIONARY)))
        else:
            ok = force or len(foreign) * 2 > len(toks)
        if ok:
            for i in run:
                is_dz[i] = True

    for k, i in enumerate(words):
        tok = parts[i]
        nxt = parts[words[k + 1]] if k + 1 < len(words) else ""
        # a capitalised syllable only opens a run when plain Dzegoban follows ("Mu gu gei fa", not "Bai in")
        shaped = syllable(tok) and (force or tok.islower() or (
            not run and tok[1:].islower() and nxt.islower() and syllable(nxt) and nxt not in REAL_ENGLISH))
        joined = k > 0 and words[k - 1] == i - 2 and parts[i - 1].strip(" .") in ("", ",")
        if shaped and (not run or joined):
            run.append(i)
        else:
            flush()
            run = [i] if shaped else []
    flush()

    out = []
    for i, p in enumerate(parts):
        if is_dz.get(i):
            out.append(_link(p, syllable(p)))
        elif p in NAMES:
            out.append(_link(p, NAMES[p]))
        elif p.endswith("'s") and p[:-2] in NAMES:
            ph = NAMES[p[:-2]]
            out.append(_link(p, ph + ("s" if ph[-1] in "ptkfθ" else "z")))
        elif p.endswith("s") and p[:-1] in NAMES and p[:-1] in ("Dzegojan", "Arturian"):
            out.append(_link(p, NAMES[p[:-1]] + "z"))
        else:
            out.append(p)
    return "".join(out)


if __name__ == "__main__":
    import json
    import sys
    root = Path(__file__).resolve().parent.parent
    seen = {}
    for ch in range(1, 33):
        for u in json.loads((root / "script" / "final" / f"ch{ch:02d}.json").read_text()):
            if "text" in u:
                for m in re.finditer(r"(?:\[[^\]]+\]\(/[^)]*/\)[ ,]*)+", mark(u["text"])):
                    words = re.findall(r"\[([^\]]+)\]", m.group(0))
                    if not all(w in NAMES or w[:-2] in NAMES or w[:-1] in NAMES for w in words):
                        seen.setdefault(" ".join(words), u["id"])
    for phrase, where in sorted(seen.items(), key=lambda kv: (len(kv[0].split()), kv[0])):
        print(f"{where:8s} {phrase}")
    print(len(seen), "distinct Dzegoban spans", file=sys.stderr)
