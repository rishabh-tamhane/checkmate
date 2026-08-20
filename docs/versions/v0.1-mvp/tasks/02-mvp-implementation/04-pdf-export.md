# Milestone 4: PDF Export

## Status

Complete. Implementation, automated evidence, and preliminary visual review
passed on 2026-08-19. Final release-level visual approval remains in milestone
5.

## Outcome

A user with a valid, non-zero split can request and download a complete,
readable PDF. The server independently revalidates and recalculates the draft,
and the renderer receives only `FinalizedSplit`, never raw or client-calculated
data.

## Requirement traceability

- PDF output in requirements section 7
- Clean and professional presentation in section 8
- Acceptance criterion 8

## Design sources

- [Domain and calculations](../../technical-design/02-mvp-implementation/02-domain-and-calculations.md)
- [Web workflow](../../technical-design/02-mvp-implementation/03-web-workflow.md)
- [PDF export](../../technical-design/02-mvp-implementation/05-pdf-export.md)
- [Security and privacy](../../technical-design/02-mvp-implementation/06-security-and-privacy.md)
- [Runtime and testing](../../technical-design/02-mvp-implementation/07-runtime-and-testing.md)

## Dependencies and renderer boundary

- [x] **M4-01:** Add `reportlab` with `uv add`; add `pypdf` and
  `types-reportlab` as development dependencies with `uv add --dev`.
- [x] **M4-02:** Define synchronous `PdfRenderer.render` accepting only
  `FinalizedSplit` and returning bytes.
- [x] **M4-03:** Implement a deterministic fake renderer for application and
  HTTP tests that do not need ReportLab layout.
- [x] **M4-04:** Keep ReportLab imports and objects inside the PDF adapter and
  prohibit monetary calculation, raw request parsing, or validation policy in
  the renderer.

## ReportLab document

- [x] **M4-05:** Implement `ReportLabPdfRenderer` with Platypus, letter page
  size, fixed margins, built-in Helvetica fonts, and an `io.BytesIO` target.
- [x] **M4-06:** Render the fixed title `Checkmate Expense Split` followed by
  optional restaurant name and receipt date.
- [x] **M4-07:** Format dates with a fixed English month-name formatter that is
  independent of host locale.
- [x] **M4-08:** Render the itemized table in receipt order with optional
  quantity, line total, and assigned participant names in participant order.
- [x] **M4-09:** Render entered subtotal, tax, tip, and total in canonical USD
  format.
- [x] **M4-10:** Render each participant's item subtotal, tax share, tip share,
  and final amount in participant order.
- [x] **M4-11:** XML-escape every restaurant, item, and participant value before
  passing it to a ReportLab `Paragraph`.
- [x] **M4-12:** Wrap long text, repeat table headers after page breaks, and
  preserve every required row without silent truncation.
- [x] **M4-13:** Set fixed title and author metadata where supported without
  relying on byte-for-byte deterministic PDF serialization.
- [x] **M4-14:** Generate entirely in memory and never create a persistent or
  application-managed temporary PDF file.

## Application and HTTP export flow

- [x] **M4-15:** Add an application export service that rebuilds validation and
  calculation from the complete draft before calling `PdfRenderer`.
- [x] **M4-16:** Reject malformed or no-longer-valid drafts with `422` and the
  same structured issues used by calculation; do not trust client totals or a
  previously returned revision.
- [x] **M4-17:** Reject a valid but fully zero receipt because it cannot produce
  a meaningful `FinalizedSplit`.
- [x] **M4-18:** Implement `POST /api/splits/pdf` with the 256 KiB body limit,
  same-origin protection, and independent finalization.
- [x] **M4-19:** Return PDF bytes with `Content-Type: application/pdf`,
  `Content-Disposition: attachment; filename="checkmate-split.pdf"`, and
  `Cache-Control: no-store`.
- [x] **M4-20:** Keep restaurant and participant text out of filenames and
  headers; map renderer failure to a sanitized `500` and log only request ID
  and safe exception category.

## Browser integration

- [x] **M4-21:** Enable **Generate PDF** only for the latest valid, non-zero,
  non-pending calculation revision.
- [x] **M4-22:** Submit the complete current draft rather than browser-computed
  totals when the user requests the PDF.
- [x] **M4-23:** Trigger a download using the server-provided attachment while
  retaining the editable draft on success or failure.
- [x] **M4-24:** Present returned validation issues when the server rejects a
  draft and a safe retryable error when rendering fails.

## Verification

- [x] **M4-25:** Unit-test required sections, optional metadata, ordering,
  canonical money, fixed English dates, escaping, and a forced multi-page
  document by extracting semantic text with `pypdf`.
- [x] **M4-26:** Assert that long item and participant values wrap and every row
  remains present across page breaks.
- [x] **M4-27:** Application-test that invalid and zero drafts never call the
  renderer and valid drafts call it once with `FinalizedSplit`.
- [x] **M4-28:** HTTP-test independent revalidation, `422` issues, body and
  origin limits, download headers, no-store policy, fixed filename, valid PDF
  bytes, and sanitized renderer failure.
- [x] **M4-29:** Browser-test disabled/pending/enabled button transitions,
  successful download, content verification, server-side rejection, and draft
  preservation after failure.
- [x] **M4-30:** Manually inspect representative one-page and multi-page PDFs
  for hierarchy, wrapping, money alignment, repeated headers, and legibility;
  record final release approval in milestone 5.
- [x] **M4-31:** Run every required `AGENTS.md` check and retain semantic rather
  than byte-equality assertions.

## Completion criteria

- [x] Acceptance criterion 8 passes with a content-verified PDF download.
- [x] Invalid, stale, malformed, and zero drafts cannot produce a PDF.
- [x] The renderer receives only `FinalizedSplit` and performs no calculation.
- [x] Generated PDFs contain every required receipt and participant value in
  deterministic order.
- [x] Automated semantic checks and preliminary visual review both pass.
