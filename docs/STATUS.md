# Project status — built vs left

Snapshot of the School Management System as of **2026-08-25**.

## Verdict

**Core onboarding and day-to-day school administration for students and classes is largely in place.** Auth, multi-school membership, guided school setup, curriculum, students (including bulk import), class management, and teacher/staff user management are real end-to-end features.

**Assessments (scoring/reports), operational fees (collect payments, fee desk UI), dashboard, and several runtime APIs are still missing or stubbed.** Data models and some fee/assessment *setup* exist; operational use does not.

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
- Roles: `admin`, `teacher`, `accountant`, `staff` (role checks via permissions; fine-grained `Permission` / `RolePermission` models exist but are unused)
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

### Academics / curriculum (done)

- Master curriculum templates + per-school levels, classes, streams, subjects, subject groups
- Post-setup class list, stats, class detail (students, subjects)
- Assign class teacher and subject teacher (API + UI)
- Manage curriculum after setup (`/classes/manage`)

### Students (done)

- List + stats, filters
- Onboarding wizard (bio, class/stream, guardians, fees snapshot)
- Student detail: bio edit, guardians CRUD, **fees view/history** (read-only)
- Parent reuse across students
- Class enrollment per term (with stream)
- **Bulk student import** (template + upload + failure download)

### Teachers & staff (mostly done)

- Teacher models: `ClassTeacher`, `TeachingAssignment`
- Setup + accounts APIs for creating/editing/deleting school users
- Teacher bulk import
- Setup staff UI is real; **main app `/staff` page is a placeholder** (logic already lives under setup + shared staff components)

### Fees — data, setup, desk, and payments (partial)

**Built:**

- Models: `FeeStructure`, `FeeItem`, `StudentFee`, `Payment`, `Receipt`, `StudentFeeCredit` (advance)
- Services: publish/apply structure, carry-forward, balances, history, record payment, excess → advance, auto-apply advance on next term apply
- Setup wizard fee items; student detail fee breakdown + payment history
- Fees desk (`GET /api/v1/fees/`, `/stats/`, `/filter-options/`) + frontend `/fees` list/detail
- Record Fees slider (list + detail); advance shown on desk rows, detail header, and record form
- Fees settings (`/fees/settings` + `/api/v1/fees/structures/`): term catalogs, item CRUD, Apply; late enrollments auto-billed

**Not exposed as product features yet:** receipt PDF, Excel export, advance refund, pure advance top-up with no owing

### Assessments — config only (partial)

**Built:**

- `AssessmentConfig`, `GradeBand`
- Setup wizard for level assessment config
- Config service + tests

**Stubbed empty models:** `AssessmentItem`, `AssessmentItemScore`, `StudentResult`, `SubjectScore`, `Report`, `CorrectionRequest`  
**No runtime scoring/report APIs or real UI** (nav page and student “Reports & Assessment” tab are placeholders)

---

## What is left (priority-oriented)

### High — product gaps users will hit immediately

| Area | Gap |
| --- | --- |
| **Dashboard** | Placeholder lorem content only |
| **Assessments (runtime)** | Enter CA/exam scores, compute grades/positions, report cards, correction flow; wire student assessment tab |
| **Fees (operations)** | Record payments, issue receipts, fee desk list/filters, publish/apply fee structures after setup, arrears reporting |
| **Staff main page** | Reuse setup staff components for `/staff` instead of placeholder |
| **Profile** | Nav links to `/profile` but no route/page |

### Medium — incomplete or scaffolded

| Area | Gap |
| --- | --- |
| **OTP delivery** | Wire existing Arkesel client into `send_otp` (or another SMS provider) |
| **School profile update** | `GET /schools/school/` only; PATCH/update still stubbed |
| **Fine-grained permissions** | `Permission` / `RolePermission` unused; access is coarse role flags |
| **Notifications** | Bell icon in navbar with no backend/UI |
| **Fees/Assessments apps** | Empty `views.py`; no dedicated URL includes under `core/urls.py` |
| **Celery / Redis** | Commented out in Compose — needed if async bulk jobs / SMS queues are planned |
| **Teacher portal UX** | Teacher role exists; no dedicated teacher-facing flows (mark entry, own classes) |

### Lower / polish

- Parent/guardian portal (parents are data records only today)
- Term promotion / year rollover UX (beyond fee carry-forward service)
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
| `/dashboard` | Stub |
| `/students`, `/students/:id` | Done (assessment tab stub) |
| `/classes`, `/classes/:id`, `/classes/manage` | Done |
| `/assessments` | Stub |
| `/fees` | Desk list (stats + table); record/settings UI-only |
| `/fees/:studentId` | Detail (reuses student fee breakdown) |
| `/staff` | Stub |
| `/profile` | Missing |

---

## Backend API surface (mounted)

Under `/api/v1/`:

- `accounts/` — auth, me, schools, users  
- `schools/` — setup wizard + school profile  
- `academics/` — levels, classes, teachers assignment  
- `students/` — CRUD-ish list/detail, onboard, guardians, fees read, bulk import  
- `fees/` — desk list, stats, filter options  

**Not mounted yet as product APIs:** payment write / receipts / assessments scoring.

---

## Suggested next build order

1. Fees operations API + `/fees` UI (record payment → receipt → student balance stays correct)  
2. Assessment scoring models/APIs + teacher/admin UI + student reports tab  
3. Real dashboard (counts, owing fees, unassigned teachers, active term)  
4. Promote `/staff` and `/profile` from stubs  
5. SMS OTP provider + optional Celery for bulk/async work  

See also [FEATURES.md](./FEATURES.md) for a domain-by-domain checklist and [ARCHITECTURE.md](./ARCHITECTURE.md) for how the pieces fit.
