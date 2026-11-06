# `hive.net` — HTTP

| call | answers with |
| --- | --- |
| `httpRequest(req)` | `Result<HttpResponse, HttpError>` |
| `httpServe(port, handler)` | `void` — **blocks forever** |

`handler` is a `proc(HttpRequest): HttpResponse`.

## The two types

```hive
hive.net.HttpRequest(method, url, headers, body)     // Str, Str, Table, Str
hive.net.HttpResponse(status, headers, body)         // Int, Table, Str
```

**Headers are a `Table` of `[name, value]` rows**, which is what makes
`row(req.headers, "content-type")` the way to read one.

An `HttpError` carries the `url` and a `message`.

## A client

```hive
asked := hive.net.HttpRequest("GET", "https://example.com/api", [], "")

if hive.net.httpRequest(asked) is Result.Ok(answer) {
	if answer.status == 200 {
		echo answer.body
	}
}
```

A `Result.Ok` means **the round trip happened**, not that the server was
pleased: a 404 and a 500 are both an `Ok` carrying that status. An `Error` is a
request that never got an answer at all.

Several requests at once are the [await-all](../concurrency.md):

```hive
both := await [hive.net.httpRequest(a), hive.net.httpRequest(b)]
```

## A server

```hive
proc handle(req: hive.net.HttpRequest): hive.net.HttpResponse {
	if req.url is "/health" {
		return hive.net.HttpResponse(200, [], "ok")
	}
	if req.url is "/users/{id}" {
		return hive.net.HttpResponse(200, [], "user {id}")
	}
	return hive.net.HttpResponse(404, [], "not found")
}

proc main(): void {
	hive.net.httpServe(8080, handle)
}
```

Routing is [string patterns](../patterns.md) on `req.url` — that is what they
are for, and a hole between two `/` never swallows a `/`.

`httpServe` blocks forever, so a program doing anything else puts it on a
thread: `async hive.net.httpServe(8080, handle)`. It runs `handle` once per
request, on a thread of its own.
