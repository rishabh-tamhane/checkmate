# Milestone 5: Production Readiness

## Status

In progress by owner direction as of 2026-08-20. Milestone 4 is complete, and
production-readiness work that does not require live-provider evidence may
proceed while the paid M3-35 evaluation is deferred. M5-32 and release
completion remain blocked until that evaluation passes.

## Outcome

The complete v0.1 workflow passes deterministic, integration, browser, external,
and manual release evidence. A fresh checkout builds a minimal production OCI
image that starts without network initialization, serves the application and
assets, passes health checks, and shuts down cleanly.

## Requirement traceability

- Complete primary flow in requirements section 2
- Clean desktop and usable mobile presentation in section 8
- All included scope and acceptance criteria in sections 9 and 10

## Design sources

- [Authoritative MVP design](../../technical-design/02-mvp-implementation.md)
- [Security and privacy](../../technical-design/02-mvp-implementation/06-security-and-privacy.md)
- [Runtime and testing](../../technical-design/02-mvp-implementation/07-runtime-and-testing.md)
- All feature guides referenced by milestones 1–4

## Close remaining project foundation work

- [x] **M5-01:** Replace the duplicated package version literal with installed
  package metadata and preserve one authoritative `0.1.0` source.
- [x] **M5-02:** Confirm every runtime dependency is necessary, directly imported
  dependencies are declared, development-only tools are excluded from
  production dependencies, and `uv lock --check` passes.
- [x] **M5-03:** Confirm wheel and source-distribution contents include required
  Python modules, Jinja templates, CSS, and JavaScript and exclude secrets,
  receipts, test artifacts, and local environments.

Evidence on 2026-08-20: `tests/test_package.py` proves the exported version is
installed metadata; the direct-import audit declares Starlette at runtime and
`httpx2` and Playwright for development; `uv lock --check` passes. `uv build`,
archive listings, and isolated `tests/smoke_test.py` runs for both the wheel and
source distribution confirm the required package contents, startup, `/`,
linked assets, and `/health`, with no excluded project data in either archive.

## Complete automated browser evidence

- [x] **M5-04:** Install the Chromium version matching the locked
  `pytest-playwright` dependency in CI and fail clearly if browser installation
  is missing.
- [x] **M5-05:** Start the application with `FakeReceiptParser` for browser tests
  so normal CI requires no network, OpenAI key, or paid request.
- [x] **M5-06:** Implement one complete desktop acceptance journey: upload the
  synthetic receipt, correct an extraction mistake, add and remove records,
  assign shared items, observe exact totals, fix a blocking mismatch, and
  download a content-verified PDF.
- [x] **M5-07:** Implement a narrow-viewport journey covering stacked layout,
  touch-size controls, horizontal table scrolling, and access to every
  participant checkbox.
- [x] **M5-08:** Implement keyboard and accessibility checks for visible focus,
  labels, native controls, error-summary navigation, and field associations.
- [x] **M5-09:** Implement a controlled out-of-order response test proving a
  stale calculation cannot overwrite the latest revision.
- [x] **M5-10:** Retain Playwright traces and screenshots only on failure and
  verify all artifacts use generated receipt data and fictional names.

Evidence on 2026-08-20: CI installs Chromium from the locked Playwright
environment; module-scoped browser fixtures run the real app with either no
parser or `FakeReceiptParser`. `tests/test_browser_workflow.py` contains the
complete desktop journey, eight-participant narrow-viewport reachability,
native-label and visible-focus assertions, and controlled stale-response
coverage. Pytest config retains traces and screenshots only on failure under
the ignored `test-results/` directory; the suite uses only generated images,
synthetic amounts, and fictional names, and a passing run leaves no artifacts.

## Security and privacy release audit

- [x] **M5-11:** Verify no secret, real receipt, personal name, request body,
  provider body, prompt body, image, filename, or monetary text appears in the
  repository, normal logs, error responses, or browser artifacts.
- [x] **M5-12:** Verify all sensitive responses use `Cache-Control: no-store`,
  user text is safely rendered in HTML and PDF, and Jinja autoescaping remains
  enabled.
- [x] **M5-13:** Verify CSP, sniffing, referrer, framing, same-origin header,
  `Origin`, CORS, upload-size, JSON-size, and extraction semaphore controls at
  their real endpoints.
- [x] **M5-14:** Document that public deployment additionally requires HTTPS,
  HSTS, matching ingress body limits, distributed extraction rate limiting,
  fleet concurrency limits, exact trusted proxy addresses, and OpenAI usage
  budgets or alerts.
- [x] **M5-15:** Verify the upload disclosure accurately describes OpenAI data
  transfer, manual entry, review responsibility, and the absence of a zero-data-
  retention claim unless separately configured.

Evidence on 2026-08-20: tracked-file and diff scans found no credential-shaped
secret, receipt image, PDF, provider payload, or browser artifact. Participant
examples are fictional; the repository owner's name remains only as deliberate
package and license attribution. HTTP and browser tests prove allowlisted logs,
safe errors, `no-store`, DOM text rendering, PDF escaping, Jinja autoescaping,
security headers, same-origin and Origin enforcement, request-size limits, and
the four-call extraction semaphore. README records all public-ingress and cost
controls, and `tests/test_web.py` asserts every required upload disclosure and
the absence of a zero-retention claim.

## Reproducible production image

- [x] **M5-16:** Add `.dockerignore` excluding Git metadata, documentation,
  tests, local virtual environments, caches, build artifacts, editor files,
  secrets, and `.env` files from the build context.
- [x] **M5-17:** Add a multi-stage `Dockerfile` whose builder pins the official
  Python 3.14.6 slim base and uv 0.11.32 image by immutable digest.
- [x] **M5-18:** Copy lock and project metadata before source code to preserve
  dependency-layer caching.
- [x] **M5-19:** Install production dependencies with
  `uv sync --locked --no-dev --no-editable --compile-bytecode` and fail rather
  than update a stale lockfile.
- [x] **M5-20:** Copy only the installed virtual environment into a clean pinned
  Python runtime stage; exclude uv, compilers, tests, docs, Git metadata, and
  local environments.
- [x] **M5-21:** Create and run as a dedicated non-root user with an explicit
  working directory, expose port 8000, and use exec-form `CMD` for
  `checkmate-web`.
- [x] **M5-22:** Verify the image requires no persistent writable directory and
  runs with a read-only root filesystem plus a small writable `/tmp` tmpfs.
- [x] **M5-23:** Build and test the production image for Linux/amd64; do not
  claim another architecture until it has a separate successful build and
  smoke test.

Evidence on 2026-08-20: `Dockerfile` pins the official Python 3.14.6 slim and
uv 0.11.32 OCI indexes by digest, installs the locked non-development project
in a builder, and copies only `/app/.venv` into the clean runtime. The
allowlist `.dockerignore` sent a 3.21 KiB production build context after cache
warmup. A loaded Linux/amd64 image passed `tests/container_smoke_test.py`,
including absence of uv, C compilers, source, tests, docs, Git, and build
metadata; UID/GID 10001; read-only root; and writable 16 MiB `/tmp` tmpfs.

## Container and package smoke verification

- [x] **M5-24:** Start the image without network-dependent initialization and
  wait for `/health` to return the exact approved status and version.
- [x] **M5-25:** Request `/`, every linked CSS/JavaScript asset, manual
  calculation, and PDF generation from the running production image.
- [x] **M5-26:** Verify the no-key image exposes manual-entry mode and remains
  healthy without contacting OpenAI.
- [x] **M5-27:** Send the container its normal termination signal and verify the
  Uvicorn process exits cleanly within the test timeout.
- [x] **M5-28:** Install the built wheel into an isolated environment and repeat
  the `/`, asset, and `/health` checks so package and container evidence detect
  missing web files.

Evidence on 2026-08-20: the reusable container smoke script verified exact
health JSON, the application shell and both discovered local assets, cent-exact
manual calculation, PDF headers and bytes, disabled upload with healthy manual
entry, and graceful `docker stop`. Isolated wheel and source-distribution runs
of `tests/smoke_test.py` independently pass the installed-package route and
asset contract.

## CI and release evidence

- [x] **M5-29:** Extend CI to install pinned Chromium and run the browser suite
  after deterministic unit, application, and HTTP integration tests.
- [x] **M5-30:** Build and smoke-test the Linux/amd64 production image only after
  lock, lint, format, type, test, coverage, and Python package jobs pass.
- [x] **M5-31:** Keep normal CI independent of OpenAI credentials and mark the
  live provider evaluation `external` and opt-in.
- [ ] **M5-32:** Record a passing external extraction evaluation for the exact
  model snapshot, prompt version, provider schema, and 12 committed generated
  fixtures included in the release.

Evidence on 2026-08-20: the single ordered CI verification job installs
Chromium from the locked environment, runs the full credential-free pytest
suite and both isolated distribution smoke tests, then builds and executes the
Linux/amd64 container smoke contract. The external marker remains excluded
unless `--run-external` is supplied; CI has no OpenAI secret dependency.
- [x] **M5-33:** Complete `../../tests.md` with exact test paths and statuses for
  all
  eight acceptance criteria.
- [x] **M5-34:** Manually approve PDF visual legibility for representative
  one-page and multi-page output.
- [x] **M5-35:** Manually approve the clean/professional interface on one desktop
  and one narrow mobile viewport.
- [x] **M5-36:** Update README instructions so a new contributor can install,
  test, build, run, and container-smoke-test Checkmate from a clean checkout.
- [x] **M5-37:** Check the remaining items in `../01-project-setup.md` only after
  their referenced version, container, health, and contributor evidence exists.
- [x] **M5-38:** Run every command required by `AGENTS.md` from a clean checkout
  and record the final passing commit.

Evidence on 2026-08-20: direct raster review approved the representative
one-page and nine-page PDFs for legibility, wrapping, alignment, escaped user
text, totals, and complete final summaries. Full-page Playwright captures at
1440 by 1000 and 390 by 844 approved the initial and ready states for visual
hierarchy, typography, stacking, touch targets, assignment-table scrolling,
reconciliation, and PDF-export affordance.

Clean-checkout evidence on 2026-08-20: this release tree passed
`uv lock --check`, Ruff lint and format checks, mypy, the full pytest suite
(177 passed, one explicitly external test skipped, 98.91% coverage), and
`uv build` from a clean Git archive.

## Scope and hosting closure

- [x] **M5-39:** Verify the release has no authentication, database history,
  saved drafts, shareable links, payments, payment tracking, groups, recurring
  balances, native application, unequal splits, or multiple currencies.
- [x] **M5-40:** Confirm the repository ends with a tested OCI image and does not
  select or configure a cloud host, registry, domain, TLS provider, or automatic
  deployment target for v0.1.
- [x] **M5-41:** Record any future hosting or product capability as backlog work
  rather than adding it to the approved MVP.

Evidence on 2026-08-20: requirements, dependencies, routes, browser state, and
delivery configuration were audited against the v0.1 exclusions. The
repository builds and tests a local OCI image but contains no host, registry,
domain, TLS, deployment, persistence, account, payment, or expanded splitting
implementation. No newly discovered future capability was added to active
scope.

## Completion criteria

- [ ] Every acceptance row in `../../tests.md` has passing automated evidence and
  any required manual evidence.
- [ ] The external extraction evaluation meets its approved thresholds for the
  exact released model and prompt.
- [x] The production image builds reproducibly, runs as non-root, passes all
  smoke checks, and shuts down cleanly.
- [ ] The full CI and `AGENTS.md` command set passes from a clean checkout.
- [x] All remaining project-setup completion gates are satisfied.
- [x] No excluded capability or undeclared hosting decision entered v0.1.
