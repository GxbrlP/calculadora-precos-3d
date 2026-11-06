# Queries

A `query` is a `func` whose body is **inline SQL** and whose **return type
describes its rows**. Calling one does not touch a database: it answers with a
`hive.sql.Fragment<rows>` — the text, and the values bound beside it — and
`hive.sql.run(<connection>, <query>)` is what runs it.

```hive
type User {
	id:   Int
	name: Str
}

query findUser(name: Str): User[dyn] {
	SELECT id, name FROM users WHERE name = {name}
}

query userNames(): Str[dyn] {      // one column needs no row type
	SELECT name FROM users
}

query deleteUser(id: Int): void {  // a statement reports what it touched
	DELETE FROM users WHERE id = {id}
}
```

| declared | `q(...)` is | `hive.sql.run(conn, q(...))` yields |
| --- | --- | --- |
| `Row[dyn]` (a declared type) | `Fragment<Row[dyn]>` | `Result<Row[dyn], hive.sql.SqlError>` |
| `Str[dyn]`, `Int[dyn]`, … | `Fragment<Str[dyn]>` | that column, as a vector |
| `Table` | `Fragment<Table>` | `Result<Table, hive.sql.SqlError>` — a header row, then every row as text |
| `void` | `Fragment<void>` | `Result<Int, hive.sql.SqlError>` — the rows it affected |

Because a fragment is a value, it can be bound, passed and held like any other
— and a `hive.sql.run` handed anything that is not one is a compile error
naming what it got instead.

## What the compiler enforces

* **Columns match fields by name**, so reordering the `SELECT` cannot silently
  remap them. A column whose name differs from its field needs an alias
  (`SELECT u.name AS author`). A row type holds scalars only.
* **A `Table` takes whatever comes back**, so it is the one result `SELECT *`
  fills.
* **`SELECT *` against a declared row type is a compile error.** It says neither
  how many columns come back nor what they are called. The rule is about the
  *result*, so `count(*)`, `a * 2`, a star inside a subquery and a `void`
  statement's select list all still compile.
* **Values are bound, never spliced.** An interpolated `{param}` becomes a
  placeholder and the value travels beside the text, so nothing a caller
  supplies can change what a statement means. Queries are written with `?` and
  rewritten to `$1, $2, …` for PostgreSQL by the connection.

## Optional filters: `WHERE { }`

A `WHERE` block ANDs the predicates whose conditions hold; a nested `or { }` or
`and { }` flips the connective:

```hive
query findColonies(apiary: Str, minFrames: Int, small: Bool, huge: Bool): Colony[dyn] {
	SELECT name, apiary, frames FROM colonies
	WHERE {
		if apiary != ""  { apiary = {apiary} }
		if minFrames > 0 { frames >= {minFrames} }
		or {
			if small { frames < 4 }
			if huge  { frames > 10 }
		}
	}
	ORDER BY name
}
```

A group that contributes nothing disappears rather than leaving a dangling
connective, and if no predicate is present at all there is **no `WHERE` clause**
— so there is no `WHERE 1 = 1` to write. A group contributing more than one
predicate is parenthesised. Every branch's text is fixed at compile time; only
which branches are taken is decided at run time.

## Two things a `WHERE` block cannot do

A **column name or sort direction can never be a parameter** — `ORDER BY {col}`
would sort by a constant string — so make the choices a variant type and dispatch
to one query per ordering. And **SQL you genuinely assemble yourself** goes
through `hive.sql.raw`, which is untyped by construction and greppable by
design.

## Inside a query body

It is SQL rather than Hive: SQL's own `--` and `/* */` comments are recognised,
SQL keywords keep SQL's upper-case convention, and a name that collides with one
is quoted the way SQL has always done it (`SELECT "order" FROM …`).

Connections come from [`hive.sql`](stdlib/sql.md).

*From `spec/04-declarations.md` §4.5.*
