# Feature inventory

Checklist by domain. Status values:

- **Done** — usable end-to-end (API + UI where expected)
- **Partial** — models/services or setup only; ops UI/API incomplete
- **Stub** — route/model placeholder
- **Not started** — no meaningful implementation

---

## Auth & tenancy

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| Admin signup + OTP | Yes | Yes | Done |
| Login + OTP | Yes | Yes | Done |
| Resend OTP / cooldown | Yes | Yes | Done |
| Update my profile | `PATCH /accounts/me/` | `/profile` | Done |
| SMS delivery of OTP | Arkesel client unused; DEBUG print only | — | Partial |
| Update school profile (post-setup) | `GET`/`PATCH /schools/school/` | Settings → School profile | Done |
| Create school / multi-school | Yes | Yes | Done |
| Select active school | Yes | Yes | Done |
| Me / refresh / logout | Yes | Yes | Done |
| School-scoped JWT | Yes | Cookies via API client | Done |

## School setup

| Step | Backend | Frontend | Status |
| --- | --- | --- | --- |
| School profile | Yes | Yes | Done |
| Academic year & term | Yes (creates the first active year) | Yes | Done |
| Classes & subjects (+ streams, groups, custom) | Yes | Yes | Done |
| Assessment config | Yes | Yes | Done |
| Fees items for term | Yes | Yes | Done |
| Teachers + assignments | Yes | Yes | Done |
| Teacher bulk import | Yes | Yes | Done |
| Staff (optional) | Via `/accounts/users/` (no staff setup URLs) | Yes (setup) | Done |
| Complete setup | Yes | Yes | Done |

## Academics / classes

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| Curriculum provisioning | Yes | Via setup | Done |
| List classes / stats | Yes | Yes | Done |
| Class detail (students, subjects) | Yes | Yes | Done |
| Assign class / subject teacher | Yes | Yes | Done |
| Assign one subject teacher across a level | Yes | Yes (staff Assign Subject → By level) | Done |
| Manage curriculum post-setup | Setup/academics APIs reused | `/classes/manage` | Done |
| Timetable | — | — | Not started |
| Attendance | — | — | Not started |

## Students

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| List + stats + filters | Yes | Yes | Done |
| Onboard (bio, class, guardians) | Yes | Multi-step form | Done |
| Detail bio edit | Yes | Yes | Done |
| Guardians CRUD / parent reuse | Yes | Yes | Done |
| Bulk import | Yes | Yes | Done |
| Class enrollment per term | Yes | Via onboard / class views | Done |
| Fees on student (read) | Yes | Yes | Done |
| Reports & assessment tab | Yes (`GET /students/:id/assessments/`) | Student detail tab | Done |
| Performance insights tab | Yes (`GET /students/:id/performance/`) | Student detail → Performance | Done |
| Mark as left / reactivate | Yes (see [mark-as-left.md](../sms-backend/docs/mark-as-left.md)) | Student bio + confirm | Done |
| Promotion / transfer | — | — | Not started |
| Parent login portal | — | — | Not started |

## Staff & teachers

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| Create/list/update/delete users by role | Yes (`accounts/users`) | Setup + shared modals | Done |
| Teaching / class-teacher assignments | Models + setup + academics | Setup + class detail | Done |
| Main `/staff` page | `accounts/staff` desk APIs | `/staff` list + detail | Done |
| Teacher markbook / portal | Via classes / assessments | Subject workspace | Done (scoped) |
| Profile page (`/profile`) | `GET`/`PATCH /accounts/me/` | `/profile` | Done (see [profile.md](./profile.md)) |

## Reports & Insights

School-wide and teacher-scoped analytics at `/reports`. See
[reports-insights.md](../sms-backend/docs/reports-insights.md).

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| Overview + compare term | `GET /reports/overview/` | Overview tab | Done |
| Teacher desk (my classes / subjects) | `GET /reports/teacher-desk/` | Teacher tabs + score curve | Done |
| Academic charts + structure KPIs | by-class, heatmap, grades, trends | Academic tab | Done |
| Finance / enrollment / fees×risk | reports APIs | Tabs | Done |
| Teachers load insights | `GET /reports/staff-capacity/` | Teachers tab (links to `/staff/:id`) | Done |

## Fees

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| Fee structure + items | Models + setup + product APIs | Setup + `/fees/settings` | Done |
| Publish / apply / carry-forward | Services + `/fees/structures/` apply | Settings Apply | Done |
| StudentFee generation on apply | Service + auto on late enroll | — | Done |
| Fees desk list + stats | Yes (`/api/v1/fees/`) | `/fees` | Done |
| Student fee balance / history APIs | Yes (on students) | Student detail + fee detail | Done |
| Record payment | Yes | Record Fees slider | Done |
| Receipts | Model + auto on payment | Eye UI-only | Partial |
| Fees settings | Yes | `/fees/settings` | Done |
| Arrears / reports | — | — | Not started |

## Assessments

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| Level assessment config + grade bands | Yes | Setup wizard + `/assessments/settings` | Done (per term; see [assessment-config.md](./assessment-config.md)) |
| Assessment items / scores | Empty models | — | Stub |
| Results / subject scores / reports | Empty models | — | Stub |
| Correction requests | Empty model | — | Stub |
| Assessments nav page | No APIs | Placeholder | Stub |
| Report card generation | Yes (R2 PDF; released only) | Assessments report page + student Reports tab (inline) | Done |

## School settings (admin, after setup)

Signup setup is unchanged. These screens edit the school after the wizard, under `/settings/:tab` (admin only).

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| School profile + student ID prefix | `GET`/`PATCH /schools/school/` | `/settings/school-profile` | Done |
| Year calendar | `GET`/`POST /schools/settings/academic-years/`, `PATCH …/<year_id>/` | `/settings/academic-year` | Done |
| Open the next term | `GET /schools/transition/`, `GET …/preview/`, `POST …/confirm/` | Navbar, dashboard, Academic year wizard | Done (see [term-transition.md](./term-transition.md)) |
| In-app alerts | `GET`/`PATCH /schools/settings/`, `GET /schools/alerts/` | `/settings/alerts` + navbar bell | Done |
| Fee catalog | Same as `/fees/settings` | `/settings/fees` and `/fees/settings` | Done |
| Assessment structure | Same as `/assessments/settings` | `/settings/assessments` and `/assessments/settings` | Done |
| Classes and subjects | Same as `/classes/manage` | `/settings/classes` and `/classes/manage` | Done |

The calendar lists every year. Past years are view-only. **Add** saves the next year’s three terms and leaves the current term active. Assessment settings are copied onto any new term that does not have them yet.

**Open the next term** places continuing pupils, marks the last class graduated at year end, copies teachers, applies the next fee catalog, and then turns that term on. See [term-transition.md](./term-transition.md). Standalone `POST …/terms/<term_id>/activate/` is disabled (403); activation only runs inside transition confirm.

Alerts are in-app only: outstanding fees (admin and accountant), unreleased results (admin and class teachers), and new enrollments (admin). The transition popup on the dashboard has its own checkbox.

## Dashboard & shell

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| App shell (nav, auth gates) | — | Yes | Done |
| Dashboard widgets | Yes (`/dashboard/admin/`, `/dashboard/teacher/`) | Yes | Done (see [dashboard.md](./dashboard.md)) |
| Activity feed | Yes (`activities` app, `GET /activities/`) | Recent Activities card | Done |
| In-app alerts | Yes (`GET /schools/alerts/`) | Navbar bell | Done |

## Cross-cutting

| Feature | Status |
| --- | --- |
| OpenAPI / Swagger | Done |
| Backend tests (accounts, schools setup, academics, students, fees services, assessment config) | Done for built areas |
| Frontend automated tests | Not started / minimal |
| Fine-grained Permission matrix | Models only — unused |
| Celery / Redis async jobs | Compose stubs only |
| Attendance, messaging, library, inventory, payroll | Not started |

---

## Existing deep-dive notes

- Teacher bulk import (frontend contract): [`sms-backend/docs/frontend-teacher-bulk-import.md`](../sms-backend/docs/frontend-teacher-bulk-import.md)
- Assessment structure per term: [assessment-config.md](./assessment-config.md)
- Admin and teacher dashboards, activity feed: [dashboard.md](./dashboard.md)
- Reports & Insights: [`sms-backend/docs/reports-insights.md`](../sms-backend/docs/reports-insights.md)
- Mark student as left: [`sms-backend/docs/mark-as-left.md`](../sms-backend/docs/mark-as-left.md)
