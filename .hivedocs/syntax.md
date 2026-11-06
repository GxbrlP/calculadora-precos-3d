# Syntax

A source file is UTF-8 text ending in `.hive`. It has no header: what it
declares is what it holds. Hive is **not** indentation-sensitive and no
statement is terminated by a newline; a `;` on its own is skipped.

```hive
// A comment runs to the end of the line. There is no block comment.
x := 1 // ...or takes the tail of one.
```

## Keywords

Every keyword is lower case, and **only that spelling is reserved**:

```
import   proc     func     query    test     type
if       else     return   is       with     switch
void     true     false    echo     assert   panic
dyn      mut      async    await    for      in
each     bounds   break    continue
```

Any other casing is an ordinary name: a union may have a variant called
`Return`, a type may be called `Query`, and a variable `proC`. A field cannot
be called `type`, since that is the keyword itself.

Two words are keywords only where they are written and are ordinary names
everywhere else: `as` (after an import path) and `timeout` (in
`with timeout`). So a variable may be called `timeout`.

## Names have shapes, and the shape is enforced

| shape | what it names |
| --- | --- |
| `camelCase` | variables, parameters, fields, every `proc`/`func`/`query`, an import's name |
| `PascalCase` | types, their variants, and atoms |
| `UPPER_CASE` | **also** allowed for a variable nothing reassigns — a constant |

Precisely: `camelCase` is a lower-case letter then ASCII letters and digits;
`PascalCase` is an upper-case letter then the same; `UPPER_CASE` is an
upper-case letter then upper-case letters, digits and underscores.

### `UPPER_CASE` is allowed, never required

**`camelCase` is the default spelling of every variable, whether or not anything
reassigns it.** `UPPER_CASE` is a second shape an *immutable* variable may take,
for a value the program treats as a constant — and taking it is your choice:

```hive
retries := 3            // fine
MAX_RETRIES := 3        // also fine, and says the same thing louder
```

Nothing is inferred from the choice, because **what makes a binding immutable is
the absence of `mut`, never its spelling**. Most immutable variables are written
`camelCase`, being ordinary values that happen not to be reassigned rather than
constants anybody would call one.

The option belongs to **variables alone**: a parameter, a field, a callable, an
import's name and a name bound by a pattern or a `for each` are `camelCase` and
nothing else, however fixed the value behind them is.

A **`mut` variable may not be `UPPER_CASE`** — that shape claims constant about
something about to be reassigned — and a counting loop's counter is held to the
same rule. That is the one direction the rule runs in: `mut` rules the shape
*out*, and nothing ever rules it in.

Any name may open with a single `_` (`_scratch`, `_MAX`); what follows is spelled
as it would be without it, and the compiler asks nothing of the prefix. On its
own, `_` throws a value away.

## Literals

`42` is an `Int` (64-bit, signed; `-1` is unary minus applied to `1`). `0xFF` is
hexadecimal, `0b1010` binary, and `_` may sit between digits: `1_000_000`. A
hexadecimal or binary literal is the 64 bits it spells, so one past `Int`'s largest,
`0xFFFF_FFFF_FFFF_FFFF`, is a `UInt64`.
`1.0` is a `Float` — a leading or trailing dot is **not** a float.
`true` / `false` are `Bool`. `#Ready` is an `Atom` and must be PascalCase.
`[a, b, c]` is a vector.

## The two string forms

**`"..."`** takes escapes and `{expression}` interpolation:

| escape | means |
| --- | --- |
| `\n` `\t` `\r` | newline, tab, carriage return |
| `\"` `\\` | a quote, a backslash |
| `\{` | a literal `{`, not an interpolation |
| `\X` | any other `X` is itself |

A newline inside one is part of it. A backtick has no meaning in one, so
`"` + a backtick + `"` is how a backtick is written at all.

## The operators

| | |
| --- | --- |
| three-character | `...` (the vector-pattern rest marker), `<<=` `>>=` |
| two-character | `:=` `>=` `<=` `==` `!=` `**` `&&` `\|\|` `++` `--` `+=` `-=` `*=` `/=` `&=` `\|=` `^=` `<<` `>>` `\|>` |
| one-character | `{` `}` `(` `)` `[` `]` `:` `;` `,` `.` `>` `<` `=` `+` `-` `*` `/` `%` `\|` `&` `^` `~` `!` |

The longest spelling that fits wins, so `...` is matched before `.` and `!=`
before `!` — which is what makes a `!` reaching the last row one standing on
its own: the negation. See [expressions](expressions.md).

**A backtick string** takes `{expression}` interpolation too, but its one escape is
`\{`: a `\` before anything else is itself. It may span lines and
**cannot contain a backtick**. Its indentation is removed at compile time, before
interpolations are read — leading and trailing blank lines dropped, then the
longest common leading whitespace of every non-blank line — so it says what it
looks like:

```hive
func goSource(name: Str): Str {
	return `
		package {name}

		func Assert(ok bool) \{ }
	`   // for "main", opens at column 1: "package main\n\nfunc Assert(ok bool) { }"
}
```

A tab and a space each count as one character of indentation.

## Two places the lexer stops reading Hive

* After **`query`**, the `{ ... }` is raw SQL, captured to its matching brace and
  dedented, with its `{param}` interpolations left for the parser.
  See [queries](queries.md).
* After **`import`**, what follows is a path rather than tokens: everything to
  the next whitespace. A quoted path (`import "./lib/my file"`) needs no
  escaping inside, and `as` after it still reads as `as`.

Inside a `query` body, SQL's own `--` and `/* */` comments are recognised, and
SQL keywords keep SQL's upper-case convention.

*From `spec/01-lexical.md` and `spec/02-grammar.md`.*
