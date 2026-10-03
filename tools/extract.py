#!/usr/bin/env python3
"""Step 1: turn the Snowmoon chapter HTML into a structured narration script.

Output: script/raw/chNN.json  - list of items, each {id, kind, runs:[{spk, text}], ...}
        script/readable/chNN.txt - the same thing, human readable (used for cast review)

spk is "N" for the narrator, or a capital letter for a character line. The book
colour-codes speech by the first letter of the speaker's name (hue = letter index
* 360/27), so the letter is all the HTML tells us; cast.json resolves it to a person.

Non-prose blocks (device screens, posters, signs, diagrams) get a default reading
here; blocks that need a hand-written reading are replaced from overrides.py.
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from overrides import OVERRIDES, VOICE_AS, KEEP_LINES  # noqa: E402
from descriptions import DESCRIPTIONS, LINE_NOTES, LINE_AFTER  # noqa: E402

HUE_STEP = 360 / 27
OKLCH = re.compile(r"oklch\([\d.]+ [\d.]+ ([\d.]+)\)")


def letter_of(style):
    m = OKLCH.search(style or "")
    if not m:
        return None
    return chr(ord("A") + round(float(m.group(1)) / HUE_STEP) - 1)


def clean(text):
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def unquote(text):
    text = clean(text)
    if len(text) > 1 and text[0] in "\"“" and text[-1] in "\"”":
        text = text[1:-1].strip()
    return text


def para_runs(p):
    """Split a paragraph into narrator / speaker runs."""
    runs = []

    def add(spk, text):
        if not text:
            return
        if runs and runs[-1]["spk"] == spk:
            runs[-1]["text"] += text
        else:
            runs.append({"spk": spk, "text": text})

    def walk(node, spk):
        for c in node.children:
            if isinstance(c, NavigableString):
                add(spk, str(c))
            elif isinstance(c, Tag):
                if c.name == "br":
                    add(spk, " ")
                    continue
                let = letter_of(c.get("style")) if c.name == "span" else None
                walk(c, let or spk)

    walk(p, "N")
    out = []
    for r in runs:
        if r["spk"] == "N":
            # narration that follows a quote starts with the comma that closed it
            t = clean(r["text"])
            t = re.sub(r"^[,;]\s*", "", t)
            if t in ("", ".", ","):
                continue
            out.append({"spk": "N", "text": t})
        else:
            t = unquote(r["text"])
            if t:
                out.append({"spk": r["spk"], "text": t})
    return out


def cell_text(el):
    for junk in el.find_all(["button", "input", "svg"]):
        junk.decompose()
    for br in el.find_all("br"):
        br.replace_with(" ")
    return clean(el.get_text(" "))


MSG_HEADS = {"from", "message", "time", "to", "zan", "tie", "tei", "dun", ""}


def message_table(table):
    """Message notifications: 'From X -> message' or 'message -> To X'."""
    heads = [clean(th.get_text()).lower() for th in table.find_all("th")]
    if not heads or not set(heads) <= MSG_HEADS or not ({"message", "tie"} & set(heads)):
        return None
    outgoing = heads[0] in ("message", "tie")
    runs = []
    for tr in table.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            return None
        who_td, msg_td = (tds[2], tds[0]) if outgoing else (tds[0], tds[2])
        span = msg_td.find("span", style=OKLCH)
        spk = letter_of(span.get("style")) if span else None
        msg = cell_text(msg_td)
        who = cell_text(who_td)
        who = who.replace("≥", "at least").replace("✓", "").strip()
        who = re.sub(r"\s+Rep score", ", reputation score", who)
        who = re.sub(r"\s+Verified", ", verified", who)
        when = cell_text(tds[3]) if len(tds) > 3 and cell_text(tds[3]).isdigit() else ""
        when = f", at {int(when):,}" if when else ""
        label = f"Message to {who}{when}:" if outgoing else f"Message from {who}{when}:"
        runs.append({"spk": "N", "text": label})
        bracket = re.fullmatch(r"\[(.*)\]", msg)
        if bracket:
            runs.append({"spk": "N", "text": bracket.group(1).capitalize() + "."})
        else:
            runs.append({"spk": spk or "N", "text": msg})
    return runs


HEX_LINE = re.compile(r"^[0-9a-f]{64}: [0-9a-f]{64}\.?$")
BINARY = re.compile(r"^[01]{4}\.?$")
NUMERIC = re.compile(r"^[\d.,]+$")


def cell_items(cell):
    """Cell text; list items inside a cell are joined so they read as a list."""
    lis = cell.find_all("li")
    if lis:
        return ". ".join(cell_text(li).rstrip(".") for li in lis)
    return cell_text(cell).replace("✓", "").replace(" ?", "").strip().rstrip(":").strip()


def table_lines(table):
    head = [cell_items(th) for th in table.find_all("th")]
    rows = [[cell_items(td) for td in tr.find_all("td")] for tr in table.find_all("tr")]
    rows = [r for r in rows if any(r)]
    lines = []
    scoreboard = len(head) > 2 and not head[0] and rows and all(NUMERIC.match(c) for r in rows for c in r[1:])
    if len(head) == 1 or (head and len(set(h for h in head if h)) == 1 and len([h for h in head if h]) == 1):
        lines.append(next(h for h in head if h))
        head = []
    for r in rows:
        cells = [c for c in r if c]
        if scoreboard:
            lines.append(f"{r[0]}: " + ", ".join(f"{h} {c}" for h, c in zip(head[1:], r[1:])))
        elif len(head) > 2 and len(r) == len(head):
            first = f"{head[0]} {r[0]}" if head[0] else r[0]
            last = f"{head[-1]}: {r[-1]}" if NUMERIC.match(r[-1].rstrip("%")) else r[-1]
            lines.append(". ".join([first, *r[1:-1], last]))
        elif len(cells) == 2:
            lines.append(": ".join(cells))
        elif cells:
            lines.append(", ".join(cells))
    return lines


def chart_runs(svg):
    """Charts carry their own text alternative in <title>/<desc>; read that."""
    desc = svg.find("desc")
    if not desc:
        return []
    title, _, rest = clean(desc.get_text()).partition(": ")
    parts = [x.strip().rstrip(".") for x in rest.split(",")]
    return [{"spk": "N", "text": title if title.endswith("?") else title + "."},
            {"spk": "N", "text": ". ".join(parts) + "."}]


FACES = {"🙁": "very unhappy", "😐": "neutral", "😊": "very happy"}


def controls(el):
    """One line naming the screen's controls: sliders and buttons."""
    parts = []
    for inp in el.find_all("input"):
        if inp.get("type") == "range":
            labels = [clean(sp.get_text()) for sp in inp.find_next_sibling("div").find_all("span")] \
                if inp.find_next_sibling("div") else []
            labels = [l for l in labels if l]
            if labels and labels[0][:1] in FACES:
                parts.append(f"a slider from {FACES[labels[0][:1]]} to {FACES[labels[-1][:1]]}")
            elif labels:
                parts.append(f"a slider from {labels[0].replace('-', 'minus ')} to {labels[-1]}")
            else:
                parts.append("a slider")
    buttons = [clean(b.get_text()) for b in el.find_all("button")]
    buttons = [b for b in buttons if b]
    if buttons:
        uniq = list(dict.fromkeys(buttons))
        parts.append(f"a {uniq[0]} button" if len(uniq) == 1 else "buttons: " + ", ".join(uniq))
    if not parts:
        return None
    text = " and ".join(parts) if len(parts) <= 2 else "; ".join(parts)
    return text[:1].upper() + text[1:] + "."


def generic_block(el):
    """Fallback reading for a device screen / quote: rows and paragraphs in order."""
    el = BeautifulSoup(str(el), "lxml").body
    control_line = controls(el)
    for junk in el.find_all(["button", "input"]):
        junk.decompose()
    had_svg = bool(el.find("svg"))
    chart = []
    for sv in el.find_all("svg"):
        chart += chart_runs(sv)
        sv.decompose()
    if chart:
        return chart, False
    for table in el.find_all("table"):
        table.replace_with(NavigableString("\n" + "\n".join(table_lines(table)) + "\n"))
    for tag in el.find_all(["p", "li", "div", "h3", "hr", "br", "pre", "b"]):
        tag.insert_before(NavigableString("\n"))
        tag.insert_after(NavigableString("\n"))
    lines = []
    for ln in el.get_text("").split("\n"):
        ln = clean(ln).replace("✓", "").replace("🔥", "").strip()
        if not ln or ln in (">", ".") or HEX_LINE.match(ln):
            continue
        if BINARY.match(ln):
            ln = " ".join("zero" if d == "0" else "one" for d in ln.rstrip("."))
        if not re.search(r"[.!?:,;]$", ln):   # a line ending in a comma ("With regards,") stays as it is
            ln += "."
        lines.append(ln)
    if control_line:
        lines.append(control_line)
    return [{"spk": "N", "text": ln} for ln in lines], had_svg


def block_item(el, kind, bid):
    table = el.find("table")
    if table is not None:
        runs = message_table(table)
        if runs:
            control_line = controls(el)
            if control_line:
                runs.append({"spk": "N", "text": control_line})
            return {"kind": "message", "runs": runs}
    runs, had_svg = generic_block(el)
    if bid in DESCRIPTIONS:
        runs = [{"spk": "N", "text": DESCRIPTIONS[bid]}] + runs
    for old_text, new_text in LINE_NOTES.get(bid, {}).items():
        for r in runs:
            if r["text"] == old_text:
                r["text"] = new_text
    if bid in LINE_AFTER:
        anchor, note = LINE_AFTER[bid]
        for i, r in enumerate(runs):
            if r["text"].endswith(anchor):
                runs.insert(i + 1, {"spk": "N", "text": note})
                break
    item = {"kind": kind, "runs": runs}
    if had_svg:
        item["svg"] = True
    return item


def dateline(el):
    place = el.find(class_="place")
    date = el.find(class_="date")
    txt = el.find(class_="txt")
    place_t = clean(place.get_text()) if place else ""
    date_t = clean(date.get_text()) if date else ""
    if not place and not date:
        date_t = clean(txt.get_text())
    elif not date:
        # "<place> · 3724 Frostime 6" with the date as bare text
        rest = clean(txt.get_text()).replace(place_t, "").strip(" ·")
        date_t = rest
    return place_t, date_t


def say_date(date_t):
    m = re.fullmatch(r"(\d{4}) (\w+) (\d+)", date_t)
    if not m:
        return date_t
    year, month, day = m.groups()
    return f"{month} {day}, thirty-seven twenty-{'four' if year == '3724' else 'five'}"


def extract(ch):
    html = (ROOT / "source" / "html" / f"chapter-{ch}.html").read_text(encoding="utf-8")
    dp = BeautifulSoup(html, "lxml").find("div", class_="document-page")
    kids = [c for c in dp.children if isinstance(c, Tag)]
    items = []
    for n, c in enumerate(kids):
        cls = c.get("class", [])
        bid = f"{ch}:{n}"
        if c.name in ("nav", "br"):
            continue
        if bid in OVERRIDES:
            ov = OVERRIDES[bid]
            if ov is None:
                continue
            item = {"kind": "override", "runs": [{"spk": s, "text": t} for s, t in ov]}
        elif c.name == "h1":
            item = {"kind": "heading", "runs": [{"spk": "N", "text": clean(c.get_text()) + "."}]}
        elif c.name == "hr":
            item = {"kind": "break", "runs": []}
        elif "dateline" in cls:
            place_t, date_t = dateline(c)
            parts = [x for x in (place_t, say_date(date_t)) if x]
            item = {"kind": "dateline", "runs": [{"spk": "N", "text": ". ".join(parts) + "."}],
                    "opening": "chapter-open" in cls}
        elif c.name == "p":
            runs = para_runs(c)
            if not runs:
                continue
            item = {"kind": "para", "runs": runs}
        elif "device-view" in cls:
            item = block_item(c, "device", bid)
        elif c.name == "blockquote":
            item = block_item(c, "quote", bid)
        elif c.name == "center":
            item = block_item(c, "sign", bid)
        else:
            raise SystemExit(f"unhandled element {c.name} {cls} at {bid}")
        if bid in KEEP_LINES:
            item["runs"] = [r for r in item["runs"] if KEEP_LINES[bid](r["text"])]
        if bid in VOICE_AS:
            for r in item["runs"]:
                r["spk"] = "@" + VOICE_AS[bid]
        if item["kind"] != "break" and not item["runs"]:
            continue
        item["id"] = bid
        items.append(item)
    return items


def readable(items):
    out = []
    for it in items:
        if it["kind"] == "break":
            out.append(f"[{it['id']}] ----- scene break -----")
            continue
        tag = "" if it["kind"] == "para" else f" <{it['kind']}{' +SVG' if it.get('svg') else ''}>"
        body = " | ".join(f"{r['spk']}: {r['text']}" for r in it["runs"]) or "(nothing read)"
        out.append(f"[{it['id']}]{tag} {body}")
    return "\n".join(out) + "\n"


def main():
    (ROOT / "script" / "raw").mkdir(parents=True, exist_ok=True)
    (ROOT / "script" / "readable").mkdir(parents=True, exist_ok=True)
    total = 0
    for ch in range(1, 33):
        items = extract(ch)
        (ROOT / "script" / "raw" / f"ch{ch:02d}.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        (ROOT / "script" / "readable" / f"ch{ch:02d}.txt").write_text(readable(items), encoding="utf-8")
        total += sum(len(r["text"]) for it in items for r in it["runs"])
    print(f"extracted 32 chapters, {total:,} characters of spoken text")


if __name__ == "__main__":
    main()
