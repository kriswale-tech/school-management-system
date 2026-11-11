# Notifications

Personal in-app inbox for school staff. Distinct from **alerts** (live digests) and **activities** (school-wide history).

**Status:** in-app Tier 1 shipped; staff email via Celery when `EMAIL_ENABLED`. Guardian SMS/email is separate — see [guardian-communications.md](./guardian-communications.md).

---

## How the three surfaces differ

| Surface | App | What it is |
| --- | --- | --- |
| **Alerts** | `schools` | Computed on read from current term state (fees owed, unreleased results, new enrollment **counts**). No per-user rows. Configurable under Settings → Alerts. |
| **Activities** | `activities` | School history / audit feed. Role-scoped lists for Insights. |
| **Notifications** | `notifications` | Event-backed personal messages for one `SchoolMembership`. Read/unread. Shown in the navbar **inbox** icon. |

Typical write path in a domain service:

1. Perform the mutation  
2. `record_activity(...)` (history)  
3. The activity bridge fans out Tier‑1 verbs into `Notification` rows for the right people  

Member-targeted events pass `notify_recipients=[...]` into `record_activity`.

---

## Backend

### App layout

```
sms-backend/notifications/
  models.py                 # Notification
  services/
    emit.py                 # notify / notify_many
    recipients.py           # admins, staff, class teachers, …
    bridge.py               # activity verb → recipients + titles
    inbox.py                # list / unread / mark read
  views.py / urls.py / serializers.py
```

Registered in `INSTALLED_APPS` as `notifications`. Mounted at `/api/v1/notifications/`.

### Model (`Notification`)

- `school`, `recipient` → `SchoolMembership` (multi-school safe)
- `actor` (optional), `event_type`, `title`, `body`, `href`
- `target_kind` / `target_id`, optional `activity` FK
- `read_at`, `email_status` (`skipped` for now; pending/sent/failed later)

### API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/notifications/` | Paginated inbox (`?unread=true`) |
| `GET` | `/notifications/unread-count/` | Badge count |
| `POST` | `/notifications/{id}/read/` | Mark one read |
| `POST` | `/notifications/read-all/` | Mark all read |

Requires an active school-scoped session (`HasActiveSchool`). There is no public create endpoint — only services emit.

### Tier 1 events (auto from activities)

| Event | Typical recipients |
| --- | --- |
| Scores published | Class teachers of that stream |
| Students approved | Admins + staff |
| Reports released | Class teachers |
| Reject / correction / reopen flow | Next actors (subject teacher, class teacher, admins/staff) |
| Class / subject teacher assigned | The assigned teacher |
| Student enrolled / left / reactivated / profile updated / guardian updated | Admins + staff + class teacher |
| Member invited / profile / phone / role changed | Affected membership (+ other admins for phone) |
| Term opened | All active memberships |

The actor is never notified about their own action.

A messaging credit shortfall is separate from the activity bridge. When a guardian send skips messages because the balance ran out, active admins and staff receive `messaging_credits`, including the person who sent. The link opens Messaging history filtered to those skipped messages.

Fee payments and subject-group placement stay on the **activity** feed only for now (Tier 2).

### Alerts note

Enrollment **alerts** (the digest count) are visible to **admin and staff**. Per-enrollment notices still go through notifications as above.

---

## Frontend

Two separate navbar icons:

1. **Bell** (`AlertsMenu`) — operational digests from `GET /schools/alerts/`. Badge = alert count. No mark-as-read (alerts stay live while the condition is true).
2. **Inbox** (`NotificationsMenu`) — personal inbox from `GET /notifications/`. Badge = unread count. Unread/read styling + mark all as read.

---

## Email (Anymail → Resend) + Celery

Outbound notification mail is separate from auth. **Login OTP** email is sent synchronously from `accounts.services.otp` (not via this Celery path).

### Flow

1. `notify()` creates the in-app row  
2. If `EMAIL_ENABLED` and the recipient has an email → `email_status=pending` and Celery task `notifications.deliver_notification_email`  
3. Worker renders templates and sends via **django-anymail** / **Resend**  
4. Status becomes `sent` or `failed` (`skipped` when no email / email disabled)

### Env

| Variable | Purpose |
| --- | --- |
| `EMAIL_ENABLED` | `true` to allow sends (keep `false` until Resend is ready) |
| `RESEND_API_KEY` | Resend API key |
| `DEFAULT_FROM_EMAIL` | Verified sender, e.g. `noreply@yourdomain.com` |
| `FRONTEND_URL` | CTA links + app logo URL |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` in Compose |

Compose: Redis on host **6380→6379** (host 6379 was already taken), plus `sms_celery_worker`. See `.env.example`.

### Templates

| File | Role |
| --- | --- |
| `base.html` | Brand header (school logo **or** app wordmark), school name, card, CTA, footer |
| `notification.html` | Greeting, title, body, optional meta chip |
| `notification.txt` | Plain-text twin |

Helpers: `email_context.build_notification_email_context`, `send_email.deliver_notification_email`.  
App logo: `sms-frontend/public/email/app-logo.svg`.  
Preview: [email-previews/notification-email-preview.html](./email-previews/notification-email-preview.html)

## Deferred (next)

- Per-membership notification preferences
- Tier 2 events (payments, fee catalog publish/apply, bulk import finished)
- Celery beat (not needed for notification send)
- Guardian SMS/email (ward enrolled on onboard + bulk import) — see [guardian-communications.md](./guardian-communications.md)

---

## Tests

`sms-backend/notifications/tests/test_inbox.py` covers list, unread count, mark read / mark all, membership scoping, and activity → notification fan-out for enrollments.
