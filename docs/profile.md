# Profile page

Every signed-in user with an active school can open **`/profile`** from the header menu. This page is for **the person**, not the school. School-wide settings stay on **`/settings`** (admin only).

## What you see

| Area | Content |
| --- | --- |
| Summary | Photo, name, role, active school, login phone (read-only), **last active** in this school, other schools and roles |
| Photo | Upload a new profile picture (multipart save) |
| Account | First name, last name, email |
| Personal | Gender, alternate phone, date of birth, address, bio (optional) |

**Last active** comes from `SchoolMembership.last_active_at` for the school you are working in. It updates when you use that school; it is not a global “last login” across all schools.

Login phone, role, and school membership are **read-only** on this page. Changing login phone still goes through admin staff tools (and only during setup for corrections). Switching schools uses **Switch school** when you belong to more than one.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/accounts/me/` | Current user; includes `last_active_at` when a school is selected |
| PATCH | `/api/v1/accounts/me/` | Update your own identity + profile fields |

PATCH accepts JSON or `multipart/form-data` (for `profile_picture`). Sending `role` or `phone_number` returns **400**.

Implementation: `accounts.services.users.update_current_user`, `MeUpdateSerializer`, `MeView.patch`.

## Who can do what

All roles (admin, teacher, accountant, staff) have the same self-service fields on `/profile`. Editing **other** people remains on **Staff** via `/api/v1/accounts/users/:id/`.

## Frontend

- Route: `sms-frontend/src/features/profile/`
- Auth store and `['me', 'session']` refresh after save so the navbar avatar and name update.

**Last reviewed:** 2026-10-13
