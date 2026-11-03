# Student bulk import

Upload many students from an Excel/CSV template (`Students` → bulk upload). Preview with `dry_run=true`, then commit. Guardians and `student_id` are optional; dates are required.

## Student ID

| Value | Behavior |
| --- | --- |
| Blank | Auto-generate using the school prefix (same as single onboard) |
| New ID | Create the student with that school-assigned ID |
| Existing ID | **Skip** the row (no update). Preview shows a warning; commit counts `students_skipped` |

Duplicate `student_id` values inside the same file are rejected.

Optional `student_id` is also available on single-student onboard and editable on student bio.

## Dates

**Preferred entry:** `YYYY-MM-DD` (example: `2015-03-12`).

The downloadable `.xlsx` template formats `date_of_birth` and `admission_date` as **Text**, so Excel should not rewrite typed ISO dates into a locale display like `3/12/2015`.

The importer also accepts:

| Source | Example | Notes |
| --- | --- | --- |
| ISO text | `2015-03-12` | Preferred |
| Excel date cell | native date / datetime | Read as a real date, independent of display format |
| Day-first locale | `12/03/2015`, `12-03-2015` | Treated as `DD/MM/YYYY` |
| Month-first locale | `03/12/2015` | Accepted when day > 12; ambiguous values prefer day-first |
| Excel serial | `42005` | Numeric date serials from some exports |

Ambiguous slash dates such as `03/04/2015` are interpreted as **day/month/year** (3 April), matching common Ghana locale usage. Prefer ISO to avoid ambiguity.

## Guardians

Guardian columns are optional on bulk import (unlike single-student onboard). If any guardian field is present on a row, `guardian_name`, `guardian_phone`, and `guardian_relationship` become required for that row (unless the row is skipped for an existing `student_id`).

Students imported without a guardian show a **Needs guardian** tag on the students list, appear under `/students?missing_guardian=true`, and surface in admin/staff **Needs Attention** plus the navbar alerts bell (Settings → Alerts → Missing guardians).

## After upload

A successful commit clears the selected file in the UI so the same sheet is not re-submitted by accident. Choose another file to continue. Rows with existing `student_id` values are skipped rather than duplicated.

## API

- `GET /students/bulk-upload/template/` — `.xlsx` template
- `POST /students/bulk-upload/?dry_run=true|false` — preview or commit
- Failure export download when some committed rows fail
