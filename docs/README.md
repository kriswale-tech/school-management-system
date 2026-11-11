# School Management System — Docs

Project status and reference docs for the SMS monorepo (`sms-backend` + `sms-frontend` + `platform-admin`).

> **Platform Admin & Billing architecture — start here:** [platform-admin-billing-architecture-v4.md](./platform-admin-billing-architecture-v4.md) is the durable source of truth for the locked **v4** blueprint (plans, capacity, subscriptions, invoices, communication credits) plus the accepted **v4.1 Messages & Communications Management** extension. It replaces all chat-only versions of that architecture.

| Doc | Purpose |
| --- | --- |
| [platform-admin-billing-architecture-v4.md](./platform-admin-billing-architecture-v4.md) | **Source of truth:** Platform Admin & SaaS billing v4 (locked) + v4.1 Messages/communications extension — plans, capacity, proration, credit ledger, provider economics |
| [platform-admin-schools.md](./platform-admin-schools.md) | Platform admin school directory: summary counts, list columns, overdue, and the create-school modal |
| [2026-11-11.md](./2026-11-11.md) | 11 Nov 2026: platform school billing controls, school Paystack checkout, messaging usage and bulk resend |
| [HOW_IT_WORKS.md](./HOW_IT_WORKS.md) | Simple walkthrough: signup → access → modules |
| [STATUS.md](./STATUS.md) | What is built vs what is left |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Stack, apps, multi-school model, API layout |
| [FEATURES.md](./FEATURES.md) | Feature inventory by domain (backend + frontend) |
| [fees.md](./fees.md) | How fees work (catalog, apply, payments, advances) |
| [term-transition.md](./term-transition.md) | Opening the next term: placement, graduation, fees, popup |
| [fees-backlog.md](./fees-backlog.md) | Deferred fees work (Excel, receipts, end-of-term, refunds) |
| [subject-groups-backlog.md](./subject-groups-backlog.md) | Subject-group student placement rules + deferred assessment lock |
| [subject-assessment-workspace.md](./subject-assessment-workspace.md) | Subject markbook + class-teacher Assessments page |
| [dashboard.md](./dashboard.md) | Admin, teacher, accountant, and staff dashboards, plus the activity feed |
| [profile.md](./profile.md) | Personal profile page, self-service fields, and `/accounts/me/` PATCH |
| [notifications.md](./notifications.md) | In-app personal inbox vs alerts vs activities; Tier 1 events; email templates |
| [guardian-communications.md](./guardian-communications.md) | Parent SMS/email outreach (events, settings, SMS shapes); distinct from staff inbox |
| [assessment-reports.md](./assessment-reports.md) | Report PDF generate (bulk Celery job), R2 existence, Send to guardians |
| [email-previews/notification-email-preview.html](./email-previews/notification-email-preview.html) | Visual preview of the shared notification email layout |

Related backend-only notes live under [`sms-backend/docs/`](../sms-backend/docs/) (e.g. Reports & Insights, teacher bulk import, [student bulk import](../sms-backend/docs/student-bulk-import.md)).

URL tab conventions for page-level panels are summarized in [HOW_IT_WORKS.md](./HOW_IT_WORKS.md) (§ URL tabs).

**Last reviewed:** 2026-11-11