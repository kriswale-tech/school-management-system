# How the app works

A plain-language walkthrough of School Management System — from first signup to day-to-day use.

---

## The big idea

1. A **person** signs in with their **phone number** (no password — they get a one-time code).
2. That person can belong to **one or more schools**, each with a **role** (admin, teacher, accountant, or staff).
3. After they pick a school, almost everything they see and change is **only for that school**.
4. New schools go through a **setup wizard** once. After that, they use the main modules (Students, Classes, Fees, and so on).

```
Phone + OTP  →  Pick school  →  Finish setup (first time)  →  Use the app
```

---

## From signup to daily use

### 1. Signup (new school admin)

Someone creates a school for the first time:

1. Enter name, email, phone, and **school name**.
2. Receive a 6-digit OTP (in development it is printed in the backend console; SMS is not fully wired yet).
3. Verify the OTP.
4. The system creates:
   - their **user** account
   - the **school**
   - an **admin** membership linking them to that school
   - a starter curriculum for the school

**Already have an account?** Signing up again with the same phone can create **another** school (as long as the name is not a duplicate of one they already administer).

### 2. Login (returning users)

1. Enter phone number.
2. Get OTP → verify.
3. If they only belong to **one** school → they go straight in.
4. If they belong to **several** schools → they must **choose a school** first.

### 3. School selection

The “active school” is stored on the login token. Until a school is selected, school data APIs refuse access.

You can switch schools later if you belong to more than one.

### 4. First-time setup wizard

If the school has not finished setup, the app sends the user to `/setup` and will not open the main app yet.

Steps (in order):

| Step | What you set |
| --- | --- |
| School profile | Basic school details |
| Academic year & term | Current year and term |
| Classes & subjects | Levels, classes, streams, subjects |
| Assessment | How scores/grades work for this school |
| Fees | Fee items for the current term |
| Teachers | Add teachers and assign classes/subjects |
| Staff | Optional extra staff (can skip) |
| Complete | Marks setup done and applies term fees |

After **Complete**, `setup_completed` is true and the main sidebar app unlocks.

### 5. Day-to-day

Logged-in users with a finished school use the sidebar:

- Dashboard  
- Students  
- Classes  
- Assessments  
- Fees  
- Staff  

---

## People, schools, and roles

### User vs membership

| Concept | Meaning |
| --- | --- |
| **User** | The person (identified by phone). Same person can work at many schools. |
| **SchoolMembership** | “This person works at **this** school as **this** role.” |

Access is never “global admin of everything.” It is always **per school + role**.

### Roles (what they mean today)

| Role | Typical meaning |
| --- | --- |
| **Admin** | Full school control: setup, users, students, classes, fees, etc. |
| **Staff** | Can help manage users, but only **teachers** (not other admins/staff/accountants). Full module access for now (packs will tighten later). |
| **Teacher** | Sees only assigned classes/subjects; limited sidebar and actions (see below). |
| **Accountant** | Role exists; still has full school capability pack until finance-only access is wired. |

### Capabilities (how UI + API share one vocabulary)

Access is driven by **capability codes** on `/accounts/me/` (`capabilities` + `access`), not scattered `if role === …` checks.

- Frontend: `useCan('classes.manage')` hides buttons / filters the sidebar / guards routes.
- Backend: same codes from membership role + teacher assignments; class lists are **scoped** for teachers.
- Pages stay shared — hide create/manage actions when the capability is missing; show different sections when needed.

### Teacher access (current)

Teachers get a **scoped** session (`access.mode = "scoped"`) based on active-term `ClassTeacher` and `TeachingAssignment` rows.

| | Subject teacher | Class teacher | Both |
| --- | --- | --- | --- |
| Sidebar | Dashboard, Classes | Dashboard, Classes, Assessments | Union |
| Classes list | Assigned subject streams only | Homeroom streams only | Union |
| Classes page UI | Managed Classes + Subject Teaching cards (View class / View subject) | Same | Same |
| Manage Classes / Add Student / Fees desk / Staff | Hidden | Hidden | Hidden |
| Record assessments | Capability granted (UI later) | — | Yes |
| Approve assessments + view fees | — | Capability granted (UI later) | Yes |

Subject-only teachers do **not** get the Assessments nav item; class teachers do.

### Subject groups (student placement)

Grouped subjects (e.g. Ghanaian Language → Twi / Ga) do **not** auto-enroll the class roster. A student belongs to at most **one** group per class-subject per academic year (`StudentSubjectGroup`).

**Placement rules (product):**

- On a subject-group Subject Detail page, **Assign students** lives on the **Students** tab (not Workspace / ActionBar).
- They may only add students who are currently **unassigned** for that class-subject.
- If a student is already in another group, this teacher **cannot** pull them over. The other group’s teacher must **unassign** them first; then they can be assigned.
- Teachers can unassign students from **their own** group (so the student becomes unassigned again).

**Markbook (Subject Detail Workspace):** see [subject-assessment-workspace.md](./subject-assessment-workspace.md) (UI + scoring rules; runtime not built yet). Grouped subjects (e.g. Twi / Ga) each have their **own** CA items for the term.

**Later (not built yet):**

- Block unassign / move once an **assessment score** has been recorded for that student in the group (or class-subject) for the term — avoids roster churn after marking starts. See [subject-groups-backlog.md](./subject-groups-backlog.md).

### Who can manage other people

Only **Admin** and **Staff** can add/edit/remove school users (`CanManageUser`).

- **Admin** → can manage all roles in that school.  
- **Staff** → can manage **teachers** only.  
- Nobody can remove the **last active admin**.  
- You cannot modify/remove **yourself**.

### How the API enforces this

Most school APIs require:

1. You are logged in (JWT in HTTP-only cookies).  
2. Your token is scoped to an **active school** (`HasActiveSchool`).  
3. For user management, your role may manage that target (`CanManageUser`).  
4. Teachers additionally get **assignment-scoped** class lists (and more scopes as modules are wired).

`HasCapability` exists for capability checks on views. Fine-grained DB `Permission` / `RolePermission` tables remain unused — codes live in `accounts/capabilities.py` (mirrored on the frontend).

---

## Modules (what each area does)

### Auth (`accounts` / frontend `auth`)

- Signup, login, OTP, resend OTP  
- Create another school  
- Select active school  
- Me / refresh / logout  
- User management and staff directory APIs  

### Setup (`schools` setup APIs / frontend `setup`)

One-time guided configuration for a new school (see steps above).

### Students

- List and search students  
- Onboard a student (bio, class, guardians)  
- Bulk import  
- Student detail (bio, guardians, fee balance/history)  

### Classes

- See classes and class details  
- Students in a class, subjects  
- Assign class teachers / subject teachers  
- Manage curriculum after setup (`/classes/manage`)  

### Fees

- Fee catalog for a term (settings)  
- Apply fees to students  
- Fees desk (who owes what)  
- Record payments (advances handled when overpaid)  

Deeper detail: [fees.md](./fees.md).

### Staff

- Directory of people in the school (teachers, staff, etc.)  
- Add / edit / deactivate via accounts APIs  
- Teacher assignments also appear under setup and classes  

### Assessments

- Configured during setup (weights, grade bands)  
- Subject markbook on Subject Detail; class-teacher `/assessments` overview  
- Status model + publish / unpublish (v1) / approve: [subject-assessment-workspace.md](./subject-assessment-workspace.md)  
- Publish APIs, class approve, and admin finalize are **not fully built yet**

### Dashboard

- App home shell exists; rich widgets are still mostly placeholder

---

## Mental model (short)

```
┌─────────────┐     belongs to      ┌─────────────┐
│    User     │────────────────────▶│   School    │
│ (phone OTP) │   via Membership    │             │
└─────────────┘   + role            └──────┬──────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
               Students               Classes /               Fees /
                                      Subjects               Payments
```

Everything under a school stays **school-scoped**. Changing active school changes which data you can touch.

---

## Where to look in the code

| Topic | Backend | Frontend |
| --- | --- | --- |
| Signup / login / OTP | `sms-backend/accounts/` | `sms-frontend/src/features/auth/` |
| Memberships & roles | `accounts/models.py`, `permissions.py` | Auth store + layouts |
| Setup wizard | `sms-backend/schools/setup_views/` | `sms-frontend/src/features/setup/` |
| Students | `sms-backend/students/` | `sms-frontend/src/features/students/` |
| Classes / curriculum | `sms-backend/academics/` | `sms-frontend/src/features/classes/` |
| Fees | `sms-backend/fees/` | `sms-frontend/src/features/fees/` |
| Staff desk | `accounts` staff APIs | `sms-frontend/src/features/staff/` |

---

## Related docs

- [ARCHITECTURE.md](./ARCHITECTURE.md) — stack and app layout  
- [FEATURES.md](./FEATURES.md) — what is done vs stubbed  
- [STATUS.md](./STATUS.md) — project snapshot  
- [fees.md](./fees.md) — fees in more detail  

**Last reviewed:** 2026-09-09
