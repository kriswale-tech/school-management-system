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
| SMS delivery of OTP | Arkesel client unused; DEBUG print only | — | Partial |
| Update school profile (post-setup) | GET only; PATCH stub | Via setup / limited | Partial |
| Create school / multi-school | Yes | Yes | Done |
| Select active school | Yes | Yes | Done |
| Me / refresh / logout | Yes | Yes | Done |
| School-scoped JWT | Yes | Cookies via API client | Done |

## School setup

| Step | Backend | Frontend | Status |
| --- | --- | --- | --- |
| School profile | Yes | Yes | Done |
| Academic year & term | Yes | Yes | Done |
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
| Reports & assessment tab | No scoring API | Placeholder | Stub |
| Promotion / transfer | — | — | Not started |
| Parent login portal | — | — | Not started |

## Staff & teachers

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| Create/list/update/delete users by role | Yes (`accounts/users`) | Setup + shared modals | Done |
| Teaching / class-teacher assignments | Models + setup + academics | Setup + class detail | Done |
| Main `/staff` page | Same APIs | Placeholder | Stub |
| Teacher markbook / portal | — | — | Not started |
| Profile page (`/profile`) | Partial (Profile model) | Link only, no route | Stub |

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
| Level assessment config + grade bands | Yes | Setup wizard | Done |
| Assessment items / scores | Empty models | — | Stub |
| Results / subject scores / reports | Empty models | — | Stub |
| Correction requests | Empty model | — | Stub |
| Assessments nav page | No APIs | Placeholder | Stub |
| Report card generation | — | — | Not started |

## Dashboard & shell

| Feature | Backend | Frontend | Status |
| --- | --- | --- | --- |
| App shell (nav, auth gates) | — | Yes | Done |
| Dashboard widgets | No | Lorem stub | Stub |
| Notifications | No | Icon only | Stub |

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
