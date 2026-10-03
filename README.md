# Snowmoon — audiobook pipeline

The pipeline that turned *Snowmoon* (https://vitalik.eth.limo/snowmoon, a novel by Vitalik Buterin,
32 chapters, ~104,000 words) into a full-cast audiobook and a video: one narrator, a voice per
character, delivery directions per line, scene ambience, spot sounds, music cues, the book's
figures and screens on the timeline, word-synced captions.

The novel is GPL v3, and its author asks that adaptations publish their pipeline. This is it,
under the same licence. Pipeline: Copyright (C) 2026 guy-do-or-die, GNU GPL v3 (see `LICENSE`,
`NOTICE.md`). The audiobook and the video are published on YouTube.

## Setup

```bash
uv venv --python 3.12 ~/.cache/snowmoon-audiobook/venv
source ~/.cache/snowmoon-audiobook/venv/bin/activate
uv pip install torch --index-url https://download.pytorch.org/whl/cpu    # only for the Kokoro path
uv pip install "kokoro>=0.9.4" "transformers>=4.45" soundfile requests numpy pillow beautifulsoup4 lxml
```

Also needed: `ffmpeg`, `inkscape` (figures), `chromium` (screens), and for the video the fonts referenced at the top of
`tools/video.py` (Noto Sans Mono, Liberation Mono, DejaVu Serif from your distribution; Inter from
https://rsms.me/inter) — or edit those paths.

ElevenLabs: an API key in `~/.config/elevenlabs/api_key` with text-to-speech, voices (read/write),
user (read), speech-to-text (forced alignment), sound generation and music enabled; a plan that
allows 192 kbps output (Creator or above — or set `OUTPUT_FORMAT` in `tools/eleven.py` to
`mp3_44100_128`); and the voice-library voices in `script/library_voices.json` added to the account
(library voice ids are the same in every account). Costs on the plan used (October 2026): the whole
book came to ~48k credits for speech with Eleven v4 (about 0.13 credits per character), ~5k for
sound effects; forced alignment and music did not count against the quota. Run
`tools/synth_eleven.py --chapters 1-32 --dry-run` before spending.

## Steps

| # | Command | Result |
|---|---|---|
| 1 | `tools/extract.py` | `source/html` → `script/raw` + `script/readable`: narration split from speech; screens, tables, signs, charts and diagrams given a spoken form |
| 2 | `tools/build.py --engine eleven` | every line resolved to a character (`script/cast`) and a voice (`tools/voicesets.py`), text made speakable, credits added → `script/final`, `script/voices.json` |
| 3 | `tools/synth_eleven.py --chapters 1-32` | speech via the Text to Dialogue API with the directions from `script/directions` → cached clips, `audio/work/chNN.json` (after a text change, `--keep-chunks` regenerates only the chunk that changed) |
| 4 | `tools/soundscape.py` | ambience beds, spot effects and music cues → `audio/sfx` |
| 5 | `tools/assemble.py --chapters 1-32 --out eleven` | clips joined with pauses, voices levelled, ambience (`script/scenes`), spot sounds, music, device/PA effects, loudness mastered → `audio/eleven/*.m4a`, `audio/Snowmoon-eleven.m4b`, `audio/work/timeline_chNN.json` (`--plain`: voices only) |
| 6 | `tools/align.py --chapters 1-32` | word timestamps per clip (forced alignment), mapped to lines and speakers → `audio/work/words_chNN.json` |
| 7 | `tools/figures.py`, `tools/screens.py` | the book's inline SVG figures → `audio/figures` (inkscape; an animated figure is photographed mid-animation in Chromium); its device screens, messages, signs and quotes rendered with its own CSS in headless Chromium → `audio/screens` |
| 8 | `tools/video.py --chapters 1-32` then `--join` | per-chapter videos with audio, `audio/Snowmoon.mp4`, `audio/youtube_chapters.txt` (`--preview 40 --start 600`: 40 s of a chapter from 10:00) |
| 9 | `tools/subtitles.py` | `audio/Snowmoon.srt` for the joined video, from the aligned words |
| 10 | `tools/teaser.py` | a teaser cut from the chapter videos along the beats in `script/teaser_plan.json` (spans of lines, word-timed, with a music bed per run) → `audio/samples/Snowmoon - teaser.mp4` |

Every step is cached or resumable; re-running regenerates only what changed.

Free local alternative to step 3: `tools/build.py --engine kokoro`, then `tools/run_kokoro.sh 1-32`
(Kokoro-82M on CPU; voices and assembles into `audio/book`). It reads evenly and cannot act, which is
why ElevenLabs was used for the published edition.

## How the annotations were made

The page colours each spoken line by the first letter of the speaker's name and most lines have no
"said X". `extract.py` recovers that letter; `script/cast/chNN.json` records, per chapter, which
character each letter is and every exception. `script/directions/chNN.json` holds a delivery direction
for ~28% of character lines (whispered neck-band calls, shouts, sighs, moods); `script/scenes/chNN.json`
the ambience per scene and the spot sounds. All three were produced by reading each chapter with an
LLM (Claude) using the briefs in `prompts/`, and checked mechanically: every lettered line resolves to
a listed character, every direction and spot points at a real line, every tag is from the fixed
vocabulary.

## Cast

`script/voices.json` (generated) lists every speaker with voice, gender, age, origin and notes. Leads
and recurring secondary characters have voices of their own (ElevenLabs default voices plus the
library voices in `script/library_voices.json`); one-scene extras share voices, never two in the same
chapter. Devices, robots and AIs get a band-limited "electronic" treatment; announcers and the news
reader a public-address echo. The narrator is a Canadian voice, as a nod to the author.

## Adaptation choices

Nothing in the prose or dialogue is reworded. Where the page shows something that cannot be read as
written, the narrator gets a short line written for the purpose; every such line is in
`tools/descriptions.py`, `tools/overrides.py` or `tools/extract.py`, with its reason:

- **Diagrams, maps, charts, game boards**: one narrator line each, written from the rendered images
  (48 of 56 figures; boards that only repeat what the prose then says in numbers stay silent). Pie
  charts are read from the text alternative in the page.
- **Device screens**: content read; controls get one line ("A slider from minus 5 to 5, and a Select
  button"). Messages become "Message from X, at <time>:" with a watch buzz, read in the sender's voice.
- **Tables** are read row by row with their labels.
- **Hex keys and hashes** are not read; a note says what was there, and a data-transfer sound marks the spot.
- **Letters and posters** signed by a character are read in that character's voice.
- **Dzegoban** (the invented language) is read aloud, as the text nearly always translates it right
  after; the one full page of it (chapter 23) is cut to its first three lines. There is no
  pronunciation guide in the book; `tools/pronounce.py` documents the reading chosen for Kokoro.
- Unison shouts are read by the narrator. The author's declarations from the index page are read as
  end credits.

## The video edition

Everything on screen is taken from the page: its dark-mode gradient and body grey, the h1 with its
purple underline, the small-caps dateline, and speech colours computed with the page's own formula
(oklch 0.7 0.15, hue from the speaker's initial). Device screens, messages, signs and quotes are the
page's own rendering (step 7); only screens too tall to read as an image fall back to paginated text
in the page's console style. The one thing that is ours is the automaton: Conway's Life in the page's
glyphs, fed with gliders — a nod to Minpentai, the book's Life-like game. Its colour, density and pace
follow the scene (`script/scenes`: a forest path is slow and green, a stadium quick and warm, a
battlefield restless and red) and pulse with the delivery directions (a shouted line stirs it, a
whisper calms it). Captions light each word as it is spoken.

## Files

- `source/html` — the chapter pages as downloaded (2026-10-02)
- `script/cast`, `script/directions`, `script/scenes` — the annotation sets; `script/library_voices.json` — the ElevenLabs library voices used. `script/raw`, `script/readable`, `script/final`, `script/voices.json` are regenerated by steps 1–2.
- `tools/` — the pipeline; `prompts/` — the annotation briefs and the review harness
- `audio/` — outputs and caches, not committed
