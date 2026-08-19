# Milestone 1: Application Foundation

## Status

Complete.

Completion date: 2026-08-18.

## Outcome

The installed Checkmate package starts one stateless FastAPI application through
`checkmate-web`, serves the initial HTML and local assets, and reports process
health. The package boundaries, configuration, safe HTTP baseline, and focused
integration-test foundation are established before business features are added.

## Design sources

- [System architecture](../../technical-design/02-mvp-implementation/01-system-architecture.md)
- [Security and privacy](../../technical-design/02-mvp-implementation/06-security-and-privacy.md)
- [Runtime and testing](../../technical-design/02-mvp-implementation/07-runtime-and-testing.md)
- [Authoritative MVP design](../../technical-design/02-mvp-implementation.md)

## Dependencies and exclusions

- Requires the existing project setup, locked dependency workflow, and package
  build configuration.
- Blocks every later milestone.
- Does not implement receipt calculation, extraction, or PDF generation.
- Does not add a database, session store, frontend build tool, or cloud host.

## Runtime dependencies

- [x] **M1-01:** Add `fastapi`, `pydantic`, `jinja2`, and `uvicorn` with
  `uv add`; commit the resulting `pyproject.toml` and `uv.lock` changes.
- [x] **M1-02:** Add `httpx` as a development dependency with `uv add --dev`
  for ASGI HTTP integration tests.
- [x] **M1-03:** Confirm no dependency required only by extraction, PDF export,
  browser automation, or a hypothetical future feature is added here.

## Package boundaries

- [x] **M1-04:** Create `domain`, `application`, `adapters`, and `web` packages
  under `src/checkmate/`, retaining `config.py` at the package root.
- [x] **M1-05:** Add the approved module skeleton for domain models, money,
  splitting, validation, application models, ports, services, web schemas, and
  the application composition root.
- [x] **M1-06:** Keep the domain package limited to standard-library imports and
  prevent FastAPI, Pydantic, OpenAI, ReportLab, and browser concerns from
  entering it.
- [x] **M1-07:** Define narrow placeholder boundaries for external adapters
  without finalizing receipt-parser or PDF-renderer data contracts ahead of
  their milestones.
- [x] **M1-08:** Centralize construction of configuration, services, and concrete
  adapters in `web.app`; do not create hidden module-level service locators.

## Configuration and process entry point

- [x] **M1-09:** Implement typed startup configuration for `HOST`, `PORT`,
  `LOG_LEVEL`, and optional `OPENAI_API_KEY` without logging secret values.
- [x] **M1-10:** Apply defaults `0.0.0.0`, `8000`, and `info`, and reject an
  invalid port or unsupported log level with a safe startup error.
- [x] **M1-11:** Add the `checkmate-web` console script to `pyproject.toml` and
  start one Uvicorn process without development reload.
- [x] **M1-12:** Provide an application factory or equivalent composition
  function that tests can call with controlled dependencies.
- [x] **M1-13:** Start successfully without `OPENAI_API_KEY`; automatic
  extraction remains unavailable until milestone 3 while the web process stays
  healthy.
- [x] **M1-14:** Keep proxy-header trust disabled by default; require a later
  hosting decision to supply exact trusted proxy addresses before enabling it.

## Initial HTTP application

- [x] **M1-15:** Implement `GET /health` returning exactly
  `{"status": "ok", "version": "0.1.0"}` without calling an external service.
- [x] **M1-16:** Implement `GET /` with a Jinja-rendered semantic HTML shell and
  links to local versioned CSS and JavaScript assets.
- [x] **M1-17:** Mount the static asset route through the same FastAPI
  application; do not use a CDN or frontend package manager.
- [x] **M1-18:** Include templates and static assets as wheel package data so an
  installed distribution does not depend on the source checkout.
- [x] **M1-19:** Add a single safe error envelope containing a stable code,
  user-facing message, and generated request ID for unexpected HTTP failures.
- [x] **M1-20:** Add request metadata logging for request ID, route, status, and
  duration; exclude bodies, query values, secrets, and user data.
- [x] **M1-21:** Add baseline response headers for same-origin content policy,
  content-type sniffing protection, referrer suppression, and framing denial.

## Verification

- [x] **M1-22:** Unit-test configuration defaults, valid overrides, invalid
  startup values, and absence of secret values in errors and logs.
- [x] **M1-23:** Integration-test `GET /health`, including its exact schema,
  version, content type, and independence from external services.
- [x] **M1-24:** Integration-test `GET /` and every linked local asset from the
  application factory.
- [x] **M1-25:** Build the wheel, install it in an isolated environment, run the
  installed `checkmate-web` entry point, and verify `/`, its assets, and
  `/health` without using files from the checkout.
- [x] **M1-26:** Verify imports follow `web -> application -> domain` and that
  vendor objects do not cross adapter boundaries.
- [x] **M1-27:** Document the local start command, configuration variables, and
  manual-entry behavior in the root README without adding deployment-provider
  instructions.
- [x] **M1-28:** Run all required repository checks from `AGENTS.md` and record
  any deliberately deferred container check against milestone 5.

## Completion criteria

- [x] `uv run checkmate-web` starts the installed application.
- [x] `/`, every required local asset, and `/health` respond successfully.
- [x] The application starts without an OpenAI credential.
- [x] Focused configuration, route, logging, header, and package-data tests pass.
- [x] No business calculation, external provider, PDF implementation,
  persistence, or unapproved dependency has been introduced.

## Verification evidence

- Configuration behavior: `tests/test_config.py`
- Package direction and vendor-boundary checks: `tests/test_architecture.py`
- Route, asset, security-header, logging, and entry-point behavior:
  `tests/test_web.py`
- Isolated wheel and source-distribution startup, route, asset, health, and
  shutdown checks: `tests/smoke_test.py`
- On 2026-08-18, `uv lock --check`, Ruff lint and format, mypy, pytest, and
  `uv build` all passed; pytest ran 20 tests with 100% line coverage.
- Production-container construction and container smoke testing remain
  deliberately deferred to
  [milestone 5](05-production-readiness.md), tasks M5-16 through M5-28.
