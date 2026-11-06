# `hive.ui` — the canvas

Two dimensions, **in the program's own units**. `canvas(attrs, marks)` is a
widget like any other and a `Mark` is a value like any other, so **what a canvas
holds is what is on it right now** — there is no drawing context, no frame to
schedule and nothing to clear.

| mark | payload |
| --- | --- |
| `dot(attrs, x, y, radius)` | a filled circle |
| `bar(attrs, x, y, width, height)` | a rectangle, **from its middle** |
| `path(attrs, points)` | `Float[]` — x, y, x, y … — a line through them |
| `patch(attrs, points)` | the same numbers, **filled** |
| `words(attrs, x, y, height, text)` | words **centred** on the place |

Every number here is a `Float`.

```hive
ui.canvas([ui.region(0.0, 0.0, 100.0, 50.0), ui.height(240)], [
	ui.path([ui.paint(ui.Tone.Muted()), ui.thick(0.5)], [0.0, 0.0, 100.0, 0.0]),
	ui.bar([ui.paint(ui.Tone.Good())], 20.0, 10.0, 6.0, 20.0),
	ui.dot([ui.paint(ui.Tone.Danger())], 60.0, 30.0, 1.5),
	ui.words([], 60.0, 34.0, 3.0, "peak")
])
```

## `region` is the whole of the coordinate system

`region(x, y, width, height)` says **which part of the plane the box shows**,
and **everything on a canvas is said in those units** — a map of a circuit is
written in metres, and a car nine metres long is drawn nine long.

The box may be any shape; **what is drawn keeps its own and is centred in it**.
`thick(Float)` is how wide a `path` is drawn, **in the region's units too** —
so a map zoomed in has thicker roads, which is what zooming in means.

## Why the payloads look like that

**A dimension is the payload rather than an attribute**, the same way it is for
a [shape](ui-scene-shapes.md): a dot without a radius is not a dot with a default
one.

**`bar` is placed by its middle** because everything else on a canvas is, and
one mark placed by its corner would be the one that is always half a width out.

## The list is short on purpose

Five marks, each passing the test the widgets passed — it cannot be made out of
the others. **A ring is a `dot` with no fill, a grid is a vector of `path`s,
an arrow is a `path`.**

The same tree a window swaps in is what `page` writes out, **so a chart drawn
for a program is a chart served by a web server with nothing changed**.
