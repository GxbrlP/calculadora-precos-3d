# `hive.math`

| | |
| --- | --- |
| **Constants** | `pi()` |
| **Angles** | `sin` `cos` `tan` `asin` `acos` `atan2(y, x)` |
| **Distances** | `sqrt` `hypot(x, y)` `abs` |
| **Bounds** | `min(a, b)` `max(a, b)` `clamp(value, low, high)` |

**Every one takes and answers with a `Float`, and there is no integer twin.** A
call handed only `Float32`s answers a `Float32`.
That is one rule for thirteen functions, and it is the same rule the rest of the
language keeps: `hive.math.max(0, health)` is a **compile error** rather than a
surprise, because `0` is an `Int`. Go in through
[`hive.conv.itf`](conv.md).

**Clamping an `Int` is an `if`**, and needs no library.

Nothing here reports an error, because none of these have one: a value outside a
function's domain answers with the non-finite `Float` the arithmetic already
produces.

`atan2` takes the two legs rather than their ratio, which is what lets it tell
the four quadrants apart. `clamp` is exactly `min(max(v, low), high)`, so
bounds the wrong way round answer with `high`.

```hive
angle := hive.math.atan2(dy, dx)
reach := hive.math.hypot(dx, dy)
held  := hive.math.clamp(wanted, 0.0, 1.0)
```
