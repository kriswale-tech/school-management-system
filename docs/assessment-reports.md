# Assessment report PDFs & guardian send

How released results become stored report PDFs, how staff generate them in bulk, and how guardians get download links.

Related: [guardian-communications.md](./guardian-communications.md), [subject-assessment-workspace.md](./subject-assessment-workspace.md), [assessment-corrections.md](./assessment-corrections.md).

---

## Concepts

| Concept | Meaning |
| --- | --- |
| **Released** | `StudentResult` released — required before a PDF can be generated |
| **Report generated** | DB `Report` row with a non-empty `file` field (list badge). Download/notify also require the object to **exist on R2** (`_report_file_exists`) |
| **generation_id** | UUID set on each successful PDF **write**. Used for auto-notify idempotency |
| **Generate (force=false)** | If R2 file exists → reuse (no new `generation_id`, no auto re-notify). If missing → create PDF |
| **Regenerate (force=true)** | Always rewrite PDF, new `generation_id`, may auto-notify again |
| **Send to guardians** | Manual report-ready SMS/email with signed public link. New batch UUID each send → **resend OK** without regenerating |

**30-day report links:** `REPORT_LINK_MAX_AGE_SECONDS` expires the **signed URL token**, not the R2 object. The app does not auto-delete PDFs after a month.

---

## Staff UI (Assessment details)

Layout:

1. **Top** — class name, teacher, term, status tabs (shared above list + detail)  
2. **List toolbar** — **Select all released**; **Release all ready** only when there is at least one ready student  
3. **Selection bar** — **Generate reports** (students missing a report) + **Send to guardians** (students with a generated report)  
4. **Progress** — while a bulk job runs, banner polls every **3s** and shows counts; toast on completion refreshes the list  
5. **Detail pane** — release / view report / send / corrections for the focused student  

Checkboxes appear for **all released** students (not only those with reports).

**Report viewer** (`/assessments/classes/:streamId/report/:studentId`): Open in new tab, **Send to guardians**, Regenerate (force).

Capability: `assessments.release`.

---

## Backend models

### `Report`

- Unique `(school, student, stream, term)`  
- `file` (R2), `generated_at`, `generation_id`, `generated_by`  
- Corrections that invalidate scores clear `file` / `generated_at` / `generation_id` (`invalidate_student_report`)

### `ReportGenerateJob`

Tracks bulk PDF work:

- `status`: `pending` → `running` → `completed` / `failed`  
- `force`, `student_ids`, counters `total` / `generated` / `skipped` / `failed`  
- `failures` (truncated list of `{student_id, full_name, reason}`)  
- `finished_at`

Migration: `assessments.0013_report_generation_job`.

---

## APIs

All under `/api/v1/academics/assessments/admin/classes/<stream_id>/…`. Require `assessments.release`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `.../students/<student_id>/report/generate/?force=` | Sync generate; `force=true` regenerates |
| `POST` | `.../reports/generate/` | Queue bulk job → **202** + job payload |
| `GET` | `.../reports/generate/<job_id>/` | Job status for polling |
| `POST` | `.../report-ready/preview/` | Estimate guardian SMS/email |
| `POST` | `.../report-ready/send/` | Queue guardian messages (manual resend) |

Bulk body: `{ "student_ids": ["…"], "term_id": "<uuid?>", "force": false }`.

Student profile generate: `POST /students/<id>/assessments/report/generate/?force=` (same `force` semantics).

Celery task: `assessments.run_report_generate_job` → `process_report_generate_job`.

---

## Generate behaviour

`assessments.services.report_pdf.generate_student_report(..., force=False)`:

1. Build preview payload (must be released)  
2. If not `force` and `_report_file_exists(report)` → return stored report (**no** notify)  
3. Else render WeasyPrint PDF, save to R2, set `generated_at` + new `generation_id`  
4. `on_commit` → `maybe_auto_notify_report_ready` if settings allow  

Bulk worker calls the same helper per student; counts **skipped** when a file already existed and `force` is false.

---

## Guardian notify behaviour

| Mode | Idempotency | Resend |
| --- | --- | --- |
| **Manual** Send to guardians | New `batch_id` (UUID) each request | Yes — same PDF |
| **Auto** on generate | `auto-{report.id}-{generation_id}` | Only after a **new** generation (regenerate or generate after invalidate/missing file) |

Do **not** use Regenerate merely because a guardian “didn’t get” the message — use **Send to guardians** again.

Settings: Report ready enabled + channels; **When to send** = manual | auto.

---

## List badge accuracy

Admin class list `has_report` is derived from DB (`file` non-empty), **not** a live R2 HEAD per student (avoids N storage calls).

- Bulk generate / GET report / notify preview use `_report_file_exists`  
- If R2 object was deleted externally, badge may linger until generate/notify discovers the gap; generate then recreates the file  

---

## Tests

- `assessments.tests.test_bulk_reports` — queue job + process skip-existing  
- `assessments.tests.test_report_ready_notices` — auto mode + per-generation idempotency  

---

## Ops

After deploy: `migrate assessments` (includes `0013_report_generation_job`) and ensure Celery workers load `assessments.tasks`.
