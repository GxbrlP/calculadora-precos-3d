# Generics

A name in a signature that is neither a builtin nor a declared type is a **type
variable**, and it makes the callable generic in it.

```hive
func first(v: T[]): Result<T, Bool> {
	if len(v) > 0 {
		return Result.Ok(v[0])
	}
	return Result.Error(false)
}
```

## Where a variable is pinned down

By wherever it appears in the **parameters** — including *inside* a parameter's
own type, which is what makes a higher-order generic work:

```hive
func filterMap(values: T[], transform: func(T): Result<K, E>): K[dyn] {
	mut K[dyn] out = []
	for each value in values {
		if transform(value) is Result.Ok(next) {
			append(out, next)
		}
	}
	return out
}
```

The call says what `T` is by the vector it passes and what `K` and `E` are by the
function it passes. **None of the three is written at the call site.** The body
may write those variables down too — `mut K[dyn] out = []`, `for each v: T in …`,
`Box<T> b = …` — and each copy substitutes through its own body.

## Generic types

A type whose fields mention variables is generic in them, in **first-appearance
order**, and is written out where it is used:

```hive
type Box {
	items: T[dyn]
	label: Str
}

type Either {
	Left  { left: A }
	Right { right: B }
}

Box<Str> people = Box(["ada", "grace"], "people")
Either<Str, Int> answer = Either.Right(42)
```

The type arguments go on the **declaration of the value**, which is also what
tells a variant constructor which instantiation it is building. Each
instantiation gets its own clone, JSON codec and structural digest, so
`Either<Str, Int>` and `Either<Int, Str>` are different types all the way down
to the wire.

## Monomorphization

Nothing about generics is dynamic. Every call site is resolved at compile time,
with the type arguments read off the argument types, and **one concrete copy is
emitted per distinct set of them** — `first_Str`, `first_Int`. No boxing, no
dispatch, no reflection.

Because each copy is an ordinary declaration, **every later check runs on it
separately**: an instantiation at `Str[3]` is held to that length while one at
`Str[dyn]` guards its indexes.

## What is rejected

* **A generic callable cannot be used as a value** — `f := first` is a compile
  error, because which copy a call reaches is decided by the argument types and
  a value carries none.
* **A variable that appears only in the return type** has nothing to be inferred
  from: `func makeOne(n: Int): T` is a compile error at the call.
* **Runaway expansion is capped**, and overrunning the limit is a compile error
  rather than a hung build.

*From `spec/11-generics.md`.*
