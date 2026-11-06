# Concurrency

**Every call blocks its caller.** Nothing about a declaration says otherwise, so
there is no `async func`, no Future and no Promise type to name. What a call
means is decided **where it is written**.

## The four call sites

### `f(x)` — wait for it

Yields `T`. It costs neither a goroutine nor a channel: it is a function call.

### `async f(x)` — as a statement

Runs the call on its own virtual thread and carries on. Fire-and-forget is the
whole of it: the result is discarded and nothing is left behind to read one
from. It works on any call — a `func`, a `proc`, a `query`, the standard
library, a service — and refuses three by name: a **global builtin**, a
**constructor**, and a **partial application**.

### `x := async f(a)` — keep the result

Starts the call the same way and keeps its result. **The wait happens wherever
`x` is read**, and only if the call has not finished by then.

```hive
rows  := async loadRows()              // Str[dyn] — starts now
total := async countAll()              // Int      — starts now, alongside
echo "loaded {len(rows)} of {total}"   // waits for both, here
```

`x`'s type is the call's return type with **nothing wrapped around it** — `Str`,
not a Future of one. There is no handle type in the language and nothing to
unwrap.

* Reading `x` again is free and always answers the same value.
* A panic inside the call is raised at the **first read**; if nothing ever reads
  `x` the work still runs and the panic is dropped with the result.
* It refuses the same three calls `async` does, and a `void` call besides.
* `mut` cannot be combined with it, and neither can `with timeout`.

### `await [f(a), f(b), f(c)]` — the await-all

The **only** `await` there is. Every call starts on its own thread and the whole
list is one barrier, resolving **in order** to a statically-sized, fully-typed
vector of their results (`Str[3]`) — never a dynamic or `Any` vector. Three
calls that each take a second take about a second.

* A list of one is legal and still means "on its own thread, then wait".
* Over `void` calls the barrier has no value and is a **statement**.
* Every entry has to be a **call**, and they must all answer with the **same
  type**. `await []` is a compile error.

Several calls that answer differently are given **names** instead — the `async`
binding above.

## `with timeout`

Any wait **written where it happens** may be bounded:

```hive
f(x) with timeout 500
await [f(a), f(b)] with timeout 500

if slowShout("worth waiting for") with timeout 100 is Result.Error(err) {
	echo "gave up after {err.waited}ms"
}
```

Without it, the wait yields the value; with it,
`Result<T, hive.task.TimeoutError>`, whose error carries `waited` and a
`message`.

* On an await-all it is **one deadline across the whole barrier**.
* A timeout abandons the **waiting, not the work**: a virtual thread cannot be
  stopped from outside, so the call runs on and only its result is dropped.
* A `void` call has no value for the `Result` to carry, so bounding one is
  refused.
* On a request to a [service](stdlib/syslink.md) the clause folds into the
  request's own error rather than wrapping a second `Result` around the first.

## Threads and `mut` arguments

A call handed a `mut` argument shares the caller's storage **only when the
caller waits for it there**. A call on a thread of its own gets a copy of
**every** argument, each bound to a name on the caller's side of the fence
before the thread starts — so what the caller does next cannot change what the
thread was given, and a call nested in an argument runs in the caller. A
literal is exempt, having nothing to work out. All three spellings alike:
`async f(v)`, `n := async f(v)`, and each call in `await [...]`. See
[mutability](mutability.md).

## What is deliberately absent

No channel type, no lock, no thread handle, no cancellation token and
no scheduler to configure. A program that needs long-lived shared state reaches
for a [service](stdlib/syslink.md), whose handler takes one message at a time and
therefore needs no lock at all; a program that needs a result from work in
flight names it.

*From `spec/09-concurrency.md`.*
