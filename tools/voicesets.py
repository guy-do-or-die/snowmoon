#!/usr/bin/env python3
"""Voice casts per speech engine.

voices      name -> (engine id, "m" | "f" | "x")
principals  characters with a fixed voice for the whole book
exclusive   characters whose voice nobody else may use
device      voice for AIs, robots, gates and written notifications
"""

NARRATOR = "Narrator"

ELEVEN = {
    # ElevenLabs default voices: the only ones a key can use without the voice library.
    "voices": {
        "George": ("JBFqnCBsd6RMkjVDRZzb", "m"), "Eric": ("cjVigY5qzO86Huf0OWal", "m"),
        "Brian": ("nPczCjzI2devNBz1zQrb", "m"), "Bill": ("pqHfZKP75CvOlQylNhV4", "m"),
        "Callum": ("N2lVS1w4EtoT3dr4eOWO", "m"), "Roger": ("CwhRBWXzGAHq8TQ4Fs17", "m"),
        "Chris": ("iP95p4xoKVk53GoZ742B", "m"), "Liam": ("TX3LPaxmHKxFdv7VOQHJ", "m"),
        "Will": ("bIHbv24MWmeRgasZH58o", "m"), "Charlie": ("IKne3meq5aSn9XLyUdCD", "m"),
        "Daniel": ("onwK4e9ZLuTAKqWW03F9", "m"), "Adam": ("pNInz6obpgDQGcFmaJgB", "m"),
        "Antoni": ("ErXwobaYiN019PkySvjV", "m"), "Arnold": ("VR6AewLTigWG4xSOukaG", "m"),
        "Sarah": ("EXAVITQu4vr4xnSDxMaL", "f"), "Jessica": ("cgSgspJ2msm6clMCkdW9", "f"),
        "Alice": ("Xb7hH8MSUJpSbSDYk0k2", "f"), "Matilda": ("XrExE9yKIg1WjnnlVkGX", "f"),
        "Laura": ("FGY2WhTYpPnrIDTdsKH5", "f"), "Lily": ("pFZP5JQG7iQjIQuC4Bku", "f"),
        "River": ("SAz9YHcvj6GT2YYXdXww", "x"),
        # voices added from the ElevenLabs library (script/library_voices.json)
        "JohnnyKid": ("8JVbfL6oEdmuxKn5DK2C", "m"), "TeddyTwinkle": ("XjGYkUkzth8BPs29fmcV", "m"),
        "Isabel": ("RwZADRjd8b3vxKTsTtLP", "f"), "Emmaline": ("nDJIICjR9zfJExIFeSCN", "f"),
        "Brayden": ("3XOBzXhnDY98yeWQ3GdM", "m"), "DavidTeacher": ("7EgG6hUPTRSnBBfZN5tp", "m"),
        "Rob": ("mkZwO4JCm0yEo6WmjZjA", "m"), "Arthur": ("sfJopaWaOtauCD3HKX6Q", "m"),
        "Boyd": ("gfRt6Z3Z8aTbpLfexQ7N", "m"), "JerryB": ("TxWZERZ5Hc6h9dGxVmXa", "m"),
        "Beth": ("8N2ng9i2uiUWqstgmWlH", "f"), "Tammy": ("TDdaEMZGTCMRB4x8bVQ2", "f"),
        # narrator candidates (Canadian)
        "AdamCalm": ("W78pxv1enhu0qj6t6IaC", "m"), "Loyal": ("mI8xLTBNjMXAf31I4xlB", "m"),
    },
    "principals": {
        NARRATOR: "AdamCalm",  # Canadian, like the author; George was the first try
        "Zei": "Liam", "Gladias": "Eric", "Seila": "Sarah", "Verdow": "Bill", "Den": "Brian",
        "Fin": "Will", "Bai": "Jessica", "Mov": "Callum", "Deluin": "Charlie", "Mu": "Alice",
        "Jahn": "Chris", "Delwart": "Roger", "Anonymous": "Roger",  # Anonymous turns out to be Delwart
        "Ephelion": "Daniel", "news reporter": "Daniel", "flight announcer": "Matilda", "Jin": "Daniel",
        "Utaku": "Lily",
        "Zven": "JohnnyKid", "boy with drone": "TeddyTwinkle", "Lily": "Isabel", "Hreda": "Emmaline",
        "Febric": "Brayden", "physics instructor": "DavidTeacher", "Belgor": "Rob", "Evelor": "Arthur",
        "Vil": "Boyd", "Lektor": "JerryB", "Su": "Beth", "Daia": "Tammy",
    },
    "exclusive": [NARRATOR, "Zei", "Gladias", "Seila", "Utaku", "Zven", "boy with drone", "Lily", "Hreda",
                  "Febric", "physics instructor", "Belgor", "Evelor", "Vil", "Lektor", "Su", "Daia"],
    "device": "River",
}

KOKORO = {
    # Kokoro-82M v1.0 English voices (a = American, b = British; f/m).
    # af_nicole (whispered) and am_santa (novelty) are left out on purpose.
    "voices": {
        "af_heart": ("af_heart", "f"), "af_bella": ("af_bella", "f"), "af_aoede": ("af_aoede", "f"),
        "af_kore": ("af_kore", "f"), "af_sarah": ("af_sarah", "f"), "af_nova": ("af_nova", "f"),
        "af_sky": ("af_sky", "f"), "af_jessica": ("af_jessica", "f"), "af_river": ("af_river", "f"),
        "bf_emma": ("bf_emma", "f"), "bf_isabella": ("bf_isabella", "f"), "bf_alice": ("bf_alice", "f"),
        "bf_lily": ("bf_lily", "f"),
        "am_michael": ("am_michael", "m"), "am_fenrir": ("am_fenrir", "m"), "am_puck": ("am_puck", "m"),
        "am_echo": ("am_echo", "m"), "am_eric": ("am_eric", "m"), "am_liam": ("am_liam", "m"),
        "am_onyx": ("am_onyx", "m"), "am_adam": ("am_adam", "m"),
        "bm_george": ("bm_george", "m"), "bm_fable": ("bm_fable", "m"), "bm_lewis": ("bm_lewis", "m"),
        "bm_daniel": ("bm_daniel", "m"),
        "af_alloy": ("af_alloy", "x"),
    },
    "principals": {
        NARRATOR: "af_heart",
        "Zei": "am_puck", "Gladias": "am_michael", "Seila": "af_bella", "Verdow": "bm_george",
        "Den": "am_fenrir", "Fin": "am_liam", "Bai": "af_kore", "Mov": "am_onyx", "Deluin": "bm_fable",
        "Mu": "bf_emma", "Jahn": "am_eric", "Delwart": "bm_lewis", "Anonymous": "bm_lewis",
        "Ephelion": "bm_daniel", "Zven": "af_sky", "news reporter": "bm_daniel",
        "flight announcer": "bf_isabella",
    },
    "exclusive": [NARRATOR, "Zei", "Gladias", "Seila"],
    "device": "af_alloy",
}

ENGINES = {"eleven": ELEVEN, "kokoro": KOKORO}
