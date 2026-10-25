# Reports & Insights

School analytics surface for admins (school-wide) and teachers (scoped to their
classes / subjects). Global filters: **Term** + optional **Compare term**.

Capability: `nav.reports` + `reports.view`.

Frontend: `sms-frontend/src/features/reports/`.  
Backend: `sms-backend/reports/` (`/api/v1/reports/`).

## Role-aware UI

| Role | Tabs |
|------|------|
| Admin / school-wide | Overview · Finance · Academic · Enrollment · Teachers |
| Teacher (scoped) | **My classes** (if class teacher) · **My subjects** (if subject teacher) · Academic |

Teachers do **not** see Overview, Finance, Enrollment, or Teachers. Tabs appear only
for roles they hold (both if they are class + subject teacher).

**My classes / My subjects** use a single selected assignment (Class / Subject
filters), not a stack of cards:

- KPI strip (average, pass rate, pass mark, count)
- Grade pie for the selection
- Subject tab also shows a term-trend line when history exists
- **Score curve** (subject tab) — distribution of published totals
- Full-width student table (links to Performance)

Chart preference: **line** / **area** and **pie** for distributions/trends; bars kept
where ranking/composition needs them (class comparison, teaching load, workflow).

## Tabs

### Overview
Landing KPIs and cross-cutting signals:

- School (or scoped) average / pass rate (published scores), with compare-term deltas
- Assessment workflow completion (pending → ready → released) — school-wide only
- **Fees × academic risk** — debtors below the pass mark (school-wide only)

Overview also returns **structure counts** used by Academic (classes, distinct
subjects, subject–class slots, teaching assignments, unassigned subject slots).

### My classes / My subjects (teachers)
`GET /reports/teacher-desk/`:

- **My classes** — filter by class; overall grade pie + full student table
- **My subjects** — filter by class (optional) + subject; grade pie, term trend,
  **score curve**, full student table

#### Score curve (subject desk)

X = score (0–100 in 5-mark bands), Y = number of students in that band.

- Built client-side from published student totals for the selected subject
- Smooth area curve; hover shows band + count
- Dashed reference line at the pass mark

Student names deep-link to `/students/:id?tab=Performance`.

### Finance (school-wide)
Built from fee desk data:

- Collected / outstanding / collection rate / debtor count
- Outstanding by class
- Top debtors

### Academic
Performance deep-dive (published scores only; already scope-filtered for teachers):

- **Summary strip** (from overview structure fields):
  - Classes
  - Distinct subjects (unique subject names)
  - Subject–class slots (`ClassSubject` offerings on classes)
  - Teaching assignments (filled subject×class teacher slots this term)
- Class comparison (optional level filter; curriculum order)
- **Subject heat map** — **level required** (defaults to first level); optional class
- **Grade distribution** — pie chart; class required (defaults to first class)
- Students to watch (top / at-risk) with optional class filter → Performance tab

### Enrollment
Retention-style change vs the previous term:

| Bucket | Meaning |
|--------|---------|
| Retained | Enrolled in previous and current term |
| New | `is_new_student` on current term |
| Graduated | Expected exit (`is_graduated`) |
| Marked left | `is_active=False` with leave reason (see `mark-as-left.md`) |
| Not re-enrolled | In previous, not current, not graduated, not marked left |

Also: headcount by class, left-by-reason breakdown.

### Teachers
Per-teacher load for the selected term (`GET /reports/staff-capacity/`):

- KPIs: teachers / class teachers / subject teachers / classes missing a class teacher
- Teaching-load bar chart (assignments per teacher)
- Per-teacher table: role, classes led (+ students), subjects taught, assignment
  count, classes taught in
- Teacher names link to `/staff/:id`

#### How counts are defined

| Field | Meaning |
|-------|---------|
| **Class teacher of** | Number of `ClassTeacher` rows for that teacher this term (homeroom / form classes) |
| **Subjects** | Distinct subject **names** they teach |
| **Assignments** | Number of `TeachingAssignment` rows — each is one **subject × class** teaching slot |
| **Teaches in** | Distinct classes/streams those teaching slots cover |

Example: Math in JHS 1A + Math in JHS 2A + English in JHS 1A → **3 assignments**,
**2 subjects**, **2 classes taught in**.

High totals usually mean demo/bulk data assigned one person to many slots — the
API counts rows, not “hours”.

## Classes page note

On `/classes`, **Total Subjects** is `total_class_subjects`: subject–class
offerings (`ClassSubject` / group rows on each class), **not** unique subject
names. The stats card describes this under the value. Unassigned subjects are
slots still without a teacher.

## Student Performance tab

On student detail (`/students/:id?tab=Performance`):

- Overall average line across enrolled terms
- Multi-subject line chart across terms
- Per-term grade pie + subject score list

API: `GET /api/v1/students/<id>/performance/`

## APIs (`/api/v1/reports/`)

| Path | Purpose |
|------|---------|
| `filters/` | Terms, levels, class levels |
| `overview/` | Academic KPIs + compare + structure counts |
| `teacher-desk/` | Class/subject teacher desk |
| `by-class/` | Class averages |
| `by-subject/` | Subject averages |
| `grade-distribution/` | Grade / score-band pie for a class |
| `subject-heatmap/` | Requires `level_id` |
| `student-trends/` | Top / at-risk |
| `workflow/` | Assessment workflow |
| `fees-academic-risk/` | Cross insight |
| `finance/` | Fee health |
| `enrollment/` | Retention proxy |
| `staff-capacity/` | Per-teacher load insights |

## Explicitly deferred (no data yet)

- Fee collection “velocity” (week-by-week chase)
- Admission / marketing hotspots
- Teacher attendance × performance
- Family / customer lifetime value
- Typed attrition beyond mark-as-left + graduation
- AI natural-language charting

## Related

- `docs/mark-as-left.md` — leave workflow used by Enrollment “marked left”
- `docs/FEATURES.md` — product status row for Reports & Insights
