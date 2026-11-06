# `hive.ui` — the code editor

`code(attrs, text, runs)` is a textarea for source: **it does not wrap, it is
set in a fixed-width face, and its text is coloured by the runs beside it**. It
types, selects, scrolls, undoes and pastes as a textarea does; Tab types a tab,
and Enter starts the new line as far in as the one it left.

```hive
ui.code([ui.grow(1), ui.numbers(true), ui.caret(state.anchor, state.head, state.moves),
	ui.onEdit(Msg.Edited(_, _, _)), ui.onCaret(Msg.Moved(_, _)), ui.onView(Msg.Showing(_, _))],
	state.text, colours(state))
```

## Runs

A run is **where it is by offsets into the text, counted in characters** — not
bytes, not pixels — from the first character it covers to the one after the last.

| call | what it does |
| --- | --- |
| `ink(from, to, tone)` | the text in a colour |
| `shade(from, to, tone)` | a colour behind the text: a match, a bracket's pair |
| `squiggle(from, to, tone)` | a wavy line under it: an error, a warning |
| `underline(from, to, tone)` | a straight one: a name that can be followed |
| `band(line, tone)` | a line's whole width behind it, **from 0**: an error's line |
| `note(line, text, tone)` | text after the end of a line that is not part of the text: the error itself |
| `marker(line, tone)` | a bar against a line's number, **from 0**: a change, a breakpoint |

Where two runs of a kind overlap, **the one given later wins**, as a later style
rule does. A run reaching past the text stops at its end.

## What it tells, and what it is told

`onEdit(f)` is handed **what an edit replaced**: from, to, and what went there
instead — so a program that keeps its text in pieces, or colours it a line at a
time, does not have to compare a whole file to learn that one letter arrived.
`onInput` still hands the whole text, for a program that would rather have that.
The text the view gives is **the program's**: one that does not take an edit in
puts its own text back.

`onCaret(f)` is handed the selection, anchor then caret, whenever the reader
moves it. `caret(anchor, head, serial)` puts it somewhere, **when any of the
three changes**: a program that goes to a line sets it once, and the reader
carries on from there. The serial is what lets it go to the same place twice —
a search that finds the same word again counts up. A selection the program
set is not told back to it.

`onFit(f)` is handed how many columns and rows fit in the editor, as that
changes: what a terminal drawn in one tells the program running in it.

`readOnly(true)` keeps the text as it is: the reader selects, scrolls and
copies, and nothing they type or paste lands in it. With `keys(["Any"])` and
`onPaste(f)` — handed the clipboard's text on Ctrl+V — it is a terminal's
screen: every key goes to the program, and the program draws what came back.

`perform(command, serial)` has the editor do one of a menu's commands once
per serial: `undo` `redo` `cut` `copy` `paste` `selectAll`.

`onView(f)` is handed the first and last lines in view, from 0, as they change —
so a long file can be coloured where it is being read and nowhere else.

`onHover(f)` is handed the character under the pointer as it moves, and -1 where
there is none — past the end of a line, or off the editor. `onJump(f)` is handed
the one under a Ctrl+click. `onProbe(f)` is handed the character under the pointer
**only while Ctrl is held**, and -1 when Ctrl is let go or the pointer leaves: an
underline on the name that can be followed, and the jump to where it is declared,
are `onProbe`, `onJump` and an `underline` run. With Ctrl held over a
character, an editor with `onJump` shows the pointing hand.

`numbers(true)` shows the line numbers, `tabSize(n)` how far a tab
reaches — four where it is not given — and `fontSize(n)` how big its letters
are, in pixels: 13 where it is not given.
