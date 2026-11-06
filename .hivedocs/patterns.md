# Patterns

`is` checks a value against a pattern. It is an ordinary expression yielding a
`Bool`, written in an `if` — or, for several values at once, as the arms of a
`switch` ([statements](statements.md)). When it matches it narrows the value and
binds parts of it to fresh names, usable in the rest of the same condition after
`&&` and in the branch body.

Four kinds of thing can be matched.

## Variant patterns

```hive
value is Type.Variant(a, b)
value is Type.Variant          // a variant that carries nothing

if shape is Shape.Circle(r) {
	echo r
} else if shape is Shape.Rectangle(w, _) {
	echo w
}
```

Fields are bound **by position**; `_` matches one without binding it, and a
pattern or a literal in its place matches what it holds (see below). A partly
written argument list is not allowed: **name every field or none**. An imported
type is matched through the name its module is reached by
(`style is text.Align.Left`).

## `Result` patterns

```hive
if indexOf(names, "bob") is Result.Ok(i) { }     // the call runs once
if parsed is Result.Error(problem) { }
```

## Vector patterns

```hive
v is ["a", x]                  // exactly two; first equals "a", second binds
v is ["a", x, ...rest]         // at least two; `rest` binds the leftovers
```

Each position is a **literal** to match (`"a"`, `3`, `#Atom`, `true`), a **name**
to bind, `_` to skip, or a **pattern** of its own. A trailing `...rest` relaxes the length from an exact
count to a lower bound; without one, the pattern matches only a vector of
exactly that length.

## String patterns

A template: literal text that must match verbatim, plus holes that bind the text
spanning each one.

```hive
path is "/health"                        // hole-less: an exact match
path is "/users/{id}/posts/{postId}"
path is "/files/{rest}"                  // a trailing hole runs to the end
```

* The template must cover the **whole** string.
* Matching is **non-greedy**, so a hole between two `/` never swallows a `/`.
* Holes must be plain binding names, and two **open** holes may not sit side by
  side — the split point would be ambiguous. Both are compile errors.

### A hole may say what it takes

`{name}` takes any text; `{name is (regex)}` takes only text matching the
regex, and binds it the same way:

```hive
if line is "{user is (\w+)}@{host is ([\w.]+)}" {
	echo "{user} at {host}"
}
if path is "/api/v{version is (\d+)}/{rest}" { }
```

**Nothing inside the parentheses is escaped by the string**, so `{year is (\d{4})}`
is four digits rather than an interpolation of `4`. That is also why a hole is
written in a `"..."` pattern and never a backtick one.

**The regex is read at compile time**, so a malformed one is a compile error. The
syntax is Go's RE2: **no backreference and no lookaround**, both refused by name.
A group inside a hole groups and does not capture — the hole is already the
binding — and a named group is a compile error for the same reason.

## Binary patterns

`<<...>>` reads a subject's bits in order, most significant first, each field as
many as its type has:

```hive
if packet is <<version: UInt4, ihl: UInt4, _: UInt8, length: UInt16, ...rest>> {
	echo "IPv{version}, {length} bytes"
}
if file is <<0x89, "PNG", size: UInt32, body: UInt8[size], ...more>> { ... }
```

A field is `name: UInt4` (that many bits, binding that type), `name` (one byte),
a literal to match (`0x45`, `0x45: UInt16`, `"PNG"`), `_: UInt3` to skip, or a
run of bytes, `body: UInt8[size]`, whose length is an earlier field or anything
in scope. `...rest` takes what is left — a `Str` for a `Str`, a `UInt8[dyn]`
otherwise. Multi-byte fields are big-endian; `size: UInt32 little` reads the
other way round.

The subject is a `UInt8[]`, a `Str` (by its bytes, without a copy) or an integer,
whose bits the fields take every one of: `op is <<code: UInt4, reg: UInt4>>` on a
`UInt8`. The match checks the length, so no field needs a bounds proof. Where each
field starts within a byte is known at compile time, so fields that come to part
of a byte, and a run, a string or a rest that starts mid-byte, are compile errors.
A `switch` over binary patterns ends with `_`.

## Patterns inside patterns

A position that binds a name — a variant's field, a vector's element — may hold a
pattern instead, and the whole is still one match:

```hive
if foo() is Result.Ok(Foo.Bar(["foo/{padding}/bar", ...rest])) { }

// exactly this, compiled the same way:
if foo() is Result.Ok(result) && result is Foo.Bar(values) && values is [head, ...rest] && head is "foo/{padding}/bar" { }
```

Each part is bound to a name no program can write and tested once the pattern
around it matched, outer parts first, so every rule of a chain holds: the subject
is evaluated once, the bindings reach the rest of the condition and the body, and
`!` cannot negate one.

* A variant's position may also hold a **literal** it has to equal:
  `Result.Ok(3)`, `Pair.Of("bees", n)`.
* **A pattern binds a name once**: `Pair.Of(a, Result.Ok(a))` is a compile error.
* **A variant pattern matches only its own type**, at any depth.

## Exhaustiveness

An **else-less** `if`/`else if` chain whose branches take every value of its
subject is a terminating path, which is what lets a total function over a union
be written without a dead `else`:

```hive
func describe(shape: Shape): Str {
	if shape is Shape.Circle(r)            { return "circle" }
	else if shape is Shape.Rectangle(w, h) { return "rectangle" }
	else if shape is Shape.Point           { return "a point" }
}
```

* **Coverage follows nesting**: `Result.Ok(Foo.Bar(_))`, `Result.Ok(Foo.Baz)` and
  `Result.Error(_)` take every `Result<Foo, E>`. A hand-written chain on the
  pattern's own bindings counts the same, since that is what a nested pattern is.
* A **vector** is covered by length — `[]` and `[x, ...rest]` take every one — and
  a `Bool` by `true` and `false`. Numbers, atoms and strings have no finite
  cover; only a template that is one open hole, `"{s}"`, takes every string.
* The subject is a variable, or a path of fields and indexes from one; a call is
  not, since it may answer differently each time. A chain may cover any one of
  the subjects its branches open by matching.
* **A branch whose condition goes on past its pattern** — `r is Result.Ok(n) && n > 0`
  — takes only part of what the pattern does, so it covers nothing.

When a chain falls short, the error names a value no branch takes: `r` when it
is `Result.Ok(Foo.Baz)`.

## `switch`

A `switch`'s arms are held to two rules a chain is not, both compile errors:

* **Every value has an arm.** Coverage is the chain's, over all the subjects
  together: `Shape.Point, _` covers a point with any fill. The error names a value
  no arm takes — `Shape.Circle(_), Fill.None` — and a subject that is a number, an
  atom or a string needs a `_` for it. A call is as good a subject as a variable,
  since it is evaluated once.
* **Every arm can run.** An arm the arms above it already take all of — anything
  after `_, _`, a literal written twice — is refused by its number, `arm 3`.

A binding's `else` (`Result.Ok(n) := r else { ... }`) is held to both, with the
pattern as its first arm: the error names a value neither takes, and an arm the
pattern already takes can never run.

`Fuzz.Variable()` still names no fields, so it only matches a variant that has
none; `Fuzz.Variable` or `Fuzz.Variable(_)` takes one whatever it carries.

## Narrowing and scope

A binding introduced by `is` is **immutable**, is in scope for the rest of the
condition after `&&` and for the branch body, and is **out of scope in an
`else`**, where the pattern did not match. Narrowing is per branch: outside one,
a union value still has only the fields every variant shares.

**A match cannot be negated.** `!(x is Shape.Circle(r))` is a compile error,
because narrowing and binding are exactly what a `!` would throw away — the
branch under one is the branch where the pattern did *not* hold, so `r` could
never be set. The other case goes in the `else`. See
[expressions](expressions.md).

*From `spec/07-patterns.md`.*
