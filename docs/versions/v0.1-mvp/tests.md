# v0.1 MVP Test and Acceptance Evidence

## Status

Planned from the approved technical design. Replace each planned test path with
its final path if implementation requires a different organization, and change
an evidence status to `Passing` only after that exact evidence runs successfully.

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

## Planned suite structure

| Layer | Planned location | Primary responsibility |
|---|---|---|
| Domain unit | `tests/unit/domain/` | Money, validation, allocation, reconciliation, and invariants |
| Adapter unit | `tests/unit/adapters/` | Image normalization, provider translation, and PDF semantics |
| Application | `tests/application/` | Use-case orchestration with fake parser and renderer |
| HTTP integration | `tests/integration/web/` | Routes, schemas, limits, status mapping, headers, and safe logs |
| Browser acceptance | `tests/browser/` | Complete workflow, responsive behavior, keyboard use, and downloads |
| External evaluation | `tests/external/` | Pinned model and prompt quality on generated receipt images |
| Package/container smoke | `tests/smoke/` and CI | Installed assets, startup, health, routes, and shutdown |

## Acceptance criteria

### AC-01: Upload a restaurant receipt

- [ ] Fake-backed browser test selects a supported generated receipt image and
  submits `POST /api/receipts/extract`.
- [ ] HTTP tests cover JPEG, PNG, and WebP plus invalid bytes, unsupported
  format, animation, encoded-size, and decoded-pixel rejection.
- [ ] Evidence status: Planned in milestones 3 and 5.

### AC-02: Convert the receipt into editable bill items

- [ ] Browser test receives the fake structured extraction and renders every
  item, optional quantity, line total, subtotal, tax, tip, total, restaurant,
  and date field as applicable.
- [ ] Browser test edits the deliberately incorrect extracted value and proves
  the corrected complete draft is sent for calculation.
- [ ] Adapter contract tests prove provider objects are converted into
  application-owned editable strings without arithmetic repair.
- [ ] Evidence status: Planned in milestones 3 and 5.

### AC-03: Add the people who shared the meal

- [ ] Browser test adds Alice and Bob, verifies insertion order, then removes
  and re-adds a fictional participant without corrupting assignments.
- [ ] Domain and HTTP tests reject blank, duplicate-after-case-folding,
  overlong, unsupported-character, duplicate-ID, and over-limit participants.
- [ ] Evidence status: Planned in milestones 2 and 5.

### AC-04: Assign items with participant checkboxes

- [ ] Browser test renders a native checkbox for every item-participant pair and
  assigns Pizza to Alice and Bob and Salad to Bob.
- [ ] Browser test proves add/remove operations clean dangling assignment IDs
  and that the table remains usable by keyboard and on a narrow viewport.
- [ ] HTTP tests reject unknown and duplicate item or participant references.
- [ ] Evidence status: Planned in milestones 2 and 5.

### AC-05: Calculate each total including tax and tip

- [ ] Domain tests prove `$10.01` shared by Alice and Bob becomes `$5.01` and
  `$5.00` according to participant order.
- [ ] Domain tests prove `$1.37` tax becomes `$0.40` and `$0.97`, and `$2.55`
  tip becomes `$0.75` and `$1.80`, using independent largest-remainder passes.
- [ ] Domain tests prove Alice owes `$6.16`, Bob owes `$14.77`, and totals equal
  `$20.93` exactly.
- [ ] Browser test proves checkbox changes calculate immediately, text changes
  calculate after debounce, and stale responses cannot replace current totals.
- [ ] Evidence status: Planned in milestones 2 and 5.

### AC-06: Correct receipt-reading mistakes

- [ ] Browser test corrects the deliberate fake extraction error and observes
  new server totals for the matching revision.
- [ ] Browser test proves failed extraction and calculation requests preserve
  the current editable draft and provide retry or manual entry.
- [ ] No-key browser test completes manual entry without calling OpenAI.
- [ ] Evidence status: Planned in milestones 2, 3, and 5.

### AC-07: Confirm the calculated and entered totals match

- [ ] Domain and HTTP tests show entered subtotal, calculated subtotal, entered
  total, calculated total, and blocking differences.
- [ ] Browser test starts with an inconsistent total, displays field and summary
  issues, blocks PDF export, then clears the issues after correction.
- [ ] Invariant tests prove item, tax, tip, and participant sums equal their
  authoritative components for every valid fixture.
- [ ] Evidence status: Planned in milestones 2 and 5.

### AC-08: Generate and download the finalized PDF

- [ ] Application test proves only `FinalizedSplit` reaches `PdfRenderer` and
  invalid, stale, malformed, and zero drafts do not invoke it.
- [ ] HTTP test verifies PDF media type, fixed attachment filename, no-store
  policy, safe errors, and independently recalculated content.
- [ ] Browser test downloads the PDF and uses `pypdf` to confirm title,
  restaurant/date, item assignments, receipt totals, and Alice/Bob totals.
- [ ] Manual evidence confirms representative one-page and multi-page PDFs are
  legible, aligned, complete, and professionally presented.
- [ ] Evidence status: Planned in milestones 4 and 5.

## Cross-cutting release evidence

- [ ] Desktop interface manual review passes for clear hierarchy, restrained
  styling, readable typography, and receipt-table focus.
- [ ] Narrow-viewport manual review passes for stacked layout, touch targets,
  horizontal scrolling, and access to every control.
- [ ] External extraction evaluation records 12/12 schema-valid outputs, exact
  item count and monetary fields, no invented items, and at least 90% exact
  normalized optional text.
- [ ] The isolated wheel and production image each serve `/`, linked static
  assets, and `/health` successfully.
- [ ] The production image starts without runtime downloads, runs as non-root
  with the approved filesystem constraints, and shuts down cleanly.
- [ ] `uv lock --check`, Ruff lint and format, mypy, pytest with coverage, and
  `uv build` all pass for the final release commit.
