# `hive.ui.scene` — surfaces

`surface(Surface)` is **the finish**, as against `paint`'s colour. Nineteen,
ordered from the ground up — what you drive on, then what things are built of,
then what they are finished in:

| | |
| --- | --- |
| ground | `Turf` `Gravel` `Tarmac` `Kerb` |
| built | `Concrete` `Brick` `Panes` `Planks` `Staves` |
| grown and gathered | `Bark` `Leaves` `Crowd` |
| open | `Mesh` |
| finished | `Speckle` `Metal` `Carbon` `Rubber` `Glass` `Gloss` |

**Every one is drawn *over* whatever colour the shape is**, so one pattern serves
a red kerb and a blue one, and `Gloss` adds no pattern at all. `Panes` is the
exception: its glass and frames are colours of their own, because a window is a
different material from the wall, and one lands in every couple of metres of
surface. A kerb's white stripe and a crowd's shirts are their own colours too.

## What a shape is made of when it does not say

Its **kind** decides: a `ground` is `Turf`, a `cylinder` or a `cone` is
`Staves`, a `sphere` is `Speckle`, and everything else is `Planks`.

That is also why saying is worth having: **a road drawn as a `ground` came out
as a lawn.**

## A finish is sized in metres, not in faces

Roughly **one tile every two metres** whatever the shape is, so a crate and a
wall are made of the same-sized boards — and **a `box` is tiled face by face**,
each by its own two dimensions. A barrier forty metres long and one metre high is
forty tiles by one, not one by one stretched forty ways.

## Many shapes are cheap, and a see-through one is not

Every opaque solid of one kind in one surface is drawn **together**, whatever
its size and colour, so a city of ten thousand boxes is a few dozen draws and a
shape's size and colour may change every frame for nothing. A **translucent**
one — a colour with an alpha — is drawn alone and sorted, and each colour of
one is a material the window keeps; keep the number of such colours small.

## `Mesh` is the one with holes in it

A chain-link fence is not a faint fence, it is wire with nothing between the
wire — so **its pattern's own transparency decides pixel by pixel**, and what is
left goes on writing depth like any solid. Nothing has to be sorted against it,
and it is **visible from both sides**.

## Every finish has relief, bar three

A surface is not only a pattern, it is a set of directions the surface faces —
so a kerb's stripes have edges that catch the sun, gravel has stones in it, and
a plank's seams are seams rather than lines.

Three have none, and none of the three is an oversight: **`Gloss`** is paint and
adds no texture by definition, **`Glass`** is the same argument, and **`Mesh`**'s
holes are transparency rather than geometry.

## A surface may be a photograph

A `Surface` names what a thing is made of; what that name *looks like* is the
window's business. **A file at `assets/textures/<surface>.jpg`, named for the
finish in lower case, is used instead of the drawing.** A second file,
`assets/textures/<surface>-normal.jpg`, is its relief.

```
assets/textures/tarmac.jpg          the road, photographed
assets/textures/tarmac-normal.jpg   and how it lies
```

**There is no call for this and no attribute that asks for it**, and that is the
point: a scene is a value, and the same value has to be right whether or not the
window found a picture. A program that ships the files gets them; one that does
not gets the drawing; neither says anything.

**A photograph is laid over the colour, not in place of it.** It is read as light
and dark about **mid grey** — the window brings the file to that mean itself — so
the average of a tile is the colour the shape asked to be painted and what the
photograph contributes is its **structure**. That is what keeps one file serving
every colour a finish is asked for.

**Nothing waits for it.** The first frame is drawn from the pattern the renderer
has, the file is fetched alongside, and the tiles are redrawn under their own
textures when it arrives — no rebuild, no flicker, and no frame held up by a
round trip. A file that is not there 404s and the drawing stands.
