# Tables

`Table` is an alias for `Str[dyn][dyn]` — a vector of rows of cells. It is what
`hive.file.csv` yields, what `hive.sql.raw` answers with, and what
`hive.map.toTable` builds. Two builtins read one by name, and a third cuts a
flat vector of cells into one:

```hive
row(table, key)      // the row whose first cell equals `key`, else []
column(table, key)   // the column whose top cell equals `key`, else []

toTable(cells, 3)    // rows three cells wide, the last one short
```

## Naming the reader

A table is read by naming its reader, which is what lets the compiler leave
the machinery for the others out of the build.

```hive
hive.file.csv("./data.csv", ",")     // a separated table
hive.file.csv("./data.tsv", "\t")    // the separator is always named
hive.file.xlsx("./book.xlsx")        // every sheet of a workbook
hive.file.ods("./book.ods")          // every table of an ODS
hive.sql.run(db, allUsers())         // a declared query, typed rows
hive.sql.raw(db, someSqlText)        // SQL built at run time
```

| call | yields |
| --- | --- |
| `hive.file.csv(path, separator)` | `Result<Table, hive.file.TableError>` |
| `hive.file.xlsx(path)` / `hive.file.ods(path)` | `Result<Table[dyn], hive.file.TableError>` |
| `hive.sql.run(connection, query)` | whatever the query declared its rows to be |
| `hive.sql.raw(connection, text)` | `Result<Table, hive.sql.SqlError>` |

A CSV is a single table, so it comes back as one `Table`. **A spreadsheet holds
many**, so xlsx and ods come back as a `Table[dyn]` — one per sheet, in document
order, an empty sheet being an empty `Table` so the positions still line up.
Both readers are dependency-free.

A `hive.file.TableError` carries a `path` and a `message`. A file that opened
and then turned out not to hold what it said it did is not a filesystem
failure, which is why it is an error apart from `hive.file.FileError`.

```hive
if hive.file.csv("./colonies.csv", ",") is Result.Ok(sheet) {
	for each line in sheet {
		echo join(line, " | ")
	}
}
```

## What a spreadsheet cell arrives as

As the file stores it, with one exception: **xlsx keeps a date as a day count**,
so the cell's number format is consulted to catch exactly those and render them
as `2026-07-25` (or with a time, or time-only). Numbers, booleans and cached
formula results pass through untouched. An ODS stores real dates, so nothing has
to be undone there. **Rows are padded to the widest row in their sheet.**

## The separator is always written

There are no optional parameters in Hive, and a comma is a choice like any
other rather than the one the language makes on your behalf.

*From `spec/14-stdlib.md` §14.6.*
