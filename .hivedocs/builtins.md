# Builtins

Always in scope, no import needed. Several are overloaded by argument type, so
a builtin is only ever called, never used as a value or partially applied. Its
arguments may be named by the names in the first column: `join(sep: ",", vector: v)`.

| function | signature | what it does |
| --- | --- | --- |
| `len` | `(T[]): Int` / `(Str): Int` / `(Map<K,T>): Int` | elements / **characters** / pairs |
| `bytes` | `(T[]): Int` / `(Str): Int` | byte footprint / **bytes** of the UTF-8 |
| `append` | `(mut T[dyn], T): void` | grows a mutable dynamic vector in place |
| `prepend` | `(mut T[dyn], T): void` | the same, at the **front** |
| `drop` | `(mut T[dyn], Int, Int): T[dyn]` | removes `low`–`high` **inclusive**, hands them back |
| `join` | `(Str[], Str): Str` | concatenates, `sep` between elements |
| `split` | `(Str, Str): Str[dyn]` | splits on `sep` |
| `replaceFirst` | `(Str, Str, Str): Str` | the first `from`, rewritten |
| `replaceAll` | `(Str, Str, Str): Str` | every `from`, rewritten |
| `indexOf` | `(T[], T): Result<Int, Bool>` / `(Str, Str): …` | position of the first match |
| `row` | `(Table, Str): Str[dyn]` | the row whose first cell equals `key`, else `[]` |
| `column` | `(Table, Str): Str[dyn]` | the column whose top cell equals `key`, else `[]` |
| `toTable` | `(Str[], Int): Table` | the cells cut into rows that wide, the last one short |
| `map` | `(T[], func(T): K): K[dyn]` | every element, transformed |
| `filter` | `(T[], func(T): Bool): T[dyn]` | the elements `keep` says yes to |
| `filterMap` | `(T[], func(T): Result<K, E>): K[dyn]` | transform and select in one pass |
| `sort` | `(T[]): T[dyn]` / `(T[], func(T, T): Bool): T[dyn]` | in order |
| `encode` | `(T, hive.codec.Codec<E>): Str` | written in the format the codec names |
| `spawn` | `(handler, S): Result<Address<M>, SyslinkError>` / `(handler, S, Atom): …` | starts a service, optionally registered under a name |
| `at` | `(Atom): Address<M>` / `(Str, Atom): Address<M>` | a named service on this node / on the node at an endpoint, `M` read off where it lands |
| `kill` | `(Address<M>): void` | stops a service |
| `hide` | `(T): Result<Secret<T>, SecretError>` | a value as a [`Secret`](types.md#secret), never swapped to disk |
| `bypass` | `(T): Secret<T>` | a value as a `Secret` in ordinary memory; cannot fail |
| `reveal` | `(Secret<T>): T` | what a `Secret` holds |
| `UInt4`, every number type | `(integer): UInt4` | the value kept to the type's bits; never fails |
| `UInt4.checked` | `(T): Result<UInt4, T>` | the value, or `Error(value)` where it does not fit |

`len` and `bytes` differ only for strings: for `"café"`, `len` is `4` and `bytes`
is `5`. `replaceFirst` and `replaceAll` **answer with a new string**, take plain
text rather than a pattern, and are not an error when `from` is absent.

`toTable` fills its rows left to right and takes what is left for the last:
`toTable(["1", "2", "3", "4", "5", "6", "7"], 3)` is
`[["1", "2", "3"], ["4", "5", "6"], ["7"]]`. A row holds at least one cell, so a
width written as a **literal** below one is a compile error — it could only hand
back an empty `Table`. A width **computed** at run time is total instead: below
one it hands back an empty `Table`, the way dividing by zero is a value.

`encode` is a builtin for the reason the rest are: a builtin operates on the
types the language hands out without an import, and a document is a `Str`. It
is also the **only one with no runtime function behind it** — the encoder is
written out of the argument's static type at the call site, which is what
makes it total and keeps it free of reflection. The codec is an **ordinary
value** — held in a variable, passed, stored — because its type,
`hive.codec.Codec<E>`, already says the format. Its other half is
`T.decode(text, codec)` — see [json](../stdlib/json.md).

`spawn`, `at` and `kill` are [services](stdlib/syslink.md). A handler is
`proc(mut S, M): M`, or `proc(mut S, M, Address<M>): M` to be handed its own
address every turn, and `spawn` takes either, answering with an `Address<M>`. A
name is one service's at a time, so a second `spawn` under a name still held
fails as `SyslinkError.Taken`; one with no name is always `Ok`. `at` builds an
address and looks nothing up, and takes its `M` from where it lands or from its
first later use.

## A declaration of your own wins

If your program declares a `func`, `proc`, `query` or type named `len`, `map`,
`join` — any of the names above — **that** is what your bare calls mean. The
builtin is still there as `hive.<name>`:

```hive
func len(label: Str, extra: Int): Str { return "{label}{extra}" }

proc main(): void {
	Str[dyn] v = ["a", "b"]
	echo len("x", 2)          // ours: "x2"
	echo hive.len(v)          // the builtin: 2
	echo hive.join(v, "-")    // the long name works either way
}
```

A local binding and a parameter shadow one the same way, and shadowing is **per
module**. Two things follow: only the builtin `append` requires a `mut` target,
and only the builtin `indexOf` hands back an index the bounds pass accepts
unguarded.

The library's module names — `conv`, `task`, `ui` and the rest — are held
the same way, and also give way to an import of the same name
([modules](modules.md)).

## Walking a vector: `map`, `filter`, `filterMap`

Each takes a vector and a function over its elements and hands back a new one.

* The function is a **`func`, never a `proc`**. A walk says nothing about the
  order its function runs in, so there is nowhere to hang a side effect. To walk
  with a proc, write a `for each` loop.
* Each is specific about what its function answers with: `filter` wants a
  `Bool`, `filterMap` a `Result`, and `map` wants *something* — a `void`
  function collects nothing.
* **A walk is sequential**, once per element, in order, on the calling thread.
  To run a batch of calls together, write the
  [await-all](concurrency.md).
* `map` is **length-preserving** and the [bounds pass](bounds.md) knows it;
  `filter` and `filterMap` are not.

## Growing and shrinking

All three write *through* a vector and all three ask for a **mutable dynamic**
one (`mut T[dyn]`). `prepend` hands nothing back, so it may only stand as a
statement. `drop` removes a range, both ends inclusive, and is the one builtin
that makes a vector **shorter** — so it costs that vector whatever the bounds
pass had proved.

## `sort`

Hands back a new vector holding the same elements in order; the original is
never touched. **One argument** orders by the element type's own order:

| element | order |
| --- | --- |
| `Int`, `Float` | numeric, ascending |
| `Str` | by UTF-8 byte order |
| `Bool` | `false` before `true` |
| `Atom` | by its compiled value |
| a vector, a `Table` | lexicographic; on a shared prefix the shorter first |
| `Result<T, E>` | every `Error` before every `Ok` |
| a struct | field by field, in declaration order |
| a tagged union | by **variant** first, in declaration order, then its fields |
| a map, a function value, a service address, or a type holding one | none — a compile error |

**Two arguments** order by a `func` of your own answering whether its first
element comes before its second — also the answer for an element type with no
default order. The sort is **stable**, and both forms are length-preserving.

### Sorting in place

A `sort` written as a **statement** throws away the vector it answers with. When
the vector it was given is `mut`, that is taken at its word and the storage is
reordered where it lies:

```hive
mut Str[dyn] names = ["pear", "apple"]

sort(names)                  // in place — `names` is now sorted
sorted := sort(names)        // NOT in place — a new vector, `names` untouched

Int[dyn] v = [3, 1, 2]
sort(v)                      // compile error: `v` is not `mut`
sort(split(line, ","))       // compile error: nothing to sort in place
```

Both conditions — discarded, and `mut` — do work, and a discarded `sort` that
cannot sort in place is a compile error rather than a statement that quietly does
nothing. The subject can be any `mut` storage: `sort(b.items)`, `sort(rows[i])`.

*From `spec/13-builtins.md`.*
