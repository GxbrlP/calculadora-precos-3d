# The standard library

Reached as `hive.<module>.<name>`, from anywhere, with no import — or as
`<module>.<name>`, `net.httpRequest`, wherever the program has not taken
that name for something of its own ([modules](../modules.md)).
`import hive.net as web` only gives the module another **spelling** —
`web.httpRequest` and `hive.net.httpRequest` are the same call, and neither
changes what is linked.

Each module owns its types under its own namespace: `hive.net.HttpRequest`,
`hive.json.JsonError`, `hive.map.Map`, `hive.syslink.SyslinkError`. The
only builtin types that live directly on `hive` are the three the language uses
without a module: `Result`, `Table` and `Address<M>`.

**A library call is held to its signature** — how many arguments, and what each
is — and a type or an enumeration variant the module does not have
(`hive.net.Nonesuch`, `hive.ui.TextSize.Small()`) is a compile error rather
than something the Go toolchain reports later.

**A failure is a variant.** Where a module can fail in more than one way, its
error is a union with a variant per way, sharing a `message` and whatever else
the module knows — so it is matched and covered like any union:

```hive
if file.read(path) is Result.Error(file.FileError.NotFound(_, _)) {
	echo "nothing there yet"
}
```

These are `FileError`, `WsError`, `SocketError`, `NetError`, `SqlError`,
`CryptoError`, `SyslinkError` and the core's `SecretError`. One comes with the
module that answers with it, whether or not the program names it, and it prints
as what went wrong and why.

**A module you don't use is not in your build.** Every module but two is
written against the target's standard library alone, so HTTP, WebSockets, TCP,
JSON, cryptography, spreadsheets and windows all build offline with no
dependencies. The two exceptions are fetched on the first build that needs them,
cached, and never linked into a program that does not: `hive.sql` links
database drivers, and `hive.ui.scene` is drawn with a pinned three.js.

| page | module | what is on it |
| --- | --- | --- |
| [conv](conv.md) | `hive.conv` | rounding, widening, rendering, parsing |
| [math](math.md) | `hive.math` | thirteen `Float` functions |
| [map](map.md) | `hive.map` | the dictionary |
| [file](file.md) | `hive.file` | the filesystem |
| [term](term.md) | `hive.term` | stdout, stderr, input, arguments, exit |
| [term-exec](term-exec.md) | `hive.term` | running another program |
| [env](env.md) | `hive.env` | the environment and `.env` |
| [task](task.md) | `hive.task` | `sleep`, `sleepForever`, and where `with timeout` lives |
| [time](time.md) | `hive.time` | Unix milliseconds and `strftime` |
| [json](json.md) | `hive.json` | your types *are* the schema |
| [crypto](crypto.md) | `hive.crypto` | hashing, encoding, random |
| [crypto-encrypt](crypto-encrypt.md) | `hive.crypto` | `encrypt` / `decrypt` |
| [crypto-jwt](crypto-jwt.md) | `hive.crypto` | tokens, as a codec |
| [net](net.md) | `hive.net` | what every server here has in common |
| [net-http](net-http.md) | `hive.net` | HTTP, client and server |
| [net-websockets](net-websockets.md) | `hive.net` | WebSockets |
| [net-sockets](net-sockets.md) | `hive.net` | raw TCP |
| [net-names](net-names.md) | `hive.net` | `resolve` and `localAddress` |
| [net-urls](net-urls.md) | `hive.net` | `urlEncode` and the query string codec |
| [sql](sql.md) | `hive.sql` | connections, drivers, and running a query |
| [syslink](syslink.md) | `hive.syslink` | what a service is |
| [syslink-calls](syslink-calls.md) | `hive.syslink` | every call, and calling an address |
| [syslink-nodes](syslink-nodes.md) | `hive.syslink` | across machines |
| [ui](ui.md) | `hive.ui` | a view is a value — **thirteen pages**, start here |
| [audio](audio.md) | `hive.audio` | a recording or a live stream, by name |

Reading a table from a CSV or a spreadsheet is [`hive.file`](file.md), and
the `Table` it answers with is [tables](../tables.md). Running a `query` is
[queries](../queries.md).

*From `spec/14-stdlib.md`.*
