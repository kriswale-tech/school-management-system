# SCHOOLASST — Platform Admin & Billing Architecture

**Version:** v4 (locked) + v4.1 Messages & Communications Management (accepted, docs-only)
**Document type:** Durable architecture source of truth
**Scope:** Platform Admin application, SaaS billing, communication credits, provider economics
**Currency:** GHS only (v1)
**Last updated:** 2026-11-06

---

## Document control

| Item | Detail |
| --- | --- |
| **v4 status** | **Approved and locked.** Approved as the Final Blueprint after the capacity-upgrade timing decision was confirmed. |
| **v4.1 status** | **Accepted and implemented (M0–M7).** Platform Admin Messages module is in the working tree; treat this document as the normative design. |
| **Supersedes** | v1–v3 blueprints and all chat-only versions of this architecture. |
| **Relationship** | v4.1 **extends** v4. It changes **no** locked v4 decision. Where they could appear to conflict, **v4 wins** and v4.1 must be re-opened. |
| **Why this file exists** | v4 previously lived only in a chat transcript. This document replaces chat as the source of truth. |

### How to read this document

- **Part 1** is the complete locked **v4** blueprint. Treat every statement there as a decision, not a suggestion.
- **Part 2** is the complete **v4.1** Messages & Communications Management extension — proposals awaiting a build go-ahead.
- **Part 3** is an as-built reference: what actually exists in the repository today, with file paths.

### Status vocabulary used throughout

| Marker | Meaning |
| --- | --- |
| **CONFIRMED** | Verified by reading the code in this repository, or verified provider capability that is already wired. |
| **NOT WIRED** | The provider documents the capability, but SCHOOLASST does not call it today. |
| **MANUAL** | No reliable API path; a human records the data in SCHOOLASST. |
| **DO NOT ASSUME** | Capability must not be designed around. Either it does not exist, or it is unverified. |
| **PROPOSED** | v4.1 design intent. Not built. Not approved for build. |

---

# Part 1 — Locked v4 blueprint

## 1.0 v4 status & change note

Approved direction for incremental implementation **after** an explicit go-ahead. No code, migrations, or repository changes were authorised by the approval itself.

**v4 change note (vs v3):** Section 7 was rewritten to lock **capacity-driven plan upgrade** billing rules — immediate plan effect, prorated **application-only** difference, preserved renewal date, untouched communications, and full billing history. Ordinary upgrades and downgrades remain **next-period** changes.

---

## 1.1 Locked product & architecture decisions

### Applications

- Monorepo keeps `sms-backend` and `sms-frontend`; add `platform-admin` (React + Vite).
- Shared Django API; separate layouts, auth realms, and deploys.
- One-VPS Docker Compose first; subdomains `app` / `admin` / `api` later **without redesign**.
- Preserve all existing school data, auth, curriculum, and school workflows.

### Access & operations

- Platform auth: **email/password + MFA**, a separate realm from the school phone-OTP realm.
- Platform roles: **Super Admin, Operations, Finance, Support, Curriculum**.
- Public school registration: **feature-flagged**; disabled once admin-created + invite onboarding is ready.
- Impersonation: **deferred**. Support ticketing: **deferred**.
- Currency: **GHS only** (v1).

### Capacity

- Plan tier is driven by **active student population** (`Student.is_active=True`).
- Configurable warning thresholds (for example 80%, 95%).
- At or over `student_max`: **block** new onboarding, bulk import, and **reactivation**.
- Never delete or lock existing student academic or fee records because of capacity.

### Mid-period communication changes

- Opt-in, opt-out, and SKU change take effect at the **next billing period**.
- **No prorated billing** for communications in v1.

### Existing schools (data migration)

- `status = active`.
- Complimentary **first-year application** subscription via promotion (list price + 100% discount → GH₵0).
- **SMS and email add-ons disabled**; **zero** communication credits.

### Credits & suspension

- Credits **never reset** on renewal, opt-out, interval change, or plan change.
- Credits are **preserved** if the school is suspended or the subscription expires.
- **Sending is blocked** while the school is suspended or the subscription is inactive.

### Money & ledger discipline

- Configurable **grace period** after a failed or overdue payment before suspension.
- All credit and financial truth lives in **immutable transaction / invoice records**.
- Cached balances are **projections only**; **no direct balance edits**.
- Distinct ledger types: recurring allocation, top-up, usage, promo grant, manual adjustment, and reversal.

---

## 1.2 Commercial model

### Application subscription

| Plan | Student capacity |
| --- | ---: |
| Starter | 1–100 |
| Basic | 101–300 |
| Standard | 301–600 |
| Premium | 601–1,000 |
| Enterprise | 1,001+ (`student_max` null / open-ended) |

- Monthly or annual application billing; prices are DB-configurable.

### Communication add-ons

- Optional SMS and/or Email **recurring** add-ons on the **same interval** as the application subscription.
- Catalog SKUs per `channel × interval`.
- **Top-ups** are one-off purchases; they do **not** change recurring add-on configuration.

### Not school-billed

- Authentication OTP SMS and email.
- Staff in-app notification emails.

These never debit a school's credit ledger.

### Billable SMS unit

- **Provider segments** — not messages, not recipients.

---

## 1.3 System topology

```text
School-Management-System/
├── sms-backend/       # Django: school APIs + /api/v1/platform/*
├── sms-frontend/      # School app (React/Vite)
├── platform-admin/    # NEW platform admin app (React/Vite)
├── docs/
└── compose.yml
```

**New backend apps:** `platform` (implemented as `platform_admin`), `billing`, `communications`
**Reuse:** `schools`, `accounts`, `academics`, `notifications.GuardianDelivery`, Celery, Arkesel, Resend
**Critical naming rule:** SaaS `billing.Payment` ≠ school `fees.Payment`. They are different domains and must never be merged or cross-queried.

**API layout:** `/api/v1/...` for school APIs, `/api/v1/platform/...` for platform APIs, Paystack webhook under platform billing.

**Auth:** separate platform vs school cookies/tokens; no shared session.

---

## 1.4 Data model (final)

### School (extend)

`status` (`pending` | `active` | `suspended` | `archived`); optional region/category; lifecycle timestamps.

### Catalog

`Plan`, `CommunicationAddonSku`, `TopUpPackage`, `PromotionCampaign`.

### Subscription

- `SchoolSubscription` (+ history rows), `pending_*` fields for next-period changes, period dates, `grace_period_ends_at`.
- `SubscriptionPeriod` — one row per billing cycle.

### Invoices & payments

`Invoice`, `InvoiceLine` (including kinds for **prorated upgrade / application difference**), `Payment`, `TopUpPurchase`, `PromotionRedemption`.

### Communications

- `CreditAccount` — cached balance per school × channel.
- `CreditLedgerEntry` — **append-only**, typed entries, idempotency keys.

### Platform

`PlatformMembership` (implemented as `PlatformUser` with a role), MFA, `PlatformAuditLog`, `PlatformSettings` (`public_school_registration_enabled`, `subscription_grace_days`).

---

## 1.5 Billing lifecycle

```text
Period open
  → Apply pending_* (ordinary plan / interval / addons)
  → Invoice application + enabled addons − promotions
  → Collect payment (or GH₵0)
  → allocation_recurring for enabled addons
  → Advance period dates

Payment fails → past_due + grace → after grace still unpaid → suspend
  (credits preserved; sends blocked while suspended/inactive)
```

Mid-period **communication** changes stay pending until the next period. There is **no communication proration**.

---

## 1.6 Billing interval change (monthly ↔ annual)

- Scheduled via `pending_interval`; effective at **`current_period_end`**.
- Credits unchanged.
- Add-on SKUs must match the new interval — auto-map when a single SKU exists for the target interval; otherwise require explicit selection before renewal can invoice.
- The first invoice on the new interval uses the new application price plus new-interval add-on prices; allocation uses the new SKU's credits (**additive**, never replacing a balance).
- **No** mid-period interval flip and **no** interval proration in v1.

---

## 1.7 Plan upgrade / downgrade (v4)

### 1.7.1 Ordinary plan upgrade (not capacity-blocked)

- The school or platform requests a higher plan **without** being blocked on enrol / import / reactivate.
- Scheduled via `pending_plan`; takes effect at the **next billing period**.
- At renewal: full new plan price for the school's existing interval. Communication add-ons unchanged unless separately pending.

### 1.7.2 Ordinary plan downgrade

- Allowed **only** if `active_student_count <= new_plan.student_max`.
- Effective at the **next billing period** only.
- Communication add-ons and credits unchanged unless separately pending.

### 1.7.3 Capacity-driven immediate upgrade (locked)

Triggered when a school is at or over capacity and needs a higher plan to **unblock** student enrolment, bulk import, or reactivation.

| # | Rule |
| --- | --- |
| 1 | The higher-capacity plan **takes effect immediately**. |
| 2 | Charge **only the prorated difference** between old and new **application** plan prices for the **remaining** current billing period. |
| 3 | **Preserve** the original subscription **renewal date** (`current_period_end` / `renewal_at` unchanged). |
| 4 | Do **not** change communication add-on flags, SKUs, or credit balances. |
| 5 | At the **next renewal**, charge the **full** price of the **new** plan at the school's existing monthly or annual interval, plus any enabled communication add-ons as usual. |
| 6 | Record the upgrade, prorated charge, invoice line(s), and payment in **billing history**. |

**Proration formula (application only):**

```text
remaining_fraction = remaining_days_in_period / total_days_in_period
amount_due         = max(0, (new_app_price - old_app_price) * remaining_fraction)
```

- Prices are the catalog **application** prices for the school's **current interval** (monthly or annual).
- If `amount_due` is 0 (for example identical prices — should not happen across tiers), still record a zero or informational invoice / audit entry for the plan change.
- **No communication lines** on a capacity-upgrade invoice.
- On successful payment (or GH₵0): set `subscription.plan` to the new plan immediately; capacity checks use the new `student_max` right away.
- Period boundaries and renewal date stay exactly as they were before the upgrade.

**Billing history must include:**

- A plan change event: old plan → new plan, reason `capacity_upgrade`, timestamp, actor.
- An invoice with a line kind such as `application_proration` / `prorated_upgrade`, described with old/new plan and the period remainder.
- A payment record linked to that invoice (Paystack, or complimentary/zero where applicable).

**Explicitly *not* part of a capacity upgrade:** interval change, add-on opt-in/out, credit grants or debits, resetting period dates.

### 1.7.4 Summary

| Change | When it applies | Money now | Renewal date | Comms |
| --- | --- | --- | --- | --- |
| Capacity-driven upgrade | Immediate | Prorated **application** difference for the remainder | Unchanged | Unchanged |
| Ordinary upgrade | Next period | Full new application price at renewal | Normal advance | Unchanged unless pending |
| Downgrade | Next period | Full new application price at renewal | Normal advance | Unchanged unless pending |

---

## 1.8 Communication usage rules

- **Typed ledger only.** Balances move through ledger entries, never by direct edit.
- A send is allowed when: the school is active, the subscription is `active` **or** `past_due` within grace, and the balance is sufficient.
- Opted-out add-ons may still **drain remaining credits** — opt-out stops future allocations, not spending.
- Suspended or inactive: **no send**; credits are kept.
- OTP and staff notification email **never** debit a school ledger.

---

## 1.9 School-facing visibility

The school application must show:

- Current plan and a capacity meter.
- Billing interval.
- Current **and pending** add-ons.
- Next renewal date.
- Upcoming invoice.
- Accumulated SMS and email balances.
- Invoice and payment history — **including capacity-upgrade proration invoices**.
- Top-ups.

Messaging surfaces: policies, delivery history, templates (phased), balances, and segment estimates.

---

## 1.10 Platform-facing scope (v1)

- Schools: list, create, invite, suspend.
- Catalog: plans, add-on SKUs, top-up packages, promotion campaigns, grace period, public-registration flag.
- Billing: subscriptions, invoices, payments.
- Communications: balances, ledger.
- Curriculum administration.
- Audit log.

**Deferred:** impersonation, support tickets, deep health dashboards.

---

## 1.11 Migration of existing tenants

- Set all existing schools to `status = active`.
- Grant a complimentary first-year **application** subscription (promotion, 100% discount).
- Communication add-ons **off**; credit balances **zero**.
- Keep the public-registration flag **on** until invite onboarding ships.

---

## 1.12 Implementation roadmap (v4 phases)

| Phase | Scope |
| --- | --- |
| **0** | Platform-admin shell, auth + MFA, settings, audit |
| **1** | School status, create + invite, flagged signup, migrate existing schools |
| **2** | Plans, subscriptions, invoices, campaigns, grace, capacity gates, **capacity-upgrade proration** |
| **3** | Communication SKUs, ledger, allocations, usage debit, send gates |
| **4** | School Billing UI + Messaging shell |
| **5** | Paystack renewals, top-ups, interval-change pending UX |
| **6** | Templates, curriculum UI, richer dashboard |
| **7+** | Read-only support access, announcements, provider sync |

See [Part 3](#part-3--as-built-reference) for what is actually present in the repository today.

---

## 1.13 Invariants checklist (14 items — all must hold)

1. Renewal **never** zeroes communication balances.
2. Opt-out **never** deletes credits.
3. Suspend / expire **never** deletes credits; sends are blocked instead.
4. OTP and staff notification email **never** debit a school ledger.
5. Add-on interval **always** equals the application interval.
6. Interval change remaps SKUs; credits unchanged.
7. Mid-period add-on changes apply next period; **no** communication proration.
8. Balances change **only** via ledger transactions.
9. Capacity block covers **onboard, import, reactivate**.
10. Existing schools: free application year, add-ons off, zero credits.
11. The school can see subscription, add-ons, renewal, upcoming invoice, and balances.
12. Grace is configurable; suspension happens after grace if still unpaid.
13. **Capacity upgrade:** immediate plan change; prorated application difference only; renewal date preserved; communications untouched; full new plan at next renewal; complete billing history.
14. **Ordinary** upgrade/downgrade: next period only.

---

# Part 2 — v4.1 Messages & Communications Management

## 2.0 Status

**Documentation only.** v4.1 extends approved v4 and **does not change any locked v4 decision**. It has been **accepted for documentation**; there is **no authorisation to implement**, migrate, or modify application code until a separate explicit go-ahead is given.

**What v4.1 adds:** a Platform Admin **Messages** module covering SMS and email pricing, provider accounts and expenses, school usage analytics, free/sponsored messaging, provider reconciliation, and messaging profitability — built on the **existing** `CreditAccount` / `CreditLedgerEntry`, `GuardianDelivery`, Arkesel, Resend, Paystack, and Celery foundations.

---

## 2.1 Investigation findings — as-built vs documented

This section is deliberately blunt. Everything marked CONFIRMED was read in this repository; everything else is flagged so the design does not rest on assumptions.

### 2.1.1 School credit wallets — CONFIRMED

| Aspect | Reality |
| --- | --- |
| Models | `communications/models/accounts.py` → `CreditAccount`, `CreditLedgerEntry` |
| Account shape | One `CreditAccount` per `(school, channel)`, unique constraint; `balance` is a **`PositiveIntegerField`** — it **cannot** go negative |
| Ledger shape | `CreditLedgerEntry` is append-only: `delta`, `balance_after`, unique `idempotency_key`, `occurred_at`, `metadata` JSON |
| Ledger links | FKs to `billing.SubscriptionPeriod`, `billing.Invoice`, `notifications.GuardianDelivery`, `platform_admin.PlatformUser` |
| Entry types | `allocation_recurring`, `topup`, `promo_grant`, `usage_debit`, `manual_adjust`, `reversal` |
| Writer | `communications/services/ledger.py` → `write_ledger_entry()` takes `select_for_update()` on the account, refuses negative balances unless `allow_negative`, and is **idempotent on `idempotency_key`** |
| Service helpers | `allocate_recurring`, `grant_topup`, `debit_usage`, `reverse_usage`, `manual_adjust` |
| Balances accumulate | No period reset anywhere in the writer or allocation path |

**Implication for v4.1:** the wallet layer is sound and must not be duplicated. All v4.1 credit movement goes through `write_ledger_entry()`.

### 2.1.2 Guardian metering and the debit-after-submit pattern — CONFIRMED

Path: `notifications/services/deliver_guardian.py`

1. `filter_items_by_credits()` (in `communications/services/gates.py`) pre-checks the running balance per school and **splits** items into sendable and skipped. It **does not debit**.
2. Items are submitted to the provider in batches (Arkesel ≤100 recipients, Resend ≤100 emails).
3. **After** a successful submit, `_debit_after_send()` calls `debit_usage(idempotency_key=f'usage:{item["idempotency_key"]}')`.
4. `GuardianDelivery.credits_charged` and `.segments` are then written back on the row.

**Known gap, stated honestly:** if the balance is exhausted between the pre-check and the post-submit debit (concurrent workers), `debit_usage` raises `InsufficientCredits`, the code **logs an error and returns 0**, and the message has been sent **without a debit**. Because `CreditAccount.balance` is a `PositiveIntegerField`, a negative balance is not representable, so there is no "overdraft" path today. v4.1 must decide between (a) allowing a negative/overdraft ledger entry for accepted sends, or (b) recording an explicit unbilled-send reconciliation item. **This is an open decision, not a settled one.**

**`reverse_usage` is defined and never called.** A repository-wide search finds exactly one occurrence: its definition in `communications/services/ledger.py`. There is **no wired refund path** for a send that fails after provider acceptance.

### 2.1.3 SMS segment calculation — CONFIRMED, limits hardcoded

Path: `communications/services/segments.py`

- GSM-7 basic set per 3GPP TS 23.038; extended set `^ { } \ [ ~ ] | €`.
- `_gsm7_septet_length()` correctly counts **extended characters as 2 septets**.
- Limits are **hardcoded constants in code**: `160` single / `153` multipart for GSM-7, `70` single / `67` multipart for UCS-2.
- `analyze_sms()` returns `{characters, encoding, segments, credits_per_recipient}` where `credits_per_recipient == segments` (1:1).
- `units_for_channel()` returns `max(1, segment_count)` for SMS and a flat **`1`** for email.
- Empty message returns 1 segment.

**Gap:** there is no database configuration for encoding limits or unit prices, and no pricing history. Changing a limit today means changing code.

### 2.1.4 Arkesel — CONFIRMED / NOT WIRED

Path: `shared/services/arkesel_sms.py`

| Capability | Status | Detail |
| --- | --- | --- |
| Send | **CONFIRMED** | `POST https://sms.arkesel.com/api/v2/sms/send`, batched to `ARKESEL_SMS_BATCH_SIZE = 100` identical-body recipients |
| Delivery callback registration | **CONFIRMED** | `callback_url` is attached to each send, pointing at `/api/v1/webhooks/arkesel/sms-dlr/` |
| DLR webhook receiver | **CONFIRMED** | `notifications/views_webhooks.py` → `ArkeselSmsDlrWebhookView`, registered unauthenticated in `core/urls.py` |
| Status lookup | **CONFIRMED** | `GET https://sms.arkesel.com/api/v2/sms/{message_id}` via `get_sms_status()`, plus a safety-net Celery beat poll every 5 minutes (`notifications.poll_pending_sms_status`) |
| Error classification | **CONFIRMED** | HTTP 401/422/429/5xx → `failed`; timeouts/SSL/connection → **`unknown`** (submission unconfirmed) |
| Account balance (`GET /api/v2/clients/balance-details`) | **NOT WIRED** | Documented by Arkesel; **no client exists in this repository**. This is the automatable balance-sync hook. |
| Programmatic credit purchase | **DO NOT ASSUME** | Not supported. Wallet top-ups must be recorded **MANUAL**ly. |
| Per-message segment/credit cost on the send response | **DO NOT ASSUME** | Not parsed or relied upon today. The **local** calculator is the source of truth for school debits. |
| Batch message reports | **NOT WIRED** | Documented; useful later for reconciliation jobs. |

### 2.1.5 Resend — CONFIRMED / NOT WIRED

Paths: `notifications/services/resend_batch.py`, Anymail configuration in `core/settings.py`

| Capability | Status | Detail |
| --- | --- | --- |
| Batch send | **CONFIRMED** | `POST https://api.resend.com/emails/batch`, ≤100 per request, header `x-batch-validation: permissive` so one bad address does not fail the batch |
| Per-item error mapping | **CONFIRMED** | `errors[].index` is mapped back to the originating item key |
| Fallback transport | **CONFIRMED** | When `EMAIL_ENABLED` is false or no API key is set, falls back to Django/Anymail single sends (console/locmem in dev and tests) |
| Staff notification email | **CONFIRMED** | Via Anymail/Django mail in the `notifications` app, Celery-driven |
| Delivery webhooks (`email.delivered`, `email.bounced`, `email.complained`, `email.delivery_delayed`, …) | **NOT WIRED** | Documented by Resend with signature verification; **no endpoint exists**. Only the Arkesel DLR webhook is registered. **Consequence: guardian email rarely advances past `submitted`.** |
| Usage API (`GET /usage`) | **NOT WIRED** | Documented; would give monthly/daily sent vs limit |
| Prepaid credit wallet | **DO NOT ASSUME** | **Does not exist.** Resend bills by subscription plus overage. |
| Invoice / billing amounts via API | **DO NOT ASSUME** | Record provider spend **MANUAL**ly or from a configured plan cost. |

### 2.1.6 Outbound delivery record — CONFIRMED

`notifications.GuardianDelivery` (in `notifications/models.py`) is the single outbound record for guardian traffic:

- **Event types:** `ward_enrolled`, `payment_receipt`, `debt_reminder`, `report_ready`, `next_term_fees`.
- **Channels:** `sms`, `email`.
- **Statuses:** `queued`, `processing`, `submitted`, `delivered`, `failed`, `unknown`, `skipped`, plus legacy `sent` retained for old rows.
- **Fields of billing interest:** `segments`, `credits_charged`, `provider_message_id` (indexed), `provider_status`, `skip_reason`, `idempotency_key` (unique), `source_delivery` (self-FK for retries), `status_updated_at`, and the split `error_message` / `user_error_message` pair.

**Gap:** there is **no billing classification field**. Paid guardian traffic, platform-funded traffic, and sponsored traffic are not distinguishable at the row level. OTP SMS and staff notification email are not recorded in this table at all, so **platform-funded provider cost is currently invisible**.

### 2.1.7 Send gates — CONFIRMED

Path: `communications/services/gates.py`

- `communications_billing_active(school)` **returns `True` unconditionally** — guardian messaging always meters; there is no legacy free path.
- `school_allows_sends()` blocks when the school is inaccessible, `suspended`, or `archived`.
- `subscription_allows_sends()` allows `active`, allows `past_due` while within `grace_period_ends_at`, blocks `past_due_grace_expired` and every other status. A school with **no** subscription row is still allowed, gated purely by credits.
- `can_send_channel()` combines the above with a balance check and returns a `SendEligibility` dataclass.

### 2.1.8 Platform Admin navigation — CONFIRMED

At the time of this investigation the shell exposed **Overview** (`/`), **Schools** (`/schools`, `/schools/:id`), **Plans** (`/plans`), **Payments** (`/payments`), and **Settings** (`/settings`), and had no Messages entry.

The shell now also includes **Discounts** (`/discounts`) and **Messages** (`/messages`, role-gated). School directory behavior is in [platform-admin-schools.md](./platform-admin-schools.md).

### 2.1.9 Existing platform communications & billing APIs — CONFIRMED

`communications/urls_platform.py`:

| Route | Purpose |
| --- | --- |
| `GET skus/` | Add-on SKU catalog |
| `POST skus/seed/` | Seed SKU catalog |
| `GET schools/<uuid>/credits/` | Per-school balances |
| `GET schools/<uuid>/ledger/` | Per-school ledger |
| `POST schools/<uuid>/addons/schedule/` | Schedule add-on change (next period) |
| `POST schools/<uuid>/credits/adjust/` | Manual adjustment |

`billing/urls_platform.py`:

| Route | Purpose |
| --- | --- |
| `plans/`, `plans/seed/`, `plans/<uuid>/` | Plan catalog |
| `topups/`, `topups/seed/`, `topups/<uuid>/` | Top-up packages |
| `payments/` | Platform-wide payments |
| `schools/<uuid>/subscription/` | Subscription detail |
| `schools/<uuid>/subscription/schedule-change/` | Next-period plan/add-on change |
| `schools/<uuid>/subscription/capacity-upgrade/` | **v4 §7.3 immediate capacity upgrade** |
| `schools/<uuid>/subscription/change-interval/` | Pending interval change |
| `schools/<uuid>/invoices/`, `schools/<uuid>/payments/` | Billing history |
| `invoices/<uuid>/mark-paid/` | Manual settlement |

School-facing routes already exist for billing (`plans`, `subscription`, `capacity`, `upcoming`, `invoices`, `topups`, `payments`), communications (`skus`, `credits`, `ledger`, `addons/schedule`), and messaging (`overview`, `deliveries`, `templates`).

### 2.1.10 Platform roles & audit — CONFIRMED

- `platform_admin/models/users.py` → `PlatformUser.Role`: `super_admin`, `operations`, `finance`, `support`, `curriculum`.
- `platform_admin/permissions.py` → `IsPlatformAuthenticated` plus `HasPlatformRole`, which reads `view.allowed_roles`.
- `platform_admin/models/audit.py` → `PlatformAuditLog(actor, action, target_type, target_id, detail JSON, ip_address)`.
- `platform_admin/models/settings.py` → `PlatformSettings(public_school_registration_enabled, subscription_grace_days)`.

### 2.1.11 Gaps v4.1 closes

- No SMS encoding **configuration** and no pricing history (provider cost vs school selling price).
- No platform-wide messaging dashboard and no school usage matrix.
- No provider purchase or expense ledger.
- No first-class `PAID` / `FREE` / `SPONSORED` classification on sends.
- No Arkesel balance sync and no Resend usage sync.
- No Resend delivery webhooks — email status is effectively terminal at `submitted`.
- No wired refund on post-acceptance failure (`reverse_usage` is dead code).
- No messaging P&L based on historical cost snapshots.
- No visibility of platform-funded provider cost for OTP and staff email.

---

## 2.2 Preserved v4 decisions (explicit)

All of v4 §§1.1–1.13 remain locked. Restated because v4.1 touches adjacent territory:

- Credits never reset; preserved on suspend/expire; sends blocked when suspended or inactive.
- OTP and staff notification email never debit a school ledger.
- Add-on interval equals application interval; mid-period communication changes apply next period; no communication proration.
- Capacity-driven upgrade: immediate, prorated **application** only, renewal date unchanged, **communications untouched**.
- GHS only; immutable ledger and invoice discipline; balances move only via ledger entries.
- Existing schools: free application year, add-ons off, zero credits.
- Billable SMS unit remains **provider segments**.

> **v4.1 does not introduce a second school wallet or a competing ledger.** There is exactly one school credit system: `CreditAccount` + `CreditLedgerEntry`.

---

## 2.3 Credit ↔ price lock for v4.1

This is the single most important clarification in v4.1, because conflating units and money is how messaging P&L goes wrong.

```text
1 billable SMS segment      = 1 school SMS credit        (unchanged from v4)
1 accepted email recipient  = 1 school email credit      (unchanged from v4)

Schools BUY credits in GHS via:
    CommunicationAddonSku.price_ghs   (recurring, credits_per_period)
    TopUpPackage.price_ghs            (one-off, credits)

Unit prices in v4.1 (school_price_per_segment_ghs, school_price_per_credit_ghs)
are ECONOMICS / P&L REFERENCE VALUES ONLY.
They are NOT charged at send time. Nothing is billed in GHS at send time.
```

Consequences:

- Metering at send time stays **credits**, never GHS.
- Package and SKU GHS prices remain the actual revenue instruments.
- Unit prices exist so Finance can value consumed units, compute gross margin, and design packages. Optionally, later: auto-suggest package prices from `unit price × credits`.
- Changing a unit price **never** re-values historical sends — snapshots govern (see §2.6).

---

## 2.4 Platform Admin navigation — the 8 Messages areas

Add a **Messages** section to the Platform Admin sidebar, implemented as nested routes under `/messages/*` (or tabs under one Messages shell) consistent with the current `AppShell` navigation pattern.

| # | Area | Route (proposed) | Primary purpose |
| --- | --- | --- | --- |
| 1 | **Overview** | `/messages` | Platform-wide messaging dashboard: volumes, balances, spend, revenue, margin |
| 2 | **SMS Pricing & Configuration** | `/messages/sms-pricing` | Encoding configs, segment limits, provider cost, reference selling price, pricing history, live calculator |
| 3 | **Email Pricing & Configuration** | `/messages/email-pricing` | Email credit unit price, estimated provider cost, billing unit, history, Resend account state |
| 4 | **Provider Credits & Accounts** | `/messages/providers` | Arkesel balance and purchases; Resend plan, allowance, usage, expenses; sync status |
| 5 | **School Usage & Analytics** | `/messages/schools` | Searchable per-school usage matrix and individual school reports |
| 6 | **Free & Sponsored Messaging** | `/messages/free` | Classification dashboards, allowances, budgets, platform-funded expense |
| 7 | **Revenue & Profitability** | `/messages/profitability` | SMS, email, and combined messaging P&L — cash view and usage view |
| 8 | **Transactions & Purchase History** | `/messages/transactions` | Unified, filterable, exportable transaction feed |

Existing school-detail credit cards stay where they are; they should **deep-link** into the Messages school report rather than duplicating it.

---

## 2.5 The five money/credit layers — never conflate

| Layer | Meaning | Source of truth |
| --- | --- | --- |
| **1. Provider wallet / plan** | Arkesel prepaid SMS balance; Resend monthly allowance | `ProviderBalanceSnapshot`, `ResendUsageSnapshot`, plus `ProviderPurchase` / `ProviderExpense` |
| **2. School credits (units)** | SMS/email units a school can spend | `CreditAccount` + `CreditLedgerEntry` |
| **3. Cash from schools (GHS)** | Paid for add-ons and top-ups | `billing.Invoice`, `billing.Payment`, top-up purchases |
| **4. Cash to providers (GHS)** | Paid to Arkesel / Resend | `ProviderPurchase`, `ProviderExpense` (manual or synced) |
| **5. Usage economics** | Consumed units × snapshot sell/cost | Delivery rows + pricing snapshots |

Two statements that must be true everywhere in the UI and in every report:

- **Unused school credits are not consumed revenue.** A credit sold is cash received and a liability to deliver; it becomes usage revenue only when consumed.
- **A full Arkesel top-up is not the cost of messages already sent.** A wallet purchase is cash out; cost of delivery accrues as segments are consumed.

No dashboard tile may add numbers from different layers together.

---

## 2.6 Data model proposals

All of these are **PROPOSED**. Nothing here is built.

### 2.6.1 Keep exactly as-is

`CreditAccount`, `CreditLedgerEntry`, `CommunicationAddonSku`, `TopUpPackage`, `GuardianDelivery`, `billing.Invoice` / `InvoiceLine` / `Payment`, `PromotionCampaign` / `PromotionRedemption`, `SchoolSubscription` / `SubscriptionPeriod`, `Plan`.

v4.1 **extends**; it does not replace.

### 2.6.2 `SmsEncodingConfig` — PROPOSED

One active row per encoding, versioned by `effective_from` + `is_active`.

| Field | Type / notes |
| --- | --- |
| `encoding` | `gsm7` \| `ucs2` (extensible for future encodings) |
| `provider_cost_per_segment_ghs` | Decimal — what Arkesel costs us per segment |
| `school_price_per_segment_ghs` | Decimal — **reference unit economics only** (see §2.3) |
| `single_segment_limit` | Integer, default 160 (GSM-7) / 70 (UCS-2) |
| `multipart_segment_limit` | Integer, default 153 (GSM-7) / 67 (UCS-2) |
| `effective_from` | DateTime |
| `effective_to` | DateTime, nullable |
| `is_active` | Boolean |
| `changed_by` | FK `platform_admin.PlatformUser` |
| `created_at` | DateTime |

**Immutability rule:** historical delivery and ledger rows carry **snapshots** of the limits and costs that were used. Editing a config row **never** rewrites history. Config edits create a new version; they do not mutate the old one.

### 2.6.3 `EmailPricingConfig` — PROPOSED

| Field | Type / notes |
| --- | --- |
| `school_price_per_credit_ghs` | Decimal — reference unit economics |
| `estimated_provider_cost_per_email_ghs` | Decimal — allocation estimate, because Resend bills by subscription + overage, not per email |
| `billing_unit` | Fixed by v4: **1 credit = 1 provider-accepted recipient delivery attempt** |
| `effective_from`, `effective_to`, `is_active`, `changed_by` | Same versioning discipline as SMS |

Any cost derived from `estimated_provider_cost_per_email_ghs` must be **labelled "estimated"** wherever it appears.

### 2.6.4 Provider accounts, purchases, expenses, snapshots — PROPOSED

**`ProviderAccount`**
`provider` (`arkesel` | `resend`), `channel`, `display_name`, `api_status`, `last_synced_at`, `metadata` JSON.

**`ProviderBalanceSnapshot`** (Arkesel)
`provider_account` FK, `sms_balance`, `main_balance_text`, `raw_response` JSON, `captured_at`, `source` (`api` | `manual`).
Append-only. One row per sync or manual capture. Never updated in place.

**`ProviderPurchase`** (prepaid wallet top-ups — Arkesel today)
`provider`, `channel`, `amount_ghs`, `credits_or_units`, `effective_cost_per_unit` (derived and stored), `provider_reference`, `purchased_at`, `payment_method`, `notes`, `recorded_by` FK PlatformUser.
**MANUAL** by necessity: Arkesel has no programmatic purchase API.

**`ProviderExpense`** (non-wallet costs — Resend subscription and overage, and anything similar)
`provider`, `expense_kind` (`subscription` | `overage` | `other`), `period_start`, `period_end`, `amount_ghs`, `units` (nullable), `notes`, `recorded_by`, `source` (`manual` | `import`).

**`ResendUsageSnapshot`**
From the Resend Usage API: monthly used, daily used, limit, sent/received counts, `raw_response`, `captured_at`, `source`.

### 2.6.5 Billing classification on every outbound attempt — PROPOSED

**Extend `GuardianDelivery`:**

| Field | Notes |
| --- | --- |
| `billing_classification` | `paid` \| `free` \| `sponsored`; default `paid` for guardian traffic (preserves current behaviour) |
| `allowance` / `campaign` | Nullable FK, set for `free` / `sponsored` |
| `provider_cost_snapshot_ghs` | Nullable Decimal — cost per unit at send time × units |
| `school_unit_price_snapshot_ghs` | Nullable Decimal — reference sell price at send time |
| `encoding_snapshot` | `gsm7` / `ucs2` as actually computed |
| `segment_limit_snapshot` | JSON: the single/multipart limits used for this send |

Backfill policy for existing rows: leave snapshots null and treat them as "pre-v4.1, unpriced" in reports rather than retroactively guessing. Reports must handle null snapshots explicitly.

**New `PlatformOutboundDelivery`** (alternatively `SystemDelivery`) — PROPOSED

The purpose is to make platform-funded provider cost **visible** without ever touching a school wallet.

- Covers OTP SMS, OTP email, staff notification email, and future platform broadcasts.
- Fields mirror the billing-relevant subset of `GuardianDelivery`: `school` (nullable — OTP may precede school context), `purpose`/`event_type`, `channel`, `provider`, `provider_message_id`, `status`, `segments`, `billing_classification` (normally `free`), `provider_cost_snapshot_ghs`, `encoding_snapshot`, `idempotency_key`, timestamps.
- **Hard rule:** rows in this table are **never** linked to a `usage_debit` ledger entry. v4 invariant 4 is enforced structurally, not by convention.

**Sponsored campaigns and allowances** — PROPOSED

Prefer a **new** `MessagingAllowancePolicy` over overloading `PromotionCampaign`, so application-subscription promotions stay separate from messaging budgets:

| Field | Notes |
| --- | --- |
| `scope` | `school` \| `platform` |
| `school` | Nullable FK |
| `channel` | `sms` \| `email` |
| `monthly_free_units` | Integer |
| `daily_limit_units` | Integer, nullable |
| `applies_to_events` | JSON list of `GuardianDelivery.EventType` values, or empty = all |
| `budget_ghs` | Nullable — platform-wide spend cap |
| `alert_thresholds` | JSON, e.g. `[0.8, 0.95]` |
| `starts_at`, `ends_at`, `is_active`, `created_by` | |

Consumption against an allowance is tracked by counting classified delivery rows in the window, not by a second wallet.

### 2.6.6 Reconciliation records — PROPOSED

**`ProviderReconciliationRun`**
`provider`, `channel`, `window_start`, `window_end`, `status`, `matched_count`, `unmatched_count`, `discrepancy_count`, `started_at`, `finished_at`, `triggered_by`, `error_detail`.

**`ProviderReconciliationItem`**
`run` FK, `internal_delivery_type` + `internal_delivery_id`, `provider_message_id`, `discrepancy_type` (`missing_internally` | `missing_at_provider` | `status_mismatch` | `unit_count_mismatch` | `unbilled_send`), `provider_payload` JSON, `resolution` (`open` | `accepted` | `adjusted` | `ignored`), `resolution_note`, `resolved_by`, `resolved_at`.

**Hard rule:** reconciliation **never** mutates historical ledger entries. A correction is a **new** `manual_adjust` or `reversal` entry with the reconciliation item referenced in `metadata`.

---

## 2.7 SMS encoding configuration and calculator rules

Reuse and **config-drive** `communications/services/segments.py`. The algorithm is already correct; only the limits move from code to configuration.

```text
1. Detect encoding:
     every char in GSM-7 basic ∪ GSM-7 extended  → gsm7
     otherwise                                    → ucs2

2. Compute length:
     gsm7 → septets, where an extended char (^ { } \ [ ~ ] | €) counts as 2
     ucs2 → UTF-16 code-unit count (len(text) in Python terms)

3. Load limits from the ACTIVE SmsEncodingConfig for that encoding
     (NOT from hardcoded constants)

4. Segment count:
     if length <= single_segment_limit:  segments = 1
     else:                               segments = ceil(length / multipart_segment_limit)
     empty message:                      segments = 1

5. School debit units = max(1, segments)

6. Template preview and estimates use the RENDERED body
     (after variable substitution), never the raw template

7. Provider variance:
     if Arkesel ever returns credits/segments for a message id,
     store it on the delivery row and FLAG the variance against the
     local count. Finance investigates. DO NOT auto-rewrite the
     school ledger without an explicit refund/adjustment decision.
```

Worked examples for the default GSM-7 limits:

```text
"Hello"                      →  5 septets            → 1 segment
160 plain GSM-7 chars        →  160 septets          → 1 segment
161 plain GSM-7 chars        →  161 septets          → ceil(161/153) = 2 segments
80 chars incl. 5 "€"         →  85 septets           → 1 segment  (extended = 2 each)
"Fees due — GH₵500"          →  contains "—" (U+2014) → UCS-2 → 1 segment (≤70)
71 UCS-2 chars               →  71 units             → ceil(71/67)  = 2 segments
```

The platform calculator endpoint must return exactly what production would debit for the same body. Any divergence between the calculator and the live send path is a defect.

---

## 2.8 Email pricing and Resend monitoring

### Billing unit (locked by v4)

**1 email credit = 1 provider-accepted recipient delivery attempt.** Acceptance by Resend is the billable event, not delivery confirmation. This matches `units_for_channel()` returning 1 per email and the debit-after-accept pattern.

### Configurable fields

- `school_price_per_credit_ghs` — reference unit economics.
- `estimated_provider_cost_per_email_ghs` — allocation estimate; always labelled estimated.
- `effective_from` / `is_active` / `changed_by` — versioned, immutable history.

### Resend account monitoring — what is real

| Metric | Status | How |
| --- | --- | --- |
| Monthly / daily volume used vs limit | **NOT WIRED** (available) | Resend Usage API `GET /usage` → `ResendUsageSnapshot` |
| Accepted email count | **CONFIRMED** (internal) | Count of `GuardianDelivery` rows reaching `submitted` |
| Delivered / bounced / complained / delayed | **NOT WIRED** | Requires Resend webhooks; **today email status does not advance past `submitted`** |
| Subscription plan name and monthly cost | **MANUAL** | `ProviderExpense(expense_kind='subscription')` |
| Included monthly allowance | **MANUAL** or from Usage API limit | Config + snapshot |
| Overage usage and charges | **MANUAL** for charges; usage from Usage API | `ProviderExpense(expense_kind='overage')` |
| Sending domain verification status | **NOT WIRED** | Resend Domains API; nice-to-have |
| API connection status | **PROPOSED** | Derived from last sync attempt on `ProviderAccount` |
| Webhook health | **PROPOSED** | Derived from last received event timestamp and signature-failure counters |
| Dollar invoice amounts via API | **DO NOT ASSUME** | Record manually |

### Resend webhook requirements (when built)

- Public, unauthenticated endpoint at `POST /api/v1/webhooks/resend/`, following the existing Arkesel DLR precedent in `core/urls.py`.
- **Verify the signature** (Svix-style headers) before processing. Reject unverified payloads and count the rejection.
- **Idempotent** on the provider event id / `svix-id`: a duplicate event must not change status twice, and must never cause a second debit or a second refund.
- Match events to `GuardianDelivery.provider_message_id` (already indexed) or `PlatformOutboundDelivery`.
- Record webhook processing failures for operational visibility rather than silently dropping them.

---

## 2.9 Provider purchases, expenses, and snapshots

### Arkesel (prepaid wallet model)

| Operation | Status | Design |
| --- | --- | --- |
| Balance read | **NOT WIRED → automate** | Celery beat sync (e.g. hourly) plus an on-demand "Sync now" action; each read appends a `ProviderBalanceSnapshot` |
| Credit purchase | **MANUAL** | Finance records a `ProviderPurchase` with amount, units, reference, and derived `effective_cost_per_unit` |
| Credits consumed | **CONFIRMED (internal)** | Sum of segments on submitted/delivered deliveries |
| Purchase history and remaining balance | **PROPOSED** | Purchases table plus latest snapshot, shown side by side and never summed |
| Programmatic purchase | **DO NOT ASSUME** | Not supported |

Displayed Arkesel panel: current provider balance (snapshot + captured-at), total units purchased, total units consumed, purchase history with effective cost per unit, and last sync time with API status.

### Resend (subscription + overage model)

Displayed Resend panel: plan name, monthly subscription expense, included allowance, usage to date, overage usage, recorded expenses, last sync time, API connection status, webhook health.

### Every provider purchase or expense records

Provider, channel, amount paid (GHS), units purchased where applicable, transaction reference, date, payment method, notes, and the platform user who recorded it. All of these are audited via `PlatformAuditLog`.

---

## 2.10 Paid / free / sponsored classification

### Classification matrix

| Traffic | Classification | School ledger | Provider cost recorded |
| --- | --- | --- | --- |
| Guardian SMS/email, school has balance | `paid` | `usage_debit` | Yes, as cost of paid traffic |
| Guardian send covered by a school free allowance | `free` | **No debit** | Yes, as platform-funded expense |
| Guardian blast sponsored by a campaign | `sponsored` | **No debit**, counts against campaign budget | Yes, as sponsored expense |
| Auth OTP SMS / OTP email | `free` | **Never** (v4 invariant 4) | Yes, via `PlatformOutboundDelivery` |
| Staff in-app notification email | `free` | **Never** (v4 invariant 4) | Yes, via `PlatformOutboundDelivery` |

### Gate extension

Today `communications_billing_active(school)` returns `True` unconditionally, so all guardian traffic is paid. The proposed gate becomes:

```text
1. Resolve classification from event policy / MessagingAllowancePolicy / campaign
2. If classification == paid:
       existing credit pre-check (filter_items_by_credits)
       → submit → debit_usage after acceptance        [unchanged behaviour]
3. If classification in (free, sponsored):
       check allowance / budget remaining
       → submit → record delivery with classification
       → SKIP the ledger debit entirely
       → still record provider_cost_snapshot for P&L
4. If allowance/budget is exhausted:
       fall back to paid (if the school has balance) or skip with a
       clear reason — this fallback must be an explicit configured
       choice, never an implicit surprise charge
```

**Default must preserve today's behaviour:** absent any allowance policy, guardian traffic classifies as `paid`. v4.1 introduces no new free messaging by default.

### Free / sponsored statistics to track

Free SMS messages, free SMS segments, free emails, sponsored SMS messages, sponsored SMS segments, sponsored emails, and total platform-funded provider expense — reported both platform-wide and per school.

---

## 2.11 Allowances and budgets

Platform administrators configure:

- Monthly free SMS allowance per school.
- Monthly free email allowance per school.
- Promotional credit allocations (these remain ordinary `promo_grant` ledger entries — a promotional **credit** is a wallet grant, which is different from a `sponsored` **send**).
- Daily messaging limits.
- School-level messaging limits.
- Platform-wide messaging budgets in GHS.
- Configurable alert thresholds when an allowance or budget approaches its limit.

Important distinction to keep visible in the UI:

```text
promo_grant  → credits land in the school wallet; the school spends them; classification = paid
sponsored    → no credits move; the platform absorbs provider cost; classification = sponsored
```

Both are legitimate; mixing them up corrupts both the wallet story and the P&L.

---

## 2.12 School usage and analytics

### Usage matrix (searchable, filterable)

| School | Paid SMS consumed | Free SMS consumed | SMS balance | Paid emails | Free emails | Email balance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |

Expandable per row: total SMS segments consumed, total emails sent, provider cost attributable to the school, revenue generated, free messaging expense, gross profit contribution, and communication add-on status.

Filters: date range, channel, billing classification, school search, add-on status.

### Individual school report

Current SMS balance, current email balance, credits purchased (top-ups), subscription allocations, promotional credits, credits consumed, free/sponsored consumption, provider costs, revenue generated, delivery success/failure statistics, top-up history, allocation history, the full usage ledger, and consumption trends over time.

**SMS consumption is always reported in billable segments**, never in message or recipient counts. A 2-segment message to 3 guardians is 6 units, and the report must say 6.

---

## 2.13 Provider reconciliation

### Arkesel reconciliation compares

Internal SMS submissions, provider message records (batch message reports), actual credits used where reported, delivery reports, and provider balance snapshots.

### Resend reconciliation compares

Internal email records, Resend email ids, provider delivery events, Usage API records, and subscription/invoice information.

### Operational surface

Last successful synchronisation per provider, unmatched provider records, missing delivery updates, credit discrepancies, failed synchronisation jobs, and overall reconciliation status — with a way for authorised administrators to investigate and resolve each discrepancy.

### The non-negotiable rule

> **Reconciliation never silently modifies historical ledger entries or balances.**

Any financial correction is a **new**, typed, idempotent ledger entry (`manual_adjust` or `reversal`) that references the reconciliation item in `metadata`, performed by a named actor, and recorded in `PlatformAuditLog`. The original rows stay exactly as they were written.

---

## 2.14 Failed messages, retries, and refunds

| Situation | School credits | Delivery record | Notes |
| --- | --- | --- | --- |
| Rejected before provider submit | **No debit** | `skipped` with `skip_reason` | Already the behaviour today |
| Accepted by provider | **Debit** (paid only) | `submitted` + cost snapshots | Debit-after-accept, idempotent on `usage:{key}` |
| Delivered | Keep debit | `delivered` via DLR/webhook | No financial change |
| Failed after acceptance | Apply refund policy | `failed` | Use `reverse_usage` with key `reversal:usage:{key}` |
| Submission status unknown | **Hold** — no auto-refund, no auto-resend | `unknown` | Must be reconciled first |
| Duplicate webhook / DLR | **No** second debit or refund | Status update only | Idempotent on provider message id / event id |
| Accepted but debit failed (race) | **Open decision** — see §2.1.2 | `submitted`, `credits_charged = 0` | Must surface as an `unbilled_send` reconciliation item |

### v4.1 default refund policy (configurable later)

```text
if provider does NOT charge for a failed DLR:
        auto reverse_usage ONCE, idempotent on reversal:usage:{original_key}
if provider DOES charge for the attempt:
        keep the debit (the cost was genuinely incurred)
if status is unknown:
        NO automatic refund until reconciliation resolves it
```

This requires **wiring the currently unused `reverse_usage`** function. Today it is dead code, so no refund happens at all.

### Retries

The original attempt and every retry are retained — `GuardianDelivery.source_delivery` already models this. Each **successful paid submit may debit again**, because each submit genuinely consumes provider units. This is the current behaviour and it is correct; it must be **stated explicitly in the UI** so schools are not surprised by two debits for one logical message.

---

## 2.15 Revenue and profitability

### Definitions (precise, because these are easy to confuse)

```text
Allocated (units)   = Σ positive ledger deltas
                      (allocation_recurring + topup + promo_grant + positive manual_adjust)
Consumed (units)    = Σ |usage_debit| − Σ reversal
Remaining (units)   = CreditAccount.balance            (cached projection of the above)
Unused (units)      = Remaining                         (a delivery liability, NOT revenue)

Provider remaining  = latest ProviderBalanceSnapshot.sms_balance   (Arkesel only)
Provider purchased  = Σ ProviderPurchase.credits_or_units
Free / sponsored    = Σ units on deliveries where billing_classification ≠ paid
```

### Cash view (what actually moved)

```text
Cash received from schools (range)
    = Σ billing.Payment(status=success, purpose=invoice) attributable to comms add-on lines
    + Σ billing.Payment(status=success, purpose=topup)

Cash paid to providers (range)
    = Σ ProviderPurchase.amount_ghs
    + Σ ProviderExpense.amount_ghs
```

### Usage view (what was actually consumed)

```text
Usage-valued revenue      = Σ (paid units × school_unit_price_snapshot_ghs)
Provider cost (usage)     = Σ (paid units × provider_cost_snapshot_ghs)
                            email: estimated allocation and/or period expense allocation

Gross profit (usage)      = Usage-valued revenue − Provider cost (usage)
Gross margin %            = Gross profit (usage) / Usage-valued revenue × 100

Free/sponsored expense    = Σ (free+sponsored units × provider_cost_snapshot_ghs)
                            + allocated share of Resend subscription per policy

Overall messaging
  contribution            = Gross profit (usage) − Free/sponsored expense
```

### Reporting rules

- **Always show the cash view and the usage view separately.** Never blend them into one "profit" number.
- Never count unused credits as consumed revenue.
- Never double-count a top-up (once as cash, again as usage revenue) — they are different views of the same sale at different times.
- Never treat the full value of a provider wallet purchase as the cost of messages already consumed.
- Always use **historical snapshots** of cost and selling price for financial reports, never today's config.
- Label every estimated figure as estimated, especially allocated email provider cost.

### Per-channel breakdowns required

**SMS:** total provider purchases, total SMS usage cost, SMS credit revenue, add-on revenue attributable to SMS, gross profit, gross margin.

**Email:** Resend subscription expense, overage expense, allocated email provider cost, email credit revenue, add-on revenue attributable to email, gross profit, gross margin.

**Combined:** total messaging revenue, total provider cost, paid messaging gross profit, free/sponsored expense, overall contribution, gross margin.

---

## 2.16 API proposals — `/api/v1/platform/messages/`

All **PROPOSED**. All platform-authenticated via `IsPlatformAuthenticated` + `HasPlatformRole` with `allowed_roles` per view, following existing platform view conventions.

| Area | Endpoints (sketch) |
| --- | --- |
| Overview | `GET overview/?range=&school=&channel=&classification=` |
| SMS pricing | `GET/POST sms-encodings/`, `GET sms-encodings/history/`, `PATCH sms-encodings/<id>/` (creates a new version) |
| Email pricing | `GET/POST email-pricing/`, `GET email-pricing/history/` |
| Segment calculator | `POST calculator/sms/` → `{encoding, characters, segments, credits_per_recipient, limits_used}` |
| Providers | `GET providers/`, `POST providers/arkesel/sync-balance/`, `GET providers/arkesel/snapshots/` |
| Purchases & expenses | `GET/POST purchases/`, `GET/POST expenses/` |
| Resend | `POST providers/resend/sync-usage/`, `GET providers/resend/usage/` |
| Resend webhook | `POST /api/v1/webhooks/resend/` — **public, signature-verified, idempotent** (sits beside the existing Arkesel DLR webhook, not under `/platform/`) |
| School analytics | `GET schools/usage/?range=&channel=&classification=&q=`, `GET schools/<uuid>/report/` |
| Free & sponsored | `GET/POST/PATCH allowances/`, `GET free-usage/` |
| Profitability | `GET profitability/?range=&channel=&view=cash|usage` |
| Transactions | `GET transactions/?type=&range=&school=&provider=` (unified feed) |
| Exports | `GET export/?type=...&format=csv|xlsx` |
| Reconciliation | `POST reconcile/arkesel/`, `POST reconcile/resend/`, `GET runs/`, `GET runs/<id>/items/`, `POST runs/<id>/items/<id>/resolve/` |

**Reuse, do not duplicate:**
`/api/v1/platform/communications/schools/<uuid>/credits|ledger|adjust|addons/schedule`, `/api/v1/platform/communications/skus/`, `/api/v1/platform/billing/topups/`, and the existing school-facing messaging endpoints. The Messages module **reads** these; it does not reimplement them.

---

## 2.17 Permission matrix

Enforced through the existing `HasPlatformRole` mechanism.

| Area | Super Admin | Finance | Operations | Support | Curriculum |
| --- | --- | --- | --- | --- | --- |
| Overview dashboard | Full | Read | Read | Read | **No access** |
| SMS pricing & configuration | Full | **Read + write** | Read | Read | No access |
| Email pricing & configuration | Full | **Read + write** | Read | Read | No access |
| Provider balances & sync | Full | Read | **Read + trigger sync** | Read | No access |
| Provider purchases & expenses | Full | **Read + write** | Read | No | No access |
| School usage & analytics | Full | Read | Read | **Read-only** | No access |
| Individual school report | Full | Read | Read | **Read-only** | No access |
| Free & sponsored allowances | Full | Read | **Read + write** | Read | No access |
| Revenue & profitability | Full | **Read + write exports** | Read (volumes only) | No | No access |
| Transactions feed | Full | **Full** | Read | Read | No access |
| Credit manual adjustment | Full | **Write** | No | No | No access |
| Reconciliation runs | Full | Read + resolve | **Trigger + investigate** | Read | No access |
| Exports | Full | **Full** | Operational exports | No | No access |

Rules:

- **Curriculum has no Messages access** unless explicitly granted later.
- **Support is strictly read-only** across every Messages surface.
- Strict school-level data isolation applies: platform roles see cross-school data; nothing in this module exposes one school's data to another school's users.
- Any write action (pricing change, purchase, expense, adjustment, allowance edit, reconciliation resolution) writes a `PlatformAuditLog` row.

---

## 2.18 UI requirements

Follow the existing platform-admin design system (`AppShell` nav pattern, summary cards, searchable tables, detail drawers).

- **Summary strips** per area, with each tile labelled by layer (provider balance / school balance / cash / usage) so numbers from different layers are never visually adjacent as if comparable.
- **Interactive charts** for volume and margin trends.
- **Searchable, sortable tables** with server-side pagination for school usage, transactions, purchases, and reconciliation items.
- **Filters** present on every data surface: date range (today, last 7 days, last 30 days, this month, last month, custom), school, channel, billing classification.
- **Detail views** for individual transactions, deliveries, purchases, and reconciliation items.
- **Responsive layouts** consistent with the current app.
- **Estimated values visibly labelled** (allocated email provider cost in particular).
- **Live SMS calculator** on the SMS pricing page showing encoding, character/septet count, segments, and credits for a pasted or rendered body — using the same code path as production metering.

**Explicit anti-requirement:** never render a single undifferentiated number that mixes provider balance, school balance, cash received, and usage value. Every financial figure states which of the five layers it belongs to.

---

## 2.19 Audit and exports

### Audit

Every one of the following writes a `PlatformAuditLog` entry (`actor`, `action`, `target_type`, `target_id`, `detail`, `ip_address`):

- SMS and email pricing configuration changes (old → new values in `detail`).
- Manual provider purchases and expenses.
- Manual credit adjustments.
- Allowance and budget edits.
- Reconciliation resolutions.
- Export generation of financial data.

Manual corrections must never silently modify historical records or balances — they append.

### Transaction history coverage

Arkesel credit purchases, Resend subscription payments, provider expenses, school credit purchases (top-ups), SMS deductions, email deductions, free messaging, sponsored messaging, refunds/reversals, promotional allocations, manual adjustments, pricing changes, and provider reconciliations.

Every transaction row shows: date, transaction type, amount or credit quantity, reference, related school (where applicable), provider, and responsible administrator.

### Exports (CSV and Excel)

School messaging consumption, provider purchases, provider expenses, SMS pricing history, email pricing history, revenue and profitability, free and sponsored messaging, credit ledger transactions, monthly communication summaries, and provider reconciliation reports.

---

## 2.20 Implementation roadmap (M0–M7)

Delta to the v4 roadmap. Each milestone is independently shippable and **none** is authorised yet.

| Milestone | Scope | Depends on |
| --- | --- | --- |
| **M0** | Messages nav shell + Overview metrics computed read-only from existing `CreditLedgerEntry` and `GuardianDelivery` | Nothing new |
| **M1** | `SmsEncodingConfig` + `EmailPricingConfig` with immutable history; make `segments.py` limits config-driven; calculator API and UI | M0 |
| **M2** | `ProviderAccount`, Arkesel balance-details sync (beat + on-demand), `ProviderBalanceSnapshot`, manual `ProviderPurchase`, Resend usage sync, `ProviderExpense` | M1 |
| **M3** | `billing_classification` on deliveries, `PlatformOutboundDelivery`, `MessagingAllowancePolicy`, free/sponsored dashboards | M1 |
| **M4** | Resend webhooks (signature + idempotency), wire `reverse_usage` under the refund policy, unknown-status hold rules, unbilled-send handling | M3 |
| **M5** | School usage matrix + individual school report + unified transactions feed | M3 |
| **M6** | Profitability views (cash and usage) + all exports | M2, M5 |
| **M7** | Reconciliation jobs, run/item models, investigation and resolution UI | M4, M6 |

Positioning against v4: this work sits alongside and after v4 Phase 7+ ("provider sync"). The school-side Billing and Messaging surfaces from v4 phases 4–5 are already partially shipped — **do not rebuild school wallets or school messaging**.

---

## 2.21 Acceptance criteria

1. A **Messages** navigation entry exists with all 8 areas (or equivalent tabs).
2. Encoding limits and unit prices are **configurable**, history is **immutable**, and the calculator matches the production debit exactly for the same body.
3. The Arkesel balance is visible via API sync with a captured-at timestamp; wallet purchases are recordable manually with a derived effective cost per unit.
4. Resend usage is visible via the Usage API; subscription and overage expenses are recordable; webhooks update email delivery status idempotently with verified signatures.
5. School SMS and email wallets remain the **sole** `CreditAccount` / `CreditLedgerEntry` system. No second wallet exists anywhere.
6. Every outbound attempt — guardian **and** platform — is classifiable as `paid` / `free` / `sponsored`; `free` and `sponsored` never debit a school wallet; provider cost is still reported for them.
7. Paid debits occur after provider acceptance; refunds are idempotent per the configured policy; duplicate webhooks and DLRs are safe.
8. P&L cleanly separates cash received, provider spend, credits sold, credits allocated, credits consumed, unused credits, and free/sponsored expense — with cash and usage views shown separately.
9. The role matrix is enforced at the API layer, and exports are available for every listed dataset.
10. Reconciliation produces **no silent historical ledger rewrites**; all corrections are new, typed, audited entries.
11. **All 14 v4 invariants still hold** after the module ships — verified by tests, not by inspection.
12. Every estimated financial figure is labelled as estimated in both API responses and UI.

---

## 2.22 Non-goals for v4.1

- A second school credit wallet or any competing ledger.
- Changing the billable SMS unit away from provider segments.
- Charging schools in GHS at send time instead of in credits.
- Debiting schools for OTP or staff notification email.
- Assuming Arkesel supports programmatic credit purchases.
- Assuming Resend has a prepaid wallet or exposes invoice amounts via API.
- Multi-currency support (GHS only, per v4).
- Impersonation and support ticketing (still deferred per v4).
- Rebuilding the school-facing Messaging or Billing surfaces.
- Retroactively pricing pre-v4.1 deliveries that have no cost snapshots.

---

# Part 3 — As-built reference

This is a **snapshot of the working tree**, provided so future readers can tell architecture from reality. Presence of a file does not mean a phase is complete; no phase-completion audit was performed.

### Backend apps relevant to this document

| App | Path | Notes |
| --- | --- | --- |
| `platform_admin` | `sms-backend/platform_admin/` | Platform auth realm (email/password + TOTP via `pyotp`), roles, settings, audit, school invites |
| `billing` | `sms-backend/billing/` | Plans, subscriptions, periods, invoices, payments, top-ups, campaigns, capacity, dunning, interval change, proration |
| `communications` | `sms-backend/communications/` | Credit accounts, append-only ledger, add-on SKUs, segment calculator, send gates |
| `messaging` | `sms-backend/messaging/` | School-facing messaging overview, deliveries, templates |
| `notifications` | `sms-backend/notifications/` | `GuardianDelivery`, guardian delivery workers, Arkesel DLR webhook, SMS status polling, staff inbox/email |
| `shared` | `sms-backend/shared/services/arkesel_sms.py` | Arkesel client |

### Key files cited in Part 2

```text
sms-backend/communications/models/accounts.py        CreditAccount, CreditLedgerEntry
sms-backend/communications/models/skus.py            CommunicationAddonSku
sms-backend/communications/services/ledger.py        write_ledger_entry + typed helpers
sms-backend/communications/services/segments.py      encoding detection, segment counting
sms-backend/communications/services/gates.py         send eligibility + credit pre-check
sms-backend/communications/urls_platform.py          existing platform comms APIs
sms-backend/notifications/models.py                  GuardianDelivery, GuardianMessageTemplate
sms-backend/notifications/services/deliver_guardian.py   debit-after-submit batches
sms-backend/notifications/services/resend_batch.py   Resend batch client + Django fallback
sms-backend/notifications/views_webhooks.py          Arkesel DLR webhook (only webhook wired)
sms-backend/shared/services/arkesel_sms.py           Arkesel send / status / error classification
sms-backend/billing/models/{plans,subscriptions,invoices,payments,campaigns}.py
sms-backend/billing/urls_platform.py                 existing platform billing APIs
sms-backend/platform_admin/{permissions,models/users,models/audit,models/settings}.py
platform-admin/src/components/AppShell.tsx           operator nav
platform-admin/src/app/routes.tsx                    operator routes
platform-admin/src/features/schools/                 directory, create modal, detail
docs/platform-admin-schools.md                       directory + create behavior
```

### As-built field values worth knowing

| Thing | Values in code |
| --- | --- |
| `CreditLedgerEntry.EntryType` | `allocation_recurring`, `topup`, `promo_grant`, `usage_debit`, `manual_adjust`, `reversal` |
| `InvoiceLine.Kind` | `application`, `application_proration`, `interval_change`, `sms_addon`, `email_addon`, `topup`, `discount`, `adjustment` |
| `Payment.Provider` / `.Status` / `.Purpose` | `paystack`\|`manual` / `pending`\|`success`\|`failed`\|`abandoned` / `invoice`\|`topup` |
| `SchoolSubscription.Status` | `pending`, `active`, `past_due`, `suspended`, `cancelled`, `expired`; `Interval` is `monthly`\|`annual`; `pending_plan`, `pending_interval`, `pending_*_sku`, `pending_change_effective_at` all present |
| Subscription snapshots | `plan_code_snapshot`, `capacity_max_snapshot`, `staff_capacity_max_snapshot`, `app_price_snapshot_ghs` |
| `GuardianDelivery.Status` | `queued`, `processing`, `submitted`, `delivered`, `failed`, `unknown`, `skipped`, legacy `sent` |
| `PlatformUser.Role` | `super_admin`, `operations`, `finance`, `support`, `curriculum` |
| Celery beat jobs | `fees.run_auto_debt_reminders` (08:00), `billing.run_dunning_cycle` (07:30), `notifications.poll_pending_sms_status` (every 5 min) |
| Provider batch limits | Arkesel 100 recipients per request; Resend 100 emails per batch |

### Honest list of open items

1. **Unbilled accepted sends.** The debit-after-accept race currently logs an error and charges nothing (§2.1.2). Needs an explicit policy decision before M4.
2. **`reverse_usage` is dead code.** No refund path exists for post-acceptance failures.
3. **Email delivery status is effectively terminal at `submitted`** until Resend webhooks are wired.
4. **Segment limits are hardcoded.** Changing them today requires a code change and deploy.
5. **Platform-funded provider cost is invisible.** OTP and staff email leave no billing-classified record.
6. **No pre-v4.1 cost snapshots.** Historical deliveries cannot be retroactively priced accurately and must be reported as unpriced.
7. **Arkesel per-message credit cost is not captured**, so local segment counts are unverified against the provider.

---

## Change log

| Version | Date | Change |
| --- | --- | --- |
| v4 | 2026-11-05 | Capacity-driven immediate upgrade rules locked (§1.7.3); blueprint approved |
| v4.1 | 2026-11-06 | Messages & Communications Management extension accepted (documentation only) |
| — | 2026-11-06 | v4 + v4.1 committed to `docs/` as the durable source of truth, replacing chat-only architecture |
| v4.1 impl | 2026-11-06 | M0–M7 implemented: models/migrations, `/api/v1/platform/messages/*`, Resend webhook, delivery classification/refunds, Platform Admin Messages UI |
| — | 2026-11-10 | School directory and create-school billing documented in [platform-admin-schools.md](./platform-admin-schools.md) |
