# Subject Detail — assessment workspace

Product reference for the subject teacher’s markbook on **Subject Detail** (`/classes/subjects/:assignmentId`).

Runtime markbook APIs live under `/academics/teaching-assignments/<id>/workspace|ca-items|marks|publish|unpublish/`. Class overview: `/academics/assessments/my-classes/`. Approve API exists; select-students approve UI is next.

**Related:** [HOW_IT_WORKS.md](./HOW_IT_WORKS.md) (teacher access), assessment setup (level weights + grade bands), [subject-groups-backlog.md](./subject-groups-backlog.md).

---

## Page layout

1. **ActionBar** — title, back. No Assign students here (search deferred).
2. **Stats cards** — class name, stream (if any), total students, subject name.
3. **White panel**
   - Header row (`justify-between`): **Button tabs** (Workspace | Students) + mode actions on the right.
   - **Workspace** (default) — spreadsheet-like mark sheet (non-paginated, scroll all students).
   - **Students** — roster table (name/ID, date admitted, actions) + **Assign students** for grouped subjects only.

Grouped-subject unassigned banner can stay above the tabs or on the Students tab; Assign students CTA belongs on **Students** only.

---

## Workspace — view mode

Columns:

| Student (name + ID beneath) | Class score | Exam | Total | Grade | Status |

- **Record assessment** (right of tabs) enters record mode.
- Status (product): **Incomplete** | **Complete** | **Published**.  
  UI may still show **Ready** for Complete until renamed — same meaning (full subject result, not yet published).

---

## Workspace — record mode

- **Class score** expands into one editable column per **CA item** (homework, test, midterm, …).
- **Exam** remains a single editable column (max always **100**).
- **Total** updates live from weights while typing.
- **Grade** and **Status** columns are hidden in record mode.
- Footer (or panel) **Save** persists marks; backend recalculates class score, total, grade, status.
- Primary action becomes **Add class assessment** (CA item): modal with **name** + **max marks**.
- Teachers may **edit** CA item name / max (with rules below) and **delete** an item only if no student has a mark for it.

Save rules:

- Save is **per student**. Only students with every **CA** cell filled are saved; empty rows are left alone.
- A student with some CA marks filled and others blank is skipped until that row is complete.
- **Exam may be empty** until the exam is taken.
- When exam is entered, mark must be `0 … 100`. CA marks must be `0 … max` for that item.

---

## Who can do what (subject side)

| Action | Who |
| --- | --- |
| View workspace / students | Subject teacher for this assignment (and broader roles later) |
| Record marks, add/edit/delete CA items | **Assigned subject teacher** only (`assessments.record`) |
| Assign / unassign group students | Subject teacher; **Students tab only** |

Subject-only teachers do **not** get Assessments nav; this page is their markbook entry.

---

## CA item scope

CA items belong to the **teaching context for the term**, not a school-wide shared list.

| Context | Scope |
| --- | --- |
| Non-grouped subject | Items for that class/stream + subject + **term** (the teaching assignment). |
| Subject groups (e.g. Twi / Ga) | **Separate** item sets per group. Each group is its own teaching context with its own teacher and assessments. |

Every new term, teachers create new CA items for that term.  
Only the **assigned teacher** for that subject (assignment) can create CA items.

---

## Scoring (locked)

School setup (per level) defines:

- `continuous_assessment_weight` + `exam_weight` = 100 (e.g. 40 / 60)
- Grade bands / result type when grades are used

### Class score

1. For each CA item with a recorded mark: `%_i = (mark_i / max_i) × 100`
2. `avg_ca% = mean(%_i)` over those items (equal weight per item after converting to %)
3. `class_score = avg_ca% × (continuous_assessment_weight / 100)`

So marks are averaged as percentages, then scaled to the CA weight (e.g. 40%).

### Exam

- Max marks always **100**
- `exam_contrib = (exam_mark / 100) × exam_weight`

### Total and grade

- `total = class_score + exam_contrib`
- Grade from configured bands when result type includes grades

### Incomplete vs Complete vs Published (subject)

- **Complete** when **class score**, **exam**, and **total** are all available (computable).
- Complete is **not** defined as “every CA item that might ever exist.”
- Class score **depends on CA item marks**; without CA data there is no class score → **Incomplete**.
- **Published** = subject teacher has released this student’s subject result to the class teacher (lock applies — see below).
- Incomplete otherwise (including Complete before publish).

---

## CA item edit / delete rules

| Action | Allowed when | Notes |
| --- | --- | --- |
| Edit **name** | Anytime in draft/record (pre-publish) | No score change |
| Edit **max marks** | If no scores yet, **or** all existing marks still `≤ new max` | Recompute % / class scores; **block** edit if any mark would exceed new max |
| **Delete** item | **No student** has a mark for that item | Once any mark exists, delete is blocked |

---

## End-to-end status model (locked)

Two lenses on the same student — **do not reuse the same label for both**.

### Subject teacher (per subject / teaching assignment)

| Status | Meaning |
| --- | --- |
| **Incomplete** | Class score and/or exam not complete for this subject. |
| **Complete** | Full subject result (class score + exam + total); not released yet. |
| **Published** | Released to the class teacher. Marks are locked for normal editing. |

### Class teacher (across that student’s subjects for the term)

| Status | Meaning |
| --- | --- |
| **Pending** | At least one required subject is not **Published** yet (or has no teacher — see enforcement). |
| **Awaiting approval** | Every required subject is **Published**; class teacher has not approved yet. |
| **Approved** | Class teacher reviewed (remarks optional) and sent the student to **admin**. |

### Admin (school-wide, per student in a class)

| Status | Meaning |
| --- | --- |
| **With class teacher** | Not yet approved by the class teacher (Pending or Awaiting approval). Admin cannot release yet. |
| **Ready for you** | Class teacher **Approved** this student. Admin can release (one student or the whole class). |
| **Released** | Admin released the result. Corrections later. |

Headline stats count **students**. A class is fully ready only when every student in it is Ready for you. Admin list: `/assessments` when the user has `assessments.release` (school operators). Class teachers keep the existing My classes list.

**Required subjects** = active class subjects for that student in the active term, including the subject group they are placed in when the subject is grouped. Ideal: every such subject has an assigned teacher.

```
Subject: Incomplete → Complete → Published (lock)
                ↓ all required subjects Published
Class:   Pending → Awaiting approval → Approved
                ↓
Admin:   With class teacher → Ready for you → Released
```

---

## Publish / approve / edit-after-publish

### Happy path

1. Subject teacher records marks → **Complete** → **Publish** (per student or batch — product UI TBD).
2. When all of a student’s required subjects are Published → class status **Awaiting approval**.
3. Class teacher may **approve selected students** who are Awaiting approval (partial approve is allowed). Others stay Pending until ready.
4. **Approved** → admin queue (**Ready for you**). Admin **Release** is one student or the whole class (detail later).

### Lock (v1)

- Once a subject result is **Published**, normal Record / save for that student on that subject is **blocked**.
- Protects class-teacher approval from silent invalidation.

### Unpublish (simpler v1 — build with publish)

- Subject teacher may **Unpublish** (recall) a student/subject **only if** that student’s class status is **not Approved**.
- After unpublish: subject status returns to **Complete**; student may fall back to class **Pending**; edits allowed again; must **Publish** again.
- If the student is already **Approved** (or admin-finalized later): **no unpublish** in v1.

### Correction request (later — not v1)

- For Approved / finalized students: subject teacher opens a correction request → class teacher and/or admin accept → unlock → edit → re-publish → class teacher re-approves.
- Optional later: class teacher **Send back** (reject) to force unpublish / Pending.

### Teacher assignment enforcement

Ideal: every subject has a teacher; every class has a class teacher.

| Strength | Behaviour |
| --- | --- |
| **Soft (recommended first)** | Surfaces on Assessments / publish UI: unassigned subjects block leaving Pending; warnings if no class teacher. |
| **Hard at approve** | Class teacher cannot **Approve** a student while any required subject lacks a teacher or isn’t Published. |
| **Hard at term (optional)** | Checklist before marking period: all class subjects have teachers. |

Do **not** hard-block enrollment/timetable solely because a teacher is missing mid-term.

**Shipped:** publish / unpublish (v1 lock), subject statuses Incomplete / Complete / Published, class overview counts. Class-teacher approve-selected UI and correction requests remain later.

---

## Checklist (product)

- [x] Subject Detail: stats + Workspace / Students tabs
- [x] Assign students only on Students tab (grouped)
- [x] Workspace view mode columns + Record mode expand CA + exam
- [x] Add / edit / delete CA items (rules above) — UI + API
- [x] Live total in record mode; save validation (no blanks for CA) — UI + API
- [x] Persist + compute class score / exam / total / grade / Ready (API)
- [x] Subject status label: rename UI **Ready** → **Complete**; implement **Published** + lock
- [x] Publish / Unpublish (v1 rules above)
- [x] Class aggregation: Pending / Awaiting approval / Approved counts (approve-selected UI later)
- [x] Class-teacher Assessment detail (split roster + subject report; approve + bulk approve)
- [ ] Soft (then hard) teacher-assignment blockers
- [x] Position ranking on class assessment detail
- [ ] Correction request after Approved (later)
- [x] Admin assessments list (stats include unfinished students; table is ready/released classes only, with a class completeness badge)
- [x] Admin assessment detail (release one or all ready; head teacher remarks; report button placeholder)
- [x] Class-teacher Assessments nav page UI (My classes table; live counts)

---

## Class-teacher Assessments page (`/assessments`)

UI for class teachers (requires `nav.assessments`). Subject-only teachers do not see this nav item.

### Layout

1. **ActionBar** — title + search (classes)
2. **Stats cards** — Pending / Awaiting approval / Approved (UI may still label the middle card **Ready** until renamed)
3. **My classes** panel — side stats (class count + student count) + table

### Table columns

Class | Students | Pending | Awaiting approval (UI: Ready) | Approved | View class  

Column accents: Pending **amber**, Awaiting approval **blue**, Approved **green**.

### Counts

Per-class cells = **number of students** in each bucket. Page stats sum those buckets (once aggregation is wired). Class teacher can approve students in **Awaiting approval** without waiting for the whole class.

### Assessment detail (`/assessments/:classTeacherId`)

Split layout:

- **Left:** class name, **Approve all awaiting**, pill filters with counts (All / Pending / Awaiting approval / Approved), student cards (name, status; Pending shows `n/m subjects published`).
- **Right:** selected student subject table … Overall position … Then optional **Conduct**, **Attitude**, **Interest**, then Class-teacher remarks + **Approve** when status is Awaiting approval.
- Bulk approve modal: shared remarks only (conduct / attitude / interest stay empty unless set per student).

API: `GET /academics/assessments/class-teachers/:id/`, `POST …/approve/`.

Class teacher name sits on the **right** of the remarks field.

### Admin assessment detail (`/assessments/classes/:streamId`)

Same split layout, admin statuses:

- **Left:** class name, **Release all ready**, pills (All / Ready for you / Released). Students still with the class teacher are a count only — they are not listed, so the admin never sees incomplete dashes.
- **Right:** same subject table. Class teacher remarks are read-only (name on the right). Head teacher remarks can be typed when the student is Ready for you (label on the right is **Head teacher** until a head-teacher person exists). **Release** saves those remarks. After release, **Generate report** opens the report page: if no PDF exists yet it is generated, uploaded to R2, and embedded; later visits load the stored PDF (Regenerate overwrites).
- **Corrections:** Admin can send back / reopen selected subjects with a reason; class teacher can reject or request reopen. See [assessment-corrections.md](./assessment-corrections.md).

Report layout: school header + logo, student box (next term begins when known, no. on roll = class size, position when used), subject table with **TOTAL** row, blank attendance dotted lines, conduct/attitude/interest, remarks, signatures, then grades interpretation.

API:
- `GET …/students/:studentId/report/` — stored PDF metadata + signed URL (404 if missing in DB **or** on R2; client auto-generates)
- `POST …/students/:studentId/report/generate/` — generate/overwrite PDF on R2
- `GET …/students/:studentId/report/preview/` — JSON payload (HTML/debug)
- also `GET /academics/assessments/admin/classes/:streamId/?term_id=`, `POST …/release/`

Report page actions: **Open in new tab** + **Share** when ready; **Regenerate** only if load/generate fails.
