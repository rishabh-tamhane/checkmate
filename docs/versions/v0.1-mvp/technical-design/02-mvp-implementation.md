# MVP Implementation Technical Design

## Status

Draft, complete proposal awaiting approval. This document has been reviewed
against `../requirements.md` and resolves the implementation decisions needed
to derive detailed tasks. Change this status to `Approved` only after the
proposed design has been reviewed as a whole.

## Design goals

- Implement only the v0.1 workflow and acceptance criteria in
  `../requirements.md`.
- Keep receipt extraction replaceable and all split calculations deterministic.
- Make core validation and calculation testable without a browser, network,
  database, or external credentials.
- Preserve reproducibility, privacy, and simple MVP architecture.

Throughout this draft, **Proposed** marks a concrete decision awaiting approval.

## System context and request flow

**Proposed:** Deploy one stateless Python web process. It serves the initial
HTML page and versioned static assets, exposes JSON endpoints for calculation,
accepts a multipart image upload for receipt extraction, and returns the final
PDF as a download. There is no database, account, server-side draft session, or
background worker in v0.1.

```text
Browser
  |-- GET / --------------------------> HTML application shell
  |-- POST /api/receipts/extract ----> ReceiptParser ----> provider
  |-- POST /api/splits/calculate ----> application -----> domain
  |-- POST /api/splits/pdf ----------> application -----> PDF renderer
  `-- GET /health --------------------> process health
```

The browser owns the editable draft for the lifetime of the page. Refreshing or
closing the page discards it, which is consistent with the requirement not to
save splits. The browser sends the complete current draft, not incremental
patches, to keep requests independently reproducible and avoid server session
state.

The flow is:

1. `GET /` returns a Jinja-rendered application shell plus local CSS and a
   vanilla JavaScript module.
2. The browser uploads one receipt image as `multipart/form-data` to
   `POST /api/receipts/extract`.
3. The application validates the upload, calls `ReceiptParser`, and returns an
   editable receipt draft. A parsing failure returns a structured error; the
   browser keeps its current draft, or its initial blank draft, so manual entry
   remains available.
4. The user edits receipt fields, participants, and assignments in browser
   state. Checkbox changes trigger calculation immediately; text edits use a
   short debounce to avoid sending a request for every keystroke.
5. `POST /api/splits/calculate` parses the complete JSON draft, runs the Python
   domain calculation, and returns field issues, reconciliation status, item
   allocations, and participant totals. The browser never calculates or
   corrects money independently.
6. The browser ignores superseded responses so a slower earlier request cannot
   overwrite a newer edit.
7. `POST /api/splits/pdf` receives the complete draft, validates and calculates
   it again on the server, and renders a PDF only from a valid finalized split.
   Client-supplied totals are never trusted.

All endpoints are same-origin. The API is private to this web application; v0.1
does not promise a stable public API.

## Web framework and UI architecture

**Proposed:** Use FastAPI for HTTP routing and boundary validation, Jinja2 for
the initial HTML document, and one small vanilla ECMAScript module for editable
browser state and DOM updates. Serve local CSS and JavaScript through the same
application. Do not add a frontend package manager, bundler, SPA framework, or
third-party browser CDN in v0.1.

FastAPI is compatible with the pinned Python 3.14 runtime and directly supports
typed request models, uploaded files, Jinja templates, static assets, and
testable ASGI endpoints. The browser Fetch and FormData APIs cover the required
JSON requests and image upload without another client library.

The browser module is a presentation adapter. It may collect raw strings and
render server responses, but it must not contain receipt reconciliation,
allocation, tax, tip, or rounding policy. This prevents separate Python and
JavaScript implementations from drifting apart.

Expected direct runtime dependencies for this decision are:

- `fastapi` for the ASGI application and Pydantic boundary models
- `pydantic` because application code directly imports its boundary models
- `jinja2` for the HTML application shell
- `python-multipart` for receipt uploads
- `openai` for the production receipt-parser adapter
- `pillow` for safe image decoding, validation, orientation, and normalization
- `reportlab` for direct PDF generation
- `uvicorn` for the production ASGI process

Dependency versions will be added with `uv add` and resolved in `uv.lock` only
after this design is approved.

Alternatives considered:

- **Django:** its ORM, authentication, admin, and larger application structure
  are unnecessary because v0.1 has no accounts or database.
- **A React/Vue SPA:** a second Node toolchain, build pipeline, component model,
  and client data layer are disproportionate for one workflow and would make
  reproducible packaging more complex.
- **A browser UI framework or CDN script:** it reduces some DOM code but adds a
  runtime dependency without removing the need for custom table state.
- **Fully server-rendered forms:** simple, but full-page submissions do not meet
  the immediate checkbox and edit feedback requirement.

Primary capability references:

- [FastAPI uploaded files](https://fastapi.tiangolo.com/tutorial/request-files/)
- [FastAPI Jinja templates](https://fastapi.tiangolo.com/advanced/templates/)
- [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/)
- [MDN Fetch
  API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)

## Module boundaries

**Proposed:** Keep one installable `checkmate` package with four explicit
layers. Start with this structure and split a module only when its current
responsibilities require it:

```text
src/checkmate/
├── domain/
│   ├── models.py
│   ├── money.py
│   ├── splitting.py
│   └── validation.py
├── application/
│   ├── models.py
│   ├── ports.py
│   └── services.py
├── adapters/
│   ├── receipt_parser.py
│   └── pdf_renderer.py
├── web/
│   ├── app.py
│   ├── schemas.py
│   ├── templates/
│   └── static/
└── config.py
```

Responsibilities and dependency direction:

- `domain` contains immutable business inputs/results, money handling,
  validation, and allocation. It imports only the Python standard library.
- `application` orchestrates use cases and declares narrow `ReceiptParser` and
  `PdfRenderer` protocols. It depends on `domain`, not on vendor SDKs or
  FastAPI.
- `adapters` implement application protocols using the selected external
  providers. Vendor response objects do not cross this boundary.
- `web` owns FastAPI routes, Pydantic request/response schemas, templates, and
  static assets. It converts boundary data into application inputs and maps
  application results into HTTP responses.
- `config.py` reads environment configuration once at application startup. It
  contains no business policy.
- `web.app` is the composition root that constructs adapters and injects them
  into application services.

The allowed dependency direction is:

```text
web ----> application ----> domain
  \            ^
   `-> adapters-'
```

There is no repository or persistence layer because v0.1 stores no data.
Pydantic is limited to HTTP and external-provider boundaries; deterministic
domain functions use standard-library dataclasses and typed values.

## Domain model

**Proposed:** Separate raw editable input from valid domain values. HTTP schemas
accept user-editable strings so an incomplete field can be returned with a
field-specific issue. Conversion creates domain values only after a field is
valid; calculation never receives malformed money.

Core values:

- `Money`: immutable integer number of USD cents.
- `ReceiptItem`: stable opaque ID, trimmed non-empty name, optional positive
  quantity, and non-negative line total.
- `Receipt`: optional restaurant name and date, ordered items, entered
  subtotal, non-negative tax, non-negative tip, and entered total.
- `Participant`: stable opaque ID and trimmed non-empty display name.
- `Assignments`: map from item ID to an ordered tuple of participant IDs.
- `SplitInput`: receipt, ordered participants, and assignments.
- `ItemAllocation`: each participant's cent share of one item.
- `ParticipantTotal`: item subtotal, tax share, tip share, and final total.
- `SplitResult`: ordered allocations and totals plus reconciliation values.
- `ValidationIssue`: stable code, field path, human-readable message, and
  blocking status.
- `FinalizedSplit`: a fully reconciled `SplitResult` with no blocking issues;
  this is the only input accepted by the PDF renderer.

Opaque IDs, rather than names or row indexes, preserve assignments across
edits. Participant ordering is insertion order and is part of the calculation
input because it breaks exact remainder ties deterministically.

The stored item amount is the **line total**, not a unit price. Quantity is
optional informational receipt data and does not multiply or recalculate the
line total. The UI must label the field `Line total` rather than the ambiguous
`Price`. This matches receipts that show quantity separately from the charged
line amount and prevents a second inferred monetary value.

Quantity accepts a positive decimal value with at most three fractional digits
so weighted receipt items can be represented. It is display-only in v0.1.

Receipt date input is either blank or an ISO `YYYY-MM-DD` string and becomes a
standard-library `date` value after validation. Restaurant, item, and
participant display strings are capped at 200 characters after trimming. For
the v0.1 PDF font, they must contain printable text representable by
Windows-1252; control characters and unsupported glyphs are rejected visibly
instead of being replaced in the PDF. These bounds apply to manual and
extracted input alike.

The requirements use dollar examples and exclude multiple currencies and
currency conversion. The v0.1 currency is therefore USD.

## Monetary and allocation policy

**Proposed:** Represent all domain money as integer cents. Use `Decimal` only
while parsing a boundary string into cents; never use binary floating point.
The browser sends canonical decimal strings and renders server-formatted USD
values.

Accepted user money input:

- Leading and trailing whitespace is ignored.
- Digits are required before the decimal point.
- Zero, one, or two fractional digits are accepted.
- Currency symbols, grouping commas, exponent notation, signs, and more than
  two fractional digits are rejected with a field issue.
- The parser adapter is responsible for normalizing provider output into this
  canonical form before it reaches user-editable schemas.

Format valid amounts as `$0.00` using exactly two fractional digits.

For an item with line total `L` cents and `N` assigned participants:

1. Require `N > 0` when `L > 0`.
2. Compute `(base, remainder) = divmod(L, N)`.
3. Give every assigned participant `base` cents.
4. Give one additional cent to the first `remainder` assigned participants in
   current participant order.

Each participant's item subtotal is the sum of their item allocations. Let `S`
be the sum of all item line totals. Allocate tax and tip independently with the
largest-remainder method:

1. For component `C` and participant item subtotal `P`, compute the exact
   numerator `C * P` over denominator `S`.
2. Assign `floor((C * P) / S)` cents initially.
3. Sort participants by descending fractional remainder, breaking exact ties
   by current participant order.
4. Distribute the remaining cents in that order.

This policy guarantees that item allocations sum to `S`, tax shares sum to the
entered tax, and tip shares sum to the entered tip.

Reconciliation calculates both equations:

```text
calculated_subtotal = sum(item.line_total)
calculated_total = calculated_subtotal + tax + tip
```

Finalization requires:

- Every money field is valid and non-negative.
- Every non-zero item is assigned to at least one participant.
- `calculated_subtotal == entered_subtotal`.
- `calculated_total == entered_total`.
- At least one participant exists when the entered total is non-zero.
- The sum of participant totals equals the entered total.

A mismatch is visible and blocking; the application does not silently change
an entered amount or generate a PDF from inconsistent data. It may return
provisional allocations alongside the issues when all values needed for the
calculation are individually valid.

If `S == 0`, tax and tip must also be zero. A fully zero receipt produces zero
participant totals and may be calculated, but PDF generation remains blocked
because there is no meaningful finalized split to share.

## Receipt upload and extraction

**Proposed:** Implement `ReceiptParser` with the OpenAI Responses API. Use the
dated `gpt-5.4-mini-2026-03-17` snapshot, image detail `original`, and Structured
Outputs parsed into a private Pydantic provider schema. The model supports image
input and Structured Outputs, and the dated snapshot prevents an alias update
from silently changing extraction behavior. The model ID and a separately
versioned prompt constant are changed only in code and require the external
extraction evaluation suite before merge.

The provider request has one job: transcribe the visible receipt into the
declared fields. It has no tools, cannot browse, and does not calculate the
split. Its system instruction treats all text in the image as untrusted receipt
content and explicitly ignores instructions found within it. The request uses
`store=False`, a bounded output schema, and no conversation or file object. The
normalized image is sent inline as an input image, so the application does not
create a separately retained OpenAI file.

The application-facing protocol is asynchronous and vendor-neutral:

```python
class ReceiptParser(Protocol):
    async def parse(self, image: NormalizedReceiptImage) -> ExtractionResult: ...
```

`NormalizedReceiptImage` contains JPEG bytes, dimensions, and a media type.
`ExtractionResult` contains optional restaurant name and date strings, ordered
extracted item drafts, optional subtotal/tax/tip/total strings, and non-blocking
review notices. It never exposes an OpenAI SDK object, prompt, response ID, or
token accounting to the web or domain layers.

The provider schema is deliberately permissive about missing receipt fields
but strict about shape:

- Optional metadata and totals use `null` when not visible.
- Each item has a required name and line-total string; quantity is optional.
- At most 100 items are accepted, and textual fields are capped at 200
  characters.
- Monetary values are strings, not JSON floating-point numbers.
- Unknown keys are rejected.

Provider values remain suggestions. The adapter trims them and converts
unambiguous monetary strings to the application's canonical decimal format,
but it does not correct inconsistent arithmetic. A receipt with no visible tip
starts with `0.00`; other missing required monetary values remain blank so the
user must supply them. The normal validation pipeline checks all values after
they become an editable draft. The UI always displays a notice telling the user
to review extracted values.

Upload contract:

- Accept one `multipart/form-data` field named `receipt`.
- Accept JPEG, PNG, or WebP. HEIC/HEIF, PDF, SVG, GIF, and multi-frame images are
  outside v0.1.
- Enforce 10 MiB encoded size by reading at most 10 MiB plus one byte.
- Identify the image from decoded content with Pillow while restricting the
  attempted formats; do not trust the filename or declared content type.
- Reject images over 25 megapixels and convert Pillow decompression-bomb
  warnings into errors.
- Decode the image fully, reject animation, apply EXIF orientation, convert to
  RGB, and downscale without upscaling so the longest edge is at most 4,000
  pixels.
- Re-encode to JPEG at quality 90 without EXIF, XMP, comments, filenames, or
  other source metadata.
- Hold the upload and normalized image only for the active request, close the
  spooled upload in `finally`, and never write application-managed receipt
  files to disk.

The OpenAI client has a 30-second overall request timeout and at most one SDK
retry for transient rate-limit or server failures. An application semaphore
limits each process to four concurrent extraction calls. Provider timeouts map
to `504`; provider unavailability, refusal, rate limiting after retry, or an
invalid structured response maps to a sanitized `502`. Invalid user uploads
map to `400`, `413`, or `415` as appropriate. Responses include a stable error
code and a safe message, never a provider response body.

On extraction failure, the browser preserves any existing draft, displays the
error, and offers the same blank/editable item controls used after a successful
extraction. If `OPENAI_API_KEY` is absent, the application starts in
manual-entry mode and the upload control explains that automatic extraction is
unavailable. Tests and local demonstrations inject a deterministic
`FakeReceiptParser`; production selects the OpenAI adapter only when the key is
present.

Primary capability references:

- [OpenAI GPT-5.4 mini model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [OpenAI image inputs](https://developers.openai.com/api/docs/guides/images-vision)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Pillow image safety limits](https://pillow.readthedocs.io/en/stable/reference/Image.html)

## Editing, participants, and assignments

**Proposed:** Keep one plain JavaScript `draft` object containing raw editable
receipt strings, ordered item and participant records, and assignments keyed by
opaque IDs. Generate IDs in the browser with `crypto.randomUUID()` for newly
added records; extraction responses provide server-generated UUIDs. IDs are
identity only and are never rendered as user content.

The page behavior is:

- A successful extraction replaces the receipt portion of the current draft
  after explicit upload, while participants are retained and assignments are
  cleared because item identities changed.
- Add-item creates an empty editable row. Remove-item deletes its assignments.
- Add-participant creates a participant at the end of participant order.
  Remove-participant removes that ID from every assignment.
- Participant display names must be non-empty and unique after trimming and
  Unicode case folding. IDs, rather than names, remain the calculation keys.
- Restaurant name and date are optional. Item name, quantity, line total,
  subtotal, tax, tip, and total remain raw strings until server validation.
- A checkbox update sends a calculation immediately. Text editing waits 300 ms
  after the latest keystroke. Add and remove actions send immediately.
- Every request carries a monotonically increasing client revision. The page
  applies a response only when the echoed response revision equals the current
  revision and marks previous totals pending while recalculation is in flight.
- Network failure leaves the draft editable, marks totals unavailable, and
  provides a retry action. It never reuses totals from a stale revision as if
  they were current.

The optional `Select All` feature is omitted from v0.1 because individual
checkboxes satisfy the requirement and need no second assignment interaction
to keep synchronized.

The table is real semantic HTML with a caption, header cells, labelled inputs,
and native checkboxes. The item columns remain on the left and participant
columns follow insertion order. Its wrapper scrolls horizontally; the item
name column remains sticky where browser support allows. On narrow viewports,
the upload and summary stack vertically, controls retain at least a 44-pixel
touch target, and horizontal table scrolling remains available instead of
changing the assignment model. Keyboard focus is visible and errors are linked
to their inputs with `aria-describedby`.

Browser state is never written to cookies, local storage, session storage, a
service worker, or an analytics service. Reloading the page intentionally
discards the draft.

The CSS uses a system sans-serif font stack, a neutral background and text
palette, and one restrained accent color for primary actions, checked states,
links, and focus. A bounded page width, consistent spacing, and tabular numbers
provide hierarchy. The receipt table is the dominant surface; summary and
validation sit beside it on wide screens and beneath it on narrow screens.
There are no gradients, decorative animations, glass effects, oversized cards,
or custom checkbox behavior.

## Validation and finalization

**Proposed:** Use the domain validation service as the single source of truth
for calculation and finalization. Each issue has a stable machine code, a field
path such as `receipt.items.<id>.line_total`, a user-facing message, and a
severity of `error` or `warning`. Errors block finalization; warnings request
review but do not.

Blocking errors include:

- Invalid, missing, negative, or over-precision monetary fields
- Empty, overlong, or unsupported-character item names; invalid dates; or
  invalid quantities
- Empty, overlong, unsupported-character, or case-insensitively duplicate
  participant names
- An overlong or unsupported-character restaurant name
- Unknown IDs or duplicate IDs in items, participants, or assignments
- A non-zero item with no assigned participant
- Assignments that reference missing items or participants
- A non-zero receipt without a participant
- Entered subtotal not matching the sum of item line totals
- Entered total not matching calculated subtotal plus tax plus tip
- Participant totals not summing exactly to the entered total
- More than 100 items or more than 50 participants

Missing restaurant name or date is valid because both are optional. Successful
extraction adds a general review warning; fields that the adapter could not
normalize are left editable and receive their normal validation errors. A
receipt arithmetic mismatch is presented prominently as a blocking error even
though the requirements call it a warning: generating a plausible but
incorrect PDF would violate the project's fail-loudly tenet.

`POST /api/splits/calculate` returns `200` with the current normalized values,
issues, reconciliation values, and any provisional allocations that can be
safely computed. Structurally malformed JSON receives `422`. User-correctable
domain issues do not use transport errors because they are the normal editing
loop.

For valid input, assignment lists are normalized into current participant
order before allocation. Duplicate or unknown IDs remain blocking issues and
cannot be finalized. JSON request bodies are capped at 256 KiB before schema
parsing.

The browser enables **Generate PDF** only when the latest revision has a valid,
non-zero finalized split, no calculation is pending, and there are no blocking
issues. The PDF endpoint independently rebuilds the finalized split. It returns
`422` with issues if the submitted draft is no longer valid, so disabling the
button is convenience rather than a security boundary.

The UI shows field issues next to their inputs and also provides a focusable
error summary above the table. Receipt reconciliation always displays entered
and calculated subtotal/total values so the user can see the source of a
mismatch.

## PDF generation

**Proposed:** Generate the PDF directly with ReportLab Platypus through a
`ReportLabPdfRenderer` adapter. ReportLab produces a simple PDF without a
browser engine, native HTML-rendering libraries, subprocess, or temporary
output file. Use only the built-in Helvetica font family so rendering does not
depend on host fonts.

The application-facing protocol is:

```python
class PdfRenderer(Protocol):
    def render(self, split: FinalizedSplit) -> bytes: ...
```

The renderer accepts only `FinalizedSplit`, writes to `io.BytesIO`, and returns
PDF bytes. It does not recalculate money or accept raw request data.

The letter-sized document uses fixed margins and this semantic order:

1. `Checkmate Expense Split` title
2. Restaurant name and receipt date when present
3. Itemized table in receipt order with quantity, line total, and participant
   names in participant order
4. Receipt subtotal, tax, tip, and total
5. Split-summary table in participant order with item subtotal, tax, tip, and
   final amount owed

Dates render with a fixed English month-name formatter rather than the host
locale, so the same input is presented consistently across machines.

Long text wraps, table headers repeat after a page break, and no required row is
silently truncated. All user text is XML-escaped before it is passed to a
ReportLab `Paragraph`, so receipt text cannot become markup. The renderer sets
fixed title/author metadata where supported, but tests assert semantic content
rather than byte-for-byte identity because PDF producer metadata may vary.

The endpoint returns `application/pdf` with
`Content-Disposition: attachment; filename="checkmate-split.pdf"` and
`Cache-Control: no-store`. It does not put restaurant or participant text in
the filename or response headers. A renderer failure returns a sanitized `500`
and is logged only with the request ID and exception category.

Automated tests parse generated bytes with the development-only `pypdf`
dependency and assert page count, required headings, ordered names, every money
total, and multi-page behavior. These semantic tests are complemented by one
manual visual check of the representative desktop acceptance fixture before
v0.1 release.

Primary capability references:

- [ReportLab package](https://pypi.org/project/reportlab/)
- [ReportLab Platypus documentation](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/)
- [pypdf package](https://pypi.org/project/pypdf/)

## Security and privacy

**Proposed:** Treat image bytes, extracted text, restaurant details,
participant names, and provider responses as sensitive request data.

- `OPENAI_API_KEY` is read from the process environment or deployment secret
  store. It is never accepted from the browser, rendered into HTML, logged, or
  stored in a repository file.
- The UI states before upload that the receipt image will be sent to OpenAI for
  extraction and that manual entry is available without an upload.
- Requests set `store=False`. OpenAI documents that API data is not used for
  training unless the customer opts in, but default abuse-monitoring logs may
  retain customer content for up to 30 days. The product must not claim zero
  retention unless the deployed OpenAI project has been separately approved
  and configured for Zero Data Retention.
- The application stores no receipt image, parsed draft, PDF, participant name,
  or provider response after the request. All related responses use
  `Cache-Control: no-store`.
- Application logs contain timestamp, level, generated request ID, route,
  status, duration, upload byte count, normalized dimensions, provider model,
  prompt version, and error category only. They exclude bodies, filenames,
  extracted values, participant names, prompt text, provider bodies, and API
  keys.
- Client errors are specific enough to correct but exclude stack traces,
  internal paths, SDK exceptions, and provider response text. Production error
  handlers return one safe JSON envelope and a request ID.
- Jinja autoescaping remains enabled. Browser rendering uses `textContent` and
  DOM properties, not `innerHTML`, for receipt and participant text.
- Static security headers include a same-origin Content Security Policy,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and denial
  of framing. HTTPS and HSTS are responsibilities of production ingress.
- State-changing browser requests require a custom same-origin request header
  and validate the `Origin` header when present. CORS is not enabled. This
  prevents ordinary cross-site forms from spending extraction quota.
- Public production ingress must enforce the same 10 MiB upload and 256 KiB
  JSON body limits, rate-limit the extraction endpoint, and cap concurrent
  requests. The application semaphore is a second resource bound, not a
  distributed rate limiter.
- Production dependencies are locked and checked by CI. Only synthetic receipt
  images and fictional names may enter tests, documentation, issue reports, or
  committed browser artifacts.

These controls reduce exposure but do not make the MVP suitable for regulated
financial, health, or identity documents. The upload notice should tell users
to submit restaurant receipts only.

Primary data-control reference:

- [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)

## Testing strategy

**Proposed:** Use a test pyramid with deterministic business tests at its base
and a small number of complete browser workflows. Normal CI must require no
network, OpenAI credential, real receipt, database, or host-installed service.

Unit tests cover:

- Money parsing/formatting and every rejected form
- Equal item allocation and deterministic remainder ties
- Largest-remainder tax and tip allocation, including zero values and ties
- Reconciliation and every finalization invariant
- ID, ordering, participant-name, quantity, item-count, and participant-count
  validation
- Image format, encoded-size, pixel-count, animation, orientation, resizing,
  and metadata-stripping behavior using generated synthetic images
- PDF rendering through semantic text assertions and forced multi-page input

Application-service tests inject fake parser and renderer implementations to
prove orchestration and error mapping without importing provider SDKs into the
domain. Parser-adapter contract tests use recorded synthetic SDK response
objects, never live HTTP or copied provider payloads containing real data.

HTTP integration tests use FastAPI's test client to cover every route, response
schema, security header, status mapping, multipart limit, cache policy, stale
reference rejection, and PDF download header. They override dependencies with
fakes and assert logs do not contain fixture names or monetary text.

Browser acceptance tests use `pytest-playwright` with headless Chromium. The
CI suite starts the application with the fake parser and verifies the complete
acceptance workflow: upload a synthetic receipt, edit extraction mistakes, add
and remove records, assign shared items, observe immediate exact totals, fix a
blocking mismatch, and download a content-verified PDF. Separate desktop and
mobile viewport tests cover horizontal scrolling, keyboard operation, visible
focus, error summary behavior, and stale-response protection. Trace and
screenshot artifacts are retained only on failure and use synthetic data.

An opt-in test marked `external` evaluates the pinned OpenAI model and prompt
against 12 committed, generated receipt images covering clean, rotated,
perspective-skewed, long, low-contrast, and optional-tip layouts. It requires
`OPENAI_API_KEY`, never runs in normal CI, and reports field accuracy without
committing provider responses. The acceptance threshold is 12/12 schema-valid
responses, exact line-item count and monetary fields for every fixture, no
invented items, and at least 90% exact normalized optional-text fields. The
initial adapter and every model or prompt change must meet that threshold in a
recorded local run before merge; otherwise the design choice must be revisited.
Normal correctness tests continue to use the fake parser because probabilistic
service output cannot be a normal release gate.

The existing 90% line-coverage threshold remains a floor, not a substitute for
behavioral assertions. `docs/versions/v0.1-mvp/tests.md` will map each acceptance
criterion to its automated evidence when implementation tasks are derived.
Before release, perform two manual checks that automation cannot fully judge:
PDF visual legibility and overall clean/professional appearance on one desktop
and one narrow mobile viewport.

Expected additional development dependencies are `httpx`, `pytest-asyncio`,
`pytest-playwright`, `pypdf`, and `types-reportlab`. Playwright's pinned
Chromium browser is installed explicitly in CI.

Primary browser-test reference:

- [Playwright for Python installation](https://playwright.dev/python/docs/intro)

## Production runtime and delivery

**Proposed:** Expose a `checkmate-web` console script that constructs the
FastAPI application and starts Uvicorn. Local development uses
`uv run checkmate-web`; production uses the same installed entry point without
reload. The process reads `HOST` (default `0.0.0.0`), `PORT` (default `8000`),
`LOG_LEVEL` (default `info`), and optional `OPENAI_API_KEY`. Invalid port or log
configuration fails startup with a safe, direct message.

Run one Uvicorn process per container. The app is stateless, so a deployment
platform may add identical container replicas behind its HTTPS ingress without
session affinity. The application does not trust forwarded headers by default;
a selected platform must configure the exact trusted proxy addresses before
proxy headers are enabled.

`GET /health` is an unauthenticated liveness/readiness check that returns only
`{"status": "ok", "version": "0.1.0"}`. It verifies application startup but
does not call OpenAI, because a transient provider outage must not restart a
healthy web process. The page exposes automatic extraction as unavailable when
no key is configured; manual splitting, calculation, and PDF generation remain
healthy.

Create a multi-stage `Dockerfile` and `.dockerignore`:

1. Pin the official Python 3.14.6 slim base image by immutable digest.
2. Copy the pinned uv 0.11.32 binary from its official image by immutable
   digest in the builder stage.
3. Copy lock and project metadata before source to preserve dependency-layer
   caching.
4. Run `uv sync --locked --no-dev --no-editable --compile-bytecode` and fail if
   the lock is stale.
5. Copy only the resulting virtual environment into a clean Python runtime
   stage; do not include uv, compilers, tests, docs, Git metadata, or local
   virtual environments.
6. Run as a dedicated non-root user with an explicit working directory, expose
   port 8000, and use exec-form `CMD` for graceful signal handling.

The application requires no persistent writable directory. Deployment should
use a read-only root filesystem with a small writable `/tmp` tmpfs if the
platform supports it. The container must build for Linux/amd64 in CI, start
without network-dependent initialization, pass `/health`, serve `/`, and shut
down cleanly. Supporting additional architectures requires a separately tested
image build, not an assumption based on a local machine.

The wheel configuration must include Jinja templates and static assets as
package data. Both the isolated wheel smoke test and container smoke test must
load `/`, its CSS/JavaScript assets, and `/health`; an import-only check would
not detect missing packaged web files.

CI builds and smoke-tests the production image after the existing lint, type,
test, and package jobs. v0.1 does not select a cloud host, container registry,
domain, TLS provider, or automatic deployment target. Publishing or deploying
the image is a later operational decision; the repository's delivery contract
ends with a reproducible, tested OCI image.

Primary runtime references:

- [uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/)
- [FastAPI container deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [Uvicorn deployment guidance](https://www.uvicorn.org/deployment/)

## Alternatives and consequences

The principal alternatives and accepted consequences are:

- **Local Tesseract OCR:** keeps images local but introduces native packages and
  still requires receipt-specific structure inference. It may be reconsidered
  when offline extraction is a product requirement.
- **A generic cloud OCR API:** returns text and geometry but leaves merchant,
  line-item, and totals interpretation to new application logic. The structured
  vision model gives a smaller MVP boundary.
- **The moving `gpt-5.6-luna` alias:** is cheaper, but its current model page
  exposes no dated snapshot. The dated GPT-5.4 mini snapshot is selected to
  favor repeatable behavior. This accepts somewhat higher extraction cost and
  requires explicit evaluation before future model upgrades.
- **HTML/CSS-to-PDF with WeasyPrint or a headless browser:** could reuse web
  styles, but adds native rendering dependencies or a browser runtime. Direct
  ReportLab layout is adequate for the intentionally simple document, at the
  cost of maintaining a separate small PDF presentation.
- **Client-side split calculation:** would make checkbox feedback local but
  duplicate monetary policy in JavaScript and make PDF trust harder. The small
  server round trip is accepted to keep one authoritative implementation.
- **Server sessions or a database:** could survive refreshes but add retention,
  cleanup, privacy, migration, and deployment concerns that are explicitly out
  of scope.
- **Background extraction jobs:** could support very slow providers but require
  job state and polling. A bounded synchronous request with visible manual
  fallback is sufficient for one receipt.
- **A frontend framework and build pipeline:** could organize a much larger UI,
  but this single workflow does not justify a second dependency ecosystem.
- **Gunicorn or multiple workers inside the image:** can use more cores on a
  single host, but one process per stateless container has fewer moving parts
  and lets the deployment platform own replication.

Accepted limitations for v0.1:

- Automatic extraction requires network access, an OpenAI API key, provider
  availability, and paid API usage. Manual entry is the fallback.
- Extraction quality varies with image quality and receipt layout; all values
  require user review.
- Drafts disappear on refresh and cannot be shared as web links.
- USD, equal per-item sharing, proportional tax/tip, and receipt-order tie
  breaking are fixed product policies.
- Display text is limited to the Western-European character repertoire of the
  built-in PDF font. Broader multilingual PDF support requires bundled fonts
  and is deferred until it is a product requirement.
- Discounts, coupons, service charges, multiple tax lines, and arbitrary fees
  are not separate domain concepts. A receipt containing them must be manually
  represented within the supported item/subtotal/tax/tip fields or cannot be
  finalized. Expanding that model requires a requirements change.
- Browser calculations require a live connection to the same application
  process; there is no offline mode.
- Rate limiting, HTTPS, HSTS, request concurrency at fleet scale, and horizontal
  replication are production-ingress responsibilities and must be configured
  when a hosting platform is selected.

## Approval criteria

Change the status to `Approved` only when:

- Every design section has an explicit decision and rationale.
- The design covers every included requirement without adding an out-of-scope
  capability.
- Calculation, validation, privacy, failure, and test behavior are unambiguous.
- All new dependencies and external services are justified.
- The implementation can be divided into ordered, independently verifiable
  tasks without making further architectural decisions.
