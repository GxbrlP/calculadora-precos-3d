# `hive.syslink` — what a service is

Addressable **services**, in this process or on another machine, reached by the
same statement either way. A service is long-lived, owns private state only it
can touch, and has an identity you can pass around: an `Address<M>`, which
says the type `M` of the messages it takes.

A service is started, named and stopped by three **builtins** — `spawn`,
`at` and `kill` — and what is left in the module is the node. Every call
is [syslink-calls](syslink-calls.md); across machines is
[syslink-nodes](syslink-nodes.md).

## The handler is one turn

```hive
proc handler(state: mut State, message: Message): Message
```

A handler **writes its state in place and returns the answer**. The state is a
`mut` parameter only the service's own mailbox ever holds, and one message is
handled at a time, so a handler's body is the only thing that ever touches that
state and needs no lock to do it. A handler is an ordinary `proc`, so a test can
call it directly with a `mut` variable of its own.

```hive
type Op {
	Add { word: Str }
	Count
	Total { n: Int }
}

proc counter(seen: mut Str[dyn], message: Op): Op {
	if message is Op.Add(word) {
		append(seen, word)
	}
	return Op.Total(len(seen))
}

proc main(): void {
	Str[dyn] empty = []
	if spawn(counter, empty) is Result.Ok(cache) {
		async cache(Op.Add("hello"))
		if cache(Op.Count()) is Result.Ok(reply) && reply is Op.Total(n) {
			echo n
		}
	}
}
```

The compiler holds a handler to that shape where the service is started: its
first parameter is `mut`, the state it starts with fits that parameter,
and it returns its own mailbox type. `spawn` answers with a `Result`, since
a service started under a name may find the name taken, holding an
`Address<M>` read off the handler.

## The mailbox type is the whole protocol

**The reply type *is* the mailbox type**, so nothing is annotated: a service
answers with one of its own messages. That is what makes one type declaration
the whole contract between a caller and a service, on this machine or another —
and the address carries it, so **a message of another type is a compile error**
where it is sent. What the compiler cannot see is whether the service under a
name really takes an `M`, so a message that does not decode where it arrives
fails as `Decode`.

**Every request is answered** with what its turn returned, and a caller on this
node is handed its own copy, since the next turn may write the state the answer
was read from. A fire-and-forget send discards it.

## A crash is local to its service

A `panic` inside a service body **kills only that service**: its monitors are
told, its callers get `Down`, and the node keeps running. **This is the one
place `panic` does not stop the program.** The node says so on standard error,
as `hive: service Counter crashed: <message>`.

## A service that knows its own address

A handler may take a third parameter, an `Address<M>` of its own mailbox type,
and is then handed its own address every turn — to give to work it starts, so that the result comes
back as a message. `spawn` takes either shape:

```hive
proc fetcher(pending: mut Int, note: Note, me: Address<Note>): Note {
	if note is Note.Fetch(url) {
		pending += 1
		async download(me, url)
	} else if note is Note.Fetched(_) {
		pending -= 1
	}
	return note
}
```

## When to reach for one

A program that needs **long-lived shared state** — a cache, a registry, a game
world, a connection nobody else may touch. The language has no channel, no lock
and no thread handle ([concurrency](../concurrency.md)); a service is
what fills that gap, and a window is one too ([ui](ui.md)).
