# Runtime and Testing Guide

## Status

Draft, awaiting review.

## Document role

This guide explains the Uvicorn process, runtime configuration, health check,
container build, package data, test pyramid, CI evidence, and release checks
proposed in [`../02-mvp-implementation.md`](../02-mvp-implementation.md). The
parent document remains authoritative. This status records review of this
design area; it does not approve the overall workstream.

Read this guide before implementing the executable web entry point, production
container, CI jobs, test suites, or release verification.

## One application, several execution environments

The same installed Checkmate package should run in local development, tests,
and the production container.

```text
Source checkout
    |
    +-- uv run checkmate-web       local application
    +-- uv run pytest              automated tests
    +-- uv build                   wheel and source distribution
    `-- Docker build               production OCI image
```

The environments differ in configuration and surrounding infrastructure, not
in business rules.

## Production process

The package exposes a `checkmate-web` console script. It constructs the FastAPI
application and starts Uvicorn without development reload.

```text
Container starts
      |
      v
checkmate-web
      |
      v
Read and validate Settings
      |
      v
Construct adapters and services
      |
      v
Start Uvicorn ASGI server
```

Development reload may be convenient during interactive work, but it should
not be baked into the production entry point because reload creates an extra
watcher process and behavior that production does not need.

## Runtime configuration

The process reads:

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `0.0.0.0` | Interface on which Uvicorn listens |
| `PORT` | `8000` | Container HTTP port |
| `LOG_LEVEL` | `info` | Safe operational log level |
| `OPENAI_API_KEY` | absent | Enables automatic receipt extraction |

Invalid configuration fails during startup with a direct, non-sensitive error.
Starting with an invalid port and failing immediately is better than starting a
process that cannot accept traffic correctly.

The hosting platform may provide a different `PORT`; reading it from the
environment keeps the container portable.

## One process per container

Each container runs one Uvicorn process. The hosting platform may run several
identical containers behind HTTPS ingress:

```text
                    +--> container A: one Uvicorn process
Public ingress -----+--> container B: one Uvicorn process
                    `--> container C: one Uvicorn process
```

Because the browser sends the complete draft and the server stores no session,
any replica can handle any request. Session affinity is unnecessary.

The design lets the deployment platform control replication rather than adding
Gunicorn or several worker processes inside one container for v0.1.

## Health endpoint

`GET /health` returns only:

```json
{"status": "ok", "version": "0.1.0"}
```

It proves that configuration and application construction succeeded and the
web process can respond. It deliberately does not call OpenAI.

```text
OpenAI outage + healthy web process
    |
    +-- /health remains healthy
    +-- manual calculation remains available
    `-- extraction reports unavailable
```

If health depended on the provider, a temporary third-party outage could cause
the hosting platform to restart an otherwise healthy application repeatedly.

## Multi-stage container mental model

A multi-stage Docker build separates construction tools from the runtime image.

```text
Builder stage
  - pinned Python base
  - pinned uv binary
  - pyproject.toml and uv.lock
  - production dependency sync
  - installed Checkmate package
            |
            | copy installed virtual environment only
            v
Runtime stage
  - pinned Python base
  - application virtual environment
  - non-root user
  - checkmate-web command
```

The final image does not need uv, compilers, tests, docs, Git metadata, or the
developer toolchain.

## Reproducible dependency installation

The production sync uses:

```bash
uv sync --locked --no-dev --no-editable --compile-bytecode
```

Meaning:

- `--locked` fails rather than changing a stale lockfile.
- `--no-dev` excludes lint, type-checking, and test dependencies.
- `--no-editable` installs the package as production code rather than linking
  imports back to a source checkout.
- `--compile-bytecode` prepares normal Python bytecode during the image build.

This is not native compilation into a standalone machine executable. Python
source still runs on the pinned Python interpreter in the container.

Pinning both the Python and uv images by immutable digest protects the build
from a mutable image tag silently changing its contents.

## Runtime image restrictions

The final image:

- Runs as a dedicated non-root user.
- Has an explicit working directory.
- Exposes port 8000 as documentation of its expected default.
- Uses exec-form `CMD` so Uvicorn receives shutdown signals directly.
- Requires no persistent writable application directory.
- Can use a read-only root filesystem with a small writable `/tmp` when the
  hosting platform supports it.

The image is initially verified for Linux/amd64. Supporting another architecture
requires an explicit build and smoke test rather than an assumption based on a
developer's Mac architecture.

## Package data matters

Python modules alone are not enough. The installed wheel must also contain:

- Jinja templates
- CSS
- JavaScript
- Any other required static application assets

An import-only package test can pass even when these files are missing. The
wheel and container smoke tests therefore request `/`, the linked assets, and
`/health` from the installed artifact.

## Test pyramid

Different tests answer different questions:

```text
                 Browser acceptance tests
              complete user workflow, few tests
             /--------------------------------\
            HTTP and application integration tests
           route contracts and orchestration, some tests
          /--------------------------------------------\
         Unit tests
        domain rules and adapters in isolation, many tests
```

Keeping most tests low in the pyramid makes failures faster and easier to
diagnose. Browser tests prove integration but should not be the first place a
rounding bug is discovered.

## Unit tests

Unit tests cover one focused behavior with no server or network:

- Money parsing and formatting
- Equal item division and tie breaking
- Largest-remainder allocation
- Validation and reconciliation invariants
- Image safety and normalization
- PDF semantic output

Synthetic builders can create precise edge cases without copying real receipts.

## Application-service tests

These tests inject `FakeReceiptParser` and a fake `PdfRenderer` to prove
coordination:

- Which dependency is called
- What application-owned values cross the boundary
- How failures are categorized
- Whether PDF rendering is blocked before finalization

They should not require the OpenAI or ReportLab implementation when those
details are irrelevant to the use case.

## HTTP integration tests

FastAPI's test client exercises the ASGI application without binding a public
network port. These tests cover:

- Route methods and schemas
- Multipart upload behavior
- Status and error mapping
- Body-size limits
- Security and cache headers
- PDF response headers
- Dependency overrides with fakes
- Privacy-safe logging

The test client is still an integration test because several application layers
participate in one request.

## Browser acceptance tests

Playwright runs headless Chromium against a started Checkmate application with
the fake parser. The main scenario follows the requirement from upload through
PDF download.

Separate checks cover:

- Desktop and narrow viewports
- Horizontal table scrolling
- Keyboard operation and visible focus
- Error-summary navigation
- Stale-response protection
- Content-verified PDF download

Screenshots and traces are retained only on failure and contain synthetic data.

## External extraction evaluation

The `external` suite is deliberately outside normal CI. It requires
`OPENAI_API_KEY` and tests the selected model and prompt against 12 generated
receipt images.

It is required when:

- The initial OpenAI adapter is introduced.
- The pinned model changes.
- The extraction prompt changes.
- The provider schema changes in a way that may affect output.

The result should be recorded without committing provider response bodies.

## CI pipeline

The existing quality checks remain required:

```text
Lock check
   |
Lint and format
   |
Static type checking
   |
Unit/integration/browser tests
   |
Python package build and wheel smoke test
   |
Production image build and container smoke test
```

Jobs may run in parallel when dependencies allow, but a release candidate must
have evidence from every required check.

The container smoke test should prove:

1. The image starts without downloading anything at runtime.
2. `/health` becomes ready.
3. `/` and its local assets load.
4. The process shuts down cleanly.

## Coverage and evidence

The 90% line-coverage threshold is a floor. It cannot prove that the correct
rounding policy was implemented or that a PDF is readable.

Evidence is layered:

| Behavior | Primary evidence |
|---|---|
| Money and allocation rules | Focused unit tests |
| Service orchestration | Fake-based application tests |
| HTTP contracts | Integration tests |
| Complete user workflow | Browser acceptance tests |
| Provider quality | Opt-in external evaluation |
| PDF appearance | Manual visual review |
| Overall professional UI | Desktop and narrow manual review |

`../../tests.md` should eventually map every acceptance criterion to its
automated and manual evidence.

## Hosting boundary

v0.1 produces and tests an OCI container but does not yet select a cloud host,
registry, domain, TLS provider, or continuous deployment target.

This is a deliberate boundary:

```text
Repository responsibility
  -> reproducible image
  -> image starts
  -> application and assets respond
  -> health check passes

Later operational responsibility
  -> publish image
  -> select host
  -> configure HTTPS, HSTS, rate limiting, and fleet concurrency
```

The container contract keeps later choices open without postponing production
readiness.

## Implications for implementation tasks

Runtime and verification tasks should be delivered alongside features:

1. Add the application entry point and validated settings with the web shell.
2. Add focused tests with each domain or adapter behavior.
3. Add HTTP integration tests as each route is introduced.
4. Add browser acceptance coverage as the manual workflow becomes complete.
5. Include templates and static assets in wheel verification.
6. Build the multi-stage production image once the application entry point and
   runtime dependencies exist.
7. Add container startup, route, asset, health, and shutdown smoke checks to CI.
8. Map the completed implementation to acceptance evidence before release.

## Review checklist

- Does local and production execution use the same installed application entry
  point?
- Does invalid configuration fail clearly during startup?
- Can `/health` pass without calling external providers?
- Is the lockfile enforced rather than regenerated during image build?
- Are development tools absent from the runtime image?
- Does the wheel contain templates and static assets?
- Can normal CI run with no network credentials or real receipts?
- Does each behavior have evidence at the smallest useful test boundary?
- Does the container start, serve, become healthy, and stop cleanly?
