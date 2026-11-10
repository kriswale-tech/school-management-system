# Architecture

## Monorepo layout

```
School-Management-System/
├── compose.yml          # Postgres + backend + frontend + Redis + Celery worker
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
| Local run | Docker Compose — backend `:9000→8000`, frontend `:3003→5173`, DB `:5434→5432`, Redis `:6380→6379`, Celery worker |
| Email | django-anymail → Resend (notification delivery; gated by `EMAIL_ENABLED`) |
| Async | Celery + Redis (notification email tasks for now) |

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
| `assessments` | Assessment config, markbook, approvals, releases, corrections |
| `dashboard` | Admin and teacher home aggregations (read-only) |
| `activities` | School activity feed. Domain services write via `record_activity`; dashboards read |
| `notifications` | Staff in-app inbox (Tier‑1 + Celery email) and guardian outbound log (`GuardianDelivery`) via `services/guardians.py` |
| `reports` | School-wide and teacher-scoped analytics |
| `shared` | `BaseModel`, helpers, shared exceptions/services |
| `platform_admin` | Platform (SCHOOLASST staff) auth realm — email/password + MFA, roles, settings, audit, school invites. Serves `/api/v1/platform/...` |
| `billing` | SaaS billing: plans, school subscriptions, periods, invoices, payments, top-ups, promotions, capacity gates, dunning. **`billing.Payment` ≠ `fees.Payment`** |
| `communications` | School SMS/email credit wallets (`CreditAccount` + append-only `CreditLedgerEntry`), add-on SKUs, segment calculator, send gates |
| `messaging` | School-facing messaging surface: overview, guardian delivery history, message templates |

> The platform side has its own separate app (`platform-admin/`, React/Vite) and its own auth realm. For the full design — plans, capacity, proration, credit ledger discipline, and provider economics — see [platform-admin-billing-architecture-v4.md](./platform-admin-billing-architecture-v4.md).

## Frontend feature modules

Under `sms-frontend/src/features/`:

`auth`, `setup`, `dashboard`, `students`, `classes`, `assessments`, `fees`, `staff`, `settings`, `notifications` (services), `reports`, `profile`

Shared UI lives in `src/components/` (layout, curriculum accordion, data-table, bulk-upload, etc.). API client: `src/app/api/api.ts`.

## Request flow (typical)

1. Admin signs up with phone → OTP → school created + admin membership.  
2. Incomplete setup → forced into `/setup` until `setup_completed`.  
3. Curriculum provisioned during classes/subjects setup from a master `Curriculum`.  
4. Day-to-day: SideNav → students / classes / (stubs for fees & assessments).

## Auth notes

- OTP is generated and stored on `PhoneOtp`.
- **Login OTP:** Arkesel SMS (`shared/services/arkesel_sms.py`) is primary; email is sent when the user has an address; if SMS fails in `DEBUG`, the code is printed to the console.
- **Signup OTP:** still DEBUG-console only for now.
- Access uses **capabilities** on `/me` (`accounts.capabilities` + `accounts.services.capabilities`), derived from membership role and teacher assignments. UI uses `useCan`; teachers get assignment-scoped class lists via `accounts.services.access_scope`.
- Fine-grained `Permission` + `RolePermission` tables remain unused.

## Infra notes

- Redis + Celery worker run in Compose (host Redis mapped to **6380**). Used for staff notification email and guardian SMS/email (batched outbound + beat for auto debt reminders).
- Also used for bulk-import ward-enrolled notices and fee-structure apply notices.
