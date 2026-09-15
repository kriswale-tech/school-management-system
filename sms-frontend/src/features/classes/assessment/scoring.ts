import type {
  AssessmentStatus,
  AssessmentWeights,
  CaItem,
  ComputedStudentResult,
  GradeBand,
  StudentAssessmentMarks,
} from './types'

const EXAM_MAX = 100

export const DEFAULT_ASSESSMENT_WEIGHTS: AssessmentWeights = {
  continuous_assessment_weight: 40,
  exam_weight: 60,
}

/** Simple letter bands for mock UI until level config is loaded from the API. */
export const DEFAULT_GRADE_BANDS: GradeBand[] = [
  { grade: 'A', min_score: 80, max_score: 100 },
  { grade: 'B', min_score: 70, max_score: 79.99 },
  { grade: 'C', min_score: 60, max_score: 69.99 },
  { grade: 'D', min_score: 50, max_score: 59.99 },
  { grade: 'E', min_score: 40, max_score: 49.99 },
  { grade: 'F', min_score: 0, max_score: 39.99 },
]

export function roundScore(value: number, digits = 2): number {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}

/** Convert a raw mark to a percentage for one CA item. */
export function caItemPercent(mark: number, maxMarks: number): number {
  if (maxMarks <= 0) return 0
  return (mark / maxMarks) * 100
}

/**
 * Class score = mean of CA item percentages, scaled to continuous_assessment_weight.
 * Returns null if there are no items or any item mark is missing.
 */
export function computeClassScore(
  caMarks: Record<string, number | null>,
  items: CaItem[],
  weights: AssessmentWeights,
): number | null {
  if (items.length === 0) return null

  const percents: number[] = []
  for (const item of items) {
    const mark = caMarks[item.id]
    if (mark === null || mark === undefined) return null
    percents.push(caItemPercent(mark, item.max_marks))
  }

  const avg = percents.reduce((sum, p) => sum + p, 0) / percents.length
  return roundScore(avg * (weights.continuous_assessment_weight / 100))
}

/** Exam contribution scaled to exam_weight (exam max is always 100). */
export function computeExamContribution(
  examMark: number | null,
  weights: AssessmentWeights,
): number | null {
  if (examMark === null || examMark === undefined) return null
  return roundScore((examMark / EXAM_MAX) * weights.exam_weight)
}

export function computeTotal(
  classScore: number | null,
  examContribution: number | null,
): number | null {
  if (classScore === null || examContribution === null) return null
  return roundScore(classScore + examContribution)
}

export function resolveGrade(total: number | null, bands: GradeBand[]): string | null {
  if (total === null) return null
  const match = bands.find((band) => total >= band.min_score && total <= band.max_score)
  return match?.grade ?? null
}

export function resolveStatus(
  classScore: number | null,
  examContribution: number | null,
  total: number | null,
  isPublished = false,
): AssessmentStatus {
  if (isPublished) return 'Published'
  if (classScore !== null && examContribution !== null && total !== null) return 'Complete'
  return 'Incomplete'
}

export function computeStudentResult(
  marks: StudentAssessmentMarks,
  items: CaItem[],
  weights: AssessmentWeights,
  bands: GradeBand[] = DEFAULT_GRADE_BANDS,
): ComputedStudentResult {
  const class_score = computeClassScore(marks.ca, items, weights)
  const exam_score = computeExamContribution(marks.exam, weights)
  const total = computeTotal(class_score, exam_score)
  return {
    student_id: marks.student_id,
    class_score,
    exam_score,
    total,
    grade: resolveGrade(total, bands),
    status: resolveStatus(class_score, exam_score, total),
  }
}

export function formatScore(value: number | null): string {
  if (value === null) return '—'
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

/** True if any student has a non-null mark for this CA item. */
export function caItemHasAnyMarks(
  itemId: string,
  rows: StudentAssessmentMarks[],
): boolean {
  return rows.some((row) => {
    const mark = row.ca[itemId]
    return mark !== null && mark !== undefined
  })
}

/** True if this student has every CA item filled (exam may be empty). */
export function isStudentCaComplete(
  row: StudentAssessmentMarks,
  items: CaItem[],
): boolean {
  if (items.length === 0) return false
  return items.every((item) => {
    const mark = row.ca[item.id]
    return mark !== null && mark !== undefined
  })
}

/** True if every row has every CA item filled (exam may be empty). */
export function areCaMarksComplete(
  rows: StudentAssessmentMarks[],
  items: CaItem[],
): boolean {
  if (rows.length === 0 || items.length === 0) return false
  return rows.every((row) => isStudentCaComplete(row, items))
}

export function emptyMarksForStudents(
  studentIds: string[],
  items: CaItem[],
): StudentAssessmentMarks[] {
  return studentIds.map((student_id) => ({
    student_id,
    ca: Object.fromEntries(items.map((item) => [item.id, null])),
    exam: null,
  }))
}

export { EXAM_MAX }
