# Cast resolution (per block of eight chapters)

You are helping produce a multi-voice audiobook of the novel "Snowmoon". Your job: work out WHO SPEAKS each line of dialogue in chapters N to M, so each character can be given a consistent voice.

## Input
Read `script/readable/chNN.txt` for the chapters in full, in order. Line format: `[<chapter>:<n>] <optional <kind>> RUN | RUN | ...` where each RUN is `X: text`.
- `N:` is narration.
- A capital letter other than N is a spoken line or a written message. The book colour-codes speech by the FIRST LETTER of the speaker's name or label, so `G:` is someone whose name/label starts with G, `M:` could be "Mov", "Mu" or an unnamed "machine", `I:` "instructor", `R:` "robot", `W:` "woman", `T:` could be numbered people like "Twenty"/"Thirteen". The letter is the only hint in the markup; most lines have no "said X", so work out the speaker from context (who is in the scene, turn-taking, content).
- If an `N:` run is clearly spoken dialogue by a character whose name starts with N (e.g. a numbered person called "Nine"), list it in `narrator_exceptions`.

## Output
For EACH chapter write `script/cast/chNN.json`:

{
  "chapter": 1,
  "characters": [
    {"name": "Gladias", "letter": "G", "gender": "male", "age": "adult, about 30", "kind": "human",
     "origin": "Veridia", "voice_notes": "thoughtful, calm; protagonist of the Veridia chapters"}
  ],
  "letters": {"G": "Gladias", "S": "Seila"},
  "exceptions": [{"id": "1:45", "letter": "M", "speaker": "ticket machine"}],
  "narrator_exceptions": [{"id": "10:33", "run": 0, "speaker": "Nine"}],
  "notes": "anything I should know, e.g. lines you could not attribute with confidence (give ids)"
}

Rules:
- `characters`: every distinct speaker in the chapter, including unnamed ones (short descriptive labels). Use the name exactly as the book spells it. `gender`: male / female / unknown / none (machines). `age`: child / teen / young adult / adult / elderly plus specifics. `kind`: human / ai / robot / device / announcer / crowd / written. `origin`: nation or city if known. `voice_notes`: personality, manner of speaking, role, relationships — a sentence or two.
- `letters`: for each letter that appears as a speaker in the chapter, the character who speaks MOST of that letter's lines.
- `exceptions`: every item where a letter's run is spoken by someone OTHER than that letter's default. If one item has two runs with the same letter by different speakers, add "run": <0-based index>.
- Be exhaustive on exceptions: check every lettered run. Letters shared by two characters in the same scene are where mistakes happen.
- Do not paraphrase or copy the book's text into the JSON beyond names/labels. Valid JSON; every speaker must match a `name` in `characters`.

## Final reply
A compact cross-chapter cast summary (name, letter, gender, age, kind, origin, chapters, one-line voice note) and any attributions you are unsure about.
