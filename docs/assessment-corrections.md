# Assessment corrections (reject / reopen)

Send-back and reopen for selected subjects, with reasons and an audit trail.

## Goals

- Admin can **reject** (pre-release) or **reopen** (post-release) with subject selection + reason.
- Class teacher can **reject** before release, or **request reopen** after release (admin approves/declines).
- Only selected **teaching assignments** are unpublished.
- Released reopen **deletes the stored report PDF** immediately.
- Roles see banners/chips when corrections are open or applied.
- Every step is logged on `CorrectionRequest` + `CorrectionRequestEvent`.

## Status model

`StudentResult.status` includes:

| Status | Meaning |
|--------|---------|
| `awaiting_approval` | Rarely stored; UI often derives this |
| `approved` | Class teacher approved |
| `released` | Admin released |
| `needs_correction` | Subjects sent back; waiting for fix + re-approve |

Class-teacher UI still folds `released` into the **Approved** pill, and exposes `is_released` for reopen actions.

Admin detail also shows `needs_correction` students (and open reopen requests).

## CorrectionRequest

| Field | Notes |
|-------|--------|
| `kind` | `reject` \| `reopen` \| `reopen_request` |
| `status` | `open` \| `declined` \| `applied` \| `resolved` |
| `reason` | Required text |
| `subjects` | `CorrectionRequestSubject` rows (`teaching_assignment` + `subject_label` snapshot) |
| `previous_result_status` | Status before apply |
| actors / timestamps | `raised_*`, `reviewed_*`, `applied_at`, `resolved_at` |

### Events (append-only)

`CorrectionRequestEvent.event_type` examples:

- `raised`
- `approved` / `declined` (reopen requests)
- `applied` (subjects unpublished, result → `needs_correction`, optional `pdf_deleted`)
- `pdf_deleted`
- `resolved` (after class teacher re-approves)

## Flows

### Reject (not released)

1. Admin or class teacher selects published subjects + reason.
2. Creates request (`reject`), applies immediately → `applied`.
3. Unpublishes those subjects; `StudentResult` → `needs_correction`.
4. Subject teacher sees **Needs correction** on the markbook (with reason tooltip).
5. After republish + class teacher approve → request `resolved`.

### Reopen (released, admin)

Same as reject, but `kind=reopen` and PDF is deleted from R2 / cleared on `Report`.

### Reopen request (released, class teacher)

1. Class teacher submits `reopen_request` (`open`); student stays released until admin acts.
2. Admin **Approve reopen** → apply (unpublish + `needs_correction` + delete PDF).
3. Admin **Decline** → `declined`.

Only one `open` request per student/stream/term at a time.

## APIs

| Method | Path | Cap |
|--------|------|-----|
| POST | `/academics/assessments/admin/classes/:streamId/students/:studentId/correction/` | `assessments.release` |
| POST | `/academics/assessments/admin/classes/:streamId/corrections/:correctionId/review/` | `assessments.release` |
| POST | `/academics/assessments/class-teachers/:id/students/:studentId/reject/` | `assessments.approve` |
| POST | `/academics/assessments/class-teachers/:id/students/:studentId/request-reopen/` | `assessments.approve` |

Body for correction actions:

```json
{
  "teaching_assignment_ids": ["…"],
  "reason": "Maths exam mark mistyped"
}
```

Review body: `{ "approve": true }`

Detail payloads include `active_correction` on each student when status is `open` or `applied`.

## UI indicators

- **Admin assessments list:** **Reopen requests** pill opens a modal (`corrections_inbox` — open `reopen_request` items from class teachers).
- **Class teacher assessments list:** **Corrections** pill opens a modal (`corrections_inbox` — open + applied items for their classes).
- **Admin / class teacher detail:** Needs correction status pill; orange banner; Approve/Decline; Send back / Reopen / Request reopen.
- **Subject teacher markbook:** **All** / **Needs correction** pills above the table; reason shown under the student name.
- **Classes → Subject Teaching:** **Corrections** pill opens a modal; cards show a needs-correction badge when count > 0. Tab persisted via `?tab=managed` or `?tab=subject`.

## Unpublish lock

Subject teachers cannot unpublish once the student is **approved** or **released**. Corrections must go through this flow.

## Related files

- `sms-backend/assessments/models.py` — `CorrectionRequest*`, `StudentResult.NEEDS_CORRECTION`
- `sms-backend/assessments/services/corrections.py`
- `sms-frontend/src/features/assessments/components/CorrectionModal.tsx`
- `AdminAssessmentDetail.tsx`, `AssessmentDetail.tsx`, `SubjectAssessmentWorkspace.tsx`
