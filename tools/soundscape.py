#!/usr/bin/env python3
"""The sound palette: ambience beds, spot effects and music cues, generated once with
ElevenLabs (sound effects + music APIs) and cached under audio/sfx/.

Beds play quietly under the first ~25 s of a scene and fade out; spot effects play
once where the narration names the event; music opens chapters.

  soundscape.py            generate anything missing from the palette
  soundscape.py --list     show the palette
"""
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import eleven  # noqa: E402

SFX_DIR = ROOT / "audio" / "sfx"
RATE = 24000

# name: (prompt, seconds, loop)
BEDS = {
    "forest_path": ("quiet forest path ambience, birdsong, light breeze in leaves, distant soft footsteps, peaceful", 22, True),
    "city_street": ("calm futuristic city street ambience, quiet electric vehicles passing, distant pedestrians, light wind, no horns", 22, True),
    "concert_crowd": ("large outdoor concert crowd ambience, cheering and chatter, distant muffled heavy rock music, night air", 22, True),
    "classroom": ("quiet lecture room ambience, faint murmur of students, chair creaks, a pen on paper", 22, True),
    "restaurant": ("small restaurant ambience, soft chatter, cutlery and cups, a kitchen in the background", 22, True),
    "stadium_crowd": ("indoor arena crowd ambience, thousands of people murmuring, occasional cheer, large hall reverb", 22, True),
    "home_interior": ("quiet family home interior ambience, distant kitchen sounds, a clock ticking, soft hum", 22, True),
    "aircraft_cabin": ("aircraft cabin ambience, steady engine hum, soft air vents, calm", 22, True),
    "winter_wind": ("cold winter wind over snow, soft gusts, distant trees creaking, sparse and lonely", 22, True),
    "library": ("very quiet library ambience, pages turning, a distant footstep on a wooden floor, soft hum", 22, True),
    "war_room": ("military operations room ambience, soft electronic beeps, radio static, keyboards, low tense hum", 22, True),
    "battlefield_distant": ("distant drone warfare ambience, far-off explosions, buzzing drone swarms, wind, snow, tense", 22, True),
    "vehicle_interior": ("inside a smooth electric car on a highway, tyre hum, gentle wind noise, calm", 22, True),
    "rain": ("steady rain on a window and street, soft thunder far away, calm", 22, True),
}

SPOTS = {
    "watch_buzz": ("short double vibration buzz of a smartwatch on a wrist, subtle, close", 1.5, False),
    "drones_flyby": ("small quadcopter drone flying past overhead, soft electric rotor whir, quiet outdoors", 4, False),
    "door_knock": ("three firm knocks on a wooden house door, interior", 2, False),
    "door_open": ("a house door unlocking and opening, then closing softly", 3, False),
    "alarm": ("urgent electronic alarm tone in an operations room, three sharp beeps", 2.5, False),
    "crowd_cheer": ("large indoor crowd erupting in cheers and applause, arena", 5, False),
    "explosion_distant": ("single distant explosion, deep rumble, snow and wind, far away", 4, False),
    "data_transfer": ("fast digital data transfer sound, soft modem-like ticks and chirps, brief, clean, futuristic", 2.5, False),
    "footsteps_stairs": ("a child running down wooden stairs fast, indoor", 3, False),
    "crowd_gasp": ("a large audience gasping in surprise then murmuring, indoor hall", 3, False),
}

MUSIC = {
    "theme_A_granular": ("abstract futuristic ambient: slowly evolving granular synth textures, glassy harmonics, "
                         "soft digital shimmer, cold and spacious, no piano, no drums, no melody, minimal, "
                         "cinematic science fiction, instrumental", 24000),
    "theme_B_subpulse": ("minimal electronic soundscape: deep slow sub-bass pulse, sparse crystalline modular synth "
                         "blips, airy mysterious atmosphere, science fiction, no piano, no drums, no melody, "
                         "instrumental", 24000),
    "theme_C_icy": ("ethereal icy synth pad with slow filter sweeps and reversed textures, faint vocoder-like "
                    "harmonics, serene and quietly hopeful, modern and abstract, no piano, no percussion, "
                    "no melody, instrumental", 24000),
    "ending_theme": ("abstract ethereal synth pad slowly resolving into warmth, glassy granular textures, faint "
                     "sub-bass, serene and quietly hopeful, a gentle ending, modern science fiction, no piano, "
                     "no drums, no melody, instrumental", 40000),
}


def _headers():
    return {"xi-api-key": eleven._key()}


def generate(name):
    out = SFX_DIR / f"{name}.flac"
    if out.exists():
        return out
    SFX_DIR.mkdir(parents=True, exist_ok=True)
    mp3 = SFX_DIR / f"{name}.mp3"
    for attempt in range(3):
        if name in MUSIC:
            prompt, ms = MUSIC[name]
            r = requests.post(f"{eleven.BASE}/v1/music", headers=_headers(),
                              json={"prompt": prompt, "music_length_ms": ms}, timeout=600)
        else:
            prompt, secs, loop = {**BEDS, **SPOTS}[name]
            r = requests.post(f"{eleven.BASE}/v1/sound-generation", headers=_headers(),
                              json={"text": prompt, "duration_seconds": secs, "loop": loop, "prompt_influence": 0.5},
                              timeout=300)
        if r.ok:
            mp3.write_bytes(r.content)
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"{name}: {r.status_code} {r.text[:200]}")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", str(RATE), str(out)], check=True)
    return out


if __name__ == "__main__":
    if "--list" in sys.argv:
        for group, table in (("beds", BEDS), ("spots", SPOTS), ("music", MUSIC)):
            print(group + ":", ", ".join(table))
        sys.exit()
    for name in [*MUSIC, *BEDS, *SPOTS]:
        path = generate(name)
        print(name, "->", path.name)
