# `hive.net` — names and addresses

| call | answers with |
| --- | --- |
| `resolve(name)` | `Result<Str[dyn], NetError>` |
| `localAddress()` | `Result<Str, NetError>` |

A `NetError` is `NotFound`, `Lookup` or `NoAddress`.

## `resolve`

**Every** address behind a name, **in resolver order** — not the first one, and
not one picked for you. It takes a **name, not an endpoint**, so no port goes in
it, and **an address literal resolves to itself**.

```hive
if hive.net.resolve("example.com") is Result.Ok(addresses) {
	for each address in addresses {
		echo address
	}
}
```

Handing back all of them is what lets a program try the next one when the first
refuses, and what lets one that cares about families choose.

## `localAddress`

The address **other machines reach this one on**: the source address the OS
would stamp on a packet leaving by the default route.

```hive
if hive.net.localAddress() is Result.Ok(here) {
	echo "listening on {here}:9000"
}
```

**Nothing is sent to find out**, and **loopback is deliberately not an answer** —
`127.0.0.1` is not an address anybody else can use, so a machine that has only
that answers `NetError.NoAddress` rather than something misleading.

This is what a [node](syslink-nodes.md) prints so another can dial it.
