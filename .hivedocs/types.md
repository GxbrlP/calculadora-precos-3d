# Types

Every expression has a type known at compile time. There is no dynamic type,
no `Any` and no reflection: where a type is needed and cannot be worked out,
the program is rejected rather than deferred to run time.

## The scalars

| type | holds |
| --- | --- |
| `Str` | UTF-8 text |
| `Int` | a 64-bit signed integer — exactly Go's `int`; past its largest or smallest value it wraps round to the other |
| `UInt1` … `UInt64` | an unsigned integer of that many bits: a `UInt4` holds 0 to 15 |
| `Int1` … `Int63` | a signed integer of that many bits: an `Int4` holds −8 to 7 |
| `Float` | a 64-bit float |
| `Float32` | a 32-bit float, computed in single precision |
| `Bool` | `true` or `false` |
| `Atom` | an interned symbol, written `#Name` |
| `void` | nothing — a **return type only**, never a variable, field or element |

`Int64` and `Float64` are second names for `Int` and `Float`.

### Sized numbers

For a program keeping many small numbers, each taking only the bits it needs.

* A sized integer **wraps at its own width**: a `UInt4` at 15 plus one is 0. `-`
  on an unsigned type is a compile error.
* A **literal takes the type it lands in** and has to fit it: `UInt4 x = 9` holds,
  `UInt4 x = 16` is a compile error. Beside a sized operand, a literal takes its type,
  so `a + 1` on a `UInt4` stays a `UInt4`.
* **No number changes type on its own.** A `UInt8` is not an `Int` until `Int(b)`
  says so, a `Float32` is not a `Float` until `Float(f)`, and `UInt4 + UInt8` is
  a compile error until one side is converted. Two integers of any sizes still
  **compare** by value, which keeps `i < len(v)` a guard.
* **Every conversion is written**: `UInt4(x)` keeps the low bits and never fails;
  `UInt4.checked(x)` answers `Error(x)` where `x` does not fit. `Float32(x)` rounds a
  `Float`. `hive.UInt4(x)` reaches the builtin past a declaration of your own.
* A sized index is its own [bounds](bounds.md) proof: a `UInt4` indexes any vector
  of 16 or more with no guard, and an unsigned index is never negative.
* A **vector of them is packed**, each value taking only its own bits: a million
  `UInt4`s take half a megabyte. Widths of 8, 16, 32 and 64 are stored as they are.

### `Str`

A `Str` is a sequence of **characters**, and `len` counts those. It holds bytes,
so a binary file survives a read/write round trip, but it is addressed as text.

* `s[0]` is its first **character** and yields a one-character `Str` — there is
  no character type.
* `s[1:3]` is characters one through three, **both bounds inclusive**.
* Every index into one is proved at compile time, and a `Str` **never** has a
  length the compiler knows — so it is always guarded or from `indexOf`.
* `s[0] = "x"` is a compile error. A `Str` is a value, not storage.

`split(s, "")` reaches every character at once and is how a string is walked
without indexing it.

### `Atom`

Written `#Name`, interned to a small integer, declared nowhere. `echo` prints its
name; coercing one to `Str` yields its decimal value. `#Nil` is the only atom the
language provides and is always first on the table.

**An atom is not a condition.** `if flag` on an `Atom` is a compile error; compare
it with the one you mean, `if flag == #Ready`. An atom cannot be computed.

## `Result<T, E>`

The one built-in generic union, and how every fallible operation reports
itself: `Result.Ok(value)` and `Result.Error(payload)`. Matching both variants
is exhaustive. See [patterns](patterns.md).

Each variant says one half of the type, so the other comes from where it lands:
a declaration, a `return`, a parameter or field declared as a `Result`, or the
other side of an `==`. Bound with `:=`, it comes from the **first later use**
that says it, and never changes after; `r := Result.Ok(3)` with nothing after it
that says is a compile error — `Result<Int, Str> r = Result.Ok(3)` says it.

## Vectors

Memory-contiguous and homogeneous. Three spellings, and **which one a name
holds is what its declaration says, never what its value happened to show**:

| written | means | legal where |
| --- | --- | --- |
| `Str[3]` | **static**: exactly three | anywhere |
| `Str[dyn]` | **dynamic**: promises nothing about the length | anywhere |
| `Str[]` | **any length** of this element type | **parameters only** |

`Str[]` is a parameter spelling and that is the whole of where it is legal: a
return and anything naming storage must say which of the two real kinds it is.

**Dynamic is declared, never inferred.** A `:=` binding reads its length off its
value, and a length read off a value is a static one:

```hive
mut v := ["a", "b", "c"]
append(v, "d")            // compile error: `v` is not a dynamic vector

mut Str[dyn] w = ["a", "b", "c"]
append(w, "d")            // fine
```

Operations: `+` concatenates into a **new** vector and adds the two lengths;
`==` compares structurally, element by element; `v[i]` indexes and `v[lo:hi]`
slices with `hi` **inclusive**. Comparing a vector to a non-vector is a compile
error, not a silent `false`. `Str[3][2]` is two vectors of three.

`Table` is an alias for `Str[dyn][dyn]` — a vector of rows of cells. See
[tables](tables.md).

## Declared types

No variants is a struct; variants make a tagged union.

```hive
type User {                 // a struct
	id:   Int
	name: Str
}

type Shape {                // a tagged union
	Circle { radius: Int }
	Rectangle { width: Int, height: Int }
	Point                   // a variant may carry nothing
}

type Event {
	at: Int                 // outside every variant: added to all of them
	Opened { by: Str }
	Closed
}
```

A field may carry `--` annotations saying what it is called in JSON and what
to read where JSON has nothing — see
[declarations](declarations.md#field-annotations).

Built by calling the type or the variant — `User(1, "ada")`, `Shape.Circle(5)`,
`Shape.Point()` — and narrowed with `is`. **There is no other way to reach a
variant's fields**: a value typed as the union has only the fields declared
outside its variants, read straight off it (`event.at`) — never assigned into,
since a union value is built whole. A field every variant declares for itself
still belongs to the variants.

A type may recurse **through a variant** (an expression tree does); a struct may
not contain itself directly, since it would have no finite size.

## Function types

Written like a declaration with the name dropped: `func(Int): Int`,
`proc(hive.net.HttpRequest): hive.net.HttpResponse`. A `func` value may be used
where a `proc` is expected; a `proc` value may not fill a `func` slot. A `proc`
type may mark a parameter `mut` — `proc(mut Str[dyn], Str): void` — and a `func`
type may not. `proc(mut Int): void` and `proc(Int): void` are different types.

## Maps

`hive.map.Map<K, T>` is the one collection that is not a vector, so it is a
module rather than a literal ([stdlib/map](stdlib/map.md)). Three type-level
rules:

* A **key is compared and hashed whole**, so it is a `Str`, `Int`, `Float`,
  `Bool` or `Atom`, or a declared type whose every field is one of those.
  **Storage cannot be a key**: `Map<Str[dyn], Int>` is a compile error.
* `hive.map.new()` says *empty* and nothing about what it holds, so it takes its
  type from where it lands, or — bound with `:=` — from the **first later use**
  that says it, such as `hive.map.set(m, "a", 1)`. Once settled it never changes: a
  later use that disagrees is a compile error.
* A map is **reached by key, never by position**. `m[0]` is a compile error and
  so is `for each` over one.

## Address

`Address<M>` is a [service](stdlib/syslink.md) taking messages of type `M`, in this
process or on another machine — what `spawn` and `at` answer with, and what a
call sends to: `box(message)`. The message has to be an `M`, and the answer is
one too. `Address` without its `M` is a compile error.

* `spawn` reads `M` off the handler it starts.
* `at` cannot, since a name says nothing about what the service takes, so `M`
  comes from where the address lands — `Address<Op> counter = at(#Counter)` — or,
  bound with `:=`, from its **first later use**: `counter := at(#Counter)` then
  `counter(Op.Add(1))`. Once settled it never changes.
* An address is an ordinary value, stored, passed and carried inside a message,
  and it has no order.
* A program that declares its own `Address` still has the builtin as
  `hive.Address<M>`.

## Secret

`Secret<T>` is a value that must not leak: a password, a key, a token, or a record
of them. `hide(value)` makes one of any `T` and `reveal(secret)` is that `T` again;
nothing else opens one. The library's secrets are text: `Secret<Str>`.

```hive
type Login {
	user: Str
	pin: Int
}

if hide(Login("ada", 1234)) is Result.Ok(kept) {
	echo reveal(kept).pin
}
```

* **It holds plain data**: text, numbers, vectors, maps, results and declared types
  made of them. A `Secret` of a function, an address, a library handle or another
  `Secret` is a compile error, and so is `Secret` without its `T`.
* **It is never shown.** `echo`, `panic` and an interpolation of a `Secret`, or of
  anything holding one, are compile errors. So is `encode`, or sending one in a
  message: a `Secret` is never written out.
* **It can be read.** `T.decode` reads a `Secret<U>` field as the `U` the document
  holds and keeps it the way `bypass` would. A value of the wrong kind says which
  kind it was, never what it held.
* **It is never swapped to disk.** Its value is kept as bytes in locked memory,
  cleared once nothing holds it. Locked memory runs out, so `hide` answers
  `Result<Secret<T>, SecretError>`, the error being `SecretError.LimitExceeded` or
  `SecretError.Unsupported`, each with a `message`.
* `bypass(value)` is a `Secret<T>` in ordinary memory: never shown, but free to be
  swapped out, and it cannot fail. For a literal, or a ciphertext.
* `hive.term.readSecretBypass` and `hive.crypto.decryptBypass` are `readSecret`
  and `decrypt` into ordinary memory the same way, with no limit to run into:
  `readSecretBypass` cannot fail at all.
* `==` compares what two hold, in constant time; there is no order. A map is kept
  in key order, so two holding the same pairs are equal, and `reveal` hands it back
  in that order.
* `hive.term.readSecret`, `hive.env.getSecret` and `hive.crypto.randomSecret`
  hand one over without it ever being a `Str` first, each as a `Result`.
* A program that declares its own `Secret` or `SecretError` still has the
  builtin as `hive.Secret<T>` or `hive.SecretError`.

## Assignability

A value of type `S` fits where `T` is expected exactly when:

1. they are the same type; or
2. `T` is `T'[]`, `S` is `T'[n]` or `T'[dyn]`, and the element types match; or
3. `T` is a `proc` type and `S` is the `func` type with the same shape; or
4. `S` is `mut T` and `T` is not `mut` — the callee gets an immutable copy.

There is **no implicit numeric conversion**, of size or of kind: `Int(b)`,
`Float(f)` and `hive.conv.itf(n)` are written. `hive.math.max(0, health)` is a
compile error rather than a surprise. There is **no subtyping and no interface**, and a variant is
not a type of its own — `Shape.Circle` cannot be a parameter's type.

A **declared static length is a promise**, so a `Str[3]` slot only ever takes a
vector of exactly three, wherever it came from. See [bounds](bounds.md).

*From `spec/03-types.md`.*
