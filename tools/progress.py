#!/usr/bin/env python3
"""How much of the book has been voiced: counts cached clips against the final script.

  progress.py            one-line summary
  progress.py --wait 50  block until at least 50 % is voiced (or the run stops), then print
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import pronounce  # noqa: E402

CLIPS = Path.home() / ".cache" / "snowmoon-audiobook" / "clips"
SPEED = 1.0
FORCE_DZEGOBAN = {"19:43"}


def lines():
    """(chapter, characters, clip path) for every spoken line; same cache key as synth_kokoro.py."""
    for ch in range(1, 33):
        for u in json.loads((ROOT / "script" / "final" / f"ch{ch:02d}.json").read_text()):
            if "text" in u:
                marked = pronounce.mark(u["text"], force=u["id"] in FORCE_DZEGOBAN)
                key = hashlib.sha1(f"kokoro-1.0|{u['voice']}|{SPEED}|{marked}".encode()).hexdigest()
                yield ch, len(u["text"]), CLIPS / key[:2] / f"{key}.flac"


ALL = list(lines())


def running():
    return subprocess.run(["pgrep", "-fc", "synth_kokor[o]"], capture_output=True, text=True).stdout.strip() not in ("", "0")


def snapshot():
    total = sum(n for _, n, _ in ALL)
    done = sum(n for _, n, p in ALL if p.exists())
    per = {}
    for ch, n, p in ALL:
        d, t = per.get(ch, (0, 0))
        per[ch] = (d + (n if p.exists() else 0), t + n)
    complete = [ch for ch, (d, t) in per.items() if d == t]
    current = next((ch for ch, (d, t) in sorted(per.items()) if d < t), None)
    return done, total, complete, current


def eta(done, total):
    """Rate since the last 'start' line in the run log."""
    log = ROOT / "audio" / "work" / "run.log"
    starts = re.findall(r"^(\S+ \S+) start", log.read_text(), re.M) if log.exists() else []
    mark = ROOT / "audio" / "work" / "progress_mark.json"
    if not starts:
        return None
    began = datetime.strptime(starts[-1], "%Y-%m-%d %H:%M:%S")
    base = json.loads(mark.read_text()) if mark.exists() else {}
    if base.get("start") != starts[-1]:
        base = {"start": starts[-1], "done": done}  # characters already cached when this run began
        mark.write_text(json.dumps(base))
    gained, elapsed = done - base["done"], (datetime.now() - began).total_seconds()
    if gained < 3000 or elapsed < 120:
        return None
    return datetime.now() + timedelta(seconds=(total - done) * elapsed / gained)


def report():
    done, total, complete, current = snapshot()
    when = eta(done, total)
    state = "running" if running() else "NOT running"
    msg = f"{100 * done / total:.1f}% voiced | chapters finished: {len(complete)}/32 | working on: " \
          f"{'chapter ' + str(current) if current else 'assembly'} | {state}"
    if when and current:
        msg += f" | estimated finish {when:%H:%M}"
    return msg, 100 * done / total


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--wait":
        target = float(sys.argv[2])
        eta(*snapshot()[:2])
        while True:
            msg, pct = report()
            if pct >= target or not running():
                break
            time.sleep(60)
        print(msg)
    else:
        print(report()[0])
