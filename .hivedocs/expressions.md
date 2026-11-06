# Expressions

## Precedence, loosest to tightest

| level | operators | associativity |
| --- | --- | --- |
| 1 | `\|\|` | left |
| 2 | `&&` | left |
| 3 | `is`, `bounds` | non-associative |
| 4 | `>` `<` `>=` `<=` `==` `!=` | non-associative |
| 5 | `&` `\|` `^` `<<` `>>` | left, one of them at a time |
| 6 | `+` `-` | left |
| 7 | `*` `/` `%` | left |
| 8 | `\|>` | left |
| 9 | unary `-`, `!`, `~` | prefix |
| 10 | `**` | right |
| 11 | a `with` clause | postfix |
| 12 | call, index, slice, member | postfix, left |

Unary `-` binds **tighter** than `* / %` and **looser** than `**`, so `-2 ** 2`
is `-(2 ** 2)` and `2 ** -3` reads the sign as part of the exponent. `!` binds
at that same level.

The bitwise operators bind tighter than a comparison, so `x & 1 == 0` asks
about `x & 1`. They have **no order** among themselves or against arithmetic:
two different ones side by side, or one beside `+ - * / % **` outside
parentheses, are a compile error — `(x >> 4) & 0xF`, never `x >> 4 & 0xF`.

`|>` binds tighter than every binary operator and looser than the prefix ones,
which is what lets a pipeline stand on either side of one — `v |> len > 2`
compares the length. It takes the value written **beside** it, so `1 + 2 |> f`
is `1 + f(2)` and a computed value is parenthesised: `(1 + 2) |> f`.

## What the operators do

| operator | on | yields |
| --- | --- | --- |
| `+` | `Int`, `Float` / `Str` / vectors | the sum / concatenation / a **new** vector |
| `-` `*` `/` `%` `**` | `Int`, `Float` | arithmetic |
| unary `!` | `Bool` | the opposite |
| `==` `!=` | any two values of **one** type | structural equality |
| `<` `>` `<=` `>=` | `Int`, `Float`, `Str` | ordering |
| `&&` `\|\|` | `Bool` | short-circuiting |
| `is` | see [patterns](patterns.md) | a `Bool`, binding as it matches |
| `bounds` | a vector and an `Int` | sugar for `i >= 0 && i < hive.len(v)` |
| `&` `\|` `^` | two integers of one type | bitwise and, or, exclusive or |
| `<<` `>>` | an integer, and a count that is unsigned or a literal | shifted; the left side's type |
| unary `~` | an integer | every bit flipped |
| `\|>` | a value and a callable | sugar for the call with the value first |

Comparing values of two different types is a compile error, not a silent
`false`, and there is **no implicit numeric conversion** anywhere.

## Bits

`&`, `|` and `^` take two integers of one type and answer it; `~x` flips every
bit. A shift answers its left side's type whatever the count is, and the count
is an **unsigned integer or a literal**, so it is never negative — an `Int` one
is converted, `x << UInt8(n)`. A right shift copies a signed type's sign bit.
Every result stays within its type's width, as arithmetic's does, and `~` on a
literal is worked in the type it lands in: `UInt8 m = ~0x0F` is `0xF0`. A
`Bool` takes none of these: `&&`, `||`, `!=` and `!` are its own.

`<<a, b, c>>` builds a `UInt8[dyn]` from its parts in order, most significant
bit first, each as wide as its type: a `UInt4` writes four bits, a `UInt16` two
bytes, a `UInt8[]` or a `Str` its bytes. A literal is a byte unless it says
otherwise, `0x0D0A: UInt16`, and `little` writes a part's bytes the other way
round. The parts come to whole bytes, a run of bytes starts on one, and both
are checked at compile time. The way back is a [binary pattern](patterns.md).

```hive
func fnv1a(text: Str): UInt32 {
	mut UInt32 hash = 0x811C_9DC5
	for each b in hive.conv.bytesOf(text) {
		hash = (hash ^ UInt32(b)) * 0x0100_0193
	}
	return hash
}

UInt8[dyn] header = <<UInt4(4), UInt4(5), 0, length, payload>>
```

## Unary `!`

It takes a **`Bool`** and answers with the opposite one. Anything else is a
compile error, for the reason a condition may not be one: there is no
truthiness, so there is nothing about an `Int`, a `Str` or an `Atom` to be the
opposite of.

It binds where unary `-` binds, which is **tighter than every comparison and
every conjunction**:

```hive
if !found { }                  // the whole of what it is for
echo !isEven(3)                // the call is the operand, not `isEven`
if !found && ready { }         // (!found) && ready
if !(a == b) { }               // parentheses, because `==` is looser
if !(v bounds i) { }           // the same, and this proves nothing about `i`
```

It is not the only way to say it and does not make the others wrong:
`found == false` is an ordinary comparison and
`indexOf(v, x) is Result.Error(_)` an ordinary match.

### A match cannot be negated

**`!` may not be applied to an expression holding an `is`**, and that is the one
`Bool` it refuses:

```hive
if !(x is Shape.Circle(r)) { }        // compile error
if !(ready && (x is Shape.Point)) { } // the same, through the `&&`
```

The reason is what `is` does beyond answering: it **narrows** the value it
matched and **binds** parts of it, and neither survives being negated — the
branch under a negated match is the branch where the pattern did *not* hold, so
`r` above could never be set.

**The other case goes in the `else`**, which is where it always went. The
refusal reaches through `&&`, `||` and a second `!` and no further, and a `!`
*beside* a match is untouched: `!a && (x is P)` negates `a` and nothing else.

## Interpolation

`"{expr}"` splices a value into a string, rendering a non-`Str` piece the way
`echo` does. `\{` is a literal brace. **This is the only implicit conversion in
the language, and it goes one way**: a value becomes text, never the reverse.

```hive
echo "loaded {len(rows)} of {total}"
```

## Calls and named arguments

Funcs, procs, queries and type constructors — the library's own record types
included — accept arguments by name:

```hive
f(b: 1, "s")
```

Named arguments may appear anywhere; only the unnamed ones need to be in order.
Names must exist, must not repeat, and **once named arguments are used the call
must cover the full parameter list**. They are evaluated in the order written.
A builtin and a library call take names too — `join(sep: ",", vector: v)`,
`hive.math.clamp(value: x, low: 0.0, high: 1.0)` — by the names their pages
give them.

### Piping a value in

`x |> f(a)` is **sugar** for `f(x, a)`: the value on the left becomes the
call's first argument. `|>` is left-associative, so a chain of them reads in
the order it runs.

```hive
echo nums |> filter(isEven) |> map(label) |> join(" ")
```

What stands on the right has to be something that can be called — a call, a
callable's name, or a constructor — and a stage with nothing else in it needs no
parentheses: `x |> f` is `f(x)`, as `x |> f()` is. A `proc`, a builtin
and a constructor all pipe, and a `_` in a stage still makes that call a
partial application: what a pipe leaves behind is the call somebody could have
written by hand.

## Function values

A callable is a value you can pass, store and call later. Two spellings:

```hive
f := takes                              // a bare reference
handler(_, db)                          // a partial application
hive.net.httpServe(8080, handler(_, db))
```

Each `_` becomes a parameter of the resulting function, **in hole order**, and
everything supplied is captured by value where it was written. A **constructor**
may be partially applied and means the same: `Msg.Changed(_)` is a
`func(Str): Msg`.

A constructor has **no bare reference**: a variant is a value once it is built,
so `Msg.Changed` on its own is a compile error and the hole is what makes one
a function value.

A callable with a **`mut` parameter** is a value like any other: `grow(_, "x")`
is a `proc(mut Str[dyn]): void`. A `mut` position in a partial application
stays a hole, since what is supplied is captured by value. A call through a
function value is held to its type — how many arguments, what each one is, and a
`mut` variable wherever the type says `mut` — and by position only: its
parameters have no names, so a named argument is refused.

Two things cannot become values: a **builtin** or **library call** (neither a
bare reference nor a `_` hole makes one — wrap it in a `func` of your own), and
a **generic** callable. A callable with a statically-sized parameter is a value
whose type carries the promise ([bounds](bounds.md)). What a partial application
is given is captured when it is written, not read again at each call.

## Member access, indexing, slicing

`x.field` reads a field; `x.member` reads through an import alias or a library module's name, the two told
apart by what the left side names. `v[i]` indexes; `v[lo:hi]` slices with **both
bounds inclusive** — `t[1:3]` is three elements — and either bound may be
omitted (`v[:2]`, `v[1:]`, `v[:]`). Every one is proved in range at compile
time ([bounds](bounds.md)).

## Arithmetic at the edges

| expression | result |
| --- | --- |
| `a / 0`, `a % 0` | `0` — division by zero is a value, not a crash |
| `Int` overflow | wraps round: `MAX + 1` is `MIN`, `MIN - 1` is `MAX` |
| `2 ** 100` | `0` — that wrap, reached by repeated multiplication |
| `-MIN`, `MIN * -1`, `MIN / -1` | `MIN` |
| `n ** k`, `k < 0` on `Int` | `0`, including `1 ** -1` |
| `n ** 0` | `1` |
| `-7 % 3` | `-1` — the remainder takes the sign of the dividend |
| `10.0 ** 400.0` | `+Inf` — `Float` arithmetic does produce non-finite values |

Converting a non-finite or too-large `Float` to an `Int` is the **one**
unspecified case in the language; check the range first if it matters.

## `with` clauses

`with` introduces one clause and only one.

* **`with timeout <ms>`** bounds a wait and turns its result into
  `Result<T, hive.task.TimeoutError>`. See [concurrency](concurrency.md).

A decode target is not written here: reading a document into a declared type
is `User.decode(text, hive.json.codec())`, the decoder that type derives
named directly.

## Evaluation order

Operands are evaluated left to right, and `&&` / `||` short-circuit — which is
what makes `if x is T.A(v) && v == "ok"` legal. Every expression is evaluated
**exactly once** per time control reaches it, an `assert`'s operand included.

*From `spec/05-expressions.md` and `spec/02-grammar.md`.*
