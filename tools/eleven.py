#!/usr/bin/env python3
"""Thin ElevenLabs client with an on-disk cache, so nothing is ever paid for twice.

The API key is read from ~/.config/elevenlabs/api_key (or $ELEVENLABS_API_KEY).
Every generated clip is stored under audio/cache/<sha1>.mp3, keyed by everything
that affects the sound (endpoint, model, voices, text, settings, context).
"""
import hashlib
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "audio" / "cache"
LEDGER = ROOT / "audio" / "spend.jsonl"
BASE = "https://api.elevenlabs.io"
OUTPUT_FORMAT = "mp3_44100_128"


class QuotaError(RuntimeError):
    pass


def _key():
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        key = (Path.home() / ".config" / "elevenlabs" / "api_key").read_text().strip()
    return key


def _cached(payload_id):
    digest = hashlib.sha1(json.dumps(payload_id, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return CACHE / f"{digest}.mp3"


def _post(path, body, chars, retries=4):
    url = f"{BASE}{path}?output_format={OUTPUT_FORMAT}"
    for attempt in range(retries):
        r = requests.post(url, headers={"xi-api-key": _key()}, json=body, timeout=300)
        if r.ok and r.headers.get("content-type", "").startswith("audio"):
            LEDGER.parent.mkdir(parents=True, exist_ok=True)
            with LEDGER.open("a") as f:
                f.write(json.dumps({"t": int(time.time()), "path": path, "chars": chars,
                                    "billed": r.headers.get("character-cost"),
                                    "request_id": r.headers.get("request-id")}) + "\n")
            return r.content
        detail = r.text[:400]
        if r.status_code in (401, 402) or "quota" in detail:
            raise QuotaError(f"{r.status_code}: {detail}")
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
            time.sleep(5 * (attempt + 1))
            continue
        raise RuntimeError(f"{r.status_code}: {detail}")


def speak(text, voice_id, model, settings=None, previous_text=None, next_text=None):
    """One voice, one clip (text-to-speech endpoint)."""
    ident = {"kind": "tts", "model": model, "voice": voice_id, "text": text,
             "settings": settings, "prev": previous_text, "next": next_text}
    out = _cached(ident)
    if out.exists():
        return out
    body = {"text": text, "model_id": model}
    if settings:
        body["voice_settings"] = settings
    if previous_text:
        body["previous_text"] = previous_text
    if next_text:
        body["next_text"] = next_text
    audio = _post(f"/v1/text-to-speech/{voice_id}", body, len(text))
    CACHE.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    return out


def dialogue(turns, model="eleven_v3", settings=None, seed=None):
    """Several voices in one clip (text-to-dialogue endpoint).

    turns: list of (voice_id, text); at most 10 distinct voices and 2,000 characters.
    """
    ident = {"kind": "dialogue", "model": model, "turns": turns, "settings": settings, "seed": seed}
    out = _cached(ident)
    if out.exists():
        return out
    body = {"inputs": [{"voice_id": v, "text": t} for v, t in turns], "model_id": model}
    if settings:
        body["settings"] = settings
    if seed is not None:
        body["seed"] = seed
    audio = _post("/v1/text-to-dialogue", body, sum(len(t) for _, t in turns))
    CACHE.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    return out
