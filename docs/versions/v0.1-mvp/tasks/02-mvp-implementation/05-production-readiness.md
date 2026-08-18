# Milestone 5: Production Readiness

## Status

Blocked by milestones 3 and 4.

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

- [ ] **M5-01:** Replace the duplicated package version literal with installed
  package metadata and preserve one authoritative `0.1.0` source.
- [ ] **M5-02:** Confirm every runtime dependency is necessary, directly imported
  dependencies are declared, development-only tools are excluded from
  production dependencies, and `uv lock --check` passes.
- [ ] **M5-03:** Confirm wheel and source-distribution contents include required
  Python modules, Jinja templates, CSS, and JavaScript and exclude secrets,
  receipts, test artifacts, and local environments.

## Complete automated browser evidence

- [ ] **M5-04:** Install the Chromium version matching the locked
  `pytest-playwright` dependency in CI and fail clearly if browser installation
  is missing.
- [ ] **M5-05:** Start the application with `FakeReceiptParser` for browser tests
  so normal CI requires no network, OpenAI key, or paid request.
- [ ] **M5-06:** Implement one complete desktop acceptance journey: upload the
  synthetic receipt, correct an extraction mistake, add and remove records,
  assign shared items, observe exact totals, fix a blocking mismatch, and
  download a content-verified PDF.
- [ ] **M5-07:** Implement a narrow-viewport journey covering stacked layout,
  touch-size controls, horizontal table scrolling, and access to every
  participant checkbox.
- [ ] **M5-08:** Implement keyboard and accessibility checks for visible focus,
  labels, native controls, error-summary navigation, and field associations.
- [ ] **M5-09:** Implement a controlled out-of-order response test proving a
  stale calculation cannot overwrite the latest revision.
- [ ] **M5-10:** Retain Playwright traces and screenshots only on failure and
  verify all artifacts use generated receipt data and fictional names.

## Security and privacy release audit

- [ ] **M5-11:** Verify no secret, real receipt, personal name, request body,
  provider body, prompt body, image, filename, or monetary text appears in the
  repository, normal logs, error responses, or browser artifacts.
- [ ] **M5-12:** Verify all sensitive responses use `Cache-Control: no-store`,
  user text is safely rendered in HTML and PDF, and Jinja autoescaping remains
  enabled.
- [ ] **M5-13:** Verify CSP, sniffing, referrer, framing, same-origin header,
  `Origin`, CORS, upload-size, JSON-size, and extraction semaphore controls at
  their real endpoints.
- [ ] **M5-14:** Document that public deployment additionally requires HTTPS,
  HSTS, matching ingress body limits, distributed extraction rate limiting,
  fleet concurrency limits, exact trusted proxy addresses, and OpenAI usage
  budgets or alerts.
- [ ] **M5-15:** Verify the upload disclosure accurately describes OpenAI data
  transfer, manual entry, review responsibility, and the absence of a zero-data-
  retention claim unless separately configured.

## Reproducible production image

- [ ] **M5-16:** Add `.dockerignore` excluding Git metadata, documentation,
  tests, local virtual environments, caches, build artifacts, editor files,
  secrets, and `.env` files from the build context.
- [ ] **M5-17:** Add a multi-stage `Dockerfile` whose builder pins the official
  Python 3.14.6 slim base and uv 0.11.32 image by immutable digest.
- [ ] **M5-18:** Copy lock and project metadata before source code to preserve
  dependency-layer caching.
- [ ] **M5-19:** Install production dependencies with
  `uv sync --locked --no-dev --no-editable --compile-bytecode` and fail rather
  than update a stale lockfile.
- [ ] **M5-20:** Copy only the installed virtual environment into a clean pinned
  Python runtime stage; exclude uv, compilers, tests, docs, Git metadata, and
  local environments.
- [ ] **M5-21:** Create and run as a dedicated non-root user with an explicit
  working directory, expose port 8000, and use exec-form `CMD` for
  `checkmate-web`.
- [ ] **M5-22:** Verify the image requires no persistent writable directory and
  runs with a read-only root filesystem plus a small writable `/tmp` tmpfs.
- [ ] **M5-23:** Build and test the production image for Linux/amd64; do not
  claim another architecture until it has a separate successful build and
  smoke test.

## Container and package smoke verification

- [ ] **M5-24:** Start the image without network-dependent initialization and
  wait for `/health` to return the exact approved status and version.
- [ ] **M5-25:** Request `/`, every linked CSS/JavaScript asset, manual
  calculation, and PDF generation from the running production image.
- [ ] **M5-26:** Verify the no-key image exposes manual-entry mode and remains
  healthy without contacting OpenAI.
- [ ] **M5-27:** Send the container its normal termination signal and verify the
  Uvicorn process exits cleanly within the test timeout.
- [ ] **M5-28:** Install the built wheel into an isolated environment and repeat
  the `/`, asset, and `/health` checks so package and container evidence detect
  missing web files.

## CI and release evidence

- [ ] **M5-29:** Extend CI to install pinned Chromium and run the browser suite
  after deterministic unit, application, and HTTP integration tests.
- [ ] **M5-30:** Build and smoke-test the Linux/amd64 production image only after
  lock, lint, format, type, test, coverage, and Python package jobs pass.
- [ ] **M5-31:** Keep normal CI independent of OpenAI credentials and mark the
  live provider evaluation `external` and opt-in.
- [ ] **M5-32:** Record a passing external extraction evaluation for the exact
  model snapshot, prompt version, provider schema, and 12 committed generated
  fixtures included in the release.
- [ ] **M5-33:** Complete `../../tests.md` with exact test paths and statuses for
  all
  eight acceptance criteria.
- [ ] **M5-34:** Manually approve PDF visual legibility for representative
  one-page and multi-page output.
- [ ] **M5-35:** Manually approve the clean/professional interface on one desktop
  and one narrow mobile viewport.
- [ ] **M5-36:** Update README instructions so a new contributor can install,
  test, build, run, and container-smoke-test Checkmate from a clean checkout.
- [ ] **M5-37:** Check the remaining items in `../01-project-setup.md` only after
  their referenced version, container, health, and contributor evidence exists.
- [ ] **M5-38:** Run every command required by `AGENTS.md` from a clean checkout
  and record the final passing commit.

## Scope and hosting closure

- [ ] **M5-39:** Verify the release has no authentication, database history,
  saved drafts, shareable links, payments, payment tracking, groups, recurring
  balances, native application, unequal splits, or multiple currencies.
- [ ] **M5-40:** Confirm the repository ends with a tested OCI image and does not
  select or configure a cloud host, registry, domain, TLS provider, or automatic
  deployment target for v0.1.
- [ ] **M5-41:** Record any future hosting or product capability as backlog work
  rather than adding it to the approved MVP.

## Completion criteria

- [ ] Every acceptance row in `../../tests.md` has passing automated evidence and
  any required manual evidence.
- [ ] The external extraction evaluation meets its approved thresholds for the
  exact released model and prompt.
- [ ] The production image builds reproducibly, runs as non-root, passes all
  smoke checks, and shuts down cleanly.
- [ ] The full CI and `AGENTS.md` command set passes from a clean checkout.
- [ ] All remaining project-setup completion gates are satisfied.
- [ ] No excluded capability or undeclared hosting decision entered v0.1.
