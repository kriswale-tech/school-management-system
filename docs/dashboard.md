# Dashboard and activity feed

How the home screen works for admins and teachers, and which school events are recorded.

**Last reviewed:** 2026-09-30

---

## Who sees which dashboard

The home route (`/` and `/dashboard`) picks a page from the active membership role.

| Role | Page |
| --- | --- |
| Admin | Admin dashboard only. Teaching assignments on an admin do not add teacher sections. |
| Teacher | Teacher dashboard for this term’s class-teacher and subject-teacher assignments. |
| Staff, accountant | Short placeholder. Those roles do not have day-to-day work in the app yet. |

Class teacher and subject teacher are term assignments (`ClassTeacher`, `TeachingAssignment`), not separate roles. One teacher can hold both, and then sees both sections on the same page.

There is no attendance, timetable, or announcements data, so neither dashboard invents those widgets.

---

## Admin dashboard

`GET /api/v1/dashboard/admin/` — admin only, active term.

The page uses `public/images/dashboard-banner.png` full-bleed against the main view. Overview cards sit half on the banner. Cards are square, capped in height, and scroll when the list is long. Rows that navigate use a pointer and a light hover.

### Overview cards

- **School Overview** — students, classes, staff.
- **Fees Overview** — collected, outstanding, debtors.
- **Academic Overview** — pending reports, reports ready, released reports. Shown once reports are actually moving (a class has students ready, released, needing correction, or an open correction). Earlier in the term this slot is **Class Coverage** (classes with no class teacher, subjects with no subject teacher, empty classes).

### Below the banner

- **Needs Attention** — the action queue. Examples: reports ready for release, reopen requests, classes with no class teacher, empty classes, subjects with no teacher, subject groups with no students. Each row deep-links with the query the destination already understands (`/assessments?status=ready_for_you`, `/assessments?inbox=1`, `/classes?tab=classes&attention=unassigned`, `/fees?debtors=true`, and so on).
- **Academic Progress** — one bar per class, shown with Academic Overview. Slate is ready for the admin, green is released. The percent is those two groups over enrolled students. Pending and needs-correction do not move the bar.
- **Setup Health** — after Academic Progress, and only while something is under 100%. Class teachers, subject teachers, classes with students, and (when the school has groups) groups with students and students placed in groups. An empty total counts as complete so it does not keep the card open.
- **Top Debtors** — up to five students. View all opens `/fees?debtors=true`. A row opens that student’s fees.
- **Recent Activities** — newest school events this term. See below.

The active term is not repeated on the page. The navbar already shows it.

From 7 days before the current term ends, admins also get a **Transition** action in the navbar and a popup on this dashboard while opening the next term still needs action. Dismissing the popup lasts for that visit. The alert checkbox controls the popup only. Detail: [term-transition.md](./term-transition.md).

---

## Teacher dashboard

`GET /api/v1/dashboard/teacher/` — teacher only, active term. The same banner and card style as the admin page.

### Overview cards

- **My Classes** — how many classes they manage, and how many students are in them. Hidden when they are not a class teacher.
- **My Subjects** — how many subjects they teach, and how many students sit those subjects. Hidden when they are not a subject teacher.
- **Academic Overview** — assessment counts only.
  - Class teacher: students still with subject teachers, ready for their approval, approved by them. Hidden until a subject in the class has been published.
  - Subject teacher: subjects still to publish, subjects already published, corrections waiting.
  - Both: ready for approval, subjects still to publish, corrections.

Fees are not on this page. A class teacher can still open a student’s fee page from elsewhere, but collected, outstanding, and debtors are an admin concern.

### Left column

- **My Classes** — one row per managed class, linking to that class’s approval page (`/assessments/<classTeacherId>`). Once reports are moving, the row is a split bar: slate is ready from subject teachers, green is approved by the class teacher. The rest of the bar is students still with subject teachers.
- **My Subjects** — one row per subject, linking to that subject workspace (`/classes/subjects/<assignmentId>`). The row states Not published, Published, Review correction, or No students. It does not ask them to publish.

### Right column

- **Needs Attention**, then **Recent Activities**.

Needs Attention lists work that is actually waiting:

| Item | When it appears |
| --- | --- |
| Students ready for your approval | Every required subject for those students is published, and the class teacher has not approved them. |
| Students who need correction | A report in their class was sent back. |
| Review a correction | A subject they teach was sent back and is still unpublished. |
| Place students in a group | They teach a subject group, and enrolled students in that class are not in any group for that subject yet. |
| Publish scores | A student on that subject already has a full class score and an exam mark, and the result is still unpublished. Students already in a correction are left on the correction line. |

Unpublished subjects at the start or middle of term do not fill this list. Incomplete markbooks are not an action yet.

The teacher activity list is the same card as the admin feed, scoped to their classes and subjects. Payments, advances, and fee-structure applies are left out.

---

## Activity feed

`activities` is its own Django app. Domain services call `record_activity` in `activities/services.py` after the action succeeds, inside the same transaction. The dashboard only reads. Django signals are not used. The summary sentence is stored when the event is written, and the actor’s name is snapshotted. Targets are plain ids plus optional `stream` and `teaching_assignment` links, so deleting a student does not delete the history.

`stream` and `teaching_assignment` are what the teacher query uses. A class teacher sees events on their class streams. A subject teacher sees events on their teaching assignments, plus class-wide academic events on streams they teach (students approved, reports released, class teacher assigned).

### Events that are recorded

| Verb | When |
| --- | --- |
| `scores_published` | A subject teacher publishes scores. |
| `students_approved` | A class teacher approves students. |
| `student_rejected` | A class teacher rejects a student before release. |
| `reopen_requested` | A class teacher asks for a reopen. |
| `reports_released` | An admin releases reports. |
| `correction_sent` | A student is sent back for correction. |
| `correction_applied` | A reopen is applied, or an admin reopens a released report. |
| `reopen_declined` | An admin declines a reopen request. |
| `payment_recorded` | A payment is recorded. Admin feed only. |
| `fee_structure_applied` | A fee structure is applied. Admin feed only. |
| `advance_created` | An overpayment is held as advance. Admin feed only. |
| `class_teacher_assigned` | A class teacher is assigned. |
| `subject_teacher_assigned` | A subject teacher is assigned. |
| `subject_group_placed` | Students are placed in a subject group (one row for the batch). |
| `student_enrolled` | A student is enrolled in a class. |

Not recorded: logins, page views, and individual score edits. Events from before this feed existed are not backfilled.

### Reading the feed

- Admins: `GET /api/v1/activities/` — newest first, paginated, active term unless `?term=` is set. The admin dashboard requests `page_size=10`.
- Teachers: the teacher dashboard payload includes up to 10 matching rows. There is no separate teacher list URL.

A row stores `href`. Clicking it in the UI follows that link.

---

## Where to look in the code

| Topic | Backend | Frontend |
| --- | --- | --- |
| Admin aggregation | `sms-backend/dashboard/services/admin_dashboard.py` | `sms-frontend/src/features/dashboard/pages/AdminDashboard.tsx` |
| Teacher aggregation | `sms-backend/dashboard/services/teacher_dashboard.py` | `sms-frontend/src/features/dashboard/pages/TeacherDashboard.tsx` |
| Routes | `sms-backend/dashboard/urls.py` | `sms-frontend/src/features/dashboard/Dashboard.tsx` |
| Activity model and writer | `sms-backend/activities/models.py`, `activities/services.py` | `components/RecentActivitiesCard.tsx` |
| Admin activity list | `sms-backend/activities/views.py` | `features/dashboard/services.ts` (`getRecentActivities`) |
