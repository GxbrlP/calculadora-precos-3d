# `hive.map`

A dictionary: keys paired with values, looked up by key. The one collection that
is not a vector, so it is a module rather than a literal.

| call | type | what it does |
| --- | --- | --- |
| `new()` | `Map<K, T>` | the empty map |
| `set(m, key, value)` | `(mut Map<K, T>, K, T): void` | adds or replaces a pair |
| `get(m, key)` | `(Map<K, T>, K): Result<T, Bool>` | the value, or `Error(false)` |
| `has(m, key)` | `(Map<K, T>, K): Bool` | the same question without the value |
| `delete(m, key)` | `(mut Map<K, T>, K): void` | removes a pair |
| `keys(m)` | `(Map<K, T>): K[dyn]` | its keys, in order |
| `values(m)` | `(Map<K, T>): T[dyn]` | its values, in the same order |
| `fromTable(t)` | `(Table): Map<Str, Str>` | reads rows as key/value pairs |
| `toTable(m)` | `(Map<Str, Str>): Table` | one two-cell row per pair |

```hive
mut hive.map.Map<Str, Int> counts = hive.map.new()
hive.map.set(counts, "apple", 3)

for each key in hive.map.keys(counts) {
	if hive.map.get(counts, key) is Result.Ok(n) {
		echo "{key}: {n}"
	}
}
```

## The rules

* **`new()` takes its type from where it lands** — a declaration, a `return`
  whose callable declares a map, or an argument to a parameter or field declared
  as one — or, bound with `:=`, from the **first later use** that says it:
  `hive.map.set(m, "a", 1)` makes `m` a `Map<Str, Int>` for good, and a later
  `set` of a `Str` value is a compile error.
* **A key is compared and hashed whole**, so it is a `Str`, `Int`, `Float`,
  `Bool` or `Atom` — or a declared type whose every field is one of those,
  which gives a composite key. **Storage cannot be a key**:
  `Map<Str[dyn], Int>` is a compile error.
* **A map is reached by key, never by position.** `m[0]` is a compile error
  pointing at `get`, and `for each` over a map is one too — a turn of the loop
  would have to be handed the key or the value, and the syntax never said which.
  Loop over `keys(m)`.
* **The order is the order you set the keys in.** `keys`, `values`, `toTable`
  and `echo` all use it, and replacing a value leaves its key where it was.
  (Go's own map iterates in a deliberately randomised order; this one prints the
  same thing twice, which is what makes it testable.)
* **Only a `mut` map can be written to.** `set` and `delete` follow `append`'s
  rule exactly, and a `proc` may take a `m: mut hive.map.Map<K, T>` parameter.
* **A map is a value**, and so is what comes out of it: `keys` and `values` are
  fresh vectors.
* **`==` compares the pairs** and ignores the order they were set in. There is
  no ordering *between* maps, so `sort` on a vector of them — or of a type
  holding one — is a compile error.
* **A map does not travel and does not encode.** `encode` refuses one
  and so does a [`hive.syslink`](syslink.md) mailbox: decoding there is by
  declared shape, while a map's keys are whatever was put in it. Send its pairs
  as a vector of a type declared for them. The one exception is a
  [`JsonValue`](json.md) object's properties, whose codec is the document itself.

The module's name `map` **coexists with the `map(v, f)` builtin**: a call
on the name is the module and a bare call is the builtin, and the two are told
apart by shape.
