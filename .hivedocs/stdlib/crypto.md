# `hive.crypto` — hashing, encoding, random

Pure, so all of it works in a `func` too. Fallible operations return
`Result<_, hive.crypto.CryptoError>`: `Malformed`, `BadSignature`, or
`LimitExceeded` or `Unsupported` where a `Secret` could not be locked, each with a
`message`.

Encryption is [crypto-encrypt](crypto-encrypt.md); tokens are
[crypto-jwt](crypto-jwt.md).

| call | answers with |
| --- | --- |
| `sha256(input)` | `Str` — lowercase hex |
| `sha512(input)` | `Str` — lowercase hex |
| `hmacSha256(input, key: Secret<Str>)` | `Str` — lowercase hex |
| `base64Encode(input)` | `Str` |
| `base64Decode(input)` | `Result<Str, CryptoError>` |
| `randomHex(bytes)` | `Str` — `bytes` random bytes, as hex |
| `randomSecret(bytes)` | `Result<Secret<Str>, SecretError>` — the same, never a `Str` |

```hive
echo hive.crypto.sha256("the message")
echo hive.crypto.hmacSha256(payload, bypass("a literal key"))
token := hive.crypto.randomHex(16)          // 32 hex characters

if hive.crypto.base64Decode(field) is Result.Ok(raw) {
	echo len(raw)
}
```

A key is a `Secret<Str>`; everything else is a `Str`, and a `Str` holds bytes rather
than validated text — so hashing a file read with
[`hive.file.read`](file.md) hashes the file, not a rendering of it.

**Only `base64Decode` can fail here.** A hash of anything is a hash, and
`randomHex` draws from the platform's own source.
