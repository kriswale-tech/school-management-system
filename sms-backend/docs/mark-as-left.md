# Mark student as left

Admins and class teachers can record that a student has left the school before
graduation. This powers honest retention reporting and keeps inactive students
out of enrollments and term transition.

## Who can do what

| Action | Admin | Class teacher | Subject teacher |
|--------|-------|---------------|-----------------|
| Mark as left | Any student in the school | Only students in their active-term class | No |
| Reactivate | Yes | No | No |

Capabilities:

- `students.mark_left` — school-wide pack + class teachers
- `students.reactivate` — school-wide pack only (enforced again as admin-only in the service)

## Leave reasons

- `dropout` — Dropped out
- `transfer` — Transferred
- `other` — Other (use notes)

Optional `notes` are stored on the student and summarized in the activity feed.

## Data model (`Student`)

- `is_active=False` when left
- `left_at`, `leave_reason`, `leave_notes`, `left_by`
- Graduated students cannot be marked left (clear graduation first if needed)
- Inactive students cannot be enrolled until reactivated
- Term transition already skips `is_active=False` students

## APIs

- `POST /api/v1/students/<id>/mark-left/` — body `{ reason, notes? }`
- `POST /api/v1/students/<id>/reactivate/` — admin only

Both return the updated student detail payload (includes leave fields).

## Activity feed

- `student_left` — when marked left (includes reason; stream set from active enrollment when present)
- `student_reactivated` — when an admin restores the student

## UI

Student Bio tab:

- **Mark as left** (capability-gated) opens a reason modal
- **Reactivate** for admins when the student is inactive
- Status shows `Left · <reason>` with left date / actor / notes when relevant
