# Milestone 2: Manual Splitting Workflow

## Status

Complete.

Completion date: 2026-08-19.

## Outcome

A user can manually enter and edit a receipt, add participants, assign items
with checkboxes, see deterministic cent-exact totals, and correct every blocking
validation or reconciliation problem. The workflow requires no network,
external provider, database, or PDF renderer.

## Requirement traceability

- Interactive split table in requirements section 4
- Split calculation and validation in section 5
- Split summary in section 6
- Visual design in section 8
- Acceptance criteria 3, 4, 5, and 7, plus the manual-editing portion of 6

## Design sources

- [System architecture](../../technical-design/02-mvp-implementation/01-system-architecture.md)
- [Domain and calculations](../../technical-design/02-mvp-implementation/02-domain-and-calculations.md)
- [Web workflow](../../technical-design/02-mvp-implementation/03-web-workflow.md)
- [Security and privacy](../../technical-design/02-mvp-implementation/06-security-and-privacy.md)
- [Runtime and testing](../../technical-design/02-mvp-implementation/07-runtime-and-testing.md)

## Browser-test dependency

- [x] **M2-01:** Add `pytest-playwright` as a development dependency with
  `uv add --dev` and install the matching Chromium browser used by local
  milestone tests.

## Domain values and boundary conversion

- [x] **M2-02:** Implement immutable typed values for `Money`, `ReceiptItem`,
  `Receipt`, `Participant`, `Assignments`, `SplitInput`, `ItemAllocation`,
  `ParticipantTotal`, `SplitResult`, `ValidationIssue`, and `FinalizedSplit`.
- [x] **M2-03:** Represent all domain money as integer USD cents and prohibit
  binary floating-point arithmetic in parsing, calculation, and formatting.
- [x] **M2-04:** Parse raw money strings using `Decimal`, accepting only digits
  before the decimal and zero, one, or two fractional digits after trimming.
- [x] **M2-05:** Reject symbols, commas, signs, exponent notation, missing
  leading digits, negative amounts, and more than two fractional digits with
  stable field issues.
- [x] **M2-06:** Format valid amounts as `$0.00` with exactly two fractional
  digits.
- [x] **M2-07:** Treat item amount as line total; accept optional positive
  quantity with at most three fractional digits without multiplying the line
  total.
- [x] **M2-08:** Validate optional ISO `YYYY-MM-DD` receipt dates and convert
  them to standard-library `date` values only after successful validation.
- [x] **M2-09:** Enforce trimmed, non-empty required names, 200-character text
  limits, printable Windows-1252 content, and case-folded participant-name
  uniqueness.
- [x] **M2-10:** Enforce unique opaque item and participant IDs, no unknown
  references, at most 100 items, and at most 50 participants.

## Deterministic allocation and finalization

- [x] **M2-11:** Divide each assigned item with `divmod`, distributing extra
  cents by current participant order.
- [x] **M2-12:** Sum each participant's item allocations into an item subtotal
  without recalculating from quantity.
- [x] **M2-13:** Allocate tax with the largest-remainder method using participant
  item subtotals and participant order as the exact-tie breaker.
- [x] **M2-14:** Allocate tip in an independent largest-remainder pass using the
  same ordering rule.
- [x] **M2-15:** Calculate item subtotal and receipt total independently from
  entered subtotal and entered total.
- [x] **M2-16:** Report a blocking issue when entered subtotal differs from the
  item sum or entered total differs from subtotal plus tax and tip; never
  silently replace an entered amount.
- [x] **M2-17:** Reject every non-zero unassigned item and every non-zero receipt
  without a participant.
- [x] **M2-18:** Require zero tax and tip when item subtotal is zero; allow a
  fully zero calculation but do not create a finalized split from it.
- [x] **M2-19:** Construct `FinalizedSplit` only when no blocking issue remains
  and participant totals sum exactly to entered total.

## Application and HTTP calculation contract

- [x] **M2-20:** Implement an application calculation service that accepts
  application-owned raw draft input, invokes domain conversion and calculation,
  and returns normalized values, issues, reconciliation, and safe provisional
  allocations.
- [x] **M2-21:** Define Pydantic request and response schemas without exposing
  Pydantic models inside the deterministic domain.
- [x] **M2-22:** Implement `POST /api/splits/calculate` with the complete draft
  and echoed client revision; do not introduce server-side draft state.
- [x] **M2-23:** Return `200` for structurally valid, user-correctable drafts and
  `422` for structurally malformed JSON.
- [x] **M2-24:** Enforce the 256 KiB JSON body limit before schema parsing and
  return a stable safe error when exceeded.
- [x] **M2-25:** Normalize valid assignment lists into participant order while
  preserving duplicate or unknown references as blocking issues.
- [x] **M2-26:** Require the approved custom same-origin request header, validate
  `Origin` when present, and keep CORS disabled.
- [x] **M2-27:** Set `Cache-Control: no-store` on calculation responses and keep
  request and response bodies out of logs.

## Browser draft and editing behavior

- [x] **M2-28:** Create one plain JavaScript draft containing raw receipt
  strings, ordered item and participant records, assignments, and revision.
- [x] **M2-29:** Generate new record IDs with `crypto.randomUUID()` and never
  display an ID as user content.
- [x] **M2-30:** Add and remove receipt items inline; removal must also delete
  the item's assignments.
- [x] **M2-31:** Add and remove participants in insertion order; removal must
  delete that participant from every assignment.
- [x] **M2-32:** Render item name, optional quantity, and `Line total` as editable
  fields, along with editable receipt metadata and subtotal, tax, tip, and
  total.
- [x] **M2-33:** Render one native checkbox per item-participant pair in a
  semantic table and omit the optional `Select All` feature.
- [x] **M2-34:** Send checkbox, add, and remove changes immediately; debounce
  text edits for 300 milliseconds after the last keystroke.
- [x] **M2-35:** Increment the client revision for every calculation request,
  apply only a response matching the current revision, and mark totals pending
  while the latest response is outstanding.
- [x] **M2-36:** Preserve the editable draft on network failure, mark totals
  unavailable, and provide a retry action without presenting stale totals as
  current.
- [x] **M2-37:** Render field issues next to inputs with `aria-describedby` and
  duplicate them in a focusable error summary.
- [x] **M2-38:** Always display entered and calculated subtotal and total values,
  including the reconciliation difference.
- [x] **M2-39:** Render participant item subtotal, tax, tip, and final amount in
  server-provided participant order.
- [x] **M2-40:** Keep **Generate PDF** disabled unless the latest response is a
  valid non-zero finalized split with no calculation pending; PDF behavior is
  implemented in milestone 4.

## Presentation and accessibility

- [x] **M2-41:** Use a semantic table with caption, header cells, labelled
  inputs, native checkboxes, visible focus, and tabular numbers.
- [x] **M2-42:** Keep item columns leftmost, participant columns in insertion
  order, and the item-name column sticky when supported.
- [x] **M2-43:** Add horizontal table scrolling, at least 44-pixel touch targets,
  and stacked summary placement on narrow viewports.
- [x] **M2-44:** Apply the approved neutral palette, system font stack, restrained
  accent, bounded width, and conventional controls without gradients,
  glassmorphism, decorative motion, or oversized cards.
- [x] **M2-45:** Render all user-controlled browser text with `textContent` or
  safe DOM properties, never `innerHTML`.
- [x] **M2-46:** Do not write the draft to cookies, local storage, session
  storage, service workers, analytics, or any server persistence.

## Verification

- [x] **M2-47:** Add table-driven unit tests for every accepted and rejected
  money, quantity, date, text, ID, count, and participant-name case.
- [x] **M2-48:** Unit-test equal sharing, indivisible cents, participant-order
  ties, proportional tax and tip, zero values, and the complete worked example
  from the domain design.
- [x] **M2-49:** Assert all allocation invariants: item shares, item subtotals,
  tax shares, tip shares, and participant totals each sum to their authoritative
  component.
- [x] **M2-50:** Test every finalization blocker, including malformed values,
  dangling references, unassigned non-zero items, subtotal mismatch, total
  mismatch, and participant-total mismatch.
- [x] **M2-51:** Application-test calculation orchestration without FastAPI,
  browser, database, network, or credentials.
- [x] **M2-52:** HTTP-test request/response schemas, revisions, status mapping,
  body limit, origin policy, cache headers, and absence of fixture values from
  logs.
- [x] **M2-53:** Browser-test manual entry, record add/remove behavior,
  assignments, immediate and debounced calculations, mismatch correction,
  stale-response rejection, keyboard operation, and narrow-viewport scrolling.
- [x] **M2-54:** Run the complete `AGENTS.md` verification suite and keep domain
  behavior covered above the repository's 90% line-coverage floor.

## Implementation evidence

- Money and boundary validation: `tests/test_money_and_validation.py`
- Allocation, reconciliation, finalization, and invariants:
  `tests/test_splitting.py`
- Framework-independent application orchestration:
  `tests/test_calculation_service.py`
- JSON schema, status, size, origin, cache, reference, and logging contracts:
  `tests/test_calculation_http.py`
- Desktop, narrow viewport, keyboard, debounce, retry, record lifecycle, and
  stale-response behavior: `tests/test_browser_workflow.py`
- Required verification passed on 2026-08-19 with 118 tests and 99% line
  coverage, followed by a successful wheel and source-distribution build.

## Completion criteria

- [x] A user can complete the manual workflow for acceptance criteria 3, 4, 5,
  and 7 without an OpenAI key.
- [x] Every valid calculation is deterministic and cent-exact.
- [x] Every invalid or inconsistent draft displays actionable issues and cannot
  become a finalized split.
- [x] Desktop, narrow-viewport, and keyboard workflow evidence passes with
  synthetic data.
- [x] No extraction, PDF rendering, persistence, authentication, payment, or
  custom-split capability has been introduced.
