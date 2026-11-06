# `hive.task`

The module is three things, and one of them has no call.

## `sleep(ms)`

Parks the calling virtual thread. **Only that goroutine waits**, so two calls
that each sleep, waited for together in one `await`, finish in about the longer
of the two rather than the sum:

```hive
await [slowly("a"), slowly("b")]   // one second, not two
```

A non-positive `ms` returns immediately.

## `sleepForever()`

Parks the calling virtual thread for good — for a `main` that has started what
the program is for and has nothing left to do itself. The program still ends
where it would have: at `hive.term.exit`, or when its last window closes.

## `TimeoutError`

The type `with timeout` answers with. It carries `waited` — the milliseconds
that were asked for, an `Int` — and a `message`.

```hive
if slowShout("worth waiting for") with timeout 100 is Result.Error(err) {
	echo "gave up after {err.waited}ms"
}
```

`with timeout` is a language clause rather than a call, and lives on
[concurrency](../concurrency.md). In short: it may follow anything that waits,
turns the result into `Result<T, hive.task.TimeoutError>`, is **one deadline
across a whole await-all**, and abandons the **waiting rather than the work** —
the call runs on and only its result is dropped.
