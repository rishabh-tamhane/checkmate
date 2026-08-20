# v0.1 MVP Test and Acceptance Evidence

## Status

Milestone 2 manual-splitting, Milestone 3 deterministic receipt-extraction,
Milestone 4 PDF-export, and Milestone 5 package-distribution and browser
acceptance evidence are passing as of 2026-08-20. The paid external-provider
evaluation is deferred by owner direction after authentication was rejected
before any fixture completed. External-provider and final clean-checkout
evidence remain open for their owning milestones.

## Evidence rules

- Normal automated evidence must run without network access, an OpenAI key, a
  database, a host-installed service, or real receipt data.
- Use generated receipt images, synthetic amounts, and fictional participant
  names in committed fixtures and browser artifacts.
- Prefer focused unit evidence for financial correctness and use browser tests
  to prove integration, not to substitute for domain assertions.
- Keep Playwright traces and screenshots only on failure.
- Run the live provider suite only with the explicit `external` marker.
- Record PDF legibility and overall visual quality as manual evidence because
  text assertions cannot establish visual correctness.

## Representative synthetic scenario

Use one shared scenario across domain, HTTP, browser, and PDF tests where doing
so improves consistency:

```text
Restaurant: Example Restaurant
Date:       2026-08-16

Pizza       $10.01    Alice and Bob
Salad        $7.00    Bob
Subtotal    $17.01
Tax          $1.37
Tip          $2.55
Total       $20.93

Alice owes   $6.16
Bob owes    $14.77
```

The fake extraction result should contain at least one deliberate, editable
transcription mistake so the browser workflow proves user correction before
finalization.

## Suite structure

| Layer | Current evidence | Primary responsibility |
|---|---|---|
| Domain unit | `tests/test_money_and_validation.py`, `tests/test_splitting.py` | Money, validation, allocation, reconciliation, and invariants |
| Application | `tests/test_calculation_service.py` | Raw-draft conversion and calculation orchestration without framework or network dependencies |
| HTTP integration | `tests/test_calculation_http.py`, `tests/test_web.py` | Schemas, limits, status mapping, headers, safe logs, shell, and health |
| Browser acceptance | `tests/test_browser_workflow.py` | Manual workflow, responsive behavior, keyboard use, debounce, retry, and stale responses |
| Adapter unit | `tests/test_receipt_images.py`, `tests/test_openai_receipt_parser.py`, `tests/test_pdf_renderer.py` | Image normalization, provider translation, and PDF semantics |
| Extraction application/HTTP | `tests/test_receipt_extraction_service.py`, `tests/test_receipt_extraction_http.py` | Bounded orchestration, cleanup, upload contracts, safe errors, and privacy |
| External evaluation | `tests/external/test_receipt_extraction_evaluation.py` (opt-in; deferred without a successful provider response) | Pinned model and prompt quality on 12 generated receipt layouts |
| Package/container smoke | Isolated wheel and source-distribution runs of `tests/smoke_test.py` pass; `tests/container_smoke_test.py` passes against the Linux/amd64 production image | Installed assets, startup, health, routes, and shutdown |

## Acceptance criteria

### AC-01: Upload a restaurant receipt

- [x] Fake-backed browser test selects a supported generated receipt image and
  submits `POST /api/receipts/extract`.
- [x] HTTP tests cover JPEG, PNG, and WebP plus invalid bytes, unsupported
  format, animation, encoded-size, and decoded-pixel rejection.
- [x] Adapter tests recreate an iPhone-style JPEG-signature MPO and prove that
  only its oriented primary frame becomes a metadata-free single-frame JPEG,
  while other multi-frame inputs remain rejected.
- [x] Evidence status: Milestone 3 deterministic evidence passing; live-provider
  and release closure remain open.

### AC-02: Convert the receipt into editable bill items

- [x] Browser test receives the fake structured extraction and renders every
  item, optional quantity, line total, subtotal, tax, tip, total, restaurant,
  and date field as applicable.
- [x] Browser test edits the deliberately incorrect extracted value and proves
  the corrected complete draft is sent for calculation.
- [x] Adapter contract tests prove provider objects are converted into
  application-owned editable strings without arithmetic repair.
- [x] Evidence status: Milestone 3 deterministic evidence passing; live-provider
  and release closure remain open.

### AC-03: Add the people who shared the meal

- [x] Browser test adds fictional participants in insertion order and removes a
  participant without corrupting assignments.
- [x] Domain and application tests reject blank, duplicate-after-case-folding,
  overlong, unsupported-character, duplicate-ID, and over-limit participants.
- [x] Evidence status: Milestone 2 evidence passing; release closure remains
  milestone 5.

### AC-04: Assign items with participant checkboxes

- [x] Browser test renders a native checkbox for every item-participant pair and
  assigns a synthetic item to two participants.
- [x] Browser test proves add/remove operations clean dangling assignment IDs
  and that the table remains usable by keyboard and on a narrow viewport.
- [x] Application and HTTP tests reject unknown and duplicate item or participant
  references.
- [x] Evidence status: Milestone 2 evidence passing; release closure remains
  milestone 5.

### AC-05: Calculate each total including tax and tip

- [x] Domain tests prove `$10.01` shared by Alice and Bob becomes `$5.01` and
  `$5.00` according to participant order.
- [x] Domain tests prove `$1.37` tax becomes `$0.40` and `$0.97`, and `$2.55`
  tip becomes `$0.75` and `$1.80`, using independent largest-remainder passes.
- [x] Domain tests prove Alice owes `$6.16`, Bob owes `$14.77`, and totals equal
  `$20.93` exactly.
- [x] Browser test proves checkbox changes calculate immediately, text changes
  calculate after debounce, and stale responses cannot replace current totals.
- [x] Evidence status: Milestone 2 evidence passing; release closure remains
  milestone 5.

### AC-06: Correct receipt-reading mistakes

- [x] Browser test corrects the deliberate fake extraction error and observes
  new server totals for the matching revision.
- [x] Browser test proves failed calculation requests preserve
  the current editable draft and provide retry or manual entry.
- [x] No-key browser test completes manual entry without calling OpenAI.
- [x] Evidence status: Manual correction, calculation recovery, and fake-backed
  extraction correction pass; live-provider and release closure remain open.

### AC-07: Confirm the calculated and entered totals match

- [x] Domain and HTTP tests show entered subtotal, calculated subtotal, entered
  total, calculated total, and blocking differences.
- [x] Browser test creates an inconsistent subtotal, displays field and summary
  issues, blocks PDF export, then clears the issues after correction.
- [x] Invariant tests prove item, tax, tip, and participant sums equal their
  authoritative components for every valid fixture.
- [x] Evidence status: Milestone 2 evidence passing; release closure remains
  milestone 5.

### AC-08: Generate and download the finalized PDF

- [x] Application tests prove only `FinalizedSplit` reaches `PdfRenderer` and
  invalid, stale, malformed, and zero drafts do not invoke it.
- [x] HTTP tests verify PDF media type, fixed attachment filename, no-store
  policy, safe errors, and independently recalculated content.
- [x] Browser, HTTP, and renderer tests download or generate PDFs and use
  `pypdf` to confirm the title, optional restaurant/date, item assignments,
  receipt totals, and participant totals.
- [x] Preliminary manual evidence confirms representative one-page and
  nine-page PDFs are
  legible, aligned, complete, and professionally presented.
- [x] Evidence status: Milestone 4 evidence passing; final release-level visual
  approval remains in milestone 5.

## Cross-cutting release evidence

- [x] Desktop interface manual review passes for clear hierarchy, restrained
  styling, readable typography, and receipt-table focus.
- [x] Narrow-viewport manual review passes for stacked layout, touch targets,
  horizontal scrolling, and access to every control.
- [ ] External extraction evaluation records 12/12 schema-valid outputs, exact
  item count and monetary fields, no invented items, and at least 90% exact
  normalized optional text.
- [x] The isolated wheel and production image each serve `/`, linked static
  assets, and `/health` successfully.
- [x] The production image starts without runtime downloads, runs as non-root
  with the approved filesystem constraints, and shuts down cleanly.
- [x] `uv lock --check`, Ruff lint and format, mypy, pytest with coverage, and
  `uv build` all pass for the final release commit.

Clean-checkout evidence on 2026-08-20: this release tree passed the complete
`AGENTS.md` command set with 177 tests passing, one explicitly external test
skipped, 98.91% coverage, and successful wheel and source-distribution builds.
