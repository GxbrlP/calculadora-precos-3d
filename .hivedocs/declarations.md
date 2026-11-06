# Declarations

A file holds imports and then declarations, in any order. There are five kinds
and **no `pub`/`priv` distinction**: everything a module declares is visible to
whoever imports it. Declarations at module level are mutually visible, so two
callables may call each other.

## `type`

See [types](types.md#declared-types) for the shapes. Every declared type gets,
derived from its declaration and emitted only where used: a deep copy, a total
order, a JSON codec and a structural digest. None of it is written by hand and
none of it uses reflection.

### Field annotations

A field may be annotated, and every annotation is about the **codecs** — what
the field is called on the wire, and what to read where the wire has nothing:

```hive
type User {
	name: Str -- JSON as username;
	age:  Int
	firstName: Str -- Default as "";
}
```

| written | means |
| --- | --- |
| `JSON as <name>;` | the key this field is read from and written as |
| `URL as <name>;` | the same, in a [query string](stdlib/net-urls.md) |
| `Flag as <name>;` | the same, as a [command-line flag](stdlib/term.md) without its dashes |
| `Default as <literal>;` | what to use where the document has `null` or nothing at all |

A `--` opens them and each clause ends at its `;`, so **they may be written
in any order** and a field may carry any of them, or none:

```hive
theme: Str -- JSON as colour_scheme; Default as "light";
theme: Str -- Default as "light"; JSON as colour_scheme;   // the same field
```

They are **compile-time**, and nothing about the Hive side of the field
changes: it is still `user.name` whatever JSON calls it, still ordered and
copied and compared as it was.

**`JSON as`, `URL as` and `Flag as` take somebody else's name**, so they are
held to none of Hive's own shapes — `user_name` is a key, and so is `user-name`,
words joined by `-`; anything else is written as a string, `"user name"`. **Two
fields of one object may not answer to one key** in any format: that is a compile
error, since the decoder would read the same member twice and the encoder would
write it twice. The names are independent, so none of them changes another
format's key. A flag is named **without its dashes**: `Flag as dry-run;` is
`--dry-run`.

**`Default as` takes a literal** — an `Int`, `Float`, `Str`, `Bool` or
`Atom`, with a leading `-` for a negative number — and it has to be a value
the field can hold. What it stands in for is a key that is **absent** and a key
that is present and **null**, which are one nothing; without it, either is an
error. It stands in for nothing else, so a value of the **wrong type** is still
an error: a default is for what was never said, not for what was said wrongly.

`--` is the same two characters the decrement step is written with, and there
is nothing to tell apart — a step is a statement, and a type body holds no
statements. It needs no space behind it, and `JSON`, `URL`, `Flag`,
`Default` and `as` are not reserved words.

## `func` and `proc`

```hive
func greet(name: Str, style: Greeting): Str {
	if style is Greeting.Formal(title) {
		return "Good evening, {title} {name}."
	}
	return "Hey {name}!"
}

proc grow(vec: mut Str[dyn], tag: Str): void {
	append(vec, tag)
}
```

A `func` **may perform I/O** — `echo`, `hive.file`, `hive.net` are all allowed —
and it **may call a `proc`**. It differs from a `proc` in exactly one way: it
cannot declare a `mut` parameter (`v: mut T`), and a `mut` value passed to a
`func` is seen as an ordinary immutable copy instead.

So what a `func` promises is not mathematical purity but that it cannot write to
storage its caller can see — and that one rule is the whole of what keeps it.
A `mut` parameter has to be handed a `mut` variable or a path into one, and the
only `mut` variables in a `func` are its own, so whatever a `proc` it calls
writes through, the caller cannot see it. A `proc` may do everything a `func`
may, plus declare a `mut` parameter. Programs start at `proc main(): void`, in the file handed to
`hive build` / `hive run`; any other signature for `main` is refused — the
command line is `hive.term.args()` and an exit status `hive.term.exit(code)`.

Parameters are `name: Type`, or `name: mut Type` in a `proc`. Every callable
declares a return type, `void` included.

## Returning on every path

Every non-`void` `proc` and `func` must return on every path. A path terminates
by ending in:

* `return`;
* `panic`, or a call to `hive.term.exit` — both handy for a tail you know
  is unreachable (an `assert` that holds carries on, so it does not count);
* an `if`/`else` whose every branch terminates;
* a `switch` whose every arm terminates — a `switch` takes every value of its
  subjects, so there is no path around it ([statements](statements.md)); or
* an **else-less** `if`/`else if` chain whose every branch terminates and whose
  patterns take every value of its subject — a `Result`'s `Ok` and `Error`,
  every variant of a declared union, nested as deep as they go
  ([patterns](patterns.md)).

```hive
func describe(shape: Shape): Str {
	if shape is Shape.Circle(r)            { return "circle" }
	else if shape is Shape.Rectangle(w, h) { return "rectangle" }
	else if shape is Shape.Point           { return "a point" }
}                                          // no `else` — adding one is an error
```

## `query`

A `func` whose body is inline SQL and whose return type describes its rows. It
has a page of its own: [queries](queries.md).

## `test`

```hive
test "an empty cart costs nothing" {
	Item[0] empty = []
	assert total(empty) == 0
}
```

Named in prose, takes no parameters, returns nothing. `return value` inside one
is a compile error; a bare `return` to leave early is fine. See
[testing](testing.md).

## `import`

Written outside any callable. See [modules](modules.md).

## Nothing about a declaration says how it runs

**Every call blocks its caller.** There is no `async func`, no Future and no
Promise type to name; what a call means is decided where it is written
([concurrency](concurrency.md)). The two callable kinds are about *what a body
may do*, never about *when it happens*.

*From `spec/04-declarations.md`.*
