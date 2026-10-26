# Opening the next term

Admins open the next term from one wizard. It places continuing pupils, marks leavers graduated, copies teachers, applies the next term’s fees, and makes that term current.

Do this after the current term has ended, once the next fee list is the one you want to bill. Opening the term flips the working term and locks that fee list. The wizard still allows an early open, and it warns when today is before the next term’s start date.

There is no repeat or demotion. The wizard does not copy CA items, attendance, or BECE results.

## When it shows

`TRANSITION_LEAD_DAYS` is 7 (`schools/services/term_transition.py`).

From 7 days before the current term’s `end_date`, and until the next term is opened:

- **Transition** sits in the navbar, to the left of the bell, on every page. Admins only.
- The same action is on the admin dashboard and on **Settings → Academic year** (**Open transition**).
- **Accountants** (and admins with fee settings) also see a **fee-prep** banner on the accountant dashboard / fees surfaces. Prep status is `GET /api/v1/fees/next-term-prep/`. Accountant work is finished once the next catalog is **published** (or already applied); the admin wizard still applies and locks it. See [fees.md](./fees.md).

The Transition button stays up through the vacation. It leaves once the next term is the current term.

A popup appears only on the admin dashboard, and only while something on the checklist is still unfinished and **Settings → Alerts** has **Popup on the dashboard while opening the next term still needs action** turned on (`SchoolSettings.transition_popup_enabled`). Dismissing it lasts for that visit. Coming back to the dashboard shows it again while work remains. The navbar button does not depend on that checkbox.

## Wizard

`GET /api/v1/schools/transition/preview/` builds the steps. `POST /api/v1/schools/transition/confirm/` runs them. Both are admin-only.

Closing the wizard keeps the current step and any stream choices for this term (browser session storage). Opening it again continues there. The fee list is loaded again, so an edit in Fees settings shows up. That saved progress is cleared once the next term is opened.

### Pupils

Within a year, everyone stays in the same class and stream.

At year end, each class moves to the next active class by `(level.order, class.order)`. The preview lists every class and where it goes, so a missing class is visible. A stream name matches the same name on the destination. An unnamed default stream matches an unnamed default. There is no fallback to a different stream.

Pupils in the last active class (for example JHS 3, or Basic 6 in a primary-only school) are marked `Student.is_graduated` and are not enrolled. `is_active` is left as it is. Past enrollments stay on the old term.

Skipped, and not moved:

- Inactive pupils.
- Anyone already enrolled on the target term.
- Active pupils with no class this term. They **block** the open until enrolled or marked left / graduated.

Roll-forward enrollments keep `is_new_student` false.

### Streams

This step appears only when a destination class has no stream with the same name. The admin picks one destination stream per source stream. A destination class with no streams blocks the open until a stream exists (**Settings → Classes**).

### Fees

The step lists the fee items that will be billed on the next term, and who each one covers (school, level, or class, and new or continuing pupils).

If the next term has no catalog yet, the list is the current term’s items. Confirm copies them forward. If the next term already has its own catalog, that catalog is the list. **Edit in Fees settings** opens `/fees/settings?term=<next term id>`.

Class and level fees stay pointed at the class or level they were written for. A pupil who moved to another class simply does not match the fee they left behind.

Confirm publishes a draft if needed, then applies the catalog. Apply locks it. An already applied catalog is left locked, and newly placed pupils are billed from it. A missing catalog, or a catalog with no items, blocks the open. The Fees and Confirm steps both say that opening locks the list, so amounts should be finished in Fees settings before the open.

Past-term balances stay on those terms. Advances already apply when the next catalog is applied.

### Confirm

Warnings (unreleased reports, unmatched subjects, subject groups that could not be copied, opening before the start date) must be acknowledged. Blockers stop the button: no next term, overlapping dates, a class with nowhere to go and no stream choice, no fee items, or active pupils with no class this term.

Confirm then:

1. Creates next-term enrollments, or sets `is_graduated` for leavers.
2. Copies class teachers and subject teachers onto empty slots. An existing assignment is not replaced. A subject with no match on the destination is a warning.
3. On a year change, copies subject-group placements when the subject and the group name both match. Misses are a warning. Groups are per academic year, so a same-year open does not copy them.
4. Applies and locks the next fee catalog.
5. Activates the next term. Assessment settings are copied onto it when it has none (`activate_term`).

Marks and bills already recorded stay on the term you leave.

## After someone has graduated

The student profile shows **Graduated**. An admin can **Clear graduation** (`POST /api/v1/students/<student_id>/clear-graduation/`). That only clears the flag. It does not enroll them. A graduated student cannot be enrolled until it is cleared.

## Checklist behind the popup

`GET /api/v1/schools/transition/` is admin-only. While the window is open it reports:

| Item | Finished when |
| --- | --- |
| Next term | The next term exists on the calendar |
| Release reports | The current term has no unreleased reports |
| Next term fees | The next catalog is already applied |
| Match class streams | Year change only. Every moving class has a matching stream or a choice |
| Pupils leaving | Year change only. Informational, always treated as done |

## Standalone activate (disabled)

`POST /api/v1/schools/settings/academic-years/terms/<term_id>/activate/` returns **403**. Term activation only happens inside transition confirm, after pupils are placed and fees applied. The settings screen does not expose activate.

## Code

| Piece | Where |
| --- | --- |
| Preview, confirm, status | `sms-backend/schools/services/term_transition.py` |
| APIs | `sms-backend/schools/views.py`, `schools/urls.py` |
| Accountant fee prep | `sms-backend/fees/services/prep.py`, `GET /fees/next-term-prep/` |
| Graduation flag | `sms-backend/students/models.py` (`is_graduated`) |
| Wizard and saved progress | `sms-frontend/src/features/settings/components/TransitionWizard.tsx` |
| Navbar and dashboard entry | `TransitionProvider.tsx`, `NavBar.tsx`, `TransitionNotice.tsx` |
| Fee prep UI | `FeePrepNotice.tsx`, Fees settings publish / copy-from-previous |

**Last reviewed:** 2026-10-26
