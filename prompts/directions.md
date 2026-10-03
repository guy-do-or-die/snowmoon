# Delivery directions (per block of eight chapters)

You are helping produce a multi-voice audiobook of the novel "Snowmoon" with ElevenLabs (Eleven v3/v4), which understands bracketed delivery directions in the text, e.g. `[whispers]`, `[shouting]`, `[sighs]`. Decide, for chapters N to M, which spoken lines need such a direction and which direction.

## Input
`script/readable/chNN.txt` in full. `N:` is narration; any other letter is a character's spoken line. Runs are numbered from 0 within an item, left to right.

## Output
For EACH chapter write `script/directions/chNN.json`: a JSON object mapping `"<item id>/<run index>"` to a direction string, e.g.
{"1:7/0": "[shouting] [excited]", "1:132/0": "[mumbling] [dejected]", "1:133/1": "[softly] [tender]"}

Rules:
- Only CHARACTER runs (never narration) and only where the text or the surrounding narration gives a reason. Expect to tag roughly 15-30% of character lines; an untagged line is read naturally, which is right for most dialogue.
- Reasons: an explicit speech cue in the same or adjacent narration ("shouted", "whispered", "said softly", "sighed", "laughed", "exclaimed", "mumbled", "snapped", "interjected angrily", "asked incredulously", "wryly"...); ALL-CAPS text; a clear emotional situation (fear, grief, relief, anger, tenderness, sarcasm, awe); public-address or announcer lines (`[announcing]`); lines whispered into a neck band or subvocalised (`[whispers]`).
- Vocabulary, at most two tags per line: [whispers] [shouting] [calling out] [excited] [cheerful] [laughs] [chuckles] [sighs] [sad] [dejected] [crying] [angry] [stern] [sarcastic] [wry] [nervous] [frightened] [surprised] [curious] [gently] [softly] [tender] [tired] [solemn] [urgent] [pleading] [mumbling] [amused] [announcing] [confident] [hesitant] [relieved] [awed].
- Tags go at the start of the line. If a line changes mood halfway, give the full line text with tags inserted inline, prefixed `INLINE:` — copy the line text exactly, only adding tags.
- Do not tag robots, devices, gates or notifications, except announcer/PA lines, which get [announcing].
- Valid JSON; keys must be real item ids and run indices.

## Final reply
Lines tagged per chapter and anything you were unsure about.
