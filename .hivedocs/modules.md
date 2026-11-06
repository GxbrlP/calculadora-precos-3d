# Modules

`import`, written outside any callable, brings another file's declarations into
scope.

```hive
import ./lib/text
import ./lib/inventory as stock

proc main(): void {
	echo text.repeat("=", 28)
	echo stock.line(stock.Item("Beeswax", 450))
}
```

## Four kinds of path, and the path says which

| written | what it names |
| --- | --- |
| `import ./lib/text` | a Hive file on this disk — `.hive` is **never** written |
| `import ./lib/util.go` | a Go file on this disk — `.go` **always** is |
| `import https://host/owner/repo/src/foo` | a file in a git repository |
| `import hive.ui` | a standard library module, which names no file |

A path may be **quoted** when it holds a space — `import "./lib/my file"` —
and nothing inside needs escaping.

## Names

* The path is **relative to the importing file's own directory**, not to where
  the compiler was run.
* A module is reached through a name: the file's own by default
  (`./lib/text` → `text`), or whatever `as` gives it. The name is `camelCase`,
  and it may not be `hive`.
* **Everything a module declares is visible.** There is no `pub`/`priv`.

## The graph

A file is **loaded once** however many modules reach for it, and **import cycles
are rejected** — direct or round any number of steps — with the loop printed.

The whole program then becomes **one module**: the entrypoint keeps its own
names and every imported module's declarations get a prefix of their own. Names
carry **no baggage across a module boundary** — two files may each declare their
own `Align` and both stay distinct types. An imported type is constructed,
annotated and matched through the name its module is reached by
(`text.Align.Left()`, a `text.Align` parameter, `style is text.Align.Left`).

Flattening has one cost: the passes after the loader report against the
**entrypoint** rather than the file a declaration came from. Lexer, parser and
import errors still name the right file.

## Importing a Go file

```hive
import ./lib/measures.go

proc main(): void {
	echo measures.grams(measures.Weight(899, "Hive tool"))
}
```

* **Every value is deep-copied in both directions**, which is why an imported Go
  function is a `func` rather than a `proc`.
* **Only what Go exports is reachable.** A callable is reached with its first
  letter lowered — `Grams` is `measures.grams` — while a type keeps its
  PascalCase.
* The signatures are read by **the Go toolchain**, not guessed at.

| Go | Hive |
| --- | --- |
| `string` / `int` / `float64` / `bool` | `Str` / `Int` / `Float` / `Bool` |
| `[]T` | `T[dyn]` |
| `[][]string` | `Table` |
| `map[K]V` | `hive.map.Map<K, T>`, with a scalar key |
| a struct the file exports | a Hive type of the same name and shape |
| `(T, error)` | `Result<T, Str>` |
| `error` alone | `Result<Bool, Str>`, whose `Ok` carries `true` |
| no result | a function answering with nothing |

Hive's `Int` *is* Go's `int`, so `int64` and the rest are **rejected** rather
than silently converted. A pointer, channel, interface, function value, variadic
parameter, fixed-size array, type from another package, or unexported field is
refused with a message saying why; a struct crosses only when *every* field of
it does. A Go map arrives with its keys **sorted**, having no order of its own.

## Importing from a git repository

```hive
import https://github.com/owner/repo/src/text
import https://github.com/owner/repo@a1b2c3/src/text        // pinned
import https://github.com/owner/repo/go/util.go as helpers
```

* `https://host/owner/repo` is the repository and everything after it is the
  path inside it. A revision goes where the repository ends: `repo@a1b2c3`,
  `repo@v1.2.0`, `repo@main`.
* The module is **named after the file inside the repository**.
* Everything is fetched **once**, into a cache shared by every program on the
  machine.
* An import naming no revision is **pinned on first use**, into a lock file
  beside the entrypoint (`main.hive` → `main.hive-lock`). Keep it in version
  control; delete a line to take the latest again.
* Fetching needs `git` on the PATH.

## The standard library

**Every module answers to its own name, with no import**: `task.sleep(10)`,
`conv.sti(text)` and a `ui.View` parameter are `hive.task.sleep(10)`,
`hive.conv.sti(text)` and `hive.ui.View`, written short. The name is held
the way a [builtin's](builtins.md) is: a declaration, an import, a local or a
parameter of the same name comes first, per module, and `hive.<module>`
reaches the library whatever was declared.

```hive
import ./lib/clock as time

proc main(): void {
	echo time.now()         // lib/clock's
	echo hive.time.now()    // the library's
	task.sleep(10)          // the library's
}
```

`import hive.net as web` gives a module another name. The path is the module
and nothing else — `import hive.ui`, never `import hive.ui.View` — and a
module this compiler does not carry (`import hive.jsno`) is refused at the
import, not at every use of it. **Nothing is imported into the program**: the
alias is a *spelling*, `web.httpServe` and `hive.net.httpServe` are the same
call, and neither changes what is linked. `import hive` is not a thing to
write.

**A module you don't use is not in your build.** Each `hive.*` module is
compiled and linked only when the program references it.

*From `spec/12-modules.md`.*
