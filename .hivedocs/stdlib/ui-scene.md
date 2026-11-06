# `hive.ui.scene`

Three dimensions inside a window. **A scene is a value like every other view**:
a camera, a sky, and a vector of shapes, rebuilt by an ordinary `func` from the
state as often as there are frames.

**Nothing here is a handle** — there is no mesh to keep, no material to allocate
and no canvas to hold — so a program that draws one answers "what is there right
now" and never "what has changed".

| page | what is on it |
| --- | --- |
| [ui-scene-shapes](ui-scene-shapes.md) | the eleven shapes, and where one is |
| [ui-scene-surfaces](ui-scene-surfaces.md) | what a thing is made of |
| [ui-scene-sound](ui-scene-sound.md) | a noise is a shape |
| [ui-scene-camera](ui-scene-camera.md) | the eye, the sky, the fog, the shadows |
| [ui-scene-input](ui-scene-input.md) | frames, keys, the mouse, a gamepad |

```hive
func view(world: World): hive.ui.View {
	return ui.scene([
		ui.eye(world.x, world.y + 1.6, world.z),
		ui.aim(world.yaw, world.pitch),
		ui.lens(75), ui.fog(400),
		ui.background(ui.Tone.HEX("#8ec5ff")),
		ui.grab(true), ui.crosshair(true),
		ui.onFrame(Msg.Frame(_)),
		ui.onKeyDown(Msg.Down(_)),
		ui.onLook(Msg.Look(_, _))
	], shapesOf(world))
}
```

`scene` is a widget, so it is laid out like one: give it `grow(1)` in a
`column`, or a `width` and `height` of its own.

## It is the module that carries a download

**`hive.ui.scene` is a module of its own because it is the one that carries a
dependency**: a pinned three.js, fetched on the first build that needs it and
cached. A window that draws no scene links none of it.

## Units and angles

**Metres and radians**, and every geometric number is a `Float` — `ui.at`,
`ui.turn`, `ui.eye`, `ui.aim` and every shape's dimensions. `ui.lens` (degrees)
and `ui.fog` (metres) are the two `Int`s. Hive never widens a number, so a
literal in one of these is written `1.0` rather than `1`.

[`hive.math`](math.md) is where the trigonometry is, and every one of those
takes and answers with a `Float` too.

## One world, and it is drawn once

**A scene is only ever drawn once, from the newest description of it.** Frames
arriving faster than the window can draw them **replace one another rather than
queueing**, so what is drawn is always the latest world.

A window draws **one** scene and any number of [insets](ui-scene-camera.md) — a
second camera on the same world.
