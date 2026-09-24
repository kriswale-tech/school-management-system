# Assessment structure — how it works

Per-term snapshot of how results are calculated (weights, result format, grade bands).  
Scoring formula: [subject-assessment-workspace.md](./subject-assessment-workspace.md).  
Fees uses the same catalog-per-term idea: [fees.md](./fees.md).

**Last reviewed:** 2026-09-23

---

## Mental model

Two layers:

| Layer | Models | Meaning |
| --- | --- | --- |
| **Structure** | `AssessmentConfig` + `GradeBand` | How this department’s results are calculated **in this term** (CA/exam weights, grade vs position, bands) |
| **Marks** | `AssessmentItemScore`, `SubjectScore.exam_mark` | What each student scored. Totals and grades are **not** stored; they are computed on read |

Scoring always uses **marks for that term + structure for that term**. Changing Term 2 to 50/50 does not rewrite Term 1.

One config per **level (department) + term**.

```
Setup / Assessment Settings
        │
        ▼
Term 1 structure (Primary 40/60, letter grades)
Term 2 structure (copy of Term 1, then optionally 50/50)
        │
        ▼
Markbook / class teacher / admin / report preview
        = raw marks + that term’s structure
```

---

## Lifecycle

### School setup

Wizard order is already year/term → classes → assessment. Saving a department writes the structure onto the **active term**. Completing assessment copies that structure onto the other terms in the same academic year that do not have one yet.

### Later terms / years

When a new academic year (and its terms) is saved, each new term that has no structure yet is filled from the most recent previous term that does.

Opening Assessment Settings for a term also copy-forwards if that term is still empty.

### Assessment Settings (`/assessments/settings`)

Same pattern as Fees Settings:

- Term picker on the ActionBar
- Current / upcoming term: editable; per-department **Save**
- Ended term (`end_date` before today): listed as **(past)** and **read-only**
- If the current term already has marks, a warning explains that a save recalculates **this term only**

### Day-to-day marking

Teachers still enter raw CA marks and exam / 100. Class score, exam contribution, total, grade, and position are computed from **that teaching assignment’s term** structure.

### Reports

Preview and a newly generated PDF use that term’s snapshot. An already stored PDF file stays as-is until it is generated again; regeneration still uses **that term’s** structure, not whatever is on a later term.

The student profile **Reports & Assessment** tab (`GET /students/:id/assessments/?term=`) uses the same per-term structure and live scores.

---

## Lock rule

| Term | Structure |
| --- | --- |
| Ended (`end_date` < today) | Frozen (read-only) |
| Current / upcoming | Editable |

That stops last year’s reports from moving when this term’s policy changes. Mid-term edits still affect **this** term’s in-progress totals (raw marks stay the same).

---

## Existing data

Configs created before term-scoping were cloned onto every existing term for that department. We cannot recover historical weights from before that migration; from then on, editing the current term leaves older terms alone.

---

## API

| Use | Endpoint |
| --- | --- |
| Setup wizard (active term) | `GET/PUT /schools/setup/assessment/` |
| Desk settings | `GET /academics/assessments/settings/?term_id=` |
| Desk save | `PUT /academics/assessments/settings/levels/<level_id>/?term_id=` |

Scoring loaders (`workspace`, class-teacher detail, admin detail, report preview) resolve config with `get_term_assessment_config(level_id, term_id)`.
