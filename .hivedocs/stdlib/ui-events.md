# `hive.ui` — the events

An event is an attribute like any other. **Two carry the message itself; the
rest carry a function of what the user did.**

| attribute | hands your function |
| --- | --- |
| `on(Msg)` | — the message itself |
| `onDismiss(Msg)` | — the message itself |
| `onInput(f)` `onSubmit(f)` `onChoose(f)` | `Str` |
| `onKey(f)` | `Str` — a key a widget took with `keys` |
| `onEdit(f)` | `Int, Int, Str` — a [code editor](ui-code.md)'s edit |
| `onCaret(f)` `onView(f)` | `Int, Int` — its selection, and the lines in view |
| `onHover(f)` `onJump(f)` | `Int` — the character under the pointer, and under a Ctrl+click |
| `onFit(f)` | `Int, Int` — the columns and rows that fit in a code editor |
| `onProbe(f)` | `Int` — the character of a code editor under the pointer while Ctrl is held, -1 when it is let go |
| `onPaste(f)` | `Str` — the clipboard's text, on Ctrl+V in a widget that takes it |
| `onMenu(Msg)` `onMiddle(Msg)` `onDouble(Msg)` | — a right click, a middle click, a double click |
| `onDrag(f)` | `Int, Int, Bool` — how far since the press, and whether it was let go |
| `onToggle(f)` | `Bool` |
| `onPick(f)` `onSort(f)` | `Int` |
| `onKeyDown(f)` `onKeyUp(f)` | `Str` — a [scene](ui-scene-input.md) |
| `onFrame(f)` | `Int` — a scene |
| `onLook(f)` | `Float, Float` — a scene |
| `onGrab(f)` | `Bool` — a scene |
| `onPad(f)` | `Int, Str, Float` — a scene |

## A constructor with a hole is the function

This is what [partial application](../expressions.md) is for. `Msg.Changed(_)`
is already a `func(Str): Msg`, so nothing has to be written to adapt it:

```hive
type Msg {
	Typed   { text: Str }
	Toggled { done: Bool }
	Chose   { option: Str }
	Send
}

ui.input([ui.onInput(Msg.Typed(_))], state.draft)
ui.checkbox([ui.onToggle(Msg.Toggled(_))], "done", state.done)
ui.select([ui.onChoose(Msg.Chose(_))], options, state.chosen)
ui.button([ui.on(Msg.Send())], "Send")
```

**The shape must match**: `onToggle` is handed a `Bool`, so its function has to
take one, and the compiler says so where it does not. An event reporting two
values wants a **two-hole** constructor —
`ui.onLook(Msg.Looked(_, _))` — and one reporting three wants three.

Where a message needs something the event does not report, fill the rest in at
the call site: `ui.onToggle(Msg.Set(item.id, _))` captures the id where it was
written.

## What each one is on

`on` is a `button` being pressed or a `link` being followed. `onDismiss` is
an `overlay` being closed. `onInput` fires as an `input` or `textarea`
changes and `onSubmit` when one is entered. `onChoose` is a `select`.
`onToggle` is a `checkbox`. `onPick` and `onSort` are a `table` — a row
chosen, and a column asked to order by, each **by index**.

## Keys a widget takes for itself

`keys(["Ctrl+S", "Escape"])` says which keys a widget takes, and `onKey(f)`
hears them. **The innermost widget around the focus that names a key gets it**,
and nothing else happens to it — the field does not type it, Tab does not move
the focus, the window does not close. A key no widget names goes on as usual.
With nothing focused, the outermost widget is what is around the focus, so a
window's shortcuts go on its outermost widget:

```hive
ui.column([ui.keys(["Ctrl+S", "Ctrl+Shift+P", "F5"]), ui.onKey(Msg.Shortcut(_))], [
	ui.input([ui.keys(["ArrowUp", "ArrowDown"]), ui.onKey(Msg.History(_))], state.line),
	ui.textarea([ui.keys(state.mode.claimed), ui.onKey(Msg.Normal(_))], state.text)
])
```

**A key is named by what it types when nothing but Shift is held** — `"a"`,
`"A"`, `":"` — and **by the key itself, modifiers first, when Ctrl or Alt
is**: `"Ctrl+S"`, `"Ctrl+Shift+P"`, `"Ctrl+Alt+O"`, `"Ctrl+,"`. Keys
that type nothing have names of their own, with Shift in front where it is held:
`Enter` `Escape` `Tab` `Backspace` `Delete` `Insert` `Space`
`ArrowUp` `ArrowDown` `ArrowLeft` `ArrowRight` `Home` `End`
`PageUp` `PageDown` `F1`…`F12` — so `"Shift+Tab"`.

`"Any"` takes every key, typing included: what an editor with a mode of its
own wants while that mode is on. The list is state like any other, so a widget
takes `"Any"` in one mode and nothing in the next.

## The pointer's own events

`onMenu`, `onMiddle` and `onDouble` go to **the innermost widget under the
pointer that hears them**, on any widget: a right click on a row of a list opens
that row's menu, and with an overlay anchored at the pointer the menu opens where
the click was. `onDrag(f)` is handed how far the pointer has moved since the
press, across and down, as it moves and once more when it is let go — so a
divider that resizes a panel keeps the size it started from and adds the distance:

```hive
ui.column([ui.height(5), ui.onDrag(Msg.Resize(_, _, _))], [])
```

A code editor's `onHover` and `onJump` are in [ui-code](ui-code.md).

The five scene events are [ui-scene-input](ui-scene-input.md).

## There is no command

The message goes to `update`, which is [a service's handler](syslink.md): it writes
the state, and what it returns is read only by a request from another node.
**Work that has to happen goes to a service** — a window has an address, handed
to an `update` that takes one third, so anything with something to say posts a
message back to it when it has one.
