# `hive.term` — running another program

Three calls. The difference between the first two is **who is talking to the
terminal**; the third is the first with an environment.

| call | answers with |
| --- | --- |
| `exec(command, arguments, directory)` | `Result<Str, ExecError>` |
| `attach(command, arguments, directory)` | `Int` — the exit status |
| `execWith(command, arguments, directory, environment)` | `Result<Str, ExecError>` |

`arguments` is a `Str[]` and `directory` is a `Str` — empty meaning where this
program is. `environment` is a `hive.map.Map<Str, Str>`.

**The arguments are a vector rather than a line of text, and that is the whole
of the safety story**: nothing is handed to a shell, so nothing in an argument
can be read as one. A command that needs a shell asks for one by name.

## `exec` captures, `attach` hands the terminal over

`exec` hands back **everything the command wrote** — standard output and
standard error together, in the order it wrote them, which is the order somebody
reading a terminal would have seen. **A status other than zero is an `Error`**,
because a command that failed is not a command that answered.

An `ExecError` carries the `command`, the `code`, the `output` and a `message`.
The output is on it because that is usually the whole of why it failed, and a
command that could not be started at all has a `code` of `-1`.

```hive
if hive.term.exec("go", ["build", "."], buildDirectory) is Result.Error(why) {
	echo "the build failed:\n{why.output}"
	hive.term.exit(1)
}
```

`attach` gives the command **this program's own terminal** — its input, its
output, its errors — and answers with the `Int` status it exited with. Nothing
is captured, because the point of it is that the command is talking to whoever
started this program.

## `execWith` is an overlay, never a replacement

Its map's pairs are set for the command **on top of** the environment this
program was started with. That is deliberate: a replaced environment is a much
sharper tool — a command with no `PATH` finds no programs and one with no
`HOME` finds no caches — and nothing that wants to set one variable wants those
as well.

So an **empty map is exactly `exec`**, byte for byte, and a name the environment
already holds is replaced rather than joined by a second.

```hive
mut hive.map.Map<Str, Str> asked = hive.map.new()
hive.map.set(asked, "GOOS", "linux")
hive.map.set(asked, "GOARCH", "arm64")

// `go env GOOS` now says `linux`, and `go` is still found on the PATH.
hive.term.execWith("go", ["build", "."], buildDirectory, asked)
```

This is what `hive build --target` is built on.
