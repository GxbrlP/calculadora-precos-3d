# Mutability and value semantics

## `mut`

Variables are immutable by default. `mut` allows reassignment, writing through
(`v[0] = …`, `rec.f = …`) and `append`.

A `mut T` is identical to `T` at run time; `mut` only says, at compile time,
that this name may be altered. A parameter or return of type `T` accepts a
`mut T` — the callee just sees an immutable `T`, copied on the way in — never
the reverse.

`mut` may not appear anywhere else a type can: **not on a field, not on a
return, not in a `func(...)` type** — a `proc(...)` type may mark a parameter
`mut`. A `mut` variable may not be `UPPER_CASE`.

## `mut` parameters

A **`proc` — and only a `proc`** — may ask for the caller's storage itself:

```hive
proc grow(vec: mut Str[dyn], tag: Str): void {
	append(vec, tag)
}
```

The argument must then be a `mut` variable or a path into one, and the callee
gets **that storage**: it may reassign it, write its elements and `append` to it,
all visible through the caller's name afterwards.

**Whether it shares depends on the call site, not the declaration:**

```hive
mut Str[dyn] v = ["a"]
grow(v, "b")          // waited for: v is now ["a", "b"]
async grow(v, "c")    // fired off: the thread grows a copy; v is untouched
```

A call you wait for *there* hands over the caller's storage; an `async` or
`await`ed one hands over a copy — a thread of its own gets storage of its own.

The same holds through a function value: `f := grow` then `f(v, "d")` grows `v`,
and `async f(v, "e")` grows a copy. A `mut` position in a partial application
stays a hole — `grow(_, "f")` — since what is supplied is captured by value.
Passing a variable to a `mut` parameter, by name or through a value, costs it
every length and index fact [already proved](bounds.md) about it, since the callee
may rebind it shorter.

**One call never lends a vector and a path inside it**: `both(v, v[0])` is a compile
error, since growing `v` moves `v[0]` and the write to it would be lost. Two
elements, `swap(v[i], v[j])`, and a field beside its record, `put(box, box.count)`,
are fine. An element of a packed vector is lent as a copy and written back after
the call.

## What a value is

Vectors, `Table`s, maps and declared types that contain them are **value
types**. Two names for one value never observe each other's mutations — unless
both are `mut`, which is how shared mutable state is opted into — and even then
it is the *storage* they share and never the names. The invariant the whole of
it rests on:

> Storage that an immutable binding observes is never mutated in place
> afterwards.

## Copy-on-binding

A binding whose right-hand side **names existing storage** (`ys := xs`,
`ys := xs[i]`, `ys := rec.field`) may need to copy. A **fresh** right-hand side
— a literal, a `+` concatenation, a function result — is already independent and
is never copied.

| target ⟵ source | decision |
| --- | --- |
| immutable ⟵ immutable | **alias** — neither side can ever mutate it |
| `mut` ⟵ `mut` | **share** — shared mutable state is the intent |
| `mut` ⟵ immutable | **alias** if the target is never written through, else **copy** |
| immutable ⟵ `mut` | **alias** if the source is never mutated again, else **copy** |

An alias is only chosen when it is provably indistinguishable from a copy, and
the analysis is deliberately conservative. An in-place `sort` counts as a write:

```hive
mut Int[dyn] a = [3, 1, 2]
b := a          // copies, because...
sort(a)         // ...this rewrites `a`, and `b` must not follow
```

### Two `mut` bindings share their storage, not their names

```hive
mut Str[dyn] a = ["x", "y", "z"]
mut Str[dyn] b = a
append(b, "w")            // len(a) is now 4
a[0] = "changed"          // b[0] is "changed" too
b = ["replaced"]          // len(a) is still 4: `b` alone was rebound
```

The two names hold **one cell** — the storage, and a pointer to it each of them
has. Writing *through* a name reaches the storage, so both see it, `append`
included: the new slice header lives in the cell rather than in either name.

**Rebinding a name is not a write through it.** `b = [...]` says what `b` is from
here on and says nothing about `a`: `b` takes a cell of its own and the two stop
sharing.

Two cases are not covered and keep storage of their own: a source that does not
name the same storage every read (`mut b = a[i]`), and a name standing for more
than one binding in a body, since nothing but the name tells the two apart.

## What a copy copies

Deep and **type-directed** — chosen by the static type, with no runtime
reflection. A flat vector copies its backing array; a nested vector or `Table`
copies every level; a map copies its key order and its lookup; a declared type
copies its storage-owning fields through a generated clone, and a scalar-only
type needs nothing.

A `mut T` parameter is the one place storage crosses a call boundary on purpose,
and it lowers to a pointer — a shared backing array would not survive `append`.

*From `spec/08-mutability-and-values.md`.*
