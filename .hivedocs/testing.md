# Testing

A test is a top-level declaration, alongside `proc`, `func`, `query` and `type`:

```hive
import ./cart

test "an empty cart costs nothing" {
	cart.Item[0] empty = []
	assert cart.total(empty) == 0
}
```

Run them with **`hive test <entrypoint.hive>`**. There is nothing to install and
nothing to register: no framework, no third-party library, no `describe`/`it`,
and no assertion vocabulary beyond the `assert` the language already has.

A test takes no parameters and returns nothing. Tests may live beside the code
they are about or in a file of their own; a file holding only tests needs no
`main`, and a run covers **every test in every file the entrypoint reaches**.

**`hive test <directory>`** (`hive test .`) needs no entrypoint: it runs the
tests of every `.hive` file under it that git does not ignore, and of every file
outside it that one of those imports, each file's tests exactly once.

## `assert` means the same thing and does something different

In ordinary code a failed assertion has proved the **program** wrong, so it
stops. Inside a test it has proved the **test** wrong, so the failure is recorded
and the rest of the suite still runs. A test that **panics** fails on its own
rather than taking the suite with it.

A failed comparison shows both sides:

```
  PASS  an empty cart costs nothing
  FAIL  lines add up
        cart.test.hive:33: assert cart.total(two) == 17
          left:  16
          right: 17

  2 tests: 1 passed, 1 failed
```

**An `assert`'s operands are evaluated exactly once**, whether it holds or not,
so an assertion over a call with an effect means what it looks like:

```hive
test "the cursor advances" {
	mut P p = P(tokens, 0, [])
	assert parseSum(p) == 42     // runs parseSum once, not twice
	assert len(p.errors) == 0
}
```

## Coverage is not a separate command

Every run reports it — there is no flag to remember:

```
  6 tests: 6 passed
  coverage: 87.5% of statements (7/8)
  never exercised: describe
```

The percentage counts statements of **your own** declarations; the clone
helpers, ordering helpers, atom table and JSON marshalling the compiler emits
are not something a test can be said to have missed. `never exercised` names
the declarations no test reached at all. With more than one file, a per-file
breakdown is printed too.

A test run **exits non-zero when any test fails**, which is what makes it the
thing a commit hook or a CI step runs.

## Where a test runs

A test runs with the working directory set to the **generated project**, not to
the entrypoint's folder — a difference from `hive run`, which chdirs to the
entrypoint's folder so `hive.file.csv("./test.csv", ",")` resolves the way its author wrote
it.

So **a test that opens a relative path is not looking where the source file
is**. A test that needs files should write them itself —
`hive.file.makeDir` and `hive.file.write` into a directory of its own — which
is also what makes it independent of how the suite was invoked.

## What runs it

`go test`. The tests are generated into a `main_test.go` in the **same Go
package** as `main.go`, which is what lets a test reach every proc, func and
type the program declares without any of them being exported or otherwise made
testable on purpose.

*From `spec/16-testing.md`.*
