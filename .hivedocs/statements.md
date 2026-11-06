# Statements

## Bindings

```hive
x := expr                    // inferred
Str[dyn] v = expr            // annotated
mut x := expr                // inferred, reassignable
mut Str[dyn] v = expr        // annotated, reassignable
_ := expr                    // throws the value away
```

`:=` infers the type from the value, **including a static vector length**.
`=` with a type in front states it, and is the **only** way to say `[dyn]`, to
say `Str[3]` as a promise rather than an observation, or to give a
`hive.map.new()` somewhere to land. Only a `[dyn]` vector grows: an inferred
length is a length all the same, so a `mut` one is rebound only to as many.

A name is declared **once per block** (an inner block may shadow it); `_` as often
as you like. A call that answers with nothing cannot be bound, and a statement
that is only an expression has to be a call — `x + 1` alone is refused, and
`_ := x + 1` drops a value on purpose.

A binding is **immutable** unless it says `mut`. An immutable name may not be
reassigned, may not be written through (`v[i] = …`, `v.f = …`), and may not be
`append`ed to.

**`mut` is what decides that, never the spelling.** An immutable variable is
written `camelCase` by default and **may** be written `UPPER_CASE` instead,
which is how a constant is spelled — `retries := 3` and `MAX_RETRIES := 3` hold
their values in exactly the same way. See [syntax](syntax.md).

## Binding with a pattern

```hive
Result.Ok(text) := hive.file.read(path) else {
	Result.Error(file.FileError.NotFound(_, _)) { return Result.Ok(defaults()) }
	Result.Error(why)                           { return Result.Error(why.message) }
}
echo text
```

A pattern on the left of `:=` binds what it takes for the **rest of the block**,
and the `else` holds a `switch`'s arms, one position each, for every value it
does not. **Every arm has to leave** — `return`, `panic`, `break` or `continue` —
so nothing after the binding runs without what it bound. It is held to what a
`switch` is: one evaluation, every value taken, no arm that can never run. What
it binds is immutable and declared in the block it is written in.

## Assignment

```hive
x = expr
v[i] = expr
rec.field = expr
b.items[0] = expr
```

The target must be a `mut` binding or a path into one. Assigning to a parameter
or to a plain `:=` binding is a compile error. `+= -= *= /=`, `&= |= ^= <<= >>=` and the steps
`++` / `--` are shorthand for the matching `x = x <op> …`.

## `if`

```hive
if cond { } else if cond { } else { }
```

The condition is a `Bool`. **There is no truthiness in Hive** — an `Atom`, an
`Int`, a `Str` and a vector are each a compile error there. Names bound by an
`is` in the condition are in scope in that branch's body and in the rest of the
same condition after `&&`.

## `switch`

```hive
switch shape, fill {
	Shape.Circle(r), Fill.Solid(color) { }
	Shape.Point, _                     { }
	_, _                               { }
}
```

Each subject is evaluated **exactly once**, left to right, before any arm is
tried. An arm has **one position per subject**, and a position is a pattern (as
after `is`), a literal the value has to equal (`0`, `-1`, `2.5`, `#Ready`,
`true`), or `_` for any value.

The **first** arm whose every position matches runs, and no other: no
fall-through, and `break` / `continue` act on the enclosing loop. An arm is the
`if` its positions spell, so what it binds is in scope in its body only, and it
binds a name once across all its positions.

A `switch` is **always exhaustive** and **every arm can run** — falling short of
either is a compile error ([patterns](patterns.md)). So one whose every arm
returns is a terminating path.

## Loops

```hive
for i := 0; i < 10; i++ { }
for ; cond; { }                      // any clause may be omitted: a while loop

for each name in values { }
for each name: T in values { }       // the annotation states the element type
```

The counter is scoped to the loop and **implicitly mutable**, so it needs no
`mut` — and is held to the `mut` naming rule, so it may not be `UPPER_CASE`.
Neither the init nor the post clause may be `async`.

`for each` walks a vector, binding each element to an **immutable** name. It
never indexes, so it needs no bounds proof. `for each` over a map is a compile
error.

`break` leaves the innermost enclosing loop; `continue` skips to its next
iteration. Either outside a loop is a compile error.

## `echo`, `assert`, `panic`

`echo value` writes one line to stdout: an atom prints its **name**, a vector
its elements, a map its pairs in its own order, a declared value its fields. It
is legal in a `func` and a `proc` alike. A `Str` echoed on its own **is** the
line and is not quoted; inside any of those it is, which is what tells
`["1", "2"]` from `[1, 2]` and from `["1 2"]`.

`assert cond` says this must hold, and **where it is written decides what
happens when it does not**: in ordinary code a failure has proved the *program*
wrong, so it stops; inside a `test` it has proved the *test* wrong, so the
failure is recorded and the suite carries on. Outside a test a failure prints the
condition as written, and both sides of an `==` or `!=`. Its operands are evaluated exactly
once either way.

`panic value` stops the program immediately, rendering `value` exactly as `echo`
would. It takes any value rather than only a `Bool`, and never returns — so a
branch ending in one counts as a terminating path. The single exception to
"stops the program" is inside a [service](stdlib/syslink.md),
where a panic kills only that service.

## `async` as a statement

```hive
async f(x)
```

Runs the call on its own virtual thread and carries on. See
[concurrency](concurrency.md).

## Expression statements

A call may stand alone, and its result is discarded. Two builtins mean something
particular there:

* a discarded **`sort`** on a `mut` vector sorts it **in place**, and one that
  cannot is a compile error rather than dead code;
* a discarded **`drop`** is the ordinary way to remove elements.

An expression that is not a call and has no effect is not a statement.

## Scope

A block introduces a scope. A name is visible from its declaration to the end of
its block, and shadowing an outer name is allowed — a local binding shadows a
module-level declaration and a builtin alike. **There is no forward reference
inside a body**: a statement may only name what is already in scope.

*From `spec/06-statements.md`.*
