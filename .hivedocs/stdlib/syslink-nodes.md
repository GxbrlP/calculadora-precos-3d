# `hive.syslink` — across machines

The same statement reaches a service in this process and one on another
machine. What changes is only how its address was built:
`at(#Cache)` against `at("10.0.0.4:9000", #Cache)`.

| call | answers with |
| --- | --- |
| `listen(endpoint)` | `Result<Str, SyslinkError>` |
| `node()` | `Str` — the endpoint this node answers on |
| `peers()` | `Str[dyn]` — the endpoints it is connected to |
| `setKey(key: Secret<Str>)` | `void` — this program's cluster key, from the next connection on |

```hive
if hive.syslink.listen("0.0.0.0:9000") is Result.Error(why) {
	echo "cannot listen: {why.message}"
	hive.term.exit(1)
}
echo "this node is {hive.syslink.node()}"
```

**`listen` answers with the endpoint a peer should dial.** A port of `0` asks the
kernel to choose, and what comes back — and what `node()` says from then on —
carries the port it chose. The host is left as written, and the port is bound on
every interface — except a loopback host, which is bound as written.

**A node has no name.** It is identified by the endpoint it can be dialled at,
so a peer list is ordinary runtime data rather than a cluster configuration.
[`hive.net.localAddress()`](net-names.md) is what a node prints so another can
reach it.

## On the wire

* **One persistent, multiplexed connection per node *pair***, carrying
  length-prefixed frames, **dialled lazily** — building an address opens nothing.
* Messages cross as **JSON**, using the same derived codecs
  [`hive.json`](json.md) builds — so a message type's `JSON as`
  annotations decide what goes on the wire here too. A mailbox type that JSON
  cannot carry cannot travel: **a map does not**, and `toTable` is the
  answer.
* **Every frame carries a 32-bit structural digest of the message type**, so a
  peer built from a different declaration **fails loudly instead of decoding
  another type's bytes**. Two nodes must be built from the same mailbox
  declaration. **A field goes into that digest under its JSON key**, since that
  is what decides the bytes; a `Default` stays out, changing what a decoder
  accepts rather than what an encoder writes.
* **Every connection is TLS 1.3, mutually authenticated, with no plaintext
  path.** There is nothing to turn on and nothing to turn off.

## The cluster key

What a connection proves both ends hold; two nodes with different keys turn
each other away. It is the last `setKey` the program made, else
`HIVE_SYSLINK_KEY`, else `~/.hive/syslink.key`, created on first use.

```hive
if hive.env.getSecret("CLUSTER_KEY") is Result.Ok(key) {
	hive.syslink.setKey(key)
}
```

* **`setKey` is the program's own**: held in memory, never written to
  `syslink.key` and never put in the environment.
* **It applies from the next connection on**, made or accepted; one already open
  stays open.
* `setKey(bypass(""))` panics: an empty key proves nothing.

## Delivery is best-effort

**Messages queued when a node is declared down are dropped.** A request gets an
error and a fire-and-forget send gets nothing, so anything that must arrive is
a request whose answer the caller checks — and `monitor` is how a service hears
that something it depended on has gone.

`with timeout` is what bounds a call to a machine that may not answer, and it
folds into `SyslinkError.Timeout`:

```hive
Address<Op> far = at(endpoint, #Cache)
if far(Op.Count()) with timeout 250 is Result.Error(syslink.SyslinkError.Timeout(_)) {
	echo "no answer in time"
}
```
