# Fees backlog

Deferred fees work. How the live product works: [fees.md](./fees.md).

## Build later

| Item | Notes |
| --- | --- |
| **Arrears report across terms** | Balances stay on the term where they were billed. There is no single report of debtors across every past term. |
| **Advance refund flow** | Credit model supports `refunded` status, but there is no UI/API yet to refund unused advance back to a parent (e.g. withdrawal, overpayment return). Add later: refund action, ledger entry, and indicators. |
| **Pay with no outstanding (pure advance)** | Today you can only record a payment when there is an owing term; excess becomes advance. Recording a payment when fully paid (to top up advance only) is not supported yet. |

## Ops / one-off

| Item | Notes |
| --- | --- |
| **Backfill historical overpayments** | `python manage.py backfill_fee_advances` (optional `--school-id`, `--dry-run`). Creates advance only for *uncovered* excess (skips terms already covered by a live payment advance). Also removes duplicate backfill credits that double-counted existing advances. |

## Done recently

| Item | Notes |
| --- | --- |
| **Payment history Excel export** | `GET /students/:id/payments/export/?scope=all_time\|academic_year\|term` — Download modal on Payment History tab |
| **Staff receipt view / print** | `GET /fees/receipts/:id/` + Payment History modal; Record Fees success → **Print receipt**. On-screen card keeps border/blue accent; print/PDF omits them. School logo beside name/contact. |
| **Record Payment** | Record Fees slider + `POST /fees/payments/` (receipt auto-issued). Waterfall = one payment + term allocations + one receipt; advance only after all owing is cleared. Success panel: print / record another / cancel. |
| **All-time fee desk** | Default `term=all` on `/fees` (lifetime billed/paid on active-term roster). Detail + reminders also support all-time owing summaries. |
| **Advance / excess credit** | Excess payment creates `StudentFeeCredit`. Auto-applied when next term fees are applied. Shown on desk rows, fee detail header, and record form. |
| **Fees Settings** | `/fees/settings` + `/api/v1/fees/structures/`. Term catalogs, item CRUD, Apply (locks). Late enrollments auto-billed from applied catalogs. |
| **Open the next term** | Wizard places pupils, then applies and locks the next catalog. Class and level fees are not retargeted. See [term-transition.md](./term-transition.md). |

## Related current surface

- Desk: `GET /api/v1/fees/`, `/stats/`, `/filter-options/`
- Structures: `GET /fees/structures/?term=`, `POST /fees/structures/items/`, item PATCH/DELETE, `POST /fees/structures/:id/apply/`
- Payments: `POST /api/v1/fees/payments/`, `GET /api/v1/fees/students/:id/payment-target/`, `GET /api/v1/fees/receipts/:id/`
- Student: `GET /students/:id/fees/?term=`, `GET /students/:id/payments/?term=`, `GET /students/:id/payments/export/`
