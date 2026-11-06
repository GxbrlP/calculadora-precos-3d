# `hive.conv`

Number and string conversions. Pure, so it works in a `func`.

**Hive never widens a number behind your back**, so this module is not a
convenience — it is the only way an `Int` becomes a `Float` at all.

| call | signature |
| --- | --- |
| `ceil(v)` `floor(v)` `round(v)` | `(Float): Int` |
| `itf(v)` | `(Int): Float` |
| `itf32(v)` | `(Int): Float32` — the nearest one |
| `its(v)` | `(Int): Str` |
| `fts(v)` | `(Float): Str` |
| `sti(text)` | `(Str): Result<Int, ConversionError>` |
| `stf(text)` | `(Str): Result<Float, ConversionError>` |
| `bytesOf(text)` | `(Str): UInt8[dyn]` — the bytes it holds |
| `fromBytes(bytes)` | `(UInt8[]): Str` — never fails: a `Str` holds any bytes |

`round` rounds **half away from zero**. A `ConversionError` carries the
offending `input` and a short `message`.

```hive
if hive.conv.sti(field) is Result.Ok(n) {
	echo n * 2
}
echo hive.math.max(hive.conv.itf(0), health)   // `0` alone would not compile
```

Converting a `Float` that is `+Inf`, `-Inf`, `NaN` or simply too large to an
`Int` is the **one unspecified case in the language** — Go leaves that
conversion implementation-dependent and Hive does not paper over it. Non-finite
values reach a program through `Float` overflow and through `stf("Inf")`, so
check the range you expect before converting if it matters.

Rendering a value into a string needs none of this:
`"loaded {n} of {total}"` interpolates anything.
