# `hive.net`

HTTP, WebSockets and raw TCP, clients and servers. Everything here performs I/O,
so it works inside a `func` or a `proc`, and **none of it adds a dependency**.

| page | what is on it |
| --- | --- |
| [net-http](net-http.md) | `httpRequest`, `httpServe`, and the two types |
| [net-websockets](net-websockets.md) | `wsConnect`, `wsServe`, `wsSend`, `wsReceive` |
| [net-sockets](net-sockets.md) | `socketConnect`, `socketServe`, and the stream |
| [net-names](net-names.md) | `resolve`, `localAddress` |
| [net-urls](net-urls.md) | `urlEncode`, `queryParamsCodec` |

## What every server here has in common

**Each of the three servers blocks forever**, so it usually goes on a virtual
thread of its own:

```hive
async hive.net.httpServe(8080, handle)
```

Each runs **its handler once per request or connection, on a thread of its
own** — so a slow handler holds up nobody but its own caller, and a handler
needs no lock only because it shares nothing. Long-lived shared state belongs
in a [service](syslink.md).

**A handler is passed by name**, and its declared shape is checked at compile
time — including through a partial application, which is how a handler reaches
anything it needs:

```hive
proc handle(db: hive.sql.SqlConnection, req: hive.net.HttpRequest): hive.net.HttpResponse {
	// ...
}

async hive.net.httpServe(8080, handle(db, _))
```

**Every call names its protocol**, so nothing reads as "the" default one: there
is no `serve`, only `httpServe`, `wsServe` and `socketServe`.

## The errors

Each protocol has its own error type, and each is a union with a variant per way
it fails, every one carrying a `message`:

| type | its variants |
| --- | --- |
| `HttpError` | none — a struct carrying the `url` and a `message` |
| `WsError` | `Handshake` `Protocol` `Closed` `Send` `Receive` |
| `SocketError` | `Connect` `Closed` `Send` `Receive` |
| `NetError` | `NotFound` `Lookup` `NoAddress` |

For a server that answers with a **page rather than a string**, `hive.ui.page`
renders the same view tree a window paints: see [ui](ui.md).
