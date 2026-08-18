# Domain and Calculations Guide

## Status

Approved.

Approval date: 2026-08-18.

## Document role

This guide explains the domain model, monetary rules, allocation algorithms,
and finalization invariants proposed in
[`../02-mvp-implementation.md`](../02-mvp-implementation.md). The parent
document remains authoritative. This status records review of this design area;
it does not approve the overall workstream.

Read this guide before implementing or reviewing money parsing, validation,
item sharing, tax and tip allocation, reconciliation, or participant totals.

## Why the domain is the center of Checkmate

Receipt extraction is allowed to be uncertain. Expense calculation is not.
After a user reviews the receipt, identical inputs must always produce
identical cent-exact outputs.

```text
Uncertain input                  Deterministic result
-----------------------------   -----------------------------
Receipt image -> extraction -> editable draft -> validation -> split
```

The domain begins at validation. It does not read images, make network calls,
render HTML, or produce PDFs.

## Raw input and valid values are different

During editing, a money input may contain `""`, `"12."`, or `"abc"`. The
browser must be allowed to send that state so the server can explain what is
wrong. It must not become a `Money` value until it is valid.

```text
Raw field: "12.50"
       |
       | validate syntax with Decimal at the boundary
       v
Money(cents=1250)
```

The separation prevents two common mistakes:

- Treating a blank value as zero and silently changing user intent.
- Allowing malformed values into arithmetic and discovering the error later.

## Why money uses integer cents

Binary floating-point numbers cannot represent many decimal fractions exactly.
For example, a computer calculation involving `0.1` and `0.2` can contain a
small hidden approximation. Financial totals need exact cent arithmetic.

Checkmate therefore stores:

```text
$0.01  -> 1 cent
$12.50 -> 1250 cents
$104.21 -> 10421 cents
```

Integer addition and `divmod` are exact. `Decimal` is used only to parse a
validated decimal string into integer cents.

Accepted examples:

| Input | Cents |
|---|---:|
| `0` | 0 |
| `12` | 1200 |
| `12.5` | 1250 |
| `12.50` | 1250 |

Rejected examples include `$12.50`, `1,000.00`, `-1.00`, `1e2`, `.50`, and
`12.345`. Rejecting ambiguous forms gives the application one canonical rule.

## Important domain identities

Names and row positions can change, so they cannot safely identify records.
Opaque IDs remain stable while users edit labels and reorder presentation.

```text
Participant
  id:   "participant-7f..."  <- identity used in assignments
  name: "Maya"               <- editable display value
```

Participant order is meaningful. It provides the deterministic tie breaker
when a cent cannot be divided equally.

An item's stored amount is its line total. Quantity is display information and
does not multiply the amount:

```text
2 Vegetable Dumplings    $18.00

quantity   = 2
line total = 1800 cents
```

This avoids guessing whether a receipt printed a unit amount or a charged line
amount.

## Equal item allocation

For a line total `L` shared by `N` participants:

```text
(base, remainder) = divmod(L, N)
```

Every assigned participant receives `base` cents. The first `remainder`
participants in participant order receive one extra cent.

### Example: an indivisible cent

A `$10.01` item is shared by Alice and Bob:

```text
divmod(1001, 2) = (500, 1)

Alice: 500 + 1 = 501 cents
Bob:   500     = 500 cents
Total:            1001 cents
```

The split is not mathematically identical, but it is cent-exact and repeatable.
Giving the extra cent according to a documented order is better than making a
random choice.

## Proportional tax and tip allocation

Tax and tip are allocated independently according to each participant's item
subtotal. The largest-remainder method preserves both proportionality and the
exact component total.

For component `C`, participant subtotal `P`, and total item subtotal `S`:

```text
exact share numerator = C * P
initial cents         = floor((C * P) / S)
fractional remainder  = (C * P) mod S
```

After assigning every floor value, remaining cents go to the largest
fractional remainders. Participant order breaks exact ties.

## Complete worked example

Receipt:

| Item | Line total | Shared by |
|---|---:|---|
| Pizza | $10.01 | Alice and Bob |
| Salad | $7.00 | Bob |

Additional amounts:

```text
Item subtotal: $17.01
Tax:            $1.37
Tip:            $2.55
Receipt total: $20.93
```

### Step 1: allocate items

Pizza:

```text
Alice = 501 cents
Bob   = 500 cents
```

Salad:

```text
Bob = 700 cents
```

Participant item subtotals:

```text
Alice =  501 cents
Bob   = 1200 cents
S     = 1701 cents
```

### Step 2: allocate tax

For 137 cents of tax:

```text
Alice: floor(137 * 501 / 1701) = 40 cents, remainder 597
Bob:   floor(137 * 1200 / 1701) = 96 cents, remainder 1104
```

The floor values total 136 cents, so one cent remains. Bob has the larger
remainder and receives it:

```text
Alice tax = 40 cents
Bob tax   = 97 cents
```

### Step 3: allocate tip

For 255 cents of tip:

```text
Alice: floor(255 * 501 / 1701) = 75 cents, remainder 180
Bob:   floor(255 * 1200 / 1701) = 179 cents, remainder 1521
```

The floor values total 254 cents. Bob receives the remaining cent:

```text
Alice tip = 75 cents
Bob tip   = 180 cents
```

### Step 4: calculate participant totals

```text
Alice = 501 + 40 + 75  =  616 cents =  $6.16
Bob   = 1200 + 97 + 180 = 1477 cents = $14.77
                                      --------
                                      $20.93
```

The participant totals exactly match the receipt total.

## Reconciliation is separate from allocation

Allocation answers “who owes what?” Reconciliation answers “is the entered
receipt internally consistent?” Both must pass before finalization.

```text
calculated_subtotal = sum(item line totals)
calculated_total    = calculated_subtotal + tax + tip
```

These must match the user's entered subtotal and total. Checkmate does not
silently replace entered values with calculated values because that could hide
an extraction or editing mistake.

### Example mismatch

```text
Items:             $17.01
Entered subtotal:  $16.01
```

The application may show provisional participant amounts if safe, but PDF
generation remains blocked until the user corrects the mismatch.

## Validation categories

### Field validation

Examples include malformed money, an empty item name, an invalid date, or an
unsupported character.

### Reference validation

Assignments must reference existing item and participant IDs. Duplicate IDs
are invalid because they make identity ambiguous.

### Business validation

Examples include a non-zero unassigned item, a non-zero receipt with no
participants, or an entered total that does not reconcile.

### Finalization validation

A `FinalizedSplit` exists only when every blocking rule passes and participant
totals sum exactly to the entered total. This type acts as proof that the PDF
renderer receives trusted data.

## Edge cases to understand explicitly

- A zero-value item may be unassigned because it changes no participant total.
- A non-zero item must have at least one assignment.
- When the item subtotal is zero, tax and tip must also be zero because there is
  no proportional basis for allocating them.
- A fully zero receipt may be calculated but is not meaningful enough to export
  as a finalized PDF.
- Tax and tip use separate largest-remainder passes; their remainders must not
  be combined.
- Participant insertion order is part of deterministic input and must remain
  stable through conversion.

## Invariants worth expressing in tests

For every valid split:

```text
sum(item shares for an item) == item line total
sum(participant item subtotals) == calculated subtotal
sum(participant tax shares) == entered tax
sum(participant tip shares) == entered tip
sum(participant final totals) == entered total
```

Tests should cover ordinary examples, cent remainders, exact ties, zero values,
invalid references, reconciliation failures, and input ordering.

## Implications for implementation tasks

Domain work should be divided into independently verifiable slices:

1. Define immutable domain values and stable identities.
2. Implement money parsing and formatting with table-driven tests.
3. Implement equal item allocation and remainder tests.
4. Implement largest-remainder tax and tip allocation.
5. Implement validation and reconciliation issue reporting.
6. Construct `FinalizedSplit` only after all invariants pass.
7. Add broader invariant/property-oriented examples around the algorithms.

The domain milestone should pass without installing or starting a browser,
database, OpenAI client, or PDF renderer.

## Review checklist

- Are all monetary calculations cent-exact and free of binary floats?
- Is participant order preserved and used consistently for ties?
- Are raw editable strings kept outside calculated domain values?
- Does every non-zero item reconcile with its allocated shares?
- Are tax and tip allocated independently?
- Can invalid input ever produce a `FinalizedSplit`?
- Do all participant totals add up exactly to the entered receipt total?
