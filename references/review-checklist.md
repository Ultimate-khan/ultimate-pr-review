# Review Checklist

Apply these rubrics during the semantic pass (step 4 of the workflow). Only
report issues you can point to in the diff or justify from surrounding code.
Do not invent problems to seem thorough.

## Severity levels

| Level | Meaning | Examples |
|---|---|---|
| `blocker` | Must fix before merge | Security hole, data loss, broken public API, crash on hot path |
| `major` | Should fix before merge | Logic bug, missing error handling, race condition, perf regression |
| `minor` | Fix soon or ticket it | Unclear naming, missing test for new branch, duplication |
| `nit` | Optional polish | Style, wording, formatting (respect team guide if present) |
| `question` | Need author clarification | Ambiguous intent, unexplained tradeoff |

## Security

- Injection: SQL built by string concatenation, shell commands with user
  input, unsanitized HTML, template injection.
- AuthZ/AuthN: new endpoints or handlers without an authorization check;
  permission checks performed client-side only.
- Data exposure: PII/tokens in logs, error messages leaking internals,
  overly broad CORS or wildcard permissions.
- Crypto: weak algorithms (MD5, SHA1, DES), `Math.random`/`random` for
  security tokens, hardcoded salts/IVs.
- Deserialization of untrusted input; SSRF via user-controlled URLs.

## Correctness

- Off-by-one and boundary conditions; empty/null/undefined inputs.
- Async: unhandled promise rejections, missing `await`, races on shared
  state, fire-and-forget calls whose errors vanish.
- Error handling: exceptions swallowed, error paths that return success,
  retries without backoff/idempotency.
- State: mutations of shared/module-level state; cleanup on early returns.
- API compatibility: renamed/removed fields, changed defaults, response
  shape changes without versioning.

## Performance (flag only when real, not theoretical)

- N+1 queries; DB/network calls inside loops over unbounded collections.
- Loading entire files/result sets into memory when streaming exists.
- Unbounded caches, queues, or retries.
- New dependencies: justify heavy ones; prefer stdlib when trivial.

## Tests

- New behavior without tests (cross-check prescan's `no-tests` signal).
- Tests that assert nothing or only assert no-exception.
- Deleted or skipped tests (`skip`, `xit`, `#[ignore]`) — demand a reason.

## Style-guide loading

If the repo contains `REVIEW_GUIDE.md`, `.review-guide.md`, or
`docs/review-guide.md`, read it first and treat its rules as authoritative
over this checklist for `minor`/`nit` findings. Never report a nit that
contradicts the team's own guide.
