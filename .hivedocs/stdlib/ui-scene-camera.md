# `hive.ui.scene` — the camera, the sky and the mouse

These go on the `scene` itself rather than on a shape.

| attribute | carries |
| --- | --- |
| `eye(x, y, z)` | where the camera is — `Float` |
| `aim(yaw, pitch)` | where it is looking, in **radians** — `Float` |
| `lens(Int)` | the field of view, in **degrees** |
| `fog(Int)` | how far you can see, in **metres** |
| `background(Tone)` | the sky, which the fog fades into |
| `shadows(Bool)` | whether the sun casts. **Absent is yes** |
| `grab(Bool)` | whether the window should hold the mouse |
| `crosshair(Bool)` | whether to draw one in the middle |
| `grain(Int)` | the short edge the world is drawn into, in pixels |
| `bits(Int)` | how many bits of colour each channel keeps |

## A picture may be drawn coarsely

`grain` renders the world into a buffer that many pixels on its short edge and
blows it up to the box **unfiltered** — a picture actually drawn small, not a
full-size one blurred; the long edge follows the box's shape. `bits` keeps that
many bits a channel, **dithered** in a fixed four-by-four pattern rather than
rounded, so a gradient comes out woven instead of banded. Together they are a
handheld's picture: `ui.grain(240), ui.bits(5)`. Insets share the buffer.
Absent, a scene is drawn at its box's size in the screen's colour.

## Lighting is not something a scene describes

**The rig is fixed** — the sky and a sun — chosen so that a solid painted a
colour comes out that colour on its lit side, and a darker, cooler shade of it
in shadow and on the side turned away.

**The light is physical, and every surface takes it its own way**: `Gloss`,
`Glass` and a window's panes reflect the sky over them, `Metal` is a metal,
and turf, tarmac and bark are matt. The sky's colour is what fills the shadows
and what a polished surface shows, so a sunset tints both.

**What makes a scene dark is its palette**, which is why a night scene is written
in dark colours rather than by turning something down — the sky's colour reaches
the light, but very little of its darkness does.

## The sun casts shadows, and it casts them near the eye

A shadow map is one texture, so it covers a box about **fifty metres around
wherever the camera is** — which is where a shadow is read anyway — and it is
redrawn on **every frame**, so nothing moving is shadowed by where it just was. **A `ground` receives shadows and does not cast one**, and
**nor does anything see-through** — a colour with an alpha is a glow, a beam or
smoke, and a shadow map has no half-shadows to give it; every other solid does both.

**`shadows(false)` turns them off**, and it is the one thing about the lighting
a scene may say: a shadow is by a distance the most expensive thing in a picture
and among the least of what a program needs from one, so a window that cannot
hold its frame rate should be able to sell the shadows before the view.

**Turning it rebuilds every shader in the scene**, so a program that means to
turn it off should turn it off and leave it — a value that changes every frame is
a recompile every frame. Something driving it off a frame-rate reading wants
**two thresholds with a gap between them**, for the same reason a thermostat
does.

The edge is **hard rather than soft**: the map is large and the read is a single
sample, because filtering the read is by a distance the most expensive thing a
scene does while the size of the map is very nearly free.

## `background` is a band rather than a colour

The tone given is **the sky at middle height**; the window deepens it overhead
and pales it toward the horizon, and it is the **horizon's** shade the fog fades
into. A flat background has no up and no far, and a scene of any size is nearly
all horizon.

**How far it pales is in proportion to how light the sky is**, because haze is
scattered light and a sky with none has none to scatter. Any daylight pales the
full amount; a sky darker than about a third of full luminance pales less, and a
black one does not pale at all — which is what lets a scene under a roof fade
into the dark rather than into grey.

## A second look: `inset`

`inset(attrs, views)` is a **widget**, and the one widget that draws in three
dimensions without being a scene: a box on the page showing the world the scene
is already showing, from wherever its own `eye`, `aim` and `lens` are
standing — a rear-view mirror, a security camera, a replay box.

```hive
ui.inset([ui.width(320), ui.height(180), ui.eye(x, y, z), ui.aim(yaw, 0.0)], [
	ui.text([ui.size(ui.TextSize.Caption())], "TURN 7")
])
```

**It holds a camera and no world**, and that is the whole of what makes it
affordable: an inset is a second *pass* over the shapes the scene already handed
over, so it costs one more draw and nothing at all in what the program has to
say. **A window still draws one scene, and any number of insets.**

Its own views are laid out exactly as a `column` lays them out, and they sit
**over** the picture rather than in it. The box itself is transparent, because
what is behind it is the second view.

**An inset has to be over the picture.** It is drawn into the canvas the scene
already has, clipped to where its box landed on it, so a box laid out where that
canvas does not reach is not drawn. Pin it into a corner with `overlay`.

The sky, the haze, whether the sun casts and how far the world reaches are the
**scene's** and are shared: an inset is another look at one world, not another
world. Shadows are drawn near the scene's own eye, so a subject far from it is
lit and unshadowed.
