# `hive.net` — raw TCP

**A stream, not a queue of messages.** Nothing here preserves the boundaries a
program wrote in: two sends may arrive as one read, and one send as two.

| call | answers with |
| --- | --- |
| `socketConnect(host, port)` | `Result<SocketConnection, SocketError>` |
| `socketServe(port, handler)` | `void` — **blocks forever** |
| `socketSend(conn, data)` | `Result<Int, SocketError>` |
| `socketReceive(conn, bytes)` | `Result<Str, SocketError>` |
| `socketReceiveLine(conn)` | `Result<Str, SocketError>` — without the newline |
| `socketPeer(conn)` | `Str` |
| `socketClose(conn)` | `void` |

`handler` is a `proc(SocketConnection): void`, run once per connection on a
thread of its own. A `SocketConnection` is **opaque**.

A `SocketError` is `Connect`, `Closed`, `Send` or `Receive`.

## A short read is normal

`socketReceive(conn, 4096)` asks for **at most** that many bytes and answers
with whatever had arrived. That is the stream being a stream rather than
something going wrong, so a program that needs a whole thing loops until it has
one.

**`socketReceiveLine` is the usual answer to that**, because a line is a
boundary the other end actually wrote:

```hive
proc serve(conn: hive.net.SocketConnection): void {
	echo "connection from {hive.net.socketPeer(conn)}"
	for ; true; {
		if hive.net.socketReceiveLine(conn) is Result.Ok(line) {
			_ := hive.net.socketSend(conn, "you said: {line}\n")
		} else {
			return
		}
	}
}

proc main(): void {
	hive.net.socketServe(7000, serve)
}
```

`socketPeer` is the far end's address, which is what a log line wants.

For a protocol of whole messages, prefer
[WebSockets](net-websockets.md); for one between Hive programs, a
[service](syslink.md) is already framed, typed and encrypted.
