# `hive.ui.scene` — sound

`sound(attrs, name)` is something in the scene that is **heard** from where it
stands instead of drawn where it stands. It takes `at` like any other shape, and
four of its own:

| attribute | carries |
| --- | --- |
| `voice(Voice)` | which noise it is |
| `pitch(Float)` | how high, as a **multiple** of the voice at rest |
| `volume(Float)` | how loud, the same way |
| `track(Str)` | which recording, named under `assets/` |

**Pitch and volume are multiples rather than hertz and decibels.** What an engine
sounds like at `1.0` is the renderer's business; a program says "twice as fast"
and "half as loud", which is what it knows.

| | `Voice` |
| --- | --- |
| **sustained** | `Engine` `Tyres` `Brakes` `Wind` `Crowd` `Music` |
| **struck** | `Impact` `Chime` `Talk` |

```hive
ui.sound([ui.at(car.x, 0.4, car.z), ui.voice(ui.Voice.Engine()),
          ui.pitch(0.8 + revs), ui.volume(0.6)], "engine-{car.id}")

ui.sound([ui.voice(ui.Voice.Music()), ui.volume(0.2),
          ui.track("audio/theme.ogg")], "music")
```

## The payload is a name, and the name is the sound's identity between frames

**This is the one place audio cannot follow the rule the solids follow.** A box
is matched to whatever was in its slot last frame, and a box rebuilt anyway is a
box nobody can tell was rebuilt. **An oscillator rebuilt anyway is a *click*,
sixty of them a second** — and a slot cannot promise a voice is the same voice,
because a scene is free to stop drawing the car in front and every sound after
it would shift up a place.

So: **a name that is in this frame and was in the last one carries on, a name
that has just arrived starts, and a name that has gone fades out.**

## What a voice does with that is the voice's own business

* A **sustained** voice lasts **as long as the scene goes on naming it**.
* A **struck** one fires **once, when the name arrives**, and is deaf to
  everything after it — because a crash is a thing that happened rather than a
  thing that is happening.

**Naming `"hit-3"` for as long as a car knows it was hit is one impact; letting
the name go and bringing it back is a second one.**

## Sounds are positioned

The listener is the scene's own `eye` and `aim`, so what is heard on the left
is what is drawn on the left, and a car goes past your ear as well as your eye.
The panning is **equal-power**, not a head model, which would convolve every one
of a grid's sixty voices.

**`Music` and `Talk` are the exceptions**: neither has anywhere to stand, so
neither is panned. `Talk` is struck like an `Impact` and unpanned like `Music`,
for anything said *about* a scene rather than in it — a commentator, a narrator
— which pinned to a place would be a voice the listener walks away from.

## Nothing is downloaded

**Every voice is oscillators and filtered noise**, for the same reason a
[`Surface`](ui-scene-surfaces.md) is a drawn pattern: a built Hive program is
one file. It buys something as well as costing something — a voice made of a
frequency can be *bent*, and an engine that is a recording of one speed played
faster is an engine you can hear looping.

## A sound may be a recording

`track(Str)` names a recording for a sound to be made of instead. The voice
still says what the noise *is* — the name decides whether it lasts or fires
once — and the recording is what it is made of.

**The program's `assets/` directory is embedded into the executable**, and a
`track` names a path within it. No such directory beside the entrypoint means
nothing is embedded and the program is exactly the size it was; where there is
one, the whole tree goes in and the window serves it to its own page over its own
socket. **Nothing crosses a network at run time.**

**A track that is not there is not an error.** A missing file, or one the browser
cannot decode, falls back to the synthesised voice — so a recording is something
a scene *gains* and never something it depends on.

A sustained voice **loops** its recording for as long as the scene names it, and
`pitch` is the **speed** it is played at. A struck one plays it once, and one
still decoding when a struck sound arrives is not heard — a bang that arrives
late is a bang nobody wanted.

**A browser will not let a page make a noise until somebody has touched it.**
There is nothing to ask for and nothing to detect: the context is built when the
first sound is asked for and nudged on every gesture until one takes.
