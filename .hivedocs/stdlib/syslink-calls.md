# `hive.syslink` — the calls

Three are **builtins**, reached with no module:

| call | answers with |
| --- | --- |
| `spawn(handler, state)` | `Result<Address<M>, SyslinkError>` — starts a service |
| `spawn(handler, state, name)` | the same, registered under `name` |
| `at(name)` | `Address<M>` — that service on **this** node |
| `at(endpoint, name)` | `Address<M>` — the same service on **another** |
| `kill(address)` | `void` — stops it |

The rest are the module's own, `hive.syslink.<call>`:

| call | answers with |
| --- | --- |
| `monitor(watcher, target, notice)` | `void` |
| `listen(endpoint)` | `Result<Str, SyslinkError>` |
| `node()` | `Str` |
| `peers()` | `Str[dyn]` |
| `setKey(key: Secret<Str>)` | `void` |

`Address<M>` is a builtin type, and **opaque**: an address is produced by `spawn`
or `at`, and `Address` without its `M` is a compile error. A
`hive.syslink.SyslinkError` is a union of what went wrong, each variant carrying
a `message`:

| variant | means |
| --- | --- |
| `Taken` | `spawn` was given a name another service holds |
| `Down` | the service died before answering, or was already gone — at once |
| `NoProc` | nothing is registered under that name on the node asked |
| `Timeout` | no answer within the time given, or the default |
| `Unreachable` | the node could not be reached |
| `Decode` | the message did not decode as the type the service takes |
| `NoPeer` | the address names no node to send to |
| `NoListener` | `listen` could not listen where it was told, or this node has not listened and was asked to reach another |
| `NoKey` | there is no cluster key to authenticate with |

## An address is called

There is exactly **one** way to reach a service, and — as with a func — the call
site decides what it means:

```hive
async inbox(Note.Say("hi"))          // send it, wait for nothing; cannot fail
answer := cache(Op.Count())          // send and wait: Result<Op, SyslinkError>
answer := cache(Op.Count()) with timeout 250
later  := async cache(Op.Count())    // wait where `later` is read
both   := await [a(m), b(m)]         // one barrier, one deadline
```

A fire-and-forget send **cannot fail** and has nothing to report. A request to an
`Address<M>` carries an `M` and answers with `Result<M, SyslinkError>`; a message
of any other type is a compile error.

`with timeout` **folds into that same error** rather than wrapping a second
`Result` around the first, so the result is still `Result<M, SyslinkError>`,
failing as `SyslinkError.Timeout`.

## Names and addresses

A service is named as it is **spawned**, by an **atom**, and a name is one
service's at a time on a node: a second `spawn` under a name still held fails as
`Taken`. One with no name has nothing to be refused, and is always `Ok`.

`at` **performs no I/O and cannot fail** — it is address *construction*, not a
lookup. Nothing is dialled until something is sent. A name says nothing about
what the service takes, so **`M` comes from where the address lands**, as
`hive.map.new()`'s does: a declaration, or — bound with `:=` — the first later
send, `x := at(#Cache)` then `x(Op.Get("k"))`. Once settled it never changes.

```hive
if spawn(counter, empty, #Cache) is Result.Error(syslink.SyslinkError.Taken(_)) {
	echo "somebody else is #Cache"
}

Address<Op> here  = at(#Cache)                    // this node
Address<Op> there = at("10.0.0.4:9000", #Cache)   // another
```

**A named address is the only kind that survives its service being restarted**,
which is the reason to name one at all: the address `spawn` answers with for a
service with no name is that instance and nothing else.

## Watching and killing

`monitor(watcher, target, notice)` posts `notice` to `watcher` — a service on
this node, such as `at(#Supervisor)` or the address a handler is handed — when
`target` dies. The notice is one of the watcher's messages, and the target may
take anything. That is how a supervisor is written, and it is why a crash
being local is useful rather than merely quiet.

`kill(address)` ends a service, on this node or another. Its name is free
again before its monitors hear of it, so a supervisor can spawn the next one
under it straight away.
