# Fees — how it works

Reference for the fees product: catalog → bill → pay → advance.  
Deferred items: [fees-backlog.md](./fees-backlog.md).

**Last reviewed:** 2026-10-26

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
| `/fees` | Desk: balances, stats, record payment, open student fee detail (admin + accountant) |
| `/fees/settings` | Catalogs by term: add/edit items, **Publish**, **Copy from previous**, **Apply** (admin); accountant prepares/publishes next term in the lead window |
| `/fees/:studentId` | Student fee breakdown + payment history |
| Student detail → Fees | Same breakdown/history; nested tabs `?tab=fees&feesTab=breakdown\|history` |
| Accountant dashboard | Fees overview + fee-prep banner (see [dashboard.md](./dashboard.md)) |
| Setup → Fees | First-term catalog during onboarding; completing school setup applies the active term |

### Main APIs

- Desk: `GET /api/v1/fees/`, `/stats/`, `/filter-options/`
- Prep: `GET /api/v1/fees/next-term-prep/` — accountant/admin banner status in the transition lead window
- Structures: `GET /fees/structures/?term=`, items CRUD, `POST /fees/structures/copy-from-previous/`, `POST /fees/structures/:id/publish/`, `POST /fees/structures/:id/apply/`
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

## Preparing the next term (accountant)

From `TRANSITION_LEAD_DAYS` (7) before the current term’s `end_date`, until the next term is opened:

1. Accountant (or admin) opens **Fees → Settings** for the next term (`/fees/settings?term=<next id>`), often via the dashboard / fees **FeePrepNotice**.
2. **Copy from previous** seeds items when the next catalog is missing or empty.
3. Review amounts, then **Publish**. Published means “ready for admin to apply.”
4. Accountant prep is **done** when status is `published` or `applied`. Apply/lock still happens in the admin transition wizard.

Status payload: `fees/services/prep.py` → `GET /fees/next-term-prep/`.

## Opening the next term (admin)

The transition wizard places pupils and then applies the next term’s catalog. Full flow: [term-transition.md](./term-transition.md).

Fees behavior inside that wizard:

- The fees step shows the items that will be billed, and who each one covers.
- If the next term has no catalog, confirm copies the current term’s items, then publishes (if still a draft) and applies.
- If the next term already has a catalog, that catalog is applied, unless it is already applied. Newly placed pupils are then billed from the locked list.
- Class and level fees stay on the class or level they were written for. Movers who no longer match are not billed for that item.
- Apply locks the catalog. Prefer finishing amounts (and publish) in Fees settings before opening the term.
- Arrears stay on the old term. Advances apply when the next catalog is applied, as they do for any apply.
- Past terms stay read-only.

Still not built: an arrears report across terms, writing off arrears, and refunding leftover advance ([fees-backlog.md](./fees-backlog.md)).
