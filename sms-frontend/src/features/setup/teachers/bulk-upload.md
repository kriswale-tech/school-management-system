# Teacher Bulk Import — Frontend Integration

Base path: `/api/v1/schools`

Authentication: same JWT cookie session as the rest of the app (`credentials: 'include'`).

Permissions: admin and staff users who can manage teachers.

Limits:

- Template download: Excel (`.xlsx`) only
- Upload: Excel (`.xlsx`) or CSV (`.csv`)
- Max file size: **5 MB**
- Max rows per file: **1000**

---

## Endpoints

### 1. Download template

`GET /setup/teachers/bulk-upload/template/`

Returns an Excel workbook with:

- **Import** sheet — columns to fill, example row, dropdowns
- **Reference** sheet — valid class/subject/stream/group combinations for the school

Save the response as `teacher-import-template.xlsx`.

---

### 2. Preview import

`POST /setup/teachers/bulk-upload/?dry_run=true`

Body: `multipart/form-data` with field `file`.

Nothing is saved. Response is JSON with per-row validation results.

Block the confirm action when `summary.rows_with_errors > 0`.

Warnings (for example replacing an existing assignment) are allowed.

---

### 3. Confirm import

`POST /setup/teachers/bulk-upload/?dry_run=false`

Body: same `file` field as preview.

Behaviour:

- Partial success — valid rows are saved even if some rows fail
- Existing teacher phone numbers are updated
- Existing assignment slots are replaced
- Extra columns in the file are ignored
- If any rows fail, response includes a temporary failure download URL

---

### 4. Download failed rows

`GET /setup/teachers/bulk-upload/failures/{token}/`

Use the token from `failures.download_url` in the confirm response.

Returns a file in the **same format as the uploaded import** (`.xlsx` or `.csv`).

The file includes original columns plus:

- `row_number`
- `failure_reason`

Files are stored in local media temporarily and expire after **24 hours**.

---

## Recommended UI flow

1. **Download template** from the teachers setup screen.
2. Admin fills the **Import** sheet using dropdowns and the **Reference** sheet.
3. **Preview** — upload the file with `dry_run=true` and show a results table.
4. If there are errors, ask the admin to fix the spreadsheet and preview again.
5. **Confirm** — upload the same file with `dry_run=false`.
6. Show summary counts from the confirm response.
7. If `failures` is present, show a **Download failed rows** action.
8. Refresh the existing teachers list via `GET /setup/teachers/`.

Copy for the screen:

- Preview: “Nothing has been saved yet.”
- Confirm: “Successful rows are saved even when some rows fail.”
- Replace warning: “This will replace the current teacher for that class/subject slot.”
- Failure download: “Fix the rows in this file and upload it again. Extra columns are ignored.”

---

## Spreadsheet columns (backend reads these only)

| Column               | Required       | Notes                                                           |
| -------------------- | -------------- | --------------------------------------------------------------- |
| `first_name`         | Yes            |                                                                 |
| `last_name`          | Yes            |                                                                 |
| `phone_number`       | Yes            | Ghana format: `0XXXXXXXXX` or `+233XXXXXXXXX`                   |
| `email`              | No             |                                                                 |
| `assignment_type`    | No             | `class_teacher` or `teaching`; leave blank for teacher-only row |
| `class_name`         | When assigning | Must match school class name exactly                            |
| `subject_name`       | For `teaching` | Required for teaching assignments                               |
| `stream_name`        | No             | Blank = whole class                                             |
| `subject_group_name` | No             | For grouped subjects only                                       |

Any other column is ignored, including `failure_reason` and `row_number` on re-upload.

---

## TypeScript types

```typescript
export type TeacherAssignmentType = 'class_teacher' | 'teaching'

export type BulkImportFileFormat = 'xlsx' | 'csv'

export type BulkImportRowStatus = 'valid' | 'error' | 'warning'

/** Columns the backend reads from the spreadsheet. */
export interface TeacherBulkImportRow {
  first_name: string
  last_name: string
  phone_number: string
  email?: string
  assignment_type?: TeacherAssignmentType | ''
  class_name?: string
  subject_name?: string
  stream_name?: string
  subject_group_name?: string
}

export interface TeacherBulkImportPreviewSummary {
  rows_total: number
  rows_valid: number
  rows_with_errors: number
  rows_with_warnings: number
  teachers_to_create: number
  teachers_to_update: number
  assignments_to_create: number
  assignments_to_replace: number
}

export interface TeacherBulkImportPreviewRow {
  row_number: number
  status: BulkImportRowStatus
  messages: string[]
  data: Partial<TeacherBulkImportRow>
}

export interface TeacherBulkImportPreviewResponse {
  dry_run: true
  summary: TeacherBulkImportPreviewSummary
  rows: TeacherBulkImportPreviewRow[]
}

export interface TeacherBulkImportConfirmSummary {
  rows_total?: number
  rows_processed: number
  rows_succeeded: number
  rows_failed: number
  teachers_created: number
  teachers_updated: number
  assignments_created: number
  assignments_replaced: number
}

export interface TeacherBulkImportFailuresInfo {
  count: number
  download_url: string
  expires_at: string
  format: BulkImportFileFormat
}

export interface TeacherBulkImportConfirmResponse {
  dry_run: false
  summary: TeacherBulkImportConfirmSummary
  failures: TeacherBulkImportFailuresInfo | null
}

export type TeacherBulkImportResponse =
  | TeacherBulkImportPreviewResponse
  | TeacherBulkImportConfirmResponse

/** Returned in failure export files and safe to re-upload. */
export interface TeacherBulkImportFailedRow extends TeacherBulkImportRow {
  row_number: number
  failure_reason: string
}

export interface ApiValidationError {
  detail?: string
  file?: string[]
  dry_run?: string[]
  [field: string]: string | string[] | undefined
}
```

---

## Example preview response

```json
{
  "dry_run": true,
  "summary": {
    "rows_total": 2,
    "rows_valid": 1,
    "rows_with_errors": 1,
    "rows_with_warnings": 0,
    "teachers_to_create": 1,
    "teachers_to_update": 0,
    "assignments_to_create": 1,
    "assignments_to_replace": 0
  },
  "rows": [
    {
      "row_number": 2,
      "status": "valid",
      "messages": [],
      "data": {
        "first_name": "Ama",
        "last_name": "Boateng",
        "phone_number": "0244567891",
        "assignment_type": "teaching",
        "class_name": "Basic 4",
        "subject_name": "Mathematics"
      }
    },
    {
      "row_number": 3,
      "status": "error",
      "messages": [
        "Subject \"Maths\" not found for class \"Basic 4\". Did you mean \"Mathematics\"?"
      ],
      "data": {
        "first_name": "Bad",
        "last_name": "Row",
        "phone_number": "0244567894",
        "assignment_type": "teaching",
        "class_name": "Basic 4",
        "subject_name": "Maths"
      }
    }
  ]
}
```

---

## Example confirm response

```json
{
  "dry_run": false,
  "summary": {
    "rows_total": 2,
    "rows_processed": 2,
    "rows_succeeded": 1,
    "rows_failed": 1,
    "teachers_created": 1,
    "teachers_updated": 0,
    "assignments_created": 1,
    "assignments_replaced": 0
  },
  "failures": {
    "count": 1,
    "download_url": "/api/v1/schools/setup/teachers/bulk-upload/failures/a1b2c3d4-e5f6-7890-abcd-ef1234567890/",
    "expires_at": "2026-07-28T08:55:00Z",
    "format": "csv"
  }
}
```

When all rows succeed, `failures` is `null`.

---

## Related existing endpoints

| Method | Path                        | Purpose                           |
| ------ | --------------------------- | --------------------------------- |
| `GET`  | `/setup/teachers/`          | Refresh teacher list after import |
| `POST` | `/setup/teachers/complete/` | Advance teachers setup step       |
