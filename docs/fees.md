# Fees — how it works

Reference for the fees product: catalog → bill → pay → advance.  
Deferred items: [fees-backlog.md](./fees-backlog.md).

**Last reviewed:** 2026-08-25

---

## Mental model

Two layers:

| Layer | Models | Meaning |
| --- | --- | --- |
| **Catalog** | `FeeStructure` + `FeeItem` | What the school charges for a term (name, amount, who it applies to) |
| **Ledger** | `StudentFee`, `Payment`, `Receipt`, `StudentFeeCredit` | What each student owes / has paid / holds as advance |

The desk and payment flows read the **ledger**. Changing the catalog does not rewrite existing bills unless you **Apply** (and Apply is blocked once the structure is locked).

One fee structure per **school + term**.

---

## Fee structure lifecycle

```
draft ──publish──► published ──apply──► applied (locked)
                ▲
carried_forward ┘  (copy of previous term’s items; still editable until applied)
```

| Status | Editable? | Students billed? |
| --- | --- | --- |
| `draft` | Yes | No |
| `carried_forward` | Yes | No |
| `published` | Yes | No — ready only |
| `applied` | **No** (locked) | Yes — `StudentFee` rows exist |

**Published does not auto-apply** when a term becomes active. Apply is always an explicit action (Settings, or school setup completion for the active term).

### Apply

`apply_fee_structure`:

1. For each enrollment in that term, create matching `StudentFee` rows from items the student qualifies for (school / level / class + new vs continuing).
2. Auto-apply any available **advance** credits against the new bill.
3. Set status to `applied` and lock the catalog.

### Late enrollments

After a term’s structure is **applied**, new enrollments (onboard, bulk import) automatically get matching `StudentFee` rows — no second Apply click.

### Past terms

A term is **ended** when `end_date` is before today.

- No new catalog for an ended term that never had one.
- If a catalog already exists, Settings keeps it listed as **(past)** and **read-only** (no edit / apply).
- Current and upcoming terms remain fully editable until applied.

---

## Who an item applies to

Each `FeeItem` has:

- **Applies to (groups):** entire school, a level, or a class  
- **Applies to (students):** all / new only / continuing only  

Matching uses the student’s `ClassEnrollment` for that term (`class_level`, `is_new_student`).

---

## Payments & advances

1. **Record payment** targets the student’s **earliest term with an outstanding balance**.
2. Amount applied reduces that term’s owing; any **excess** becomes a `StudentFeeCredit` (advance).
3. When a later term’s fees are **applied** (or a late join is billed onto an applied term), available advances are applied FIFO as `advance_credit` payments.

Advances show on the fees desk, fee detail header, and record-payment summary.  
Refunding unused advance is **not built yet** (see backlog).

---

## Product surfaces

| UI | Role |
| --- | --- |
| `/fees` | Desk: balances, stats, record payment, open student fee detail |
| `/fees/settings` | Catalogs by term: add/edit items, Apply, view past catalogs read-only |
| `/fees/:studentId` | Student fee breakdown + payment history |
| Student detail → Fees | Same breakdown/history in student context |
| Setup → Fees | First-term catalog during onboarding; completing school setup applies the active term |

### Main APIs

- Desk: `GET /api/v1/fees/`, `/stats/`, `/filter-options/`
- Structures: `GET /fees/structures/?term=`, items CRUD, `POST /fees/structures/:id/apply/`
- Payments: `POST /fees/payments/`, `GET /fees/students/:id/payment-target/`
- Student: `GET /students/:id/fees/`, `GET /students/:id/payments/`

---

## Day-to-day checklist (current)

1. Ensure academic year/terms exist.  
2. In **Fees Settings**, select the term → add items (or keep carried-forward copy).  
3. **Apply** when ready to bill enrolled students (locks amounts).  
4. Record payments on the desk; overpayments become advances.  
5. Late joiners on an applied term are billed automatically.

---

## End of term flow (planned — not built)

Closing a term cleanly spans **calendar**, **enrollment**, and **fees**. Today these are mostly manual / incomplete. Target flow for a later feature:

### Goals

- Mark the current term as finished and activate the next term.  
- Place every continuing student into the next term’s class/stream (promotion / roll-forward).  
- Ensure the next term’s fee catalog is ready and **applied** so bills exist.  
- Carry **arrears** (still owing on previous terms) and **advances** into ongoing collection.  
- Keep past term catalogs **read-only**.

### Proposed steps

1. **Prep next catalog** (can happen mid-term today via Settings)  
   - Select next term → review/edit items → optionally leave as draft until close.

2. **Close current term** (new guided flow)  
   - Confirm outstanding / advances summary for the closing term.  
   - Set current term inactive; set next term `is_active`.  
   - Freeze further edits on the closed term’s fee structure (already true once applied + ended).

3. **Roll enrollments**  
   - Create next-term enrollments from current (same class or promotion map).  
   - Mark `is_new_student` only for true admissions.

4. **Bill next term**  
   - Publish + **Apply** next structure (or auto-apply as part of close if catalog is ready).  
   - Advances from prior overpayments apply automatically on apply / late enroll.  
   - Prior-term balances remain on those terms; record payment still targets earliest owing term.

5. **Ops follow-up**  
   - Desk filter on new active term.  
   - Arrears report / debtors across terms (not built).  
   - Optional: remind to apply if close ran without a ready catalog.

### Out of scope for v1 close (likely)

- Changing applied amounts on the closed term  
- Automatic write-off of arrears  
- Refund of leftover advance (separate backlog item)

### Implementation notes (when building)

- Prefer an explicit **“End term”** wizard over silent cron, unless ops later request scheduled rollover (Celery exists but unused).  
- Reuse: term activate APIs, `get_or_create_fee_structure` / carry-forward, `apply_fee_structure`, `ensure_enrollment_fees`, advance apply-on-bill.  
- New work: enrollment roll-forward / promotion, guided UI, validation that next catalog exists before close completes, reporting snapshot.

Track delivery in [fees-backlog.md](./fees-backlog.md).
