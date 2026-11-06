# `hive.net` — WebSockets

RFC 6455. **The handshake, frame headers, masking, ping/pong and fragmentation
are the runtime's business; a program sees whole messages as `Str`.**

| call | answers with |
| --- | --- |
| `wsConnect(url)` | `Result<WsConnection, WsError>` |
| `wsServe(port, handler)` | `void` — **blocks forever** |
| `wsSend(conn, message)` | `Result<Int, WsError>` — the bytes it carried |
| `wsReceive(conn)` | `Result<Str, WsError>` — the next message |
| `wsRequest(conn)` | `HttpRequest` — the request that opened it |
| `wsClose(conn)` | `void` |

`handler` is a `proc(WsConnection): void`, run once per connection on a thread
of its own. A `WsConnection` is **opaque** — a handle to hold and hand back.

A `WsError` is `Handshake`, `Protocol`, `Closed`, `Send` or `Receive`.
**A peer that hangs up is `WsError.Closed` — the ordinary end of a
conversation**, not a failure to report.

## A server

```hive
proc echoBack(conn: hive.net.WsConnection): void {
	for ; true; {
		if hive.net.wsReceive(conn) is Result.Ok(message) {
			if hive.net.wsSend(conn, message) is Result.Error(_) {
				return
			}
		} else {
			return                       // "Closed": they hung up
		}
	}
}

proc main(): void {
	hive.net.wsServe(9001, echoBack)
}
```

`wsRequest(conn)` is how a server reads **the path and the headers it was
reached at** — the URL a browser opened, and any token in it.

## A client

```hive
if hive.net.wsConnect("wss://example.com/feed") is Result.Ok(conn) {
	_ := hive.net.wsSend(conn, "subscribe")
	if hive.net.wsReceive(conn) is Result.Ok(first) {
		echo first
	}
	hive.net.wsClose(conn)
}
```

A receive **blocks the calling virtual thread** and nobody else, so a client
that also does something else reads on a thread of its own.
