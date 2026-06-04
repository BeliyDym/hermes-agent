# Code Review Style Guide

A generic, stack-agnostic guide for the multi-vendor AI PR audit. The
reusable Claude workflow carries the deep, language-aware review logic; this
file tunes the Gemini Code Assist lens toward correctness, security, and
maintainability over style nits.

## Review Priorities (in order)

1. **Security** — secrets, injection, authn/authz, data exposure.
2. **Correctness** — logic bugs, unhandled errors, race conditions, off-by-one.
3. **Data safety** — destructive operations, missing validation, migrations.
4. **Maintainability** — clarity, dead code introduced by the change, naming.

Style preferences (formatting, import order) are owned by the repo's linter /
formatter in CI, not by this review. Do not flag what a linter already catches.

## Critical Review Areas

### 1. Secrets must never reach a client bundle or a log

- **Flag** any hardcoded secret in source: API keys (`sk-...`), JWTs (`eyJ...`),
  bearer tokens, connection strings with embedded passwords, private keys.
- **Flag** a secret referenced under a client-exposed name (e.g. a
  `NEXT_PUBLIC_*` / `VITE_*` / `REACT_APP_*` variable, or any value imported
  into a browser-reachable module).
- **Flag** `console.log` / logger calls that interpolate a key, an auth header,
  or a full request body that may carry tokens. Secret values in logs are a
  leak.

### 2. Data-access boundary + authorization

- **Flag** a new database table / collection / migration that does not enforce
  access control (row-level security, scoped policies, or an equivalent
  server-side guard). An unprotected store holding user data is an
  exposure blocker, not a nit.
- **Flag** a privileged read/write (admin client, service-role, raw DB) reached
  from a context that isn't authenticated, or from browser-reachable code.
- **Flag** a route handler / endpoint / server action that performs a privileged
  operation without verifying the caller's session or permissions.

### 3. Input validation at every boundary

- **Flag** a handler that consumes a request body, query params, or a webhook
  payload and uses it without schema validation (Zod / Joi / Pydantic /
  equivalent) before the value flows into a DB write, a query, or an external
  call. Never trust external input.
- **Flag** untyped data (`any`, untyped JSON) flowing from an external response
  straight into a privileged operation.

### 4. Injection + unsafe interpolation

- **Flag** string-interpolated SQL / shell / command construction from
  user-controlled input. Require parameterized queries / argument arrays /
  escaping.
- **Flag** unsanitized user input rendered as HTML (XSS), or interpolated into a
  template, redirect target, or file path (path traversal).

### 5. Error handling + failure modes

- **Flag** a swallowed exception (`catch {}` with an empty body) — log with
  context and either re-throw or return a typed error.
- **Flag** a user-facing error that leaks internals (stack traces, table names,
  secret-bearing payloads).
- **Flag** a security-relevant operation that fails open (proceeds on error)
  where it should fail closed (deny on error).

### 6. Destructive + irreversible operations

- **Flag** a destructive operation (drop table, mass delete/update, force
  overwrite, irreversible migration) without a guard, a backup/rollback path, or
  a clear scope limit.

## Code Style Rules

- Prefer immutable updates over in-place mutation, especially for shared or
  server-side state. Return new objects rather than mutating arguments.
- Keep types honest: avoid `any`; model external data with a schema and infer
  the type where the language supports it.
- Keep comments about *why*, not *what*. Self-documenting code over redundant
  docstrings on internal helpers.
- NEVER use em-dashes in strings, comments, or UI copy. Use commas, colons, or
  parentheses.

## What NOT to Flag

- Anything the repo's linter / formatter already enforces (import order,
  whitespace, quote style) — that's the CI lint step's job.
- Lockfile content diffs (`package-lock.json`, `yarn.lock`, `Cargo.lock`,
  `poetry.lock`) — review the manifest change that drove them, not the
  generated content.
- File length alone — some modules are legitimately long.
- Generated / scaffolded boilerplate — review the intent, not the scaffold.
- Code that differs from older framework patterns purely because a dependency's
  major version changed — verify against the version in use, don't assume older
  behavior.
