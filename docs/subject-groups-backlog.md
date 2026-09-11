# Subject groups — backlog

Deferred work around student placement in subject groups (e.g. Ghanaian Language → Twi / Ga).

## Locked product rules (current intent)

- Subject teachers assign only **unassigned** students to their group.
- Reassignment across groups is **not** allowed for the claiming teacher; the current group teacher must **unassign** first.
- One student → one group per class-subject per academic year (already enforced in `StudentSubjectGroup`).

## To build (UI + API)

- [x] Subject Detail CTA **Assign students** (grouped subjects only; intended on **Students** tab, not Workspace)
- [x] Candidate list: class/stream roster with group status (unassigned / this group / other group)
- [x] Banner: count of students with **no** group for this class-subject
- [x] Assign selected unassigned students to this group
- [x] Unassign selected students from **this** group only
- [x] API rejects assigning a student who already has another group for the same class-subject/year

## Later — assessment lock

Once assessment recording exists for subject groups:

- [ ] **Do not allow unassign (or any group change)** for a student if they already have a recorded assessment score for that group / class-subject in the active term (exact binding TBD when scoring models land).
- [ ] Surface a clear error in UI: e.g. “Cannot remove Ada — scores already recorded.”
- [ ] Admin override (optional) only if product later needs it; default is hard lock.

**Why:** placement must stabilize after marking starts so marks stay attached to the right tutor/group.

## Out of scope for v1

- Auto-placement algorithms
- Class teacher bulk “place everyone” UI (nice follow-up)
- Notifications to the other group teacher when someone is unassigned
