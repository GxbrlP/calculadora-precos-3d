# `hive.sql`

Talks to **SQLite** (the pure-Go `modernc.org/sqlite` driver, compiled straight
into your executable) and **PostgreSQL** (`github.com/lib/pq`). This is the one
module that links a dependency, fetched on the first build that needs it.

| call | answers with |
| --- | --- |
| `connect(driver, connString)` | `Result<SqlConnection, SqlError>` |
| `pool(driver, connString, maxOpen, maxIdle)` | `Result<SqlConnection, SqlError>` |
| `close(conn)` | `void` |
| `run(conn, fragment)` | whatever the query declared its rows to be |
| `raw(conn, text)` | `Result<Table, SqlError>` |

The driver is a `hive.sql.DatabaseDriver`, built with `.SQLite()`,
`.PostgreSQL()` or `.Other(name)`. A `SqlConnection` is **opaque**.

**Opening a connection and running what a query built is the whole of this
module's surface.** Everything else a program does with a database it does
through a [`query` declaration](../queries.md): calling one answers with a
`hive.sql.Fragment<rows>` — the text, and the values bound beside it,
nothing having run yet — and `run` is what runs one.

SQL you genuinely assemble yourself goes through `raw`, which is untyped by
construction — a `Table`, header row and all — and greppable by design.

```hive
proc main(): void {
	opened := hive.sql.connect(hive.sql.DatabaseDriver.SQLite(), "./hive.db")
	if opened is Result.Error(why) {
		echo "cannot open the database: {why.message}"
		hive.term.exit(1)
	}
	if opened is Result.Ok(db) {
		if hive.sql.run(db, findUser("ada")) is Result.Ok(rows) {
			for each user in rows {
				echo user.name
			}
		}
	}
}
```

## A connection is a pool

A `SqlConnection` is a **connection pool**, safe to hold for the life of the
program and to share across virtual threads. **Open it once in `main` and pass
it along; never open one per query.** A handler reaches it through a partial
application — `hive.net.httpServe(8080, handle(db, _))`.

## The errors

A `SqlError` is one of four variants, each carrying a `message`:

| variant | means |
| --- | --- |
| `Connection` | the database could not be opened or reached, or the connection is closed |
| `Statement` | the statement itself failed |
| `Shape` | the columns are not the row's fields: one fills none, or a field has none |
| `Convert` | a cell did not fit its field's type |

## In-memory SQLite

It belongs to the **connection**, not the process, which under a pool means each
connection lands on a database of its own. Ask for a shared cache —
`pool(driver, "file::memory:?cache=shared", 8, 1)` — or pin the pool to one
connection.

A program that opens a database makes `hive container` resolve the drivers with
`go mod tidy` before it compiles; both drivers are pure Go, so nothing of them
is left for the runtime stage to carry.
