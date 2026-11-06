# `hive.file`

General filesystem access. Contents move as `Str`, which holds bytes rather
than validated text, so **a binary file survives a read/write round trip**.
Reading a whole [`Table`](../tables.md) out of one — `csv`, `xlsx`, `ods` —
lives here too.

| call | answers with |
| --- | --- |
| `read(path)` | `Result<Str, FileError>` |
| `lines(path)` | `Result<Str[dyn], FileError>` |
| `write(path, contents)` | `Result<Int, FileError>` — the bytes written |
| `append(path, contents)` | `Result<Int, FileError>` |
| `size(path)` | `Result<Int, FileError>` |
| `copy(from, to)` | `Result<Int, FileError>` |
| `delete(path)` | `Result<Bool, FileError>` |
| `makeDir(path)` | `Result<Bool, FileError>` |
| `move(from, to)` | `Result<Bool, FileError>` |
| `list(path)` | `Result<Str[dyn], FileError>` |
| `exists(path)` | `Bool` — **not** a `Result`; a directory counts |
| `csv(path, separator)` | `Result<Table, TableError>` |
| `xlsx(path)` | `Result<Table[dyn], TableError>` — one per sheet |
| `ods(path)` | `Result<Table[dyn], TableError>` — one per table |

A `FileError` is `NotFound`, `Permission`, `Exists` or `Io`, each carrying the
`path` and the underlying `message`. A file that
opened and then turned out not to hold what it said it did is not a filesystem
failure, so the readers answer with a `TableError` of their own, carrying the
`path` and a `message`.

**The separator is always written.** There are no optional parameters in Hive,
and a comma is a choice like any other rather than the one the language makes
on your behalf. It is one character, and a longer one is an error. Which reader
a program names is also what lets the compiler leave the others out of the
build: one that reads a CSV carries neither `archive/zip` nor `encoding/xml`.

A CSV's rows keep the length they have — a ragged file is a ragged `Table` — blank
lines are skipped, and a byte-order mark at the start is dropped.

```hive
if hive.file.read("./notes.txt") is Result.Ok(text) {
	echo text
}

if hive.file.write(path, rendered) is Result.Error(why) {
	echo "cannot write {path}: {why.message}"
}
```

## Worth knowing

* `lines` splits on newlines, **dropping the empty piece a trailing newline
  leaves** and any Windows carriage returns.
* `write` replaces a file, creating it when absent; `append` adds to the end.
  **Neither creates missing parent directories** — call `makeDir` first.
* `writeSecret(path, contents)` writes a [`Secret<Str>`](../types.md#secret), leaving the file **readable by the user running the
  program and nobody else**: mode `0600` on Linux and macOS, and on Windows an
  access list naming that one account, protected so the containing folder
  hands nothing down. Who may read it is settled **before any of the secret is
  in it**, and a file that was already there is narrowed rather than trusted.
  A file owned by somebody else is an `Error` rather than a secret written in
  the clear. Permissions are all it is, so it is **not encryption**: an
  administrator, and `root`, can read any file on the machine.
* `makeDir` creates a directory **along with any missing parents**, and is not
  an error when it is already there.
* `delete` removes a file, or an **already-empty** directory.
* `list` answers **sorted and without any leading path** — the names in the
  directory, not paths to them.

A test runs with the working directory set to the generated project rather than
the entrypoint's folder, so **a test that needs files should write them itself**
with `makeDir` and `write`. See [testing](../testing.md).
