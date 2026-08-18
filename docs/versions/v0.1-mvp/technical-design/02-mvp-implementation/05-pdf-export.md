# PDF Export Guide

## Status

Draft, awaiting review.

## Document role

This guide explains finalization, the PDF renderer boundary, ReportLab layout,
safe response behavior, and PDF verification proposed in
[`../02-mvp-implementation.md`](../02-mvp-implementation.md). The parent
document remains authoritative. This status records review of this design area;
it does not approve the overall workstream.

Read this guide before implementing `PdfRenderer`, ReportLab output, the PDF
endpoint, download behavior, or PDF tests.

## PDF export is the final trusted operation

The PDF is intended to be shared, so it must never preserve an invalid or stale
calculation as if it were final.

```text
Browser submits complete draft
            |
            v
Server validates and calculates again
            |
       valid and non-zero?
          /       \
        no         yes
        |           |
        v           v
  return issues   FinalizedSplit
                      |
                      v
                 PdfRenderer
                      |
                      v
                   PDF bytes
```

The server ignores any client-supplied totals. Disabling the button in the
browser is helpful feedback, but server-side revalidation is the actual trust
boundary.

## Why the renderer accepts only `FinalizedSplit`

The renderer should arrange trusted information, not decide whether it is
correct.

```python
class PdfRenderer(Protocol):
    def render(self, split: FinalizedSplit) -> bytes: ...
```

This signature makes responsibilities visible:

- Domain code calculates and validates.
- Application code obtains a finalized result.
- The adapter lays out that result.
- The web layer returns the bytes.

If the renderer accepted a raw HTTP draft, it could accidentally duplicate or
bypass financial policy.

## Why ReportLab Platypus

ReportLab generates PDFs directly in Python. Platypus is its higher-level
layout system: a document is built from “flowables” such as paragraphs, tables,
spacers, and page breaks.

Conceptually:

```text
FinalizedSplit
    |
    v
[Title, metadata paragraph, item table, totals table, split table]
    |
    v
Platypus lays flowables onto pages
    |
    v
io.BytesIO
    |
    v
bytes returned to the endpoint
```

This avoids a headless browser, subprocess, temporary file, and native
HTML-to-PDF libraries. It does mean the PDF has its own intentionally small
presentation definition instead of reusing webpage CSS.

## Document contents and order

The letter-sized document uses fixed margins and always follows this semantic
order:

1. `Checkmate Expense Split`
2. Restaurant name and receipt date when present
3. Itemized bill in receipt order
4. Receipt subtotal, tax, tip, and total
5. Participant split summary in participant order

Stable ordering helps readers compare the PDF with the edited receipt and makes
tests deterministic.

Example structure:

```text
CHECKMATE EXPENSE SPLIT
Example Restaurant
August 16, 2026

Item              Qty   Line total   Shared by
------------------------------------------------
Noodles             1       $16.00   Maya, Alex

Subtotal                     $16.00
Tax                           $1.60
Tip                           $3.20
Total                        $20.80

Person    Items    Tax    Tip    Amount owed
------------------------------------------------
Maya      $8.00   $0.80  $1.60       $10.40
Alex      $8.00   $0.80  $1.60       $10.40
```

## Text, fonts, and escaping

The built-in Helvetica family keeps the runtime independent of operating
system fonts. Its limited character repertoire is why the domain rejects text
that the selected PDF font cannot represent.

ReportLab `Paragraph` values interpret a small XML-like markup language. User
text must therefore be XML-escaped before it is inserted. A restaurant name
such as `A&B <Kitchen>` must render as text rather than become markup.

Dates use a fixed English formatter instead of the machine locale. This avoids
one developer seeing `August 16, 2026` while another machine generates a
different language or ordering.

## Pagination and long content

Real receipts may contain many items or long names. The design requires:

- Long text wraps rather than disappears.
- Item table headers repeat after a page break.
- A row is not silently truncated.
- The participant summary remains readable across pages.

The renderer does not promise that all receipts fit on one page. Correct,
complete multi-page output is preferable to shrinking text until it is
unreadable.

## In-memory generation

The adapter writes to `io.BytesIO` and returns bytes. It does not create a
persistent file:

```text
FinalizedSplit -> memory buffer -> HTTP response -> buffer released
```

This matches the no-storage requirement and makes cleanup simpler. The
production process needs no writable receipt or PDF directory.

## HTTP download behavior

The endpoint returns:

```http
Content-Type: application/pdf
Content-Disposition: attachment; filename="checkmate-split.pdf"
Cache-Control: no-store
```

The fixed filename avoids placing restaurant or participant names in headers,
browser download histories, or logs. `no-store` tells clients and intermediaries
not to retain the response as reusable cached content.

If finalization fails, the endpoint returns structured validation issues rather
than a PDF. If rendering unexpectedly fails, it returns a sanitized `500` with
a request ID and logs only the safe exception category.

## What automated tests can prove

`pypdf` can parse generated bytes and assert semantic content:

- The response is a readable PDF.
- Required headings are present.
- Items and participants appear in the expected order.
- Every receipt and participant amount is present.
- Optional metadata appears only when supplied.
- A long fixture creates readable multi-page content with repeated headers.

Tests should not require byte-for-byte equality. PDF libraries may include
producer metadata or object ordering that changes while the visible document
remains equivalent.

## What still needs visual review

Text extraction cannot judge whether columns overlap, wrapping looks awkward,
or hierarchy feels professional. Before release, a person reviews a rendered
representative PDF.

The visual check should cover:

- Ordinary one-page output
- A long item name
- Several participants
- A forced multi-page receipt
- Alignment of money columns
- Legible title, tables, spacing, and page breaks

This is intentional manual evidence, not a replacement for semantic tests.

## Implications for implementation tasks

The export milestone should be ordered as follows:

1. Define the renderer protocol around `FinalizedSplit`.
2. Build the fixed document styles and date formatting.
3. Render metadata, item, receipt-total, and participant-summary sections.
4. Add wrapping, repeated headers, and multi-page behavior.
5. Escape every user-controlled string.
6. Generate bytes entirely in memory.
7. Implement the endpoint with independent finalization and safe headers.
8. Add semantic unit and HTTP integration tests.
9. Record the required manual visual review before release.

## Review checklist

- Can raw or invalid request data reach the renderer?
- Does the renderer contain any monetary calculation?
- Is all user text escaped and representable by the chosen font?
- Are long receipts complete rather than truncated?
- Are personal values excluded from filenames and headers?
- Does the endpoint set `Cache-Control: no-store`?
- Do automated tests check semantics rather than unstable PDF bytes?
- Is visual review explicitly included in release evidence?
