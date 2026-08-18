# Web Workflow Guide

## Status

Approved.

Approval date: 2026-08-18.

## Document role

This guide explains the browser state, FastAPI endpoints, editable table,
request timing, error presentation, and accessibility behavior proposed in
[`../02-mvp-implementation.md`](../02-mvp-implementation.md). The parent
document remains authoritative. This status records review of this design area;
it does not approve the overall workstream.

Read this guide before implementing Jinja templates, JavaScript state, HTTP
schemas, the editable receipt table, or browser acceptance tests.

## Browser and server responsibilities

The browser owns presentation and temporary editable state. Python owns all
business validation and money calculations.

| Browser | Python server |
|---|---|
| Store raw form strings while the page is open | Validate raw strings |
| Add and remove visible rows and columns | Validate identities and references |
| Send the complete current draft | Allocate items, tax, and tip |
| Render issues and totals | Reconcile entered and calculated totals |
| Disable export while invalid or pending | Revalidate before generating a PDF |

The browser must never “fix” a split or calculate a total independently. That
would create a second implementation of the financial rules.

## Initial page load

`GET /` returns a Jinja-rendered HTML shell. “Shell” means the durable page
structure: headings, upload controls, empty receipt controls, table container,
summary region, and links to local static assets.

Jinja helps generate the initial document, but ordinary editing after load is
handled by one small JavaScript module. A frontend build system is unnecessary
for this single workflow.

```text
GET /
  |
  v
HTML shell
  +-- /static/checkmate.css
  `-- /static/checkmate.js
```

## Shape of browser draft state

The exact HTTP schema will be defined during implementation, but the mental
model is one plain object:

```javascript
const draft = {
  revision: 7,
  receipt: {
    restaurantName: "Example Restaurant",
    date: "2026-08-16",
    items: [
      {
        id: "item-1",
        name: "Noodles",
        quantity: "1",
        lineTotal: "16.00",
      },
    ],
    subtotal: "16.00",
    tax: "1.60",
    tip: "3.20",
    total: "20.80",
  },
  participants: [
    {id: "person-1", name: "Maya"},
    {id: "person-2", name: "Alex"},
  ],
  assignments: {
    "item-1": ["person-1", "person-2"],
  },
};
```

Raw money remains a string so an in-progress edit can be represented without
JavaScript rounding or accidental coercion.

## Editing lifecycle

### Adding and removing items

Adding an item creates a new stable ID and an empty editable row. Removing it
also removes its assignment entry so the next request cannot contain a dangling
reference.

### Adding and removing participants

Adding a participant appends a stable ID to participant order and therefore
adds a checkbox column. Removing a participant removes that ID from every item
assignment.

### Applying extraction results

A successful upload replaces receipt fields and items because the extracted
item identities describe a new receipt transcription. Existing participants
remain, but assignments are cleared because old item IDs no longer exist.

The application should make this replacement predictable rather than trying to
guess which old assignments correspond to newly extracted rows.

## Calculation request timing

Different edits need different timing:

- Checkbox, add, and remove actions calculate immediately.
- Text inputs wait 300 milliseconds after the latest keystroke.

The delay is a debounce. If a user types `12.50`, the browser should not send a
request after every character when the typing continues quickly.

```text
User types "1" ---- timer starts
User types "2" ---- old timer cancelled, new timer starts
User types "." ---- old timer cancelled, new timer starts
User stops -------- 300 ms -------- request is sent
```

Debouncing reduces noise, but it does not change correctness. The complete
latest draft is always sent.

## Preventing stale responses

Network responses may return in a different order from requests:

```text
Request revision 10 ----------------------> response arrives second
Request revision 11 ----------> response arrives first
```

If revision 10 were rendered last, it would overwrite newer totals. Every
request therefore includes a monotonically increasing client revision, and the
server echoes it.

The browser applies a result only when:

```text
response.revision == current draft revision
```

While the latest calculation is pending, old totals are visibly pending or
unavailable. They must not look current.

## Normal editing errors versus HTTP failures

A user entering an incomplete receipt is part of normal operation. The
calculation endpoint returns `200` with structured issues when it can understand
the request shape.

```json
{
  "revision": 11,
  "issues": [
    {
      "code": "invalid_money",
      "path": "receipt.items.item-1.line_total",
      "message": "Enter an amount with at most two decimal places.",
      "severity": "error"
    }
  ]
}
```

Malformed JSON is different: it does not match the API structure and receives
`422`. Provider outages, oversized uploads, and internal failures use their
documented transport statuses.

## Rendering validation well

Every issue appears in two useful locations:

1. Near the field that needs correction.
2. In a focusable error summary above the table.

The field uses `aria-describedby` to associate the visible message with its
input. Selecting an error-summary link should move focus to the corresponding
control when practical.

Reconciliation should always show both entered and calculated values:

```text
Entered subtotal:    $47.00
Calculated subtotal: $47.50
Difference:           $0.50
```

This tells the user what to investigate instead of merely saying “invalid.”

## The interactive table

The table uses semantic HTML rather than a visual grid built from generic
`div` elements:

- A caption describes the table.
- Column and row headers establish relationships.
- Inputs have programmatic labels.
- Assignments use native checkboxes.
- Money uses tabular number styling.

```text
| Item inputs | Qty | Line total | Maya | Alex |
|-------------|-----|------------|------|------|
| Noodles     | 1   | 16.00      | [x]  | [x]  |
```

The table scrolls horizontally when participant columns exceed the viewport.
This keeps the same interaction model on mobile instead of introducing a
second, potentially inconsistent assignment UI.

## Responsive behavior

Desktop:

```text
+-----------------------------------+----------------+
| Receipt table                     | Split summary  |
+-----------------------------------+----------------+
```

Narrow viewport:

```text
+---------------------------+
| Upload and receipt fields |
+---------------------------+
| Horizontally scrollable   |
| receipt table             |
+---------------------------+
| Split summary             |
+---------------------------+
```

Controls retain at least a 44-pixel touch target, keyboard focus stays visible,
and the user can reach every checkbox without relying on pointer precision.

## PDF button state

The browser enables **Generate PDF** only when all of the following describe the
latest revision:

- Calculation has completed.
- No blocking issue exists.
- The split is valid and non-zero.
- No newer calculation is pending.

This is good feedback, but it is not a security boundary. The PDF endpoint
revalidates and recalculates the submitted draft because any HTTP client can
call an endpoint without using the page.

## Network and extraction failure behavior

The current draft must remain editable when a request fails. The page marks
totals unavailable and offers retry rather than clearing the user's work.

When automatic extraction is unavailable or fails, the same item controls used
for correcting an extraction remain available for manual entry. Manual entry
is a first-class fallback, not a separate application.

## No browser persistence

The draft is not written to cookies, local storage, session storage, a service
worker, or analytics. Closing or refreshing the page discards it.

This implements the current no-history requirement and avoids creating an
undeclared retention mechanism for receipt and participant data.

## Implications for implementation tasks

A useful sequence is:

1. Render the accessible HTML shell and local assets.
2. Define the draft state and stable-ID operations.
3. Render editable receipt items and participant columns.
4. Serialize the complete draft into the calculation request.
5. Add debounce, revision tracking, and stale-response protection.
6. Render field issues, reconciliation, and participant totals.
7. Implement valid/pending/failed PDF button states.
8. Add desktop, narrow-viewport, and keyboard acceptance coverage.

Each behavior should be testable with the fake receipt parser so browser tests
never depend on a live external service.

## Review checklist

- Does the browser keep raw strings rather than calculate with money?
- Are item and participant identities stable across edits?
- Are dangling assignments removed when records are deleted?
- Can an older response overwrite a newer draft?
- Are current totals visibly pending during recalculation?
- Can every error be found and understood with a keyboard and screen reader?
- Does PDF generation remain protected by server-side validation?
- Is the complete workflow usable when automatic extraction is unavailable?
