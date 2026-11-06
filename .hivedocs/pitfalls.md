# Pitfalls

The refusals a program written in another language's habits runs into. Every one
below is a **compile error**, and each is followed by what to write instead.

## Conditions and operators

**There is no truthiness.** A condition is a `Bool`; an `Atom`, `Int`, `Str` or
vector there is an error. → `if flag == #Ready`, `if len(v) > 0`, `if s != ""`.

**`!` inverts a `Bool` and nothing else** — there being no truthiness, there is
nothing about an `Int` or an `Atom` to be the opposite of.

**`!` binds tight**, at unary `-`'s level, so anything looser needs parentheses:
`!(a == b)`, `!(v bounds i)`. `!a && b` is `(!a) && b`, and
`!x is Shape.Point` is `(!x) is …` — a type error, not what it looks like.

**A match cannot be negated.** `!(x is Shape.Circle(r))` is an error: `is`
narrows and binds, and neither survives a `!`, so `r` could never be set. → put
the other case in the `else`.

**No number is widened for you.** `hive.math.max(0, health)` is an error
because those calls take `Float`. → `hive.conv.itf(0)`.

**Comparing two different types** is an error, not a silent `false`.

## Vectors

**`[dyn]` is declared, never inferred.** `mut v := ["a"]` is a `Str[1]` and
`append`ing to it is an error. → `mut Str[dyn] v = ["a"]`.

**`append`, `prepend` and `drop` need a `mut` target.** An immutable binding
cannot be written through at all.

**Every index must be proved.** `v[len(v) - 1]` is a computed index and is
refused. → bind it and guard it: `last := len(v) - 1`, then
`if v bounds last { v[last] }`.

**A slice's high bound is inclusive.** `v[0:2]` is **three** elements, not two.

**`filter` and `filterMap` lose the length** for good — no index into their
result is ever provable without a guard.

**`Str[]` is a parameter spelling only.** A return and anything naming storage
must say `[dyn]` or `[n]`.

## Strings

**A `Str` never has a length the compiler knows**, so even `s := "abc"` needs
`if s bounds 1` before `s[1]`. An index from `indexOf` needs no guard.

**`s[0] = "x"` is an error** — a `Str` is a value, not storage. Build a new one.

**Indexing a `Str` counts characters, not bytes**, and yields a one-character
`Str`. `len` counts characters; `bytes` counts bytes.

## Names and declarations

**A keyword's own spelling is never a name**, so a field cannot be called `type`.
→ `kind: Str -- JSON as type;` where the JSON key has to be `type`. Any other
casing is free: `Return` is a fine variant.

**A `mut` variable may not be `UPPER_CASE`**, a counting loop's counter
included. The rule runs that way only: an immutable variable **may** be
`UPPER_CASE` and is never obliged to be — `camelCase` is the default for every
variable, and `retries := 3` needs no shouting to hold still.

**`UPPER_CASE` is for variables and nothing else.** A parameter, a field, a
callable, an import's name and a name bound by a pattern or a `for each` are
`camelCase`, however fixed the value behind them is.

**A `func` cannot declare a `mut` parameter.** If a body needs one, it is a
`proc`. Calling one is fine either way.

**Every non-`void` path must return.** An `if`/`else if` chain over a whole
union counts, and so does a `switch` whose every arm returns.

**`mut` goes nowhere but a declaration and a `proc` parameter**: not on a field,
not on a return, not in a function type.

## Matching

**A `switch` never falls through and never misses a case.** Each arm has one
position per subject, the first arm that matches runs, a value no arm takes is a
compile error, and so is an arm that can never run.

**A pattern on the left of `:=` needs an `else` whose every arm leaves** —
`return`, `panic`, `break` or `continue`. →
`Result.Ok(n) := parse(s) else { Result.Error(why) { return Result.Error(why) } }`.

**Name every field of a variant or none** — a partly written argument list is
refused. Use `_` for the ones you do not want.

**A variant is built by calling it**, one that carries nothing included:
`Shape.Point` on its own names the variant rather than a value of it. →
`Shape.Point()`, or `Shape.Circle(_)` where a function value is wanted.

**String patterns never make a chain exhaustive** (bar a lone `"{s}"`), so a
function matching on those still needs a terminating `else` or a final `return`.

**Two open string-pattern holes may not sit side by side** — `"{a}{b}"` is
ambiguous. Put a literal between them, or give one a regex.

**A binding from `is` is out of scope in the `else`.**

## Concurrency

**`async` is not an expression.** It appears as a statement of its own and on
the value side of a declaration, and nowhere else.

**Every entry of an `await` must be a call**, they must all answer with the same
type, and `await []` is an error.

**A `void` call takes neither an `async` binding nor `with timeout`** — there
would be nothing for the name or the `Result` to hold.

**An `async` call gets a copy of a `mut` argument**, not the caller's storage.

**One call never lends a vector and a path inside it.** `both(v, v[0])` with both
parameters `mut` is an error. → lend `v` alone and reach `v[0]` through it.

**An address says what its service takes.** `Address` on its own is an error, and
so is `box := at(#Cache)` with nothing after it that sends to `box` or hands it to
a parameter, since a name says nothing about the messages. →
`Address<Op> box = at(#Cache)`, or a send: `box(Op.Ping())`.

**What went wrong is a library error's variant**, matched like any union's →
`why is file.FileError.NotFound`, or a `switch` over every one.

## Collections and modules

**`hive.map.new()` must land somewhere that says what it holds**, or be used later
in a way that does. `m := hive.map.new()` with nothing after it that says is an
error. → `hive.map.set(m, "a", 1)`, or `mut hive.map.Map<Str, Int> m = hive.map.new()`.

**A number does not change size on its own.** `UInt8 b = n` with `n` an `Int` is
an error, and so is `Int n = b`, and so is `UInt4 x = 16`. → `UInt8(n)` to keep
the low bits, `UInt8.checked(n)` for a `Result`, `Int(b)` to widen.

**A map has no subscript and no `for each`.** → `hive.map.get`, and loop over
`hive.map.keys(m)`.

**A Hive import never writes `.hive`; a Go import always writes `.go`.**

**An import may not be named `hive`**, and `import hive` is not a thing to
write — the library is reached a module at a time.

## Generics and values

**A generic callable cannot be used as a value**, and neither can a builtin or a
library call, bare or partially applied.

**A type variable that appears only in the return type** cannot be inferred.

## Queries

**`SELECT *` against a declared row type is an error**, and columns match
fields **by name** — alias anything spelled differently.

**A column name or a sort direction can never be a `{param}`.**

## Sorting

**`b := sort(a)` does not sort `a`** — it answers with a new vector. Only a
**discarded** `sort` on a `mut` vector sorts in place, and a discarded one that
cannot is an error rather than dead code.

*Every rule here is stated in full on the page for its feature; start at
[README](README.md).*
