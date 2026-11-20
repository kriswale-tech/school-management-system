# Data migration — bringing an existing school in

How a school loads pupils and old fee records. The current-term Excel import on the student list is separate and still works. It creates this term’s students only.

**Last reviewed:** 2026-11-20

---

## Who can run it

School **admin** and **staff**. Accountants and teachers cannot. Platform admin does not migrate a school.

One import can be saving at a time for a school. Mapping and the preview do not hold that lock. Saving does.

The home is `/migration`. **Back** on an import returns there.

## The four imports

| Import | What one row is | Creates students? |
| --- | --- | --- |
| Student information | One pupil | Yes, when the row is new |
| Enrollment history | One pupil in one term | No. The pupil must already exist |
| Opening balances | Amount still owed for one pupil and one term | No |
| Fee history | A charge file and a payment file, together or one at a time | No |

Jobs started without a template still use the older combined student-and-enrollment behaviour. The screens always pick a template.

## Files

Excel or CSV. Headers are mapped to SCHOOLASST fields. Suggestions come from an exact header, a mapping this school already approved, a known alias, or a close text match. An uncertain suggestion is not applied on its own. Extra columns are ignored. Their raw values stay on the row.

Values that are not already SCHOOLASST choices (term, payment method, relationship, and similar) are matched on the check-values step. Relationship, student status, and new/continuing student can be left out. Gender cannot.

A sheet is included only when its checkbox is ticked. Replacing a file replaces that file. On fee history, replacing the charges file keeps the payments file, and the reverse. A file cannot be replaced after any of its rows have been saved.

Files are stored privately for the school, not with report PDFs and not with the older bulk-import folder. The default is the app disk. After an import is fully saved, the spreadsheet bytes are deleted. The file name and the record of the import stay. A partly saved import keeps the file. A finished import cannot be deleted from the list in a way that removes the report, and its file cannot be swapped.

## Matching pupils

An exact student ID links the row. If that ID is present and unknown, the row does not fall through to a name match. A previously approved external ID links when the student ID cell is blank. A likely match on name plus date of birth, or name plus phone, waits for confirmation. Nothing is merged automatically.

Student information: a student ID that appears twice is blocked on every row that uses it, until the file is unique.

Enrollment history, opening balances, and fee history expect the same student ID on many rows. Those repeats are not treated as duplicates.

Empty fields on a pupil who already exists can be filled. A stored value that differs from the file is kept unless someone resolves the conflict.

## Years and old classes

A year already on the school calendar is reused. A missing past year needs start and end dates from the person running the import. The label must look like `2020/2021`, the start date must fall in the first year, and the end date in the second. The span must be at least three days. The import then creates that year inactive, with three terms, and does not change the current year or term.

Enrollment history for the **current** term must use a real class. Older terms may use **Keep as old class**. Those snapshot classes stay out of class setup, teacher lists, promotion, fee class pickers, and reports.

## Review and save

Rows that need a change can be edited on the review step. Needs-attention rows can be downloaded, with the reason, under the import’s name.

Save writes in batches. Each row is its own step, so one failure does not undo the rows already saved. Running the save again does not create a second copy of a row that already saved.

**Continue** retries only rows that can still be saved. **Finish without these** marks the remaining rows as left out and closes the import. Saved rows stay saved. The screen stays on the results.

Results show a Saved table and, when anyone was left out, a Not saved table. Both are paged at 50. While the save is still running, Not saved is hidden and the page says the waiting rows are not listed yet. When the save finishes, both lists are loaded again, so a finished import does not show the same rows as saved and not saved.

A finished import is a report. The step buttons are gone. **Finish** returns to the migration home.

## Opening balances

Use this when the school knows what is still owed and does not have the old bills and receipts.

The download columns are Student ID, Academic year, Term, Outstanding balance, Source reference, and Notes. Source reference is an optional label from the old system. It is stored and shown on the results. It is not used to match the pupil or to decide a duplicate.

The amount becomes a `StudentFee` on a fee item named **Opening balance**. That item is not part of the fee catalog. Fees settings will not edit it. Apply, carry-forward, and copy-from-previous skip it. One opening balance per pupil per term. A second import of the same pupil and term is left out. Zero is left out. A negative amount is blocked. Two rows for the same pupil, year, and term are both blocked and are not added together. Amounts are Ghana cedis.

The person running the import confirms the total before save. Nothing is written as a payment, a receipt, or a credit.

## Fee history

Use this when the old bills and payments are available. For one pupil and one term, use either an opening balance or fee history, not both. If an opening balance is already saved for that pair, every charge and payment for that pair is left out. Other terms for the same pupil still save.

Two files, one import:

- **Charges.** Student ID, Academic year, Term, Fee item, Amount, Source reference, Notes. Amount is the net payable. The same fee name for the same pupil, year, and term is blocked, not added together. Zero is left out.
- **Payments.** Student ID, Payment reference, Payment date, Amount, Payment method, Academic year, Term, Receipt number, Payment type, Notes. Amount is that term’s share. Payment methods are cash, cheque, bank transfer, mobile money, and other. Payment type is an ordinary payment or an advance.

One workbook with a charges sheet and a payments sheet is not supported. The button used on upload decides what the file is. A file may have several sheets only when every sheet is the same kind. Either file can be saved on its own. Charges alone leave the pupil owing the full charge. Payments alone apply money to the term with no bill, so the balance can go the other way. A later import of the other file is a new job. An already saved fee line or payment reference is left out, not merged.

The same payment reference, with the same pupil, date, method, receipt number, and type, is **one** payment. The amount is the sum of the term shares. The payment sits on the earliest of those terms, with one allocation per term. The same reference twice for the same term is left out. An advance mixed with other rows for that reference is left out. If one row in a group needs attention, the other rows in that group are left out too.

An ordinary overpayment stays on the term. It is not turned into an advance. An **advance** is stored as money held aside. It does not reduce what the pupil owes, and it is not applied when fees are applied or when the pupil enrolls.

Historical fee names are their own fee items, marked as imported history, with the catalog amount at zero. The real amount sits on the pupil’s bill. They do not appear in Fees settings and are not stamped onto other pupils when a structure is applied.

There is no SCHOOLASST receipt. The old receipt number is kept and shown on payment history, including search. An advance with no allocation shows as **Advance** on that history.

The save does not require the totals to match a confirmed figure. It does require at least one row that can be saved. Charges are written first, then payments. No receipt, no text, no fee notice, and no activity is created by the writer.

## What the rest of the app does with imported debt

Red on a fee screen means billed is higher than paid. The screen does not care whether the bill was a normal fee, an opening balance, or fee history.

| Place | What turns red |
| --- | --- |
| Fee list, current term (this is how the list opens) | This term only, for pupils enrolled this term |
| Fee list, All time | Lifetime billed minus lifetime paid, including imported debt, for pupils enrolled this term |
| A pupil’s own fees page | The year or term you are looking at, or all time |
| Dashboard debtor count | The current term |

A pupil who is not enrolled this term does not appear on the fee list, even on All time. Their own fees page still shows the old year.

Recording a payment starts at the earliest term that still owes, including an imported balance, then moves forward.

**Remind parents** uses the filter on the fee list. All time sends the lifetime total and names the terms. One term sends only that term.

The **automatic** reminder sends for all debt still owed by pupils enrolled this term, on the school’s schedule, when the total is at least the school’s minimum. It uses the same all-time message as Remind parents on All time.

An imported charge or opening balance on the **current** term is current debt. It is included in the current-term list and can be reminded on its own. A past term alone does not appear on that current-term list.

## Not in this import

- Marks, published results, and report cards from previous years.
- Discounts, waivers, scholarships, or concessions on a pupil’s bill. The school’s own SCHOOLASST subscription discounts are unrelated.
- A way to undo a saved import from the screen.
- Charge-by-charge allocation. A payment is one amount against a term, which is how the live payment button already works.
