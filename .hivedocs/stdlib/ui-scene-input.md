# `hive.ui.scene` — what the player did

| event | reports |
| --- | --- |
| `onFrame(f)` | `Int` — how many **milliseconds** the last frame took |
| `onKeyDown(f)` / `onKeyUp(f)` | `Str` — the key's name |
| `onLook(f)` | `Float, Float` — how far the mouse moved, across and down |
| `onGrab(f)` | `Bool` — whether the window is holding the mouse now |
| `onPad(f)` | `Int, Str, Float` — which pad, which control, where it now is |
| `onSize(f)` | `Int, Int` — how wide and how tall the scene's box landed, in pixels |
| `onRate(f)` | `Int` — the screen's refresh rate, in hertz |

Each takes a function of what it reports, which is what a
[constructor with holes](ui-events.md) already is:

```hive
ui.onFrame(Msg.Frame(_))
ui.onKeyDown(Msg.Down(_))
ui.onLook(Msg.Look(_, _))
ui.onPad(Msg.Pad(_, _, _))
```

## `onFrame` is a clock

**It reports the time since the last frame the program was told about, and not
the time since the last frame the window drew.** The two are the same whenever a
program can keep up and are deliberately not the same when it cannot.

A window holds **at most one frame in flight**: having reported one it says
nothing more until the program has handled it, and while it waits the gap goes on
growing — so the frame that does go carries the whole of the time that passed. A
program that can handle sixty frames a second is told about sixty; one that can
manage twenty is told about twenty, of fifty milliseconds each.

That is what makes it a clock. Were it one message per refresh regardless, a slow
program would be handed more frames than it could take, and since nothing between
the window and `update` ever drops a message the excess would **queue**: input
would sit behind a backlog of stale frames, and a world stepped by the gaps in
them would run slower than real time.

**A gap longer than a tenth of a second is still reported as a tenth of a
second**, because a world stepped by a full stall would teleport. So step the
world by what `onFrame` hands you and nothing else.

## `onSize` and `onRate`

`onSize` is said **when the scene starts listening and whenever its box changes
size, and at no other time** — keep it in the model, because a model that loses
it is not told again until the box moves. `onRate` is measured from the window's
own frames rather than the program's, and said when it changes, at most once a
second, between 20 and 480.

## Keys

**A key is named the same on every layout the browser can report**: a letter or
a digit is itself, and everything else is the word for it — `space`, `enter`,
`escape`, `tab`, `shift`, `ctrl`, `up`, `down`, `left`, `right`.

Hold state is the program's: `onKeyDown` and `onKeyUp` are what `update` uses to
keep its own set of what is held.

## The mouse

`grab(true)` asks the window to hold the pointer, which is what makes `onLook`
report **movement** rather than a position. `onGrab` says whether it currently
holds it — a browser gives it up on `escape`, and a program that dims the world
when it loses the mouse reads this.

## A gamepad

**A gamepad is the one input a browser will not tell you about**: there is no
event for a stick moving, only a snapshot you have to ask for. So a pad is read
**once a frame** and what arrives is **what changed** — which makes a button on a
pad the same kind of thing as a key going down.

One shape covers the whole device, because a button is a control that is only
ever 0 or 1:

| control | name | reports |
| --- | --- | --- |
| sticks | `leftX` `leftY` `rightX` `rightY` | −1 to 1 |
| triggers | `lt` `rt` | 0 to 1 |
| face | `a` `b` `x` `y` | 0 or 1 |
| shoulders | `lb` `rb` | 0 or 1 |
| dpad | `up` `down` `left` `right` | 0 or 1 |
| the rest | `back` `start` `guide` `lstick` `rstick` | 0 or 1 |
| anything past those | `b17` `b18` … `axis4` … | by number |
| the pad itself | `here` | 1 when it arrives, **2** when it arrives with a layout the browser could not name, 0 when it goes |

**The names are by position, for every pad** — including the ones the browser
declines to name. It leaves `mapping` empty for any device missing from its own
table, which on a desktop is most of them and very nearly every wheel. A pad
nobody can name is still a pad.
