# Hive, for whoever is writing it

Hive is a memory-managed language that compiles to Go. Values behave like
values, and a great deal of what other languages leave to run time — every
vector index, every branch of a match, the columns a SQL query comes back
with — is settled while it compiles.

Source files end in `.hive`. The standard library is reached as `hive.*`.

## How to use these pages

Each page is short and complete about one thing. **Read the page for what you
are about to write** rather than guessing the syntax: Hive refuses a great deal
that other languages accept, and every refusal below is one the compiler
actually makes.

| page | what is on it |
| --- | --- |
| [syntax](syntax.md) | comments, keywords, how a name must be spelled, both string forms |
| [types](types.md) | scalars, vectors, `Result`, declared types, maps, what may be assigned to what |
| [declarations](declarations.md) | `type` `func` `proc` `query` `test`, and returning on every path |
| [expressions](expressions.md) | operators, precedence, calls, named arguments, function values |
| [statements](statements.md) | bindings, assignment, `if`, `switch`, loops, `echo` / `assert` / `panic` |
| [patterns](patterns.md) | `is`, its four pattern kinds, nesting them, narrowing, exhaustiveness, a `switch`'s coverage |
| [mutability](mutability.md) | `mut`, `mut` parameters, why a binding sometimes copies |
| [concurrency](concurrency.md) | `async`, the await-all, `with timeout` |
| [bounds](bounds.md) | how every index and slice is proved in range |
| [generics](generics.md) | type variables and monomorphization |
| [modules](modules.md) | `import`, the four path kinds, importing Go, the library's short names |
| [builtins](builtins.md) | the functions that need no import |
| [tables](tables.md) | CSV, spreadsheets, and the `Table` type |
| [queries](queries.md) | `query` declarations and the SQL in them |
| [testing](testing.md) | `test`, `assert`, coverage |
| [cli](cli.md) | every `hive` command |
| [pitfalls](pitfalls.md) | **the mistakes that do not compile** — read this one first |
| [stdlib/](stdlib/README.md) | every `hive.*` module, one page each |

## Eight rules that catch everybody

1. **There is no truthiness.** A condition is a `Bool` and nothing else.
2. **`!` inverts a `Bool` and nothing else**, and it binds tight: `!a && b` is
   `(!a) && b`, and a match may not be negated at all.
3. **Every index must be proved in range** at compile time, or guarded with
   `if v bounds i`. See [bounds](bounds.md).
4. **A slice's high bound is inclusive**: `v[1:3]` is three elements.
5. **`append` needs a `mut T[dyn]`**, and `[dyn]` is declared, never inferred:
   `mut v := ["a"]` is a `Str[1]` and cannot grow.
6. **No number is widened for you.** `Int` does not become `Float`; go through
   `hive.conv.itf`.
7. **A name's spelling says what it is** — `camelCase` values, `PascalCase`
   types — and it is enforced. `UPPER_CASE` is *allowed* for an immutable
   variable, never required: `camelCase` is the default for every variable.
8. **Every call blocks its caller.** Concurrency is decided where a call is
   written, never where it is declared.

## Where these came from

Every page is condensed from `spec/` in the Hive repository, which is the
normative reference. A page ends with the chapters it came from; read those
when a page leaves a question open.
