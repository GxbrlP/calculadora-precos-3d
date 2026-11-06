# `hive.env`

```hive
if hive.env.get("DATABASE_URL") is Result.Ok(url) {
	echo url
}
```

`get(name)` → `Result<Str, hive.env.EnvironmentError>`, whose error carries
the `key` and a `message`. `getSecret(name)` is the same lookup answering a
[`Secret<Str>`](../types.md#secret): the program's copy is locked and unprintable, though
the environment and the `.env` file still hold it as text.

**It resolves in this order:**

1. the `.env` file beside the executable;
2. the one in the working directory — the entrypoint's folder, under `hive run`;
3. the `.env` in the parent folder of either;
4. the OS environment.

So a value put in a nearby `.env` wins over one exported in the shell.

The `.env` file is read **once**, on the first `get`. Blank lines and `#`
comments are ignored, an optional `export ` prefix is allowed, and a value may
be wrapped in quotes, which are stripped.

```
# a comment
export DATABASE_URL="postgres://localhost/hive"
PORT=8080
```

A container hands variables over with `docker run -e` and `get` reads those the
same way, which is why a `.env` holding anything private belongs in a
`.dockerignore`.
