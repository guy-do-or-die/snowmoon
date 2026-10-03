#!/usr/bin/env python3
"""Hand-made decisions for blocks that cannot be read aloud as they stand
(diagrams, game boards, hex keys, on-screen controls).

Keys are "<chapter>:<element index>", as shown in script/readable.

OVERRIDES   None = read nothing; otherwise a list of (speaker, text) runs that
            replaces the default reading. Speaker is "N" (narrator), a letter
            (resolved through the chapter cast) or "@Name" (a cast member).
VOICE_AS    read the whole block in this character's voice (letters, screeds).
KEEP_LINES  filter for the default reading's lines.
"""

OVERRIDES = {
    # ch1 - voting screen: read the content, not the slider and buttons
    "1:20": [("N", "Vote on: Badra Street, number 1103."),
             ("N", "Emerald AI summary: Five-storey apartment building. Blue-grey colored."),
             ("N", "A slider from minus 5 to 5, and a Select button.")],
    "1:39": [("N", "The same screen: the slider from minus 5 to 5, and the Select button.")],
    # ch2 - class location notification (Dzegoban labels, yellow checkmark)
    "2:26": [("N", "mun gui 1842. tei 70,000.")],
    # ch5 - hotel check-in
    "5:24": [("N", "Reputation score at least 100, verified. Payment successful."),
             ("N", "Checked in. Your room numbers are: 714, 715, 716.")],
    # ch6 - loan request (nullifier hex omitted)
    "6:140": [("N", "Reputation-backed loan request."),
              ("N", "Work history: teaching assistant. Positive review from the professor and 5 students."),
              ("N", "Nullifier: a hexadecimal code, zero x one eight f four, ending six zero c five."),
              ("N", "Requested loan: 2773 zipcoins. A Submit button.")],
    "6:146": [("N", "Payment succeeded. Base: 10.5 zipcoins. Tax: 1.1 zipcoins. Total: 11.6 zipcoins.")],
    # ch7 - the robot's rating screen repeats the question it just asked aloud
    "7:8": [("N", "A slider from very unhappy to very happy, and a Select button.")],
    # ch12 / ch18 - hotel check-in screens in Dzegoban
    "12:38": [("N", "sen hen zi li die fe 150, zo lia kin. man dun li jie hu."),
              ("N", "cau tie zen. ci fan zi li 304.")],
    "18:51": [("N", "sen hen zi li die fe 100, zo lia kin. man dun li jie hu."),
              ("N", "cau tie zen. ci fan zi li 448.")],
    # ch17 - the three motions; Gladias then answers them in order
    "17:119": [("N", "Rubric: openness in hardware."),
               ("N", "First motion. Add after line 3 in Tier 1 and line 3 in Tier 2: Products in military, "
                     "surveillance and counter-surveillance applications are not eligible for this tier."),
               ("N", "Second motion. Increase tax brackets from 0, 6, 12, 18, 24, to 0, 10, 20, 26, 32."),
               ("N", "Third motion. Change line 4 in Tier 4 and line 4 in Tier 5, from: Use of hardware means "
                     "to prevent third-party repair. To: Use of hardware or software means to prevent "
                     "third-party repair."),
               ("N", "Each motion has Yes and No buttons.")],
    "19:162": [("N", "Thinking... estimated remaining time: 440.")],
    # ch22 - taxi fare breakdown
    "22:13": [("N", "Taxi fare. Driver base fare: 3.69. Per-minute toll, 9 minutes: 1.89. "
                    "Per-kilometer toll, 5.65 kilometers: 1.26. Acceleration and deceleration toll, "
                    "113 meters per second delta-v: 1.03. Road congestion tolls: 1.50, 1.00, and 2.25. "
                    "Total: 12.52.")],
}

VOICE_AS = {
    "3:7": "Ephelion",     # Lord Ephelion's poster
    "13:68": "Ephelion",   # Lord Ephelion's on-screen screed
    "19:175": "Deluin",    # Deluin's letter
    "29:129": "Deluin",
    "30:6": "Deluin",
    "30:33": "Deluin",
    "30:69": "Deluin",
}

KEEP_LINES = {
    # ch23 - a full page of a Dzegoban book: read the opening lines only,
    # Gladias then translates it line by line
    "23:23": lambda text, _seen=[]: (_seen.append(text) or len(_seen) <= 3),
}
