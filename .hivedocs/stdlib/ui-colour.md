# `hive.ui` — colour

`Tone` is carried by `ui.tone` (a foreground), `ui.background` (a fill) and
`ui.paint` (a canvas mark or a scene shape).

| variant | is |
| --- | --- |
| `Normal()` | the ordinary role |
| `Muted()` | secondary text |
| `Good()` | success |
| `Warn()` | caution |
| `Danger()` | failure, destruction |
| `HEX(Str)` | a colour outright |
| `RGBA(Int, Int, Int, Int)` | a colour outright, with alpha |

`Tone` is the one enumeration that is not only a closed set: past the five
**roles**, `HEX` and `RGBA` carry a colour themselves.

```hive
ui.text([ui.tone(ui.Tone.Danger())], "could not save")
ui.dot([ui.paint(ui.Tone.HEX("#f2a"))], x, y, 3.0)
ui.sphere([ui.paint(ui.Tone.RGBA(255, 255, 255, 96))], 1.0)   // translucent
```

## A role and a colour are not the same kind of thing

**A role becomes a class the stylesheet answers for; a colour becomes a
declaration.** So a role follows the theme and **brings a readable foreground
with it**, while a computed colour brings nothing — text painted a colour of
your own is legible because you chose it, not because the window did.

Prefer a role wherever one fits. Reach for `HEX` or `RGBA` where the colour
*is* the information: a series on a chart, a team's livery, a shape in a scene.

## A colour is checked, not trusted

* `HEX` takes a `#` and **3, 4, 6 or 8** hex digits. **Anything else is
  `Normal`** — it does not fail, it falls back, so a colour computed from data
  can never break a page.
* `RGBA` **clamps each channel** to 0–255.

## Alpha means something in a scene

`RGBA(r, g, b, a)` and an eight- or four-digit `HEX` carry an alpha, and in a
[scene](ui-scene.md) it is honoured: **the shape is drawn see-through and writes
no depth**, so whatever is behind it stays visible. That is how a ghost, a
tinted screen or the plume behind something is drawn.

A [surface](ui-scene-surfaces.md) is drawn **over** whatever colour a shape is,
so one finish serves a red kerb and a blue one.
