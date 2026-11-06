# The `hive` command line

```
hive check     <entrypoint.hive>       Report any errors, build nothing
hive emit      <entrypoint.hive>       Print the generated Go source
hive build     <entrypoint.hive>       Compile to a native executable
hive export    <entrypoint.hive>       Package as an app, for a handset
hive run       <entrypoint.hive> [..]  Compile and run
hive test      <entrypoint.hive>       Run the program's tests, with coverage
hive test      <directory>             Run every test under it, git-ignored files aside
hive analyze   <entrypoint.hive>       Score what it will cost, and write a page
hive container <entrypoint.hive>       Write a Dockerfile that builds and runs it
hive agents                            Write .hivedocs/ for coding agents
hive indent    <directory or file>     Indent every Hive file there with spaces
hive version                           Print which release this compiler is

  --target <goos>/<goarch>             Build for another platform, on `build` and
                                       `export` alone
```

The entrypoint is the file holding `proc main(): void`, and a program is that
file plus everything it imports.

## Which to reach for

* **`hive check`** runs every compiler pass and stops before the Go toolchain, so
  it answers as fast as the front end does and writes nothing next to the file.
  It is the one to run on every save, and the one to run after an edit.
* **`hive test`** runs the suite with coverage and **exits non-zero when any
  test fails**.
* **`hive run`** compiles and runs, forwarding everything after the entrypoint
  to the program and chdir'ing to the entrypoint's folder. The program's exit
  status becomes the command's.
* **`hive build`** leaves the executable beside the entrypoint and the generated
  Go module in `<entrypoint>-build/`.
* **`hive emit`** prints the Go to stdout, so `hive emit x.hive > main.go`
  works — progress and every error go to stderr for exactly that reason.
* **`hive analyze`** scores what the program will cost to run, and lists what it
  declares and never reaches. It builds nothing and runs nothing, so it answers
  about as fast as `check` does.

`--target` belongs to `build` and `export`; `go tool dist list` names every
platform `build` takes. A flag a command does not know is **refused rather than
quietly dropped**, and so is anything after the entrypoint of a command that
takes nothing more. A compile error opens with `file:line:` — in the imported
file it happened in — and a usage error with `hive:`; both exit non-zero.

## `hive export`

```
hive export chat.hive --target android/arm64     writes chat-android-arm64.apk
```

The same program `hive build` writes, with a WebView host in front of it, signed
and installable as it stands. **No Android SDK and no network**: the manifest,
resource table and APK Signature Scheme v2 signature are written by the build,
under a key made on first use at `~/.hive/android.key` so a later build installs
over an earlier one. The application id comes from the entrypoint —
`chat.hive` is `hive.chat` — and `assets/icon.png` is the launcher icon.

* `android/arm64` is the only Android target, and a program that opens no window
  is refused: an app with nothing to show has no way to start.
* The app asks for `INTERNET` and `ACCESS_NETWORK_STATE`; its `$HOME` and
  working directory are its own files directory, and what it prints goes to
  logcat.
* It runs with `GOGC=off` and `GOMEMLIMIT=256MiB`, because a window rebuilds
  its world every frame over a small live heap. An intent extra named
  `HIVE_FOLDS`, `GOGC` or `GOMEMLIMIT` reaches the program's environment
  (those three alone), and `HIVE_INSPECT` lets `chrome://inspect` attach:

```
adb shell am start -n hive.chat/dev.hive.app.MainActivity --es HIVE_FOLDS 1
```

## Diagnostics

Every error opens with where it happened, and nothing is printed in front of it:

```
main.hive:12: cannot prove this index is in range: the index is a computed
    expression. Bind it to a variable and guard it (`if j >= 0 && j < len(v)`).
```

`file:line: message`, with a message that runs on continuing on **indented**
lines so one error stays one entry in a quickfix list. For Vim or Neovim:

```vim
setlocal makeprg=hive\ check\ %:S
setlocal errorformat=%-G\ %.%#,%f:%l:\ %m,%-G%.%#
```

**Two limits worth knowing.** Errors from the passes after parsing land on a
**declaration** rather than a statement, and in a program with imports those
same errors are reported against the **entrypoint** even when the declaration at
fault came from an imported module — flattening is what discards which file it
came from. Lexer, parser and import errors do name the right file and line.

## `hive analyze`

Reads the program the emitter is about to write, scores every `proc` and `func`
out of a hundred, prints the worst of them and writes the whole thing as
`<entrypoint>-analysis.html` beside the entrypoint. It takes an entrypoint and
no flags. Nothing is built and nothing is run:

```
  chat.hive scores 93/100 over 37 callables
  8 findings — 7 copies to pay for, 1 wait inside a loop

  50  greet                               proc, line 512
        ×8     hive.task.sleep(500)
             `hive.task.sleep` waits on the clock, once per turn of the loop
```

What it looks for is a loop inside a loop, a linear search inside one, a name
rebuilt out of itself a turn at a time, a call inside a loop that nothing the
loop changes is handed to, something that waits on a disk, a network, a
database or another process once per turn — and the one a language of values
has that others do not, an **implicit deep copy**.

A copy is the only one of those that is not a guess. `writes` has already
worked out which fields a copy has to walk, so a copy this names is one the
emitter will really emit, at about the size it says. **Everything else is a
weight rather than a measurement**: no compiler knows how many times a loop
goes round, so a finding inside two of them is multiplied by a constant and
not by a length.

The score is logarithmic — every doubling of the cost costs ten points — because
a cost here runs from four to thirty thousand and a linear curve would put
everything past the first loop at zero. A callable cheap enough to say nothing
about scores 100.

**It also lists what is never reached** — every `func`, `proc`, `query` and type
that nothing reached from `main` or a test names, however indirectly — and every
parameter its body never reads:

```
  2 declarations never reached from `main`:
        cart.oldTotal                       func, line 40
        cart.legacyTax                      func, line 52 — named only by cart.oldTotal

  1 parameter never read:
        cart.price                          `currency`, line 18
```

A declaration named only by unreached code is listed too, beside what names it.
A parameter starting with `_` says it is unused on purpose and is left out, and
so is every parameter of a callable passed as a value, whose shape is the slot's
to decide. A file with neither a `main` nor a test lists nothing.

## `hive container`

Writes a Dockerfile into the folder it runs in — `Dockerfile`, or
`Dockerfile-hive-container` when one is already there — and says which. A program
that does not compile gets its errors instead, as `hive check` would give them:

```
hive container main.hive
docker build -t main .
docker run --rm -p 8080:8080 main
```

Nothing but Docker is needed. The first stage downloads Go and **the compiler
that wrote the file**, named in `ARG HIVEC_VERSION`, so an image never
follows a newer release on its own; the second is the executable alone on
`distroless/static`. What is not a template is read off the program: a
`hive.net.httpServe(8080, ...)` becomes `EXPOSE 8080`, and an import naming a
repository puts `git` in the build stage.

## `hive agents`

Writes this documentation. It takes no entrypoint and no flags, rewrites its own
files under `.hivedocs/` from the compiler that is running, and leaves anything
else in that directory alone. It also creates an `AGENTS.md` if there is none,
adds `.hivedocs/` to a `.gitignore` that has one, and puts `@AGENTS.md` at the
top of a `CLAUDE.md` that does not open with it. **Run it again after upgrading
the compiler.**

## `hive indent`

Rewrites the indentation of every Hive file under a directory that git does not
ignore, or of one file, in spaces: a tab moves to the next multiple of four. It
names each file it changed. **What a literal holds is never touched**, so the
program reads the same text afterwards: a `"..."` string spanning lines keeps
every character, and a backtick string or a query body only loses its tabs in the
indentation the compiler strips from it anyway. A file that does not lex is left as
it was and named, and the command exits non-zero.

*From `spec/17-diagnostics.md` and the compiler's own `src/hivec.hive` and
`src/analyze.hive`.*
