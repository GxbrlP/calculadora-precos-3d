# `hive.audio`

Sound that is not in a scene: a recording or a **live stream** — an internet
radio station, say — played by name until it is stopped.

| call | answers |
| --- | --- |
| `play(name, url, volume)` | `void` |
| `stop(name)` | `void` |

```hive
if inCar && radioOn {
	hive.audio.play("radio", "https://example.com/live.mp3", 0.5)
} else {
	hive.audio.stop("radio")
}
```

**The name is the stream's identity**, as a sound's is in a
[scene](ui-scene-sound.md). `play` with a name already playing the same
`url` only sets its `volume` (0 to 1), so a program may say what it wants
every frame and nothing restarts; a different `url` under the name replaces
the stream. `stop` with a name that is not playing does nothing.

**It is played by the program's window.** The window's engine is where the
platform's decoders are — MP3, AAC, Ogg, whatever it reads — so a stream is
buffered and decoded there, and picked up again a moment after it drops. Until
a window is open nothing is heard, and a window opened later plays whatever is
wanted by then. A window will not make a sound until somebody has touched it;
a stream that was refused starts on the next key or tap.

`hive.audio` is a module of its own: it uses nothing of `hive.ui`, and a
program that never calls it carries none of it.
