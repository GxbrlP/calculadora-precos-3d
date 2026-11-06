# `hive.crypto` — JWT

| call | answers with |
| --- | --- |
| `jwtCodec(secret: Secret<Str>)` | `hive.codec.Codec<JwtError>` — HS256 under this secret |
| `jwtDecode(token)` | `Result<Str, CryptoError>` — **without verifying** |
| `jwtHeader(token)` | `Result<hive.crypto.Header, CryptoError>` |

A token is **a format like any other**, so there is nothing here to sign or
verify with: `jwtCodec` is a codec beside [`hive.json.codec`](json.md), and
[`encode`](../builtins.md) and `T.decode` are what a program
writes and reads one with. The claims are **one of your own types**, so a
token's payload is a type declaration rather than a bag of strings.

```hive
type Claims {
	sub: Str
	exp: Int
}

token := encode(Claims("ada", hive.time.now() / 1000 + 3600), hive.crypto.jwtCodec(secret))

if Claims.decode(token, hive.crypto.jwtCodec(secret)) is Result.Ok(claims) {
	echo claims.sub
}
```

## What the codec checks

Decoding checks the signature **and the `exp`/`nbf` claims** before it reads
anything. **Only HS256 is accepted**, so `alg: none` and algorithm confusion
are rejected outright rather than negotiated.

A token that does not check out is a `hive.crypto.JwtError`, like claims of the
wrong shape, and its `found` opens with the reason — `"Expired"`,
`"BadSignature"`, `"AlgorithmMismatch"` or `"Malformed"`. A forged token and
claims of the wrong shape are then one failure to handle rather than two,
which is what a caller was going to do with them anyway.

`jwtDecode` decodes **without verifying anything at all**, and is for
inspection only — logging what a token claims, reading a `sub` before deciding
which secret to check it with. **Never authorise on what it answers.**

`jwtHeader` reads `alg`, `typ` and `kid` off the token, which is what a
program rotating keys needs before it can pick the secret.

`exp` and `nbf` are Unix seconds, as RFC 7519 has them, and
[`hive.time.now()`](time.md) answers milliseconds — so `hive.time.now() / 1000`.
