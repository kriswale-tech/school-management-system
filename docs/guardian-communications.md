# Guardian communications

Outbound **SMS / email to `Parent` contact records** when something happens to their ward.

Distinct from:

| Surface | Audience |
| --- | --- |
| **Alerts** | Staff digests (bell) — nothing emailed/texted |
| **Notifications** | Staff inbox (`SchoolMembership`) + optional Celery email |
| **Guardian communications** | Parent phone/email — no parent login required |

**Status:** infra + **ward enrolled** (onboard + bulk import) + **payment receipt signed link** + **manual + automatic debt reminders** + **report-ready signed links** + **next-term fee schedules** wired. Guardian SMS/email send via **Celery** in batches of **100** (Arkesel multi-recipient + Resend batch API). Settings → Messaging shows balances, a usage breakdown, and history with bulk resend. A send that does not fit the balance warns on the debt-reminder and report-ready previews, sends what fits, and notifies admins and staff. See [2026-11-11.md](./2026-11-11.md).

---

## Locked product decisions

1. **Audience** — school setting `guardian_audience`: `primary` (default) or `all`. Nested under Settings → Parent messages (not a separate “report notify” top field).
2. **Report notify mode** — `report_parent_notify_mode`: `manual` (default, staff send from Assessment details / report viewer) or `auto` (notify when a report PDF is **newly** generated). Lives **inside** the Report ready event card as **When to send**.
3. **Receipts / reports / fee schedules** — signed public links. Live: receipts HTML; reports → R2 PDF; per-student fee schedules HTML (print/save as PDF).
4. **SMS / email credits** — guardian sends are metered against school `CreditAccount` / `CreditLedgerEntry` (1 SMS segment = 1 credit; 1 email = 1 credit). Debit runs after successful provider submit. Platform Admin Messages economics (pricing, provider balances, free/sponsored, P&L) are specified in [platform-admin-billing-architecture-v4.md](./platform-admin-billing-architecture-v4.md) § Part 2 (v4.1) — not yet built. School Settings → Messaging shows balances / top-ups where Phase 4 UI shipped.
5. **SMS body prefix** — all guardian SMS open with `{ARKESEL_SMS_SENDER} [{school_name}]:` and do **not** repeat the school name mid-message.
6. **Report auto-notify idempotency** — once per `report.id` + `generation_id`. Manual **Send to guardians** uses a new batch UUID each click (resend without regenerating). See [assessment-reports.md](./assessment-reports.md).

---

## Settings UI (Parent messages)

Tab order under **Settings**: School profile → Academic year → Classes → Assessments → Fees → Alerts → **Parent messages**.

Section copy:

- Explains school allow ∩ parent preference ∩ phone/email on file (plain language, not set-theory).
- **Default audience** — plain label; short help under the select.
- **Report ready** event — enable + channels; **When to send** nested below (staff vs automatic).
- **Debt reminders** — optional **Send automatically on a schedule** with frequency help under the checkbox (Accra time ~8:00 AM).

Staff email fields (profile / staff form) already note optional notification use. Guardian email fields note optional use for parent messages.

---

## Channel resolution

Effective channels = **school allow ∩ parent preference ∩ available contacts**.

- School: per-event `*_channels` (`sms` | `email` | `both`)
- Parent: `Parent.notify_channel` (`sms` | `email` | `both` | `off`), default `both`
- SMS requires `phone_number`; email requires `email`

---

## Parent message preference

Set per guardian (not in Settings):

| Surface | Field |
| --- | --- |
| Student → Guardians (detail) | Read-only **Parent messages** |
| Add / Edit guardian | Select + help under the field |
| Add student → Guardian Info | Same select; sent on onboard |

Backend: `Parent.notify_channel`. Onboard and link-existing-parent paths accept `notify_channel` and update the parent when provided (`GuardianInputSerializer` + `_resolve_parent`).

---

## Backend

### Settings (`SchoolSettings`)

| Field | Default | Notes |
| --- | --- | --- |
| `guardian_audience` | `primary` | Who gets messages |
| `report_parent_notify_mode` | `manual` | Staff-triggered vs auto on PDF generate |
| `guardian_ward_enrolled_enabled` | `true` | **Wired** |
| `guardian_ward_enrolled_channels` | `both` | |
| `guardian_payment_receipt_enabled` | `false` | **Wired** — opt in under Settings → Parent messages |
| `guardian_payment_receipt_channels` | `both` | |
| `guardian_debt_reminder_enabled` | `false` | **Wired** — manual Fees desk + optional auto |
| `guardian_debt_reminder_channels` | `both` | |
| `guardian_debt_reminder_auto_enabled` | `false` | **Wired** — Celery beat schedule |
| `guardian_debt_reminder_frequency` | `end_of_month` | `end_of_month` (default) · `weekly` · `biweekly` |
| `guardian_report_ready_enabled` | `false` | **Wired** — Assessment details / auto on generate |
| `guardian_report_ready_channels` | `both` | |
| `guardian_next_term_fees_enabled` | `false` | **Wired** — on fee structure apply (+ late enrollment billing) |
| `guardian_next_term_fees_channels` | `both` | |

API: existing `GET/PATCH /schools/settings/`.

### Delivery log (`GuardianDelivery`)

`notifications.GuardianDelivery` — one row per channel attempt:

- `event_type`, `channel`, `status` (`sent` / `failed` / `skipped`)
- `recipient_address`, `body_preview`, `provider_message_id` (Arkesel id)
- `error_message` / `skip_reason` — stored for failures/skips (**no staff UI yet** to browse)
- `idempotency_key` unique — prevents double SMS/email for the same scope+parent+channel

Celery task return values (`sent` / `failed` / `skipped`) count **SMS items in that batch chunk**, not students selected. Preview **Estimated SMS** is the queue estimate; multiple Celery tasks appear when more than 100 SMS are queued.

### Service

`notifications.services.guardians`

- `resolve_channels(...)`
- `notify_guardians_ward_enrolled` / `schedule_ward_enrolled_notice`
- `notify_guardians_payment_receipt` / `schedule_payment_receipt_notice`
- `notify_guardians_debt_reminder` / plan helpers (batch-scoped idempotency)
- `notify_guardians_report_ready` / plan helpers
- Next-term fees plan + enqueue

SMS via `shared.services.arkesel_sms` — Celery chunks of 100; identical bodies share one Arkesel request. Sandbox when `DEBUG`.  
Email via Resend batch API when enabled. Templates under `notifications/email/guardian_*.*`.

Worker tasks: `notifications.deliver_guardian_sms_batch`, `notifications.deliver_guardian_email_batch`.

### SMS body shapes

Prefix: `{sender} [{school_name}]:` (`sender` = `ARKESEL_SMS_SENDER` or `SCHOOLASST`).

| Event | Body after prefix |
| --- | --- |
| Ward enrolled | `{student} has been enrolled ({class}). You are listed as a guardian.` |
| Payment receipt | `Payment of GHS {amount} received for {student}. Receipt {number}: {url}` |
| Debt reminder (term) | `Reminder — {student} has an outstanding balance of GHS {balance} for {term_label}. Please contact the school to pay.` |
| Debt reminder (all-time) | `Reminder — {student} owes GHS {amount} across terms ({summary}). Please contact the school to pay.` |
| Report ready | `{student}'s report for {term_label} is ready. Download: {url}` |
| Next-term fees | `Fees for {student} ({term_label}) total GHS {total}. Details: {url}` |

### Debt reminders (manual + automatic)

**Manual (Fees desk)**

1. Enable **Debt reminders** under Settings → Parent messages  
2. On Fees, select debtors (row checkboxes, or header checkbox = **all matching debtors across pages**)  
3. **Remind parents** → preview modal → queue send (Celery)

API:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/fees/selection-ids/` | All debtor student ids for current filters (select-all) |
| `POST` | `/fees/debt-reminders/preview/` | Estimate without sending |
| `POST` | `/fees/debt-reminders/send/` | Queue SMS/email for selected student ids |

Body: `{ "term_id": "<uuid?>", "student_ids": ["…"] }`. Requires `fees.record_payment`.

**Automatic**

1. Enable **Debt reminders** and **Send automatically on a schedule**  
2. Choose frequency (default **end of each month**; also weekly / biweekly Mondays)  
3. Celery beat ~08:00 UTC (documented in UI as ~8:00 AM Accra time)  
4. Active-term debtors with balance ≥ `fees_alert_threshold`; period-scoped batch ids keep runs idempotent  

Compose service: `celery-beat` (`sms_celery_beat`).

### Report ready

Full staff flow (bulk generate PDFs, badges, **Send to guardians**, auto vs manual idempotency): **[assessment-reports.md](./assessment-reports.md)**.

Summary:

1. Enable **Report ready** + choose **When to send** under Settings → Parent messages  
2. Assessment details: select **released** students → **Generate reports** (Celery job) and/or **Send to guardians**  
3. Report viewer: **Send to guardians** for the open student  
4. Auto mode fires after a **new** PDF write (`generation_id` changes); skipping an existing R2 file does not re-notify  

API (notify):

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/academics/assessments/admin/classes/<stream_id>/report-ready/preview/` | Estimate without sending |
| `POST` | `/academics/assessments/admin/classes/<stream_id>/report-ready/send/` | Queue for selected student ids |

Requires `assessments.release`.

### Public receipt / report / fee schedule links

Unchanged signed-token public URLs — see prior sections in git history or:

- Receipts: `RECEIPT_LINK_MAX_AGE_SECONDS` (default 30 days) — **link** TTL, not R2 object lifecycle  
- Reports: `REPORT_LINK_MAX_AGE_SECONDS` (default 30 days) — same; PDF may still exist on R2 after the link expires  
- Fee schedules: `FEE_SCHEDULE_LINK_MAX_AGE_SECONDS` (default 90 days)

There is **no app job** that deletes report PDFs after 30 days. If R2 lifecycle rules remove objects, download/notify paths treat missing files as “not generated” (`_report_file_exists`).

### Hooks

| Event | Trigger |
| --- | --- |
| Ward enrolled | `onboard_student`; bulk import Celery after commit |
| Payment receipt | `record_student_payment` (when enabled) |
| Debt reminder | Fees desk send, or Celery beat auto |
| Report ready | Manual **Send to guardians**, or auto after new PDF generate |
| Next-term fees | Fee structure apply + late enrollment billing |

Term transition / re-enrollment does **not** re-notify ward enrolled. Dry-run bulk import does not send.

---

## Frontend

- Settings → **Parent messages** — as above  
- Student guardians + onboard guardian step — **Parent messages** preference + email help  
- Fees desk — debtor selection + Remind parents modal  
- Assessment details / report viewer — generate + **Send to guardians** (see [assessment-reports.md](./assessment-reports.md))

---

## Suggested next slices

1. A toast after a debt-reminder or report-ready send that says how many were sent and how many were skipped
2. Bulk resend beyond the latest 100 matching messages

See also [notifications.md](./notifications.md) and [assessment-reports.md](./assessment-reports.md).
