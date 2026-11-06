# `hive.ui`

**A view is a value** — a tree of widgets — and what paints it is decided
somewhere else.

| call | what it does |
| --- | --- |
| `window(title, view, update)` | a window, as a handler for `spawn` — which opens it |
| `webview(title, view, update)` | the same window, always drawn as a page |
| `html(view)` | renders the tree as an HTML **fragment** → `Str` |
| `page(title, view)` | renders it as a whole **document** → `Str` |

`view` is a `func(State): hive.ui.View` and `update` is a
`proc(mut State, Msg): Msg`, or `proc(mut State, Msg, Address<Msg>): Msg` to be handed
the window's own address. `window` answers with a handler of the same shape, and
the state a window starts from is what it is spawned with:
`spawn(ui.window("Notes", view, update), fresh())`.

| page | what is on it |
| --- | --- |
| [ui-widgets](ui-widgets.md) | every widget and its payload |
| [ui-attributes](ui-attributes.md) | layout, text, state — what an attribute carries |
| [ui-events](ui-events.md) | `on`, `onInput`, `onChoose` and the rest |
| [ui-enums](ui-enums.md) | `Align` `Justify` `TextSize` `Axis` `Anchor` `InputKind` `Icon` |
| [ui-colour](ui-colour.md) | `Tone` |
| [ui-canvas](ui-canvas.md) | two dimensions, in the program's own units |
| [ui-code](ui-code.md) | a code editor: text in colours, a caret its program can move |
| [ui-scene](ui-scene.md) | three dimensions — **five pages**, start there |

## What a window is

On Windows and Linux, **one the program draws itself** — see below. Elsewhere, an
**application-mode browser window** — no address bar and no tabs — running
against a **profile of its own**, so it is its own process rather than a window
inside somebody's browser: none of your own session, extensions or history is in
it, and quitting a browser does not close it. A machine with no Chromium-family
browser falls back to an ordinary tab.

**On Windows and Linux the program draws its window itself**, with no browser
anywhere: every widget but a `scene` has a version of its own there, laid out
by the stylesheet's own rules and light or dark as the desktop is. Linux speaks
X11, which a Wayland desktop serves through XWayland, and sets the system's own
sans-serif. A window with a scene in it keeps the page, and so does one opened
with `webview`, a program shipping a typeface of its own, a Linux machine with
no display or no usable font, macOS and Android. The layout is modelled on
[Clay](https://github.com/nicbarker/clay), by Nic Barker.

**It behaves as a page would**: text is selected and copied, a right click opens a
menu, a field undoes, scroll bars drag, a screen reader reads it (UI Automation on
Windows, AT-SPI on Linux), and on Linux IBus or Fcitx5 types into it. An `image`
may be PNG, JPEG, GIF, WebP or SVG.

**Opening one does not wait for it**, so a program may open as many as it likes.
Closing a window kills its service, and **closing the last one ends the
program**. A `main` that returns while a window is open waits for them all;
[`hive.task.sleepForever`](task.md) says the same for one with nothing left to
do.

On Windows a **built** windowed program carries no console, so what opens is the
window and nothing else. `hive run` keeps one, because that is where the
program's own output belongs while you are writing it.

## Its icon is `assets/icon.png`

A PNG of at most 256×256, beside the entrypoint. The build **embeds it into the
executable** — the window links it, and on Windows the file carries it as a
resource, so a file manager and a pinned shortcut show it too. A window that
ships none shows Hive's own mark.

It is **the program's** icon, not the window's: any program may ship one, and a
Windows build carries it whether a window ever opens or not.

```
my-app/
  app.hive
  assets/icon.png     the window's icon, and the executable's
```

**Nothing in the source names it.** What a window shows and what the file
carries have to be one image, so there is one place to put it.

## Its typeface is `assets/font.woff2`

By the same convention: ship the file and every widget is set in it; ship none
and the window uses the system's own. Nothing in the source names it either.

## A finger is not a mouse

Where the pointer is coarse, a button, a field and a checkbox stand **at least
44px tall** and a field's text is **16px** — below which a phone zooms the page on
focus and never zooms back. **No layout moves:** a `row` is a row at every width,
on every device.

## Two environment variables

| variable | does |
| --- | --- |
| `HIVE_WINDOW=print` | prints `hive-window <url>` instead of opening a browser |
| `HIVE_FOLDS=1` | prints, once a second, turns taken and drawn, the median, 90th-percentile and worst time in `update`, `view` and sending the page, and the collections since |

An app from `hive export` takes `HIVE_FOLDS` as an intent extra — see
[cli](../cli.md).

A window the program draws itself usually has no console to print a crash
to, so **what a crash prints is also appended to
`<temp>/<program>-crash.log`** — the file to look in when one closes by itself.

## The window is a service

`update` is **a [service's](syslink.md) handler**, and is checked as one, and a
window is started by `spawn` like any other service. So a window **has an
address**, may be spawned under a name, and can be posted to by a background task
or by another machine. That is why the module needs no notion of a *command*.

## The view is a `func`, and that is not a formality

**A `func` cannot take a `mut` parameter, so drawing cannot write the model** — or
anything else the caller can see — which matters because a repaint happens on
every change.

```hive
type Msg {
	Typed { text: Str }
	Send
}

type State {
	draft: Str
	lines: Str[dyn]
}

func view(state: State): hive.ui.View {
	return ui.column([ui.gap(8), ui.pad(16)], [
		ui.text([ui.size(ui.TextSize.Title())], "Notes"),
		ui.input([ui.onInput(Msg.Typed(_)), ui.placeholder("a line")], state.draft),
		ui.button([ui.on(Msg.Send())], "Add")
	])
}

proc update(state: mut State, message: Msg): Msg {
	if message is Msg.Typed(text) {
		state.draft = text
	} else if message is Msg.Send {
		append(state.lines, state.draft)
		state.draft = ""
	}
	return message
}

proc main(): void {
	Str[dyn] empty = []
	spawn(ui.window("Notes", view, update), State("", empty))
}
```

## One tree, two destinations

**The same tree a window swaps in is what `page` writes out**, so a view built
for a window is a view an `httpServe` handler can answer with, unchanged:

```hive
proc handle(req: hive.net.HttpRequest): hive.net.HttpResponse {
	return hive.net.HttpResponse(200, [], ui.page("Notes", view(state)))
}
```

`link` is the one widget that works without an event: a window follows the
**message** and a served page follows the **href**, from the identical tree.

## Why the widget list is short

**A widget is here only if it cannot be composed from the others *and* needs
something the renderer has that Hive does not.** A card is a `column` with
padding, a toast is an `overlay` and a message, a divider is a `row` with a
border. Do not go looking for those.
