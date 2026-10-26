# Project status — built vs left

Snapshot of the School Management System as of **2026-10-26**.

## Verdict

**Core onboarding and day-to-day school administration for students and classes is largely in place.** Auth, multi-school membership, guided school setup, curriculum, students (including bulk import), class management, and teacher/staff user management are real end-to-end features.

**Dashboards exist for admin, teacher, accountant, and staff** ([dashboard.md](./dashboard.md)). Accountant/staff capability packs are tightened; next-term fee prep and URL-persisted page tabs are in place. Parts of the older sections below may still understate assessments and fees maturity.

---

## What is in place

### Platform & infra

- Docker Compose: Postgres, Django backend (`:9000`), Vite frontend (`:3003`)
- Django REST Framework + `drf-spectacular` (OpenAPI / Swagger at `/api/v1/docs/`)
- React 19 + Vite + TypeScript + TanStack Query + Tailwind 4 + Zustand
- Cookie-based JWT auth flow (access/refresh), school-scoped membership on requests

### Auth & accounts (done)

- Phone-based signup / login with OTP verify + resend (OTP printed in DEBUG; `shared/services/arkesel_sms.py` exists but is **not wired** into OTP)
- Multi-school: `SchoolMembership`, create school, select school
- Roles: `admin`, `teacher`, `accountant`, `staff` with dedicated capability packs in `accounts/capabilities.py` (fine-grained DB `Permission` / `RolePermission` models remain unused)
- User CRUD for school staff (`/api/v1/accounts/users/`)
- Frontend: signup, login, OTP pages, school picker, logout

### School setup wizard (done)

Guided multi-step setup with progress tracking (`SchoolSetup`):

1. School profile  
2. Academic year & term  
3. Classes & subjects (curriculum provisioning, streams, subject groups, custom classes)  
4. Assessment config (CA/exam weights, result/grade types, grade bands)  
5. Fees setup (fee structure + items for the active term)  
6. Teachers (create + class-teacher / subject teaching assignments + **bulk Excel import**)  
7. Staff (optional — does **not** block setup completion)  
8. Complete setup (also publishes/applies active-term fees)

Frontend mirrors these steps under `/setup/:step`. Staff UI in setup talks to `/accounts/users/` (there is no dedicated staff setup API; `schools/setup_views/staff.py` is empty).

### School settings (done, admin)

After setup, admins use `/settings` (tabs keep the selection in the URL). Signup still uses the wizard and `POST /schools/setup/academic-year-term/`, which creates the first year and marks it active.

- **School profile** — name, contact, logo, and the prefix used on new student IDs (`GET`/`PATCH /schools/school/`). Existing student IDs stay as they are.
- **Academic year** — every year and its three terms. The current term is marked. Past years are view-only. Adding the next year saves dates only; the current term stays current. New terms with no assessment setup receive a copy of the latest previous setup.
- **Open the next term** — wizard from the navbar, the admin dashboard, and Academic year. Places pupils, marks leavers graduated, copies teachers, applies the next fee catalog, then makes that term current. See [term-transition.md](./term-transition.md).
- **Alerts** — in-app rules for outstanding fees, unreleased results, and new enrollments. The navbar bell lists the ones that apply to the signed-in role. One more switch controls the dashboard popup while opening the next term still needs action.
- **Fees, assessments, and classes** — the same screens as `/fees/settings`, `/assessments/settings`, and `/classes/manage`, also opened from `/settings/fees`, `/settings/assessments`, and `/settings/classes`. Those original routes stay in place.

### Academics / curriculum (done)

- Master curriculum templates + per-school levels, classes, streams, subjects, subject groups
- Post-setup class list, stats, class detail (students, subjects)
- Assign class teacher and subject teacher (API + UI)
- Assign one teacher to a subject across every class in a level (`PUT /academics/levels/<id>/subject-teacher/`). Grouped subjects stay class-by-class.
- Teacher picker summaries collapse to the level name when that teacher covers the subject in every listed class of the level. Search still matches class names.
- Manage curriculum after setup (`/classes/manage`)

### Students (done)

- List + stats, filters
- Onboarding wizard (bio, class/stream, guardians, fees snapshot)
- Student detail: bio edit, guardians CRUD, **fees view/history** (read-only), **reports & assessment** (read-only, term filter)
- Parent reuse across students
- Class enrollment per term (with stream)
- **Bulk student import** (template + upload + failure download)

### Teachers & staff (mostly done)

- Teacher models: `ClassTeacher`, `TeachingAssignment`
- Setup + accounts APIs for creating/editing/deleting school users
- Teacher bulk import
- Setup staff UI is real; main app `/staff` desk + `/staff/:id` detail (bio / workspace) are in place

### Fees — data, setup, desk, and payments (partial)

**Built:**

- Models: `FeeStructure`, `FeeItem`, `StudentFee`, `Payment`, `Receipt`, `StudentFeeCredit` (advance)
- Services: publish/apply structure, carry-forward, balances, history, record payment, excess → advance, auto-apply advance on next term apply
- Setup wizard fee items; student detail fee breakdown + payment history
- Fees desk (`GET /api/v1/fees/`, `/stats/`, `/filter-options/`) + frontend `/fees` list/detail
- Record Fees slider (list + detail); advance shown on desk rows, detail header, and record form
- Fees settings (`/fees/settings` + `/api/v1/fees/structures/`): term catalogs, item CRUD, copy-from-previous, publish, Apply; late enrollments auto-billed
- Next-term fee prep for accountants (`GET /fees/next-term-prep/`, dashboard/fees banner) in the transition lead window

**Not exposed as product features yet:** receipt PDF, Excel export, advance refund, pure advance top-up with no owing

### Assessments — config only (partial)

**Built:**

- `AssessmentConfig`, `GradeBand`
- Setup wizard for level assessment config
- Config service + tests

**Stubbed empty models:** `AssessmentItem`, `AssessmentItemScore`, `StudentResult`, `SubjectScore`, `Report`, `CorrectionRequest`  
Runtime scoring, class/admin assessment, and the student **Reports & Assessment** tab exist; STATUS snapshot above is otherwise stale on assessments.

---

## What is left (priority-oriented)

### High — product gaps users will hit immediately

| Area | Gap |
| --- | --- |
| **Dashboard** | Done for admin, teacher, accountant, and staff — see [dashboard.md](./dashboard.md). |
| **Assessments (runtime)** | Enter CA/exam scores, compute grades/positions, report cards, correction flow (much of this exists; STATUS rows below may lag) |
| **Fees (operations)** | Receipt PDF / Excel export / arrears reporting still open; desk, payments, publish/apply, and accountant prep are done |
| **Staff main page** | Desk exists; polish / gaps vs setup flows may remain |
| **Profile** | Done — see [profile.md](./profile.md). School settings are separate (school record, admin only). |

### Medium — incomplete or scaffolded

| Area | Gap |
| --- | --- |
| **OTP delivery** | Wire existing Arkesel client into `send_otp` (or another SMS provider) |
| **Fine-grained permissions** | `Permission` / `RolePermission` unused; access is coarse role flags |
| **Fees/Assessments apps** | Empty `views.py`; no dedicated URL includes under `core/urls.py` |
| **Celery / Redis** | Commented out in Compose — needed if async bulk jobs / SMS queues are planned |
| **Teacher portal UX** | Teacher role exists; no dedicated teacher-facing flows (mark entry, own classes) |

### Lower / polish

- Parent/guardian portal (parents are data records only today)
- Receipt numbering / PDF download
- Attendance, timetable, messaging, inventory — not started
- Frontend tests (backend has solid coverage for built areas)
- Production hardening: SMS, Cloudinary in prod, secrets, HTTPS cookies, etc.

---

## Frontend route map (quick)

| Route | Status |
| --- | --- |
| `/auth/*` | Done |
| `/setup/:step` | Done |
| `/dashboard` | Admin, teacher, accountant, staff (see [dashboard.md](./dashboard.md)) |
| `/students`, `/students/:id` | Done (`?tab=` + nested `feesTab`) |
| `/classes`, `/classes/:id`, `/classes/manage` | Done (`?tab=` on list and detail) |
| `/assessments` | Built (class/admin flows; see assessment docs) |
| `/fees` | Desk + record payment; settings publish/apply/prep |
| `/fees/:studentId` | Detail (reuses student fee breakdown) |
| `/staff`, `/staff/:id` | Desk + detail (`?tab=` / `?view=`) |
| `/reports` | Reports & Insights (`?tab=`) |
| `/settings`, `/settings/:tab` | Admin: school profile, academic year, alerts, plus fees, assessments, and classes (same screens as their own routes) |
| `/profile` | Personal profile for all roles (see [profile.md](./profile.md)) |

---

## Backend API surface (mounted)

Under `/api/v1/`:

- `accounts/` — auth, me, schools, users  
- `schools/` — setup wizard, school profile, settings (year calendar, term transition, alerts)  
- `academics/` — levels, classes, teachers assignment  
- `students/` — CRUD-ish list/detail, onboard, guardians, fees read, bulk import  
- `fees/` — desk list, stats, filter options, payments, structures (publish/apply/copy), next-term prep  
- `reports/` — overview, teacher desk, academic/finance/enrollment/staff insights  
- `dashboard/`, `activities/` — admin/teacher dashboards and activity feed  

**Still light / deferred:** receipt PDF download, advance refund, Excel fee export.

---

## Suggested next build order

1. Fees operations API + `/fees` UI (record payment → receipt → student balance stays correct)  
2. Assessment scoring models/APIs + teacher/admin UI + student reports tab  
3. ~~Real dashboard~~ Done for admin and teacher ([dashboard.md](./dashboard.md))  
4. Promote `/staff` from stub  
5. SMS OTP provider + optional Celery for bulk/async work  

See also [FEATURES.md](./FEATURES.md) for a domain-by-domain checklist and [ARCHITECTURE.md](./ARCHITECTURE.md) for how the pieces fit.
