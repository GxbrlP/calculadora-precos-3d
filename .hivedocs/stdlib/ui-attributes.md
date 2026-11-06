# `hive.ui` — the attributes

**Attributes are semantic tokens rather than CSS values**, and each is a call
answering with a `hive.ui.Attr`. They go in the vector every widget takes
first. Events have a page of their own: [ui-events](ui-events.md).

| attribute | carries |
| --- | --- |
| `gap(n)` `pad(n)` `width(n)` `height(n)` `grow(n)` | `Int` |
| `align(Align)` `justify(Justify)` | an [enumeration](ui-enums.md) |
| `scroll(Axis)` | `Axis` |
| `anchor(Anchor)` | `Anchor` — an overlay that opens at the pointer or the caret |
| `size(TextSize)` | `TextSize` |
| `heading(n)` | `Int` — the heading level |
| `tone(Tone)` `background(Tone)` `paint(Tone)` | [`Tone`](ui-colour.md) |
| `kind(InputKind)` | `InputKind` |
| `placeholder(text)` `hint(text)` `title(text)` | `Str` |
| `touch(name)` | `Str` — a thumb control, heard as pad -1 by a scene's `onPad` |
| `keys(names)` | `Str[dyn]` — the keys its [`onKey`](ui-events.md) takes |
| `caret(anchor, head, serial)` `tabSize(n)` `fontSize(n)` | `Int` — a [code editor](ui-code.md)'s |
| `border(n)` `radius(n)` `borderTone(Tone)` | `Int`, `Tone` — a button's or a field's edge: how thick (0: none), how round, in what |
| `ring(b)` | `Bool` — `false` hides the accent ring a button or a field shows while it has the focus |
| `hover(Tone)` | `Tone` — the colour behind any widget while the pointer is over it; a link with one is not underlined |
| `numbers(b)` `readOnly(b)` | `Bool` — a code editor's line numbers, and whether it can be typed in |
| `perform(command, serial)` | `Str, Int` — a code editor does undo, copy, paste… once per serial |
| `focus(serial)` | `Int` — focus this widget (or the first field in it) whenever the number changes |
| `clip(text, serial)` | `Str, Int` — put `text` on the clipboard whenever the number changes |
| `disabled(b)` `busy(b)` | `Bool` |
| `region(x, y, width, height)` `thick(w)` | `Float` — a [canvas](ui-canvas.md) |
| `at(x, y, z)` `turn(x, y, z)` | `Float` — a [shape](ui-scene-shapes.md) |
| `surface(Surface)` | a [finish](ui-scene-surfaces.md) |
| `voice(Voice)` `pitch(f)` `volume(f)` `track(path)` | a [sound](ui-scene-sound.md) |
| `eye(x, y, z)` `aim(yaw, pitch)` `lens(deg)` `fog(m)` | a [camera](ui-scene-camera.md) |
| `shadows(b)` `grab(b)` `crosshair(b)` | `Bool` — a scene |
| `grain(px)` `bits(n)` | `Int` — a scene [drawn coarsely](ui-scene-camera.md) |

**Watch the number type.** `gap`, `pad`, `width`, `height`, `grow`, `heading`,
`lens`, `fog`, `grain` and `bits` take an `Int`; everything geometric — `at`, `turn`, `eye`,
`aim`, `region`, `thick`, `pitch`, `volume` — takes a `Float`. Hive never
widens a number, so `ui.at(0, 1, 0)` is a compile error and
`ui.at(0.0, 1.0, 0.0)` is not.

```hive
ui.column([ui.gap(8), ui.pad(16), ui.scroll(ui.Axis.Vertical())], [
	ui.text([ui.size(ui.TextSize.Title()), ui.heading(1)], "Colonies"),
	ui.text([ui.tone(ui.Tone.Muted())], "{len(rows)} of {total}"),
	ui.table([ui.grow(1)], rows)
])
```

## Layout

`gap` is the space **between** a `row`'s or `column`'s children; `pad` is the
space **inside** its own edge. `align` places children across the axis and
`justify` along it. `grow(n)` gives a child a **share** of the leftover room —
two children at `grow(1)` take half each — and `scroll` says which way a box
may be scrolled when its contents do not fit.

`width` and `height` are a fixed size; `align(ui.Align.Stretch())` is how a
child fills the cross axis instead.

**`width` on a `row` or a `column` is a width, not a floor**: the box is never wider
than the space it is given, so `width(460)` is 460 where there is room and the
screen's width where there is not. A `canvas`, a `scene` and an `image` keep the
width they asked for, since one wider than its box is what `scroll(Horizontal)`
is for.

## State

`disabled` takes a `Bool` rather than being present or absent, so it is
written straight off the state — `ui.disabled(len(items) == 0)` — and there is
no branch to build a different attribute vector.

`busy` says a widget is waiting; `placeholder` is the ghost text in an empty
`input`; `hint` is the note beside one. `kind` says what an `input` is for,
which is what gets a date picker or a hidden password.

`title` on the outermost widget is what the window's title bar says, and it
follows the state like everything else — `ui.title("count {n}")`. Below the
outermost widget it says nothing; a window whose view gives none keeps the title
it was opened with.

`kind(ui.InputKind.Range())` is a **slider** running 0–100, whose value and
`onInput` text are that number. While it has focus it keeps only the keys that
move it, so a scene beside it still hears `escape`.

## Colour

`tone` is the **foreground** of text, `background` is a box's fill, and `paint`
is what a canvas mark or a scene shape is coloured. All three take a
[`Tone`](ui-colour.md).
