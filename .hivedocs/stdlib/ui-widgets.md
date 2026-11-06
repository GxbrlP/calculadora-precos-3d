# `hive.ui` — the widgets

**Every widget takes the same two things: its attributes, then its payload.**
There are no optional parameters in Hive, so what would be an optional argument
elsewhere is an entry in the attribute vector.

| widget | payload |
| --- | --- |
| `row(attrs, children)` / `column(attrs, children)` | `View[]` |
| `spacer()` | — takes **nothing at all**, not even attributes |
| `none()` | — the same; draws nothing |
| `spinner(attrs)` | — attributes only |
| `overlay(attrs, child)` | `View` |
| `text(attrs, content)` | `Str` |
| `image(attrs, src, alt)` | `Str, Str` |
| `link(attrs, href, label)` | `Str, Str` |
| `icon(attrs, name)` | `Icon` |
| `button(attrs, label)` | `Str` |
| `input(attrs, value)` / `textarea(attrs, value)` | `Str` |
| `checkbox(attrs, label, checked)` | `Str, Bool` |
| `select(attrs, options, chosen)` | `Str[], Str` |
| `table(attrs, rows)` | `Table` |
| `canvas(attrs, marks)` | `Mark[]` — [ui-canvas](ui-canvas.md) |
| `code(attrs, text, runs)` | `Str, Run[]` — [ui-code](ui-code.md) |
| `scene(attrs, shapes)` | `Shape[]` — [ui-scene](ui-scene.md) |
| `inset(attrs, views)` | `View[]` — a second look at that scene |

```hive
ui.row([ui.gap(12), ui.align(ui.Align.Center())], [
	ui.icon([], ui.Icon.Star()),
	ui.text([ui.tone(ui.Tone.Muted())], "starred"),
	ui.spacer(),
	ui.button([ui.on(Msg.Clear()), ui.disabled(len(items) == 0)], "Clear")
])
```

A widget's value is a `hive.ui.View`, which is **opaque**: build it with these
calls, write it down as a type, and hand it on.

## `spacer` against `grow` against `none`

`spacer()` eats the leftover room in a `row` or a `column`, which is what
pushes what follows it to the far end. `ui.grow(n)` is an
[attribute](ui-attributes.md) that gives a **child** a share of it. `none()`
draws nothing and is what a branch returns when there is nothing to show —
Hive has no optional view.

## An `overlay` that says where it goes is not a dialog

* With **neither `align` nor `justify`** it is centred over a dimmed page,
  which is what a dialog is.
* With **either of them** it is pinned to that edge instead: nothing is dimmed,
  and **clicks pass through everywhere the panel is not** — which is what a
  heads-up display in a corner, a toast, or a legend over a picture needs.

* With **`anchor`** it opens where the pointer was last pressed
  (`Anchor.Pointer`) or under the caret of the code editor being typed in
  (`Anchor.Caret`), above it where there is no room below. Nothing is dimmed,
  and **a press anywhere else is its `onDismiss`** — which is what a context
  menu and a list of completions need.

A pinned panel keeps none of the dialog's own shape either: no rounded corner,
no shadow, and no cap on its height, so `grow` and `align(Stretch)` will run
one the full width or height of the window.

## A button or a field in a colour of its own

A `button`, `input`, `textarea`, `select` or `code` given a `background`
draws **no edge of its own** unless it asks for one with `border` or `borderTone` —
the edge was there to set the default look off from the page — and a button in
a colour of its own lights up under the pointer rather than taking the accent.
`radius(n)` rounds it (a button is a pill until told otherwise), and
`ring(false)` keeps the accent ring off while it has the focus.

## `link` works without an event

The window follows the **message** and a served page follows the **href**, from
the identical tree. **Where a link may point is a closed set** — a path within
the page, a relative path, or `http`, `https`, `mailto` — and anything else
renders as no destination at all.

## `select` and `checkbox` hold their own value

Both take **what is currently chosen** as their payload, because a view is a
function of the state: `select(attrs, options, chosen)` redraws with whatever
`chosen` now is, and the [event](ui-events.md) is what changed the state.
Nothing is remembered inside a widget.
