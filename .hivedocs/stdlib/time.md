# `hive.time`

**Times are plain `Int`s — Unix milliseconds.** There is no date type to build, no
duration type to convert, and arithmetic on a time is arithmetic.

| call | answers with |
| --- | --- |
| `now()` | `Int` |
| `timezone()` | `Str` — the zone name or abbreviation at this instant |
| `timezoneOffset()` | `Int` — minutes east of UTC |
| `format(time, template)` | `Str` — rendered in **local** time |
| `dateFrom(year, month, day)` | `Int` — that date at midnight |
| `dateTimeFrom(year, month, day, hour, minute, second)` | `Int` — that instant |

`format` takes a `strftime`-style template. Unrecognised `%x` escapes pass
through verbatim:

| | | | |
|---|---|---|---|
| `%Y` year (4) | `%y` year (2) | `%m` month | `%d` day |
| `%H` hour 00–23 | `%I` hour 01–12 | `%M` minute | `%S` second |
| `%p` AM/PM | `%j` day-of-year | `%Z` zone name | `%z` zone offset |
| `%A`/`%a` weekday | `%B`/`%b` month name | `%%` literal `%` | |

```hive
echo hive.time.format(hive.time.now(), "%Y-%m-%d %H:%M")
echo hive.time.format(stamp, "%A %e %B")           // %e passes through
elapsed := hive.time.now() - started               // milliseconds, as an Int
```

## Building a time

`dateFrom` and `dateTimeFrom` answer with the same kind of `Int` `now()` does,
for a date you name rather than this one. Both build in **local** time, so a
stamp round-trips with `format`.

A field out of range **carries into the next one**, the way a clock does:
month 13 is January of the year after, and day 0 is the last day of the month
before. That is not a mistake to work around — it is how a boundary is reached
without a calendar:

```hive
hive.time.dateFrom(2026, 9, 14)                  // 2026-09-14 00:00:00
hive.time.dateTimeFrom(2026, 9, 14, 13, 30, 0)   // 2026-09-14 13:30:00
hive.time.dateFrom(2026, 13, 1)                  // 2027-01-01
hive.time.dateFrom(2026, 3, 0)                   // 2026-02-28, February's last
```

## The current instant, field by field

Each answers one field of **now**, read in local time. They take no arguments:
to read a field off some other stamp, render that stamp with `format`.

| call | answers |
| --- | --- |
| `year()` | the full year — `2026` |
| `month()` | `1`–`12` |
| `day()` | `1`–`31` |
| `weekday()` | `1` Monday – `7` Sunday, the ISO numbering |
| `lastDayOfMonth()` | `28`–`31` — how long **this** month is |
| `hour()` | `0`–`23` |
| `minute()`, `second()` | `0`–`59` |
| `millisecond()` | `0`–`999` |

Together they are the ends of the current month, which needs no calendar of
your own:

```hive
year := hive.time.year()
month := hive.time.month()
first := hive.time.dateFrom(year, month, 1)
last := hive.time.dateFrom(year, month, hive.time.lastDayOfMonth())
```

A stamp is in milliseconds, the unit `with timeout` and
[`hive.task.sleep`](task.md) speak too. `millisecond()` is something else: the
sub-second **field** of this instant, the way `second()` reads `0`–`59`.
