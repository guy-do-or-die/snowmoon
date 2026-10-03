# Prompts and harness

The three annotation passes over the book were done by reading each chapter with an LLM
(Claude, four parallel agents of eight chapters each) and checking the output mechanically
against the script. These are the briefs, verbatim apart from the local file paths.

- `cast.md` — who speaks each lettered line (→ `script/cast/chNN.json`)
- `directions.md` — delivery directions per line, from a fixed vocabulary (→ `script/directions/chNN.json`)
- `scenes.md` — ambience per scene and spot sounds (→ `script/scenes/chNN.json`)
- `review-video-pipeline.workflow.js` — the adversarial code review run before the video render
  (three reviewers by dimension, two verifiers per finding, one of them told to refute it)

Everything else (speaker letters, speakable text, chunking, mixing, alignment, rendering) is
deterministic code in `tools/`.
