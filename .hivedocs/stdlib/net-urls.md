# `hive.net` — URLs and query strings

| call | answers with |
| --- | --- |
| `urlEncode(text)` | `Str` — safe in a path segment and a query alike |
| `queryParamsCodec()` | `hive.codec.Codec<QueryParamsError>` — the value that says query string |

Neither performs I/O.

## `urlEncode`

Every byte but letters, digits, `-`, `.`, `_` and the tilde is
percent-encoded, so a space is `%20` rather than `+`:

```hive
hive.net.urlEncode("rust & go")   // rust%20%26%20go
```

## A query string is a codec

`queryParamsCodec` goes where [`hive.json.codec()`](json.md) goes, so a type's
fields are written with [`encode`](../builtins.md) and read with `T.decode` —
**without** the leading `?`:

```hive
type Search {
	term: Str -- URL as q;
	page: Int -- Default as 1;
	tags: Str[dyn] -- URL as tag;
}

encode(Search("rust & go", 2, ["web", "cli"]), hive.net.queryParamsCodec())
// q=rust%20%26%20go&page=2&tag=web&tag=cli

if Search.decode("q=hive+lang&tag=web", hive.net.queryParamsCodec()) is Result.Ok(search) {
	echo search.term   // hive lang, on page 1
}
```

* **`URL as` names the parameter**, the way `JSON as` names a key; without it
  the field's own name is the key. Two fields may not answer to one.
* **A vector is its key repeated**, once per element and in order. An absent key
  reads as an empty vector, and a `T[n]` needs it exactly `n` times.
* **A missing field is an error** unless it has a `Default`, and so is a key
  given twice for a field that is not a vector.
* `+` and `%20` both read as a space, a leading `?` is tolerated, and a
  parameter the type does not declare is ignored. A `Bool` is `true` or
  `false`.

## What travels as one

A query string is **flat**, so only a type without variants does, and each of its
fields is a `Str`, `Int`, `Float`, `Bool` or `Atom`, or a vector of one.
Anything else is a compile error at the `encode` or `decode` that asked.

A failure is a `hive.net.QueryParamsError`: the `path` that failed, such as
`$.page`, what was `expected` there, and what was `found`.
