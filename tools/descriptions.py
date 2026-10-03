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
    "2:77": "Next slide: the two jars joined by a narrow neck, a molecule slipping through it; two million molecules, "
            "velocities from zero to 499,999.",
    "3:139": "A map on his watch: his own dot in the room, and Mov's at the doorway, moving away up the passage.",
    "4:7": "An animation on a grid: a wall of cells down the middle, marked by thin yellow lines; from the "
           "right, small clusters of cells glide toward it step by step and slip through to the other side, "
           "and a counter in the corner ticks.",
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
    "12:54": "A diagram titled tun bia zi sin de sia: twelve bits across the top feeding into nine boxes labelled fai "
             "hie, lines crossing between the rows, only six bits coming out at the bottom, and an orange line looping "
             "from the first input bit round the side into a plus sign on the output.",
    "12:198": "The board, a hexagon this time: circles at the top, squares at the bottom.",
    "14:54": "The audience's view: five shrines marked as triangles, centre, north, south, east and west, "
             "with circles and squares scattered between them.",
    "14:74": "The audience's view again: four symbols left, a single square tucked in the north-east corner and three "
             "circles, north-west, east and south-west.",
    "14:88": "Only two symbols left in view: a square by the north shrine and a circle by the south one.",
    "14:118": "A menu: a cup, a leaf, a cow and a fish, drawn strangely this time, with odd extra strokes and no words "
              "under them.",
    "17:58": "A diagram: Airborne disease resistance at the centre, branching into Air quality, Early "
             "detection, Treatment, Individual non-pharmaceutical prevention and Prophylactics, each edge "
             "marked with a percentage, and branching again into Ventilation, Filtration, Ultraviolet light, "
             "Wastewater scanning and more.",
    "17:79": "Zoomed in: Ultraviolet light splits into 222-nanometre lamp efficiency, 222-nanometre safety "
             "testing, upper-room deployment, krypton chloride lamps and research into alternative lamp "
             "designs, each with its percentage, down to named research groups.",
    "19:40": "An envelope icon, and the words:",
    "19:115": "A download screen: eight files, each named by a long hexadecimal hash, each with a progress bar barely "
              "started, one to three percent, and a time-remaining line in Dzegoban beneath.",
    "22:85": "A view: seven pale circles, six in a hexagon and one at its centre, and a red square with a short dashed "
             "trail low between the bottom two.",
    "22:94": "The red square has crept a little further in, up and to the left, still well short of the centre.",
    "22:100": "A red X beside the square, and small triangles entering from the south.",
    "22:107": "Two triangles close on the square from the north.",
    "22:120": "Three X marks now, two of them on circles of the ring; one triangle left, and three more red squares "
              "coming in from the south-east.",
    "22:140": "A closer view: nine X marks; all four red squares crossed out, and three of the four circles with them; "
              "only one circle is untouched.",
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
    "26:146": "A close view: the two drones flying on north, the two checkmarks left behind them at the corner of one "
              "road, and a second road running straight past to the east.",
    "29:36": "A map: the coast and the sea, Northglade on the shore; four Veridian groups, North, Center, South and "
             "Naval, their dashed routes fanning out: North's up to the inlet far north of the city, Center's and "
             "South's toward Northglade, Naval's in from the sea to the east.",
    "29:62": "The map: red markers appearing against Group North's flank.",
    "29:73": "A close view: a bent line of Veridian markers, red Arctic ones along its north and down its east side, "
             "and three more Veridian markers coming up from the south-east.",
    "29:81": "The lines have mixed: Veridian markers in among the red ones.",
    "29:87": "The wide map again: a single red marker left just behind Group North with a small Veridian dot beside "
             "it, and all four groups well along their routes.",
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
