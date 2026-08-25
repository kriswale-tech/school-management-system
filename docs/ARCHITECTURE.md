# Architecture

## Monorepo layout

```
School-Management-System/
├── compose.yml          # Postgres + backend + frontend (Redis/Celery commented out)
├── .env                 # Shared env for Compose
├── requirements.txt     # Root pin (backend also has its own deps via Dockerfile)
├── docs/                # Project docs (this folder)
├── sms-backend/         # Django + DRF
└── sms-frontend/        # React + Vite SPA
```

## Stack

| Layer | Choice |
| --- | --- |
| API | Django  + Django REST Framework |
| API docs | drf-spectacular (`/api/v1/schema/`, `/api/v1/docs/`) |
| DB | PostgreSQL 16 |
| Auth | Phone OTP + JWT in HTTP-only cookies; school membership on token/request |
| Media | Cloudinary (profile/school logos configured via settings) |
| Frontend | React 19, Vite, TypeScript, TanStack Query, React Router 7, Tailwind 4, Zustand, Zod + RHF |
| Local run | Docker Compose — backend `:9000→8000`, frontend `:3003→5173`, DB `:5434→5432` |

## Multi-school model

- A **User** is identity only (`phone_number` as username).
- **SchoolMembership** links a user to a school with a **role** (`admin` | `teacher` | `accountant` | `staff`).
- After login, users with multiple memberships pick a school (`select-school`).
- Requests are **school-scoped** via `HasActiveSchool` / membership on the request (see `accounts.permissions`, `accounts.authentication`).

## Backend apps

| App | Responsibility |
| --- | --- |
| `core` | Settings, root URLs, pagination, exceptions |
| `accounts` | Users, memberships, OTP, JWT cookies, user management API |
| `schools` | School entity, academic year/term, **setup wizard** APIs |
| `academics` | Curriculum templates + school levels/classes/streams/subjects; class APIs |
| `students` | Students, parents, enrollments, onboard, bulk import, fee *read* APIs |
| `teachers` | Class teacher & teaching assignment models (APIs mostly via schools setup + academics) |
| `fees` | Fee structures, student fees, payments, receipts — **services**, minimal views |
| `assessments` | Assessment config + grade bands; scoring models **stubbed** |
| `shared` | `BaseModel`, helpers, shared exceptions/services |

## Frontend feature modules

Under `sms-frontend/src/features/`:

`auth`, `setup`, `dashboard`, `students`, `classes`, `assessments`, `fees`, `staff`

Shared UI lives in `src/components/` (layout, curriculum accordion, data-table, bulk-upload, etc.). API client: `src/app/api/api.ts`.

## Request flow (typical)

1. Admin signs up with phone → OTP → school created + admin membership.  
2. Incomplete setup → forced into `/setup` until `setup_completed`.  
3. Curriculum provisioned during classes/subjects setup from a master `Curriculum`.  
4. Day-to-day: SideNav → students / classes / (stubs for fees & assessments).

## Auth notes

- OTP is generated and stored on `PhoneOtp`; in `DEBUG`, OTP is printed to the server console.
- An Arkesel SMS helper lives at `shared/services/arkesel_sms.py` but is **not called** from the OTP flow yet.
- Role permissions: coarse `IsAdmin` / `IsTeacher` / etc. Fine-grained `Permission` + `RolePermission` tables are unused.

## Infra not yet enabled

- Redis and Celery worker/beat are present in `compose.yml` but **commented out**.
- Useful later for SMS send, large bulk imports, scheduled term rollover, etc.
