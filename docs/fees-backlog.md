# Fees backlog

Deferred fees work. How the live product works: [fees.md](./fees.md).

## Build later

| Item | Notes |
| --- | --- |
| **Payment history Excel export** | Download modal UI exists on student fees → Payment History. Scope filters: All time, Academic year, Term. Generate `.xlsx` and wire the Download Excel button. |
| **Receipt view / PDF** | Payment history receipt column shows an eye when a receipt exists (UI-only for now). Add receipt detail view and/or PDF download. |
| **End of term flow** | Guided close: activate next term, roll/promote enrollments, apply next fee catalog, carry arrears/advances. Spec in [fees.md](./fees.md#end-of-term-flow-planned--not-built). |
| **Advance refund flow** | Credit model supports `refunded` status, but there is no UI/API yet to refund unused advance back to a parent (e.g. withdrawal, overpayment return). Add later: refund action, ledger entry, and indicators. |
| **Pay with no outstanding (pure advance)** | Today you can only record a payment when there is an owing term; excess becomes advance. Recording a payment when fully paid (to top up advance only) is not supported yet. |

## Ops / one-off

| Item | Notes |
| --- | --- |
| **Backfill historical overpayments** | `python manage.py backfill_fee_advances` (optional `--school-id`, `--dry-run`). Creates advance only for *uncovered* excess (skips terms already covered by a live payment advance). Also removes duplicate backfill credits that double-counted existing advances. |

## Done recently

| Item | Notes |
| --- | --- |
| **Record Payment** | Record Fees slider + `POST /fees/payments/` (receipt auto-issued) |
| **Advance / excess credit** | Excess payment creates `StudentFeeCredit`. Auto-applied when next term fees are applied. Shown on desk rows, fee detail header, and record form. |
| **Fees Settings** | `/fees/settings` + `/api/v1/fees/structures/`. Term catalogs, item CRUD, Apply (locks). Late enrollments auto-billed from applied catalogs. |

## Related current surface

- Desk: `GET /api/v1/fees/`, `/stats/`, `/filter-options/`
- Structures: `GET /fees/structures/?term=`, `POST /fees/structures/items/`, item PATCH/DELETE, `POST /fees/structures/:id/apply/`
- Payments: `POST /api/v1/fees/payments/`, `GET /api/v1/fees/students/:id/payment-target/`
- Student: `GET /students/:id/fees/?term=`, `GET /students/:id/payments/?term=`
