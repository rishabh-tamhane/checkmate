# Expense Splitting Web App

## MVP Requirements

## 1. Overview

The app helps a group split a restaurant receipt based on the items each person consumed.

The MVP should keep the workflow simple:

**Upload receipt → Review/edit → Assign people → Calculate split → Generate PDF**

The app does not need accounts, payment integrations, saved history, or other advanced expense-management features.

---

## 2. Primary User Flow

1. The user uploads a photo or image of a restaurant receipt.
2. The app reads the receipt and extracts the bill into structured line items.
3. The user reviews the extracted information and corrects anything that was read incorrectly.
4. The user adds the names of the people sharing the bill.
5. The app displays the receipt as an interactive table.
6. Each person appears as a column in the table.
7. For every item, the user checks the box for each person who shared that item.
8. The app calculates each person's share automatically.
9. The user reviews the final totals.
10. The user clicks **Generate PDF** and downloads a summary of the split.

---

## 3. Receipt Extraction

The app should attempt to extract:

- Restaurant name, when available
- Receipt date, when available
- Item name
- Quantity, when available
- Item price / line total
- Subtotal
- Tax
- Tip, when present on the receipt
- Final total

Receipt extraction does not need to be perfect. All important extracted values must be editable by the user before the split is finalized.

If receipt extraction fails, the user should still be able to manually add or edit items.

---

## 4. Interactive Split Table

After the receipt is read, the app should show the extracted items in a table.

Example:

| Item | Qty | Price | Rishabh | Alex | Maya | Sam |
|---|---:|---:|:---:|:---:|:---:|:---:|
| Xiao Long Bao | 1 | $15.50 | ☑ | ☑ | ☑ | ☑ |
| Chicken Fried Rice | 1 | $14.00 | ☑ | ☑ | ☐ | ☐ |
| Vegetable Dumplings | 2 | $18.00 | ☐ | ☐ | ☑ | ☑ |
| Cucumber Salad | 1 | $9.50 | ☑ | ☐ | ☑ | ☑ |
| Noodles | 1 | $16.00 | ☐ | ☑ | ☐ | ☐ |

### Table behavior

- Each bill item is one row.
- Each participant is one column.
- A checkbox indicates whether that participant shared the item.
- Clicking a checkbox should immediately update the calculated totals.
- An item shared by multiple people is divided equally among the checked participants.
- Item name, quantity, and price should be editable inline.
- The user should be able to add or remove a bill item.
- The user should be able to add or remove participants.
- A simple **Select All** option may be provided for items shared by everyone.

For the MVP, the table may horizontally scroll when there are many participants rather than introducing a more complex assignment UI.

---

## 5. Split Calculation

### Item split

If an item costing `$20` is assigned to four people, each person receives `$5` of that item's cost.

### Tax and tip

Tax and tip should be distributed proportionally based on each person's item subtotal.

Example:

- Rishabh's items: $30
- Alex's items: $20
- Item subtotal: $50
- Tax: $5

Rishabh is responsible for 60% of the item subtotal, so he receives 60% of the tax. Alex receives the remaining 40%.

### Rounding

The final per-person amounts must add up exactly to the receipt total. Any fractional-cent rounding difference should be handled automatically.

### Validation

Before generating the final PDF:

- Every non-zero item should be assigned to at least one person.
- Prices must contain valid monetary values.
- The app should visibly warn the user if the calculated bill does not match the receipt total.

---

## 6. Split Summary

The app should show a simple summary beneath or alongside the table.

Example:

| Person | Amount Owed |
|---|---:|
| Rishabh | $25.31 |
| Alex | $26.84 |
| Maya | $27.03 |
| Sam | $25.03 |
| **Total** | **$104.21** |

Totals should update immediately when the user edits the receipt or changes an assignment checkbox.

---

## 7. PDF Output

The final action for the MVP should be **Generate PDF** rather than saving the split to an account or database.

The generated PDF should contain:

- Restaurant name, if available
- Receipt date, if available
- Itemized bill
- People assigned to each item
- Subtotal
- Tax
- Tip
- Receipt total
- Final amount owed by each person

The PDF should be clean and easy to share. It does not need elaborate styling.

Example structure:

```text
DIN TAI FUNG
August 16, 2026

Item                    Price     Shared By
-------------------------------------------------
Xiao Long Bao           $15.50    Rishabh, Alex, Maya, Sam
Chicken Fried Rice      $14.00    Rishabh, Alex
Vegetable Dumplings     $18.00    Maya, Sam

Subtotal                           $47.50
Tax                                 $4.50
Tip                                 $8.00
Total                              $60.00

Split Summary
-------------------------------------------------
Rishabh                            $XX.XX
Alex                               $XX.XX
Maya                               $XX.XX
Sam                                $XX.XX
```

---

## 8. Visual Design

The interface should be **clean, minimal, and professional**.

- Use a simple layout with clear hierarchy.
- Use neutral colors with one restrained accent color if needed.
- Use readable typography and conventional form controls.
- Make the receipt table the main focus of the page.
- Prefer familiar checkboxes, inputs, and buttons over custom interactions.
- Avoid gradients, glassmorphism, decorative animations, oversized cards, and other visually flashy elements.
- Optimize the table experience for desktop, while keeping the app usable on mobile.

The product should feel like a lightweight productivity tool rather than a highly stylized consumer app.

---

## 9. MVP Scope

### Included

- Receipt image upload
- Receipt data extraction
- Manual correction of extracted receipt data
- Adding/removing participants
- Checkbox-based item assignment
- Equal splitting of shared items
- Proportional tax and tip allocation
- Automatic per-person totals
- Bill-total validation
- PDF generation and download

### Not included

- User accounts or authentication
- Database-backed bill history
- Saving previous splits
- Shareable web links
- Venmo, PayPal, Zelle, or other payment integrations
- Tracking whether someone has paid
- Groups or recurring balances
- Native mobile apps
- Unequal/custom percentage splits for individual items
- Multiple currencies or currency conversion

These features can be considered after the MVP is working well.

---

## 10. MVP Acceptance Criteria

The MVP is complete when a user can:

1. Upload a restaurant receipt.
2. See the receipt converted into editable bill items.
3. Add the people who shared the meal.
4. Assign each item by clicking participant checkboxes in the table.
5. See each person's total calculated automatically, including tax and tip.
6. Correct any receipt-reading mistakes.
7. Confirm that the calculated total matches the receipt total.
8. Generate and download a PDF containing the finalized split.

No login or saved account is required to complete this workflow.

---

## 11. Scope Guardrail for Technical Design

This document defines **what** the MVP should do. Frameworks, OCR/vision services, PDF-generation libraries, application architecture, deployment, and other implementation choices belong in the technical design document.
