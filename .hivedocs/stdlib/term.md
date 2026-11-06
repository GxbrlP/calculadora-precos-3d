# `hive.term`

Line-oriented terminal I/O. Running *another* program is
[term-exec](term-exec.md).

| call | answers with |
| --- | --- |
| `print(text)` | `void` — a line to **stdout** |
| `status(text)` | `void` — a line to **stderr** |
| `isTerminal()` | `Bool` |
| `read()` | `Str` |
| `readSecret()` | `Result<Secret<Str>, SecretError>` — see [`Secret`](../types.md#secret) |
| `readSecretBypass()` | `Secret<Str>` — the same, in ordinary memory; **cannot fail** |
| `args()` | `Str[dyn]` |
| `codec()` | `hive.codec.Codec<FlagError>` — the value that says command-line flags |
| `exit(code)` | `void` — nothing after it runs |

## Which stream, and why it matters

`print` is `echo` restricted to a `Str` — the same lowering. `status` writes to
**standard error**: what a program is *doing*, as against what it was asked for.
Redirecting the answer never takes the progress with it, which is what lets
`hive emit x.hive > main.go` be Go while the compiler still says where it has
got to.

`isTerminal()` is whether **standard error** is a terminal rather than a file or
a pipe — the difference between somebody sitting there waiting and output being
collected for later. A program that reports its own progress asks this first.

## Input

`read()` blocks for a line, stripped of its trailing newline, and **parks only
the calling virtual thread**. At end of input it returns whatever preceded EOF
(`""` if nothing).

`readSecret()` is that same read with the terminal's echo turned off. The echo
is put back before the call returns, and also if the program is interrupted at
the prompt. Where there is no terminal at all, the line is read exactly as
`read()` reads it and only the hiding of it is lost.

`readSecretBypass()` is that read into ordinary memory, as `bypass` is to
`hide`: never shown, but free to be swapped out, so there is no locked-memory
limit to run into and it answers a `Secret<Str>` rather than a `Result`.

## Arguments and exit

`args()` is the command-line arguments in order, **excluding the program
name** — so `args()[0]` is the first thing the user typed after it.

`exit(code)` ends the program with a status. There is no value to answer with
and nothing after it runs, which is what makes it a statement rather than a call.

```hive
proc main(): void {
	args := hive.term.args()
	if len(args) < 1 {
		hive.term.status("usage: greet <name>")
		hive.term.exit(1)
	}
	if args bounds 0 {
		echo "hello {args[0]}"
	}
}
```

## Flags into a type

`codec()` reads **command-line flags** into one of your own types through
`T.decode`, and [`encode`](../builtins.md) writes one back. It reads one line
of text, split the way a shell would, so a quoted argument stays together:

```hive
type Options {
	name: Str
	dryRun: Bool -- Flag as dry-run; Default as false;
	count: Int -- Default as 10;
}

options := Options.decode(join(hive.term.args(), " "), hive.term.codec())
if options is Result.Error(why) {
	hive.term.status("{why.path}: expected {why.expected}, found {why.found}")
	hive.term.exit(2)
}

Options.decode("--name Ada --dry-run --count=3", hive.term.codec())
encode(Options("Ada Lovelace", true, 3), hive.term.codec())
// --name "Ada Lovelace" --dry-run true --count 3
```

* **A flag always opens with `--`**: `--name value` or `--name=value`. Its name
  is the field's own, or what `Flag as` says without the dashes — so
  `--something-else` is `somethingElse: Str -- Flag as something-else;`.
* A `Bool` standing alone is `true`; followed by `true` or `false`, it is that.
* A vector is its flag repeated, once per element.
* **A missing flag is an error** unless the field has a `Default` — a `Bool`
  included — and so is one given twice for a field that is not a vector.
* Words that are no flag's value are ignored, and so is everything after a lone
  `--`. Quotes and a backslash keep a word together, and a quoted word is never
  a flag.
* Only a type without variants travels as flags, each field a `Str`, `Int`,
  `Float`, `Bool` or `Atom`, or a vector of one. A failure is a
  `hive.term.FlagError` whose `path` is the flag as written, `--count`.
