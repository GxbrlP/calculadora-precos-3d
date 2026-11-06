# `hive.crypto` — encryption

| call | answers with |
| --- | --- |
| `encrypt(plaintext: Secret<Str>, password: Secret<Str>)` | `Str` — base64; **cannot fail** |
| `decrypt(ciphertext, password: Secret<Str>)` | `Result<Secret<Str>, CryptoError>` |
| `decryptBypass(ciphertext, password: Secret<Str>)` | `Result<Secret<Str>, CryptoError>` — the same, in ordinary memory |

The plaintext and the password are [`Secret<Str>`s](../types.md#secret), and so is what
`decrypt` opens: it goes from locked memory into AES-GCM and back without
ever being a `Str`. The ciphertext is a `Str`, safe to print and store.

```hive
if hive.term.readSecret() is Result.Ok(password) {
	sealed := hive.crypto.encrypt(bypass("attack at dawn"), password)

	if hive.crypto.decrypt(sealed, password) is Result.Ok(opened) {
		echo reveal(opened)
	} else if hive.crypto.decrypt(sealed, password) is Result.Error(crypto.CryptoError.BadSignature(_)) {
		echo "wrong password, or the message was changed"
	}
}
```

`decrypt` fails as `LimitExceeded` or `Unsupported` where there is no locked
memory to open the plaintext into. `decryptBypass` opens it into ordinary memory
instead, as `bypass` is to `hide`: free to be swapped out, so it fails only as
`Malformed` or `BadSignature`.

## What it does, exactly

`encrypt` seals under a **password** with **AES-256-GCM**, base64-encoded. The
key is derived with **600,000 rounds of PBKDF2-HMAC-SHA256** over a random salt,
and **the salt and nonce are drawn afresh every call** — so the same text under
the same password never encrypts alike. That is a property to expect rather than
a bug to chase: two ciphertexts of one message are supposed to differ.

GCM's tag travels with the ciphertext, so **an edited message is rejected rather
than opened into something else**. That is reported as `"BadSignature"`, which
is also what a **wrong password** gives — the two are indistinguishable by
design, and a program should not try to tell a user which it was.

The rounds are what make this safe to use with something a human typed, and they
are also what make it slow on purpose: a call is not free, so derive once and
hold what you got rather than encrypting field by field in a loop.

For **integrity without secrecy** — proving a message was not altered by someone
who has the key — reach for `hmacSha256` on [crypto](crypto.md) instead. For a
**claim somebody else has to read**, [crypto-jwt](crypto-jwt.md).
