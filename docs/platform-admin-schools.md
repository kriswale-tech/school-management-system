# Platform admin — school directory

Operator view of every school on the platform. This is the list at **Schools** (`/schools`) in `platform-admin`. The school detail page (`/schools/:id`) is separate and is not described here.

Signed-in platform operators only. Routes live under `/api/v1/platform/`.

## Summary strip

`GET /platform/schools/summary/`

Counts the whole platform. Search and the status filter do not change these numbers.

| Field | Meaning |
| --- | --- |
| `school_count` | Every school |
| `active_school_count` | Schools whose lifecycle status is `active` |
| `student_count` | Active student records |
| `staff_count` | Active school memberships (admins, teachers, accountants, and other staff) |
| `overdue_school_count` | Schools whose payment is overdue (rule below) |

## Directory list

`GET /platform/schools/?status=&search=&page=&page_size=`

Default page size is 10. The Schools page requests 100 and shows Previous / Next when the result is shorter than `count`. `search` matches name, phone, email, and region.

Each row:

| Column | Source |
| --- | --- |
| School | Name, with region underneath. An empty region is shown as an em dash. Region is the administrative region (for example Greater Accra), not the street address. |
| Admin | Active admin memberships: name, phone, and email. Further admins are counted as “+N more”. No admin is an em dash. |
| Plan | Current subscription plan name and interval (`monthly` or `annual`). No current subscription is an em dash. |
| Renewal | `current_period_end` when that subscription is `active` or `past_due`. Cancelled, expired, suspended, and missing subscriptions have no renewal date. |
| Status | School lifecycle: `pending`, `active`, `suspended`, `archived`. |
| Payment | **Overdue** or **Current**. Current is only an active subscription that is not overdue. Anything else is an em dash. |
| Staff / Students | Same counts as the summary, for this school only. |

**Overdue** is true when either:

- the current subscription is `past_due`, or billing has suspended the school (`billing_suspended_school`), or
- an `open` invoice has `due_at` in the past and `total_ghs` is still greater than `amount_paid_ghs`.

An unpaid opening invoice is due at the period start, so it counts as overdue as soon as that moment has passed.

**Actions** call `POST /platform/schools/<id>/status/` with `active`, `pending`, `suspended`, or `archived`. Suspend and archive ask for confirmation. The current status is not offered.

## Create school

The **Create school** button opens a modal. `POST /platform/schools/`.

School fields: name, phone (`024…` or `+233…`), email, region, category. The new school is `pending`.

Billing fields, required by the modal:

| Field | Meaning |
| --- | --- |
| `plan_code` | An active plan |
| `interval` | `monthly` or `annual` |
| `sms_sku_code` | Optional. Must be an active SMS SKU for that interval and plan. |
| `email_sku_code` | Optional. Same rule for email. |

The opening invoice is the plan price for that interval plus any selected add-on prices. The complimentary first year is **not** applied. Add-on credits are granted when that invoice is paid, not when the school is created.

A create request that omits `plan_code` still receives the complimentary annual subscription (Starter when the school has no students or staff, 100% off the application fee for 12 months, add-ons off). The modal always sends a plan, so that path is for other callers, including older invites that create a school without billing choices.

The API rejects a plan without an interval, an interval without a plan, an unknown plan, and an add-on whose channel, interval, or plan does not match. The modal only lists add-ons that already match, and it clears them when the plan or interval changes. The footer shows the opening invoice total before submit.
