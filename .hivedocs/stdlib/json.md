# `hive.json`

Built on the idea that **Hive's type declarations *are* the JSON schema**. There
is no schema to write, no tag to annotate a field with, and no reflection: a
decoder for a type is derived at compile time.

| call | answers with |
| --- | --- |
| `hive.json.codec()` | `hive.codec.Codec<JsonError>` — the value that says JSON |
| `T.decode(text, codec)` | `Result<T, E>` — `E` is the codec's error, `JsonError` here |
| `T.Variant.decode(text, codec)` | the same — one variant's payload |
| `encode(value, codec)` | `Str` — **cannot fail** |
| `JsonValue.decode(text, codec)` | `Result<JsonValue, _>` — any document |

A `JsonError` carries the exact `path` that failed, what was `expected`
and what was `found`. `encode` and `decode` name no format: **the codec is
the only thing that says JSON**, which is what lets another format be another
codec — [`jwtCodec`](crypto-jwt.md), [`queryParamsCodec`](net-urls.md) and
[`hive.term.codec`](term.md) are —
rather than a change to the language. A codec's type names the error its
decoding fails with, `hive.codec.Codec<E>`, and each module owns its own.

A codec is an **ordinary value**: its type already says the format, so one held
in a variable, passed to a function or kept in a field encodes and decodes
exactly as one written at the call.

```hive
type User {
	id:   Int
	name: Str
}

if User.decode(body, hive.json.codec()) is Result.Ok(user) {
	echo user.name
}
echo encode(user, hive.json.codec())
```

## The annotations steer both codecs

A field's `--` annotations are what decide the key and what happens when it is
not there — see [declarations](../declarations.md#field-annotations):

```hive
type User {
	name: Str -- JSON as username;
	age:  Int
	firstName: Str -- Default as "";
}

encode(User("ada", 36, "Ada"), hive.json.codec())
// {"username":"ada","age":36,"firstName":"Ada"}

User.decode("\{\"username\":\"ada\",\"age\":36}", hive.json.codec())
// Result.Ok — `firstName` fell back to ""
```

`JSON as` renames in **both** directions, so a round trip agrees with itself.
`Default as` is what turns a required field into an optional one: an absent
key and a `null` one are the same nothing, and both read as the literal.

## Decoding

* **Missing fields, wrong types and wrong static vector lengths become errors**
  carrying the path that failed — unless the field has a `Default`, which
  covers the first of those and **not** the second.
* **JSON fields the type doesn't declare are ignored.**
* **Variants decode as `{"VariantName": {...}}`**, and JSON `null` selects a
  type's first field-less variant.
* `encode` derives the encoder from the **static** type and therefore cannot
  fail — it answers with a `Str`, not a `Result`.
* **A map does not encode.** Its keys are whatever was put in it, while decoding
  here is by declared shape. Send its pairs as a vector of a type declared for them
  — or hold the document as a `JsonValue`, below, whose objects are maps.
* **Nor does a `Table`**, anywhere in a value: it is rows of cells with nothing
  to name them. `Table.decode` does not exist.

## When the shape is not yours to declare

`hive.json.JsonValue` is any document, as the JSON it is:

```hive
type JsonValue {
	String { value: Str }
	Boolean { value: Bool }
	Int { value: Int }
	Float { value: Float }
	Array { values: JsonValue[dyn] }
	Object { properties: hive.map.Map<Str, JsonValue> }
	Null
}
```

It reads and writes the document itself — `"x"`, never
`{"String": {"value": "x"}}` — and is taken apart like any union:

```hive
if hive.json.JsonValue.decode(config, hive.json.codec()) is Result.Ok(doc) {
	if doc is hive.json.JsonValue.Object(properties) {
		for each key in hive.map.keys(properties) {
			echo key
		}
		if hive.map.get(properties, "name") is Result.Ok(name) {
			echo name
		}
	}
}
```

* A number is an `Int` where it reads as one and a `Float` otherwise, so
  `1.0` stays a `Float` both ways.
* An object's properties are a [map](map.md), in the order the document wrote
  them. A key written twice keeps its first place and its last value — as it
  does for a declared type — and text after the document is an error.
* Holding a map, a `JsonValue` has no order: `sort` over them takes the
  `func` that says which comes first.
* `null` is `Null()`, wherever the document holds one.
* It is read whole: the document says which variant it is, so
  `JsonValue.String.decode` is refused.
* A field may be one, which leaves that part of a declared type undeclared.

The same derived codecs are what a [`hive.syslink`](syslink.md) message
crosses the wire as.
