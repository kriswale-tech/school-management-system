# Guardian communications

Outbound **SMS / email to `Parent` contact records** when something happens to their ward.

Distinct from:

| Surface | Audience |
| --- | --- |
| **Alerts** | Staff digests (bell) — nothing emailed/texted |
| **Notifications** | Staff inbox (`SchoolMembership`) + optional Celery email |
| **Guardian communications** | Parent phone/email — no parent login required |

**Status:** infra + **ward enrolled** (onboard + bulk import) + **payment receipt signed link** + **manual + automatic debt reminders** + **report-ready signed links** + **next-term fee schedules** wired. Guardian SMS/email send via **Celery** in batches of **100** (Arkesel multi-recipient + Resend batch API). SMS credits UI (per school in this app + platform admin elsewhere) is next.

---

## Locked product decisions

1. **Audience** — school setting `guardian_audience`: `primary` (default) or `all`.
2. **Report notify mode** — `report_parent_notify_mode`: `manual` (default, staff send from Assessment details) or `auto` (notify when a report PDF is generated).
3. **Receipts / reports / fee schedules** — signed public links. Live: receipts HTML; reports → R2 PDF; per-student fee schedules HTML (print/save as PDF).
4. **SMS credits** — every send is logged on `GuardianDelivery` for later billing; Settings shows a **Credits — coming soon** placeholder. Per-school credit UI will live in this app; a separate platform admin will also control billing across schools.

---

## Channel resolution

Effective channels = **school allow ∩ parent preference ∩ available contacts**.

- School: per-event `*_channels` (`sms` | `email` | `both`)
- Parent: `Parent.notify_channel` (`sms` | `email` | `both` | `off`), default `both`
- SMS requires `phone_number`; email requires `email`

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

### Parent prefs

`Parent.notify_channel` — editable on guardian create/update APIs and in the student guardians UI.

### Delivery log (`GuardianDelivery`)

`notifications.GuardianDelivery` — one row per channel attempt:

- `event_type`, `channel`, `status` (`sent` / `failed` / `skipped`)
- `recipient_address`, `body_preview`, `provider_message_id` (Arkesel id)
- `idempotency_key` unique — prevents double SMS/email for the same student+parent+event+channel

### Service

`notifications.services.guardians`

- `resolve_channels(...)`
- `notify_guardians_ward_enrolled(student=..., class_name=...)`
- `schedule_ward_enrolled_notice(student_id=..., class_name=...)` — after `transaction.on_commit`
- `notify_guardians_payment_receipt(...)` / `schedule_payment_receipt_notice(...)`
- `notify_guardians_debt_reminder(...)` (batch-scoped idempotency)
- `notify_guardians_report_ready(...)` (batch-scoped; includes signed report URL)
- `plan_guardians_next_term_fees(...)` / structure-apply Celery task (per-student items + signed schedule URL)

SMS via `shared.services.arkesel_sms` — Celery chunks of 100; identical bodies share one Arkesel request (`recipients` array). Sandbox when `DEBUG`.  
Email via Resend **batch** API (`POST /emails/batch`, ≤100) when `EMAIL_ENABLED` + `RESEND_API_KEY`; otherwise Django/console/locmem fallback. Templates under `notifications/email/guardian_*.*`.

Worker tasks: `notifications.deliver_guardian_sms_batch`, `notifications.deliver_guardian_email_batch`. HTTP APIs only plan + enqueue (no provider wait).

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

Body: `{ "term_id": "<uuid?>", "student_ids": ["…"] }`. Server re-checks school, outstanding balance, settings, and parent channels. Requires `fees.record_payment`.

**Automatic**

1. Enable **Debt reminders** and **Send automatically on a schedule**  
2. Choose frequency (system default **end of each month**; also weekly / every 2 weeks on Mondays)  
3. Celery beat runs daily ~08:00 (`fees.run_auto_debt_reminders`); schools only enqueue when their frequency says today is due  
4. Active-term debtors with balance ≥ `fees_alert_threshold` are queued; period-scoped batch ids keep runs idempotent  

Compose service: `celery-beat` (`sms_celery_beat`).

### Report ready (Assessment details)

1. Enable **Report ready** under Settings → Parent messages  
2. Choose **Report notify mode**: staff triggered (default) or automatic when a PDF is generated  
3. On Assessment details, select released students that already have a generated report  
4. **Notify parents** → preview → queue signed download links (Celery)

Eligible only when results are **released** and a report PDF exists. Auto mode enqueues the same path after `generate_student_report` commits.

API:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/academics/assessments/admin/classes/<stream_id>/report-ready/preview/` | Estimate without sending |
| `POST` | `/academics/assessments/admin/classes/<stream_id>/report-ready/send/` | Queue for selected student ids |

Body: `{ "term_id": "<uuid?>", "student_ids": ["…"] }`. Requires `assessments.release`.

### Public receipt link

- Token: Django `signing.dumps` (`fees.services.receipts`), max age `RECEIPT_LINK_MAX_AGE_SECONDS` (default 30 days)
- URL: `{PUBLIC_BASE_URL}/api/v1/public/receipts/<token>/` (no auth)
- Page: printable HTML (`fees/templates/fees/public/receipt.html`) with Print / save as PDF
- Env: `PUBLIC_BASE_URL` (default `http://localhost:9000`), see `.env.example`

### Public report link

- Token: Django `signing.dumps` (`assessments.services.report_links`), max age `REPORT_LINK_MAX_AGE_SECONDS` (default 30 days)
- URL: `{PUBLIC_BASE_URL}/api/v1/public/reports/<token>/` (no auth)
- Behaviour: validates token → redirects to a fresh R2/presigned PDF URL
- Env: `PUBLIC_BASE_URL`, `REPORT_LINK_MAX_AGE_SECONDS`

### Public fee schedule link

- Token: Django `signing.dumps` (`fees.services.fee_schedule_links`) for `{student_id, term_id}`, max age `FEE_SCHEDULE_LINK_MAX_AGE_SECONDS` (default 90 days)
- URL: `{PUBLIC_BASE_URL}/api/v1/public/fee-schedules/<token>/` (no auth)
- Page: printable HTML listing **that student’s** `StudentFee` rows (itemised from fee items) + total
- Trigger: fee structure **apply** (Celery `fees.notify_fee_structure_applied`) and late `ensure_enrollment_fees` (idempotent per student/term)

### Hooks

| Event | Trigger |
| --- | --- |
| Ward enrolled | `students.services.onboard_student`; bulk import via Celery `students.notify_bulk_ward_enrolled` after commit |
| Payment receipt | `fees.services.payments.record_student_payment` (when setting enabled) |
| Debt reminder | Manual Fees desk send, or Celery beat auto schedule |
| Report ready | Manual Assessment details send, or auto after report PDF generate when mode=`auto` |
| Next-term fees | Fee structure apply + late enrollment billing (when setting enabled) |

Term transition / re-enrollment does **not** re-notify ward enrolled. Dry-run bulk import does not send.

---

## Frontend

- Settings → **Parent messages** — audience, report mode, per-event toggles/channels, SMS credits placeholder
- Student guardians — show/edit **Parent messages** preference (`EditGuardianForm` / `AddGuardianForm`)
- Fees desk — debtor selection (select-all across pages) + Remind parents modal  
- Assessment details — selection for released+report students + Notify parents modal

---

## Suggested next slices

1. SMS credits ledger UI (per school here; platform admin in a separate app)

See also [notifications.md](./notifications.md).
