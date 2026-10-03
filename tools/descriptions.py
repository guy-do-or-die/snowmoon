#!/usr/bin/env python3
"""Spoken descriptions of the book's diagrams, maps and game boards.

The page shows these as SVG; a listener gets one short narrator line saying what
the picture shows. Written from the rendered images (see README). Boards that
only repeat what the prose then says in numbers are left silent.
"""

DESCRIPTIONS = {
    "1:79": "A chart on the screen: his prediction score over the past two years, climbing from the high "
            "seventies to ninety-two, just above a dashed line at ninety.",
    "2:59": "A slide: two jars of gas, a million molecules each. In the left jar the velocities run from zero "
            "to 999,999; in the right, from zero to 99.",
    "2:77": "Next slide: a single jar of two million molecules, velocities from zero to 499,999.",
    "3:139": "A map on his watch: his own position, and Mov's, moving away down the street.",
    "4:7": "An animation of a game field: four kinds of symbols, triangles, pluses, circles and squares, "
           "scattered across it.",
    "4:25": "A menu of four pictures: a cup, a leaf, a cow and a fish, labelled ja, kai, bau and lui.",
    "4:29": "A diagram: lettuce, oil, nuts, tomato and avocado, each with its Dzegoban name, combining into "
            "a bowl labelled kai can.",
    "4:125": "The summary view: four players' symbols spread over the field, triangles, pluses, circles and squares.",
    "4:149": "The field again: the pluses are gone; three players' symbols remain.",
    "5:50": "A diagram of the United Cities: Silverbeach, Mabuli, Inglewore, Hapton, Imber, Arturia, Deplexi, "
            "Freetown, Redshire, Petersvil, Devanvil, Ondak, Iptak, Mantak and Belpaki, joined by arrows "
            "marked five, ten or fifteen.",
    "6:42": "A diagram: from all Keepers, random selection draws the current Keepers for this rubric, those "
            "added this year, last year and the year before, and random selection again splits them into "
            "three discussion groups.",
    "7:90": "The board as the audience sees it: circles across the north, squares across the south.",
    "8:102": "The screen: twenty votes in a ring, ten green and ten red.",
    "8:108": "The ring again, with a green dot in the centre: the Chairman's vote.",
    "9:114": "A diagram: four computers at the top, three layers of nodes beneath them, lines crossing "
             "between every layer.",
    "12:54": "A diagram titled tun bia zi sin de sia: a row of bits at the top feeding into nine boxes "
             "labelled fai hie, lines crossing between the rows, and a single output at the bottom.",
    "12:198": "The board, a hexagon this time: circles at the top, squares at the bottom.",
    "14:54": "The audience's view: five shrines marked as triangles, centre, north, south, east and west, "
             "with circles and squares scattered between them.",
    "14:88": "Only two symbols left in view: a square by the north shrine and a circle by the south one.",
    "14:118": "A menu: a cup, a leaf, a cow and a fish.",
    "17:58": "A diagram: Airborne disease resistance at the centre, branching into Air quality, Early "
             "detection, Treatment, Individual non-pharmaceutical prevention and Prophylactics, each edge "
             "marked with a percentage, and branching again into Ventilation, Filtration, Ultraviolet light, "
             "Wastewater scanning and more.",
    "17:79": "Zoomed in: Ultraviolet light splits into 222-nanometre lamp efficiency, 222-nanometre safety "
             "testing, upper-room deployment, krypton chloride lamps and research into alternative lamp "
             "designs, each with its percentage, down to named research groups.",
    "19:40": "An envelope icon, and the words:",
    "19:115": "A download screen: eight sources, each identified by a long hexadecimal address, each "
              "contributing between one and three percent, and a counter in Dzegoban.",
    "22:85": "A view: six pale circles in a ring across a field marked with faint dashes, and a red square "
             "with a short trail near the bottom edge.",
    "22:94": "The red square has moved to the centre of the ring.",
    "22:100": "A red X beside the square, and small triangles entering from the south.",
    "22:107": "Two triangles close on the square from the north; a third approaches.",
    "22:120": "Three X marks now, and more red squares entering from the south-east.",
    "22:140": "A closer view: nine X marks, every red square crossed out, the circles intact.",
    "25:5": "Four boxes of circles: three in the top left, four in the top right, ten in the bottom left, "
            "thirteen in the bottom right.",
    "25:13": "The top left box is down to two.",
    "25:17": "The bottom right is down to twelve.",
    "25:21": "The bottom left: seven.",
    "25:25": "The bottom right: one.",
    "25:30": "Two circles remain: one in the top right, one in the bottom right.",
    "26:104": "The screen: three of his drones in the lower left with their trails, a building marked at "
              "the upper right, and a dark yellow triangle beside it.",
    "26:118": "Nine drones spread across the screen in formation; three are marked with a red X.",
    "26:134": "Three drones left near the building, two yellow checkmarks beside it, one more drone "
              "crossed out behind.",
    "26:146": "A close view: two drones with their trails beside the road into the residence, and two checkmarks.",
    "29:36": "A map: the coast and the sea, Northglade on the shore; four Veridian groups, North, Center, "
             "South and Naval, with their planned routes marked toward it.",
    "29:62": "The map: red markers appearing against Group North's flank.",
    "29:73": "A close view: a chain of red Arctic markers facing a line of Veridian ones, and three more "
             "Veridian markers coming up from the south.",
    "29:81": "The lines have mixed: Veridian markers in among the red ones.",
    "29:87": "The wide map again: Group North facing the red markers, the other groups advancing toward Northglade.",
    "29:92": "The map: red markers pressing on Group Center and Group South, close to Northglade.",
    "30:55": "The map: Veridian markers pushing through the red ones, the front dissolving into a scatter of both.",
    "30:80": "The map: the Veridian markers have reached the coast and surround what remains of the red ones.",
}

# screens whose omitted parts deserve a word
LINE_NOTES = {
    "30:6": {"Network:": "Network: four pairs of long hexadecimal addresses and keys.",
             "Proxies:": "Proxies: four more pairs."},
}
LINE_AFTER = {
    "30:33": ("Here are some more proxy endpoints.", "Six hexadecimal endpoint pairs follow."),
}
