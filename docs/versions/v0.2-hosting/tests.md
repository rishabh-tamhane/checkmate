# v0.2 Initial Hosting Verification Plan

Statuses are `Planned`, `Passing`, `Failing`, or `Blocked`. Evidence must be
synthetic and must not contain credentials, Access cookies, tunnel tokens,
personal receipt content, or email addresses.

| Requirement | Evidence | Initial status |
|---|---|---|
| Public-origin validation | Settings unit tests and FastAPI HTTP regression tests | Passing: full suite on 2026-08-20 |
| Production image contract | Existing `tests/container_smoke_test.py` using `checkmate:hosting-m1` | Passing locally on 2026-08-20; repeat for release tag |
| Compose and Nginx configuration | `docker compose config` plus `tests/hosting_stack_smoke_test.py` | Passing locally on 2026-08-20 |
| Ingress body limits | Synthetic JSON request above the 256 KiB boundary; application image tests retain exact upload limits | Passing locally on 2026-08-20 |
| Local health and restart | `/health`, deliberate app restart, and Compose health state | Passing locally on 2026-08-20 |
| Tunnel isolation | Loopback bind assertion passes; router and tunnel confirmation remain | Partially passing |
| TLS and HSTS | External header probe against canonical hostname | Planned |
| Access allowlist | Non-allowlisted challenge/denial and allowlisted owner login | Planned |
| Extraction rate limit | Synthetic authenticated requests reaching 429 without provider calls where practical | Planned |
| Existing-site preservation | Before/after probes for `/`, one unrelated `www` path, and the two redirect paths | Planned |
| Complete remote workflow | iPhone cellular manual entry, calculation, and PDF download | Planned |
| Optional extraction | One owner-authorized synthetic receipt upload with OpenAI budget monitoring | Planned |
| Recovery | Checklist drill covering Docker, app, ingress, tunnel, and Cloudflare route | Planned |

## Required repository checks

Run before release:

```bash
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
```

Run the production image smoke contract and all focused hosting checks added by
the implementation tasks. A paid extraction request is optional for the travel
launch only if the owner explicitly defers it; the release evidence must record
that automatic extraction quality still inherits the deferred v0.1 evaluation.
