# Bounds

A dedicated flow-sensitive pass proves **every index and slice in range at
compile time**, so the generated code can never fail out of bounds. Anything the
pass cannot prove safe is a **compile error**, not a runtime crash.

## What counts as a proof

An access is safe when one of these holds:

* the vector's length is **statically known** and the index is a literal within
  it — `v[2]` on a `Str[3]` compiles, `v[3]` does not;
* it sits under a **guard the pass can read**:
  `if i >= 0 && i < len(v) { v[i] }`, `if v bounds i { v[i] }` (the same
  guard, spelled shorter), or the condition of a counting `for` loop —
  `for i := 0; i < len(v); i++` — whose counter starts at a non-negative
  literal, steps by one and is held strictly below something. An `Int` wraps
  past `MAX`, so a counter stepping by more, or with nothing above it, proves
  nothing;
* the index came from **`indexOf`**;
* the index is a **sized integer** the vector's known length is past the top of:
  a `UInt4` indexes any vector of 16 or more, an `Int4` one of 8 or more under
  an `i >= 0` guard. An unsigned index is never negative, so against a `[dyn]`
  vector only `i < len(v)` is left. `Int(i)` is an `Int`, and proves nothing;
* the index is **masked by a literal**, `i & 15`, against a vector whose known
  length is past the mask: `buckets[hash & 255]` on a `Str[256]`;
* the access is a **`for each`**, which never indexes.

Any other **computed** index is not provable and must be bound to a variable and
guarded:

```hive
echo v[len(v) - 1]                  // compile error: a computed index

last := len(v) - 1
if v bounds last { echo v[last] }   // fine
```

## A known length survives what cannot lose it

| operation | length of the result |
| --- | --- |
| `a + b` | the two added — `Str[2] + Str[8]` fills a `Str[10]` |
| `map(v, f)` | `v`'s, unchanged |
| `sort(v)` / `sort(v, first)` | `v`'s, unchanged |
| `filter`, `filterMap` | **unknown, always** |
| `split`, `hive.map.keys`, most library calls | unknown |

They compose, so `map(a, f) + sort(b)` is as long as `a + b`. If **either**
side of a concatenation is unknown the result is unknown — there is no "at least
this many". `filter` claims nothing because what is knowable about it is a
*maximum*, and a maximum can never put an index in range.

## A declared length is a promise

`Str[3]` means three, so **every** value landing in such a slot must be a vector
of exactly that many — an initialiser, a later assignment, an argument, a field
of a constructed value, a returned value:

```hive
mut Str[3] v = ["a", "b", "c"]
v = ["x", "y", "z"]              // fine — still three
v = ["x"]                        // compile error: `v` is declared `Str[3]`
Str[3] parts = split(line, ",")  // compile error: that length isn't known
```

Because the promise is kept everywhere it is never lost: `v[2]` stays legal
after the reassignment, and a `Str[3]` parameter is indexed inside the callee
without a guard.

**A promise travels with a callable as a value.** `f := takes` is a
`proc(Str[3]): void`, and every call through it — or through a parameter, field
or vector holding it — is checked exactly as a direct one is. So it fills only a
slot that promises as much: a `proc(Str[]): void` parameter would hand it any
length, and passing `takes` there is a compile error.

## An inferred length is weaker

It survives a write *through* the name and dies the moment the name is rebound —
including in a branch that may not even run:

```hive
mut v := ["a", "b", "c"]
v[0] = "x"                  // still three
if changed { v = ["x"] }
echo v[2]                   // compile error: v's length is no longer known
```

The same applies to a field: replacing it costs whatever had been proven about
the old value. A `Str[3]` **field** is enforced wherever a value reaches it, so
it can be indexed unguarded.

## `indexOf` returns an index you can use

```hive
found := indexOf(names, "bob")
if found is Result.Ok(i) {
	echo "{i}: {names[i]}"   // no guard needed
}
```

The proof is tied to the vector that was searched, and only while that vector
means the same thing: an index found in `a` still needs a guard to index `b`.

## What costs a proof

* **rebinding** the vector, including in a branch that may not run;
* **`drop`**, the one builtin that makes a vector shorter;
* passing the vector to a **`mut` parameter**, by name or through a function
  value, since the callee may rebind it;
* replacing a **field** that held it.

`drop(v, low, high)` removes `low` through `high` **inclusive** and its bounds
are proven exactly as a slice's are. Crossed bounds take nothing.

## A `Str`'s own bounds

A `Str` is indexed and sliced like a vector and proved like one, with a single
difference: **a `Str` never has a length the compiler knows.**

```hive
s := "abc"
echo s[1]                    // compile error, even though `s` is right there
if s bounds 1 { echo s[1] }  // fine

if indexOf(line, "=") is Result.Ok(at) {
	echo line[at:]           // no guard: the search proved it
}
```

A slice's two bounds are proved separately, so a guard settling one says nothing
about the other.

*From `spec/10-bounds.md`.*
