# `hive.ui.scene` — the shapes

**A shape is here only if it cannot be made out of the others.** Dimensions are
the payload rather than attributes, because they are what the shape *is*: a
sphere without a radius is not a sphere with a default one.

| shape | payload |
| --- | --- |
| `box(attrs, width, height, depth)` | a solid |
| `sphere(attrs, radius)` | |
| `cylinder(attrs, radius, height)` | standing on its end |
| `cone(attrs, top, bottom, height)` | standing on its end, **both** radii |
| `roof(attrs, wide, tall, long)` | a ridge down its length, a slope each side, a gable each end |
| `ground(attrs, width, depth)` | a plane that **already lies flat** |
| `label(attrs, words)` | `Str` — words that always face the viewer |
| `sprite(attrs, image, wide, tall)` | a picture from `assets/` that always faces the viewer |
| `figure(attrs, model, bones, paints)` | [a body from `assets/`](#a-figure-is-a-body-out-of-a-file), posed and painted |
| `line(attrs, fromX, fromY, fromZ, toX, toY, toZ)` | |
| `sound(attrs, name)` | `Str` — [a noise at a place](ui-scene-sound.md) |

**A `box` and a `cylinder` have round edges**: a fifth of the smallest side,
never more than 35 cm — a wall's edges softened, a bench's or a bumper's rounded,
and a sheet of glass or a painted line, a few centimetres thick, still crisp. A
cylinder's rims go by its diameter or its height, whichever is less.

Every dimension is a `Float`.

## Where a shape is, and what it is made of

| attribute | carries |
| --- | --- |
| `at(x, y, z)` | **where its middle is** |
| `turn(x, y, z)` | its rotation, in **radians**, applied X then Y then Z |
| `paint(Tone)` | its [colour](ui-colour.md) |
| `surface(Surface)` | [what it is made of](ui-scene-surfaces.md) |

```hive
ui.box([ui.at(0.0, 0.5, -4.0), ui.paint(ui.Tone.HEX("#c33")),
        ui.surface(ui.Surface.Planks())], 2.0, 1.0, 1.0)

ui.ground([ui.surface(ui.Surface.Tarmac())], 200.0, 200.0)

ui.cone([ui.at(3.0, 0.0, -6.0), ui.paint(ui.Tone.Warn())], 0.05, 0.3, 0.7)

ui.label([ui.at(0.0, 2.0, -4.0)], "start")
```

## Three shapes take less than you expect, and why

**`cone` takes both of its radii** rather than only the base. A cone in the
world is hardly ever the perfect one — a track marker is snub-nosed, a nose cone
ends in a blade, a stack of tyres narrows without coming to a point. **A top of
nought is the perfect one, and a top equal to the bottom is a `cylinder`.**

**`ground` is already lying down**, so a floor costs no rotation and `turn`
still means everywhere what it means anywhere.

**`label` takes no rotation**, for the same reason a label exists: one you can
read from one side only is not a label.

**`line` takes no `at`**, because a line is *between* two places and has no
third one to call its own.

## A sprite stands on its place

`sprite` names a picture under the program's own `assets/` and stands it in the
world `wide` by `tall` metres. Like a label it always faces the viewer and takes
no rotation, and **its place is its foot, not its middle** — one centred on its
position would be buried to the waist.

It is drawn **unfiltered**, pixel for pixel however near the camera gets, and
`paint` *tints* it: a picture drawn white takes the colour asked for, and absent
it is untinted. A file that is not there draws nothing, and the scene carries on.

## A figure is a body out of a file

`figure` names a **skinned glTF binary** (`.glb`) under `assets/` — a person,
an animal, anything that is bones with a skin over them — and stands it at `at`,
turned by `turn`, where the file's own origin is.

**`bones` is three numbers a bone**, in the order of the skin's joints: each one's
turn, in radians, applied as `turn`'s are, *on top of* how the bone stands in the
file. A bone left out stands as the file has it, so `[]` is the file's own pose.
There is no clip to play and no animation to name: a walk is the program's, worked
out frame by frame like anything else that moves. At most 85 bones.

**`paints` is a colour a part**, a part being one of the mesh's primitives, in the
file's order. A part the vector does not reach keeps its material's own colour, and
**a part painted see-through is not there at all** — not drawn and casting no
shadow — so one file can carry a shirt and the skin under it, three heads of hair,
a hat, and a program shows the ones it wants. The file's vertex colours, where it
has them, shade whatever a part is painted.

```hive
ui.figure([ui.at(x, 0.0, z), ui.turn(0.0, yaw, 0.0)], "people/man.glb",
          [0.0, 0.0, 0.0,  0.3, 0.0, 0.0],
          [skin, ui.Tone.RGBA(0, 0, 0, 0), shirt])
```

Every figure of a file shares its geometry, and each is **one draw**, whatever it
is painted. A file that is not there draws nothing, and the scene carries on.

## Building the vector

A scene's shapes are an ordinary vector built by an ordinary `func`, so the
usual tools apply — `map` over the state, `+` to concatenate, a
`mut Shape[dyn]` to append into:

```hive
func shapesOf(world: World): hive.ui.Shape[dyn] {
	mut hive.ui.Shape[dyn] out = [ui.ground([], 200.0, 200.0)]
	for each car in world.cars {
		append(out, ui.box([ui.at(car.x, 0.4, car.z), ui.turn(0.0, car.yaw, 0.0),
		                    ui.paint(car.livery)], 1.8, 0.8, 4.0))
	}
	return out
}
```
