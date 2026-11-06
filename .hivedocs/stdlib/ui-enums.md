# `hive.ui` — the enumerations

Ordinary closed types, reached the way every other type is, and **called with
`()` like any other variant**: `ui.Align.Center()`, not `ui.Align.Center`.

**None is an atom, deliberately**: the atom table belongs to your program, and a
library that added to it would renumber the atoms you wrote.

| type | variants |
| --- | --- |
| `Align` | `Start` `Center` `End` `Stretch` |
| `Justify` | `Start` `Center` `End` `Between` |
| `TextSize` | `Title` `Subtitle` `Body` `Caption` |
| `Axis` | `Horizontal` `Vertical` `Both` |
| `Anchor` | `Pointer` `Caret` — where an [overlay](ui-widgets.md) opens |
| `InputKind` | `Text` `Number` `Date` `Password` `Search` `Range` |
| `Icon` | `Search` `Close` `Check` `Plus` `Minus` `Up` `Down` `Left` `Right` `Warning` `Info` `Star` `Heart` `Reply` `Repeat` `Trash` `User` `Menu` |
| [`Tone`](ui-colour.md) | `Normal` `Muted` `Good` `Warn` `Danger` `HEX(Str)` `RGBA(Int, Int, Int, Int)` |
| [`Surface`](ui-scene-surfaces.md) | nineteen finishes |
| [`Voice`](ui-scene-sound.md) | `Engine` `Tyres` `Brakes` `Wind` `Crowd` `Music` `Impact` `Chime` `Talk` |

```hive
ui.text([ui.size(ui.TextSize.Caption()), ui.tone(ui.Tone.Muted())], "TURN 7")
ui.input([ui.kind(ui.InputKind.Password())], state.secret)
ui.icon([], ui.Icon.Trash())
ui.column([ui.scroll(ui.Axis.Both())], rows)
```

The order above is **declaration order**, which is also the order `sort` puts
them in and the order a `==` comparison rests on.

**The icon list is closed and that is the whole of it.** There is no name to
pass and no file to point at: an icon that is not on the list is a `text` or an
`image`.

Being ordinary types, they are matched like any other — `if chosen is ui.Align.End`
— and a program that stores one stores a `hive.ui.Align`.
