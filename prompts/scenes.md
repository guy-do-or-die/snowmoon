# Scene ambience and spot sounds (per block of sixteen chapters)

You are helping produce an immersive audiobook of the novel "Snowmoon". Tag each SCENE with a background ambience (or none) and mark a few SPOT SOUNDS where the narration explicitly names a sound event. Restraint is the brief: sound only where it helps the drama, never to overwhelm.

## Input
`script/readable/chNN.txt` in full. A scene starts at the first item of a chapter and after every `----- scene break -----` line. Datelines name the place.

## Palette (use ONLY these names)
Ambience beds: forest_path, city_street, concert_crowd, classroom, restaurant, stadium_crowd, home_interior, aircraft_cabin, winter_wind, library, war_room, battlefield_distant, vehicle_interior, rain — or null for none.
Spot sounds: watch_buzz, drones_flyby, door_knock, door_open, alarm, crowd_cheer, explosion_distant, data_transfer, footsteps_stairs, crowd_gasp.

## Output
For EACH chapter write `script/scenes/chNN.json`:
{"chapter": 1,
 "scenes": [{"start": "1:1", "setting": "wooded foot path", "ambience": "forest_path"}, ...],
 "spots": [{"id": "1:5", "sound": "drones_flyby", "why": "a small drone flew over his head"}, ...]}

Rules:
- `start` is the item id where the scene begins. Also start a new scene entry when the setting clearly changes WITHOUT a scene break; one or two settings per scene is typical.
- `ambience`: only when the setting clearly matches a palette name and sound would add to the scene; null for neutral or indoor-quiet settings, phone calls, anything abstract. Expect null for a third to a half of scenes.
- `spots`: ONLY where a narration line explicitly describes that sound event. Do not add watch_buzz for `<message>` blocks (they buzz automatically). At most 4 spots per scene; skip anything doubtful.
- Valid JSON; ids must exist in the file.

## Final reply
Scenes and spots per chapter and anything you were unsure about.
