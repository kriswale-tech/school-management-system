import type { GradeBand, GradeTemplate, GradeType, LevelConfig, LevelConfigPayload, ResultType } from './types'

export type GradeRow = {
  grade: string
  min: string
  max: string
  remarks: string
}

export type GradeTableState = {
  gradeType: GradeType | null
  rows: GradeRow[]
}

export const templateToRows = (templates: GradeTemplate[]): GradeRow[] =>
  templates.map((template) => ({
    grade: template.grade,
    min: String(template.min_score),
    max: String(template.max_score),
    remarks: template.remark,
  }))

export const gradeBandToRows = (bands: GradeBand[]): GradeRow[] =>
  bands.map((band) => ({
    grade: band.grade,
    min: String(band.min_score),
    max: String(band.max_score),
    remarks: band.remark,
  }))

export const rowsForGradeType = (
  gradeType: GradeType,
  gradeTemplates: { letter: GradeTemplate[]; numerical: GradeTemplate[] },
  savedBands?: GradeBand[] | null,
  savedGradeType?: GradeType | null,
): GradeRow[] => {
  if (savedBands?.length && savedGradeType === gradeType) {
    return gradeBandToRows(savedBands)
  }

  return templateToRows(gradeTemplates[gradeType])
}

export const rowsToGradeBands = (rows: GradeRow[], existingBands?: GradeBand[] | null): GradeBand[] =>
  rows.map((row) => {
    const existing = existingBands?.find((band) => band.grade === row.grade)

    return {
      id: existing?.id ?? '',
      grade: row.grade,
      min_score: Number(row.min),
      max_score: Number(row.max),
      remark: row.remarks,
    }
  })

const showsGradeTypeTable = (resultType: ResultType | null) =>
  resultType === 'grade' || resultType === 'grade_and_position'

export type LevelFormValues = {
  continuousAssessmentWeight: number
  examWeight: number
  resultType: ResultType
  gradeType: GradeType
  gradeBands: GradeBand[]
}

export const validateLevelForm = (
  values: {
    continuousAssessmentWeight: string
    examWeight: string
    resultType: ResultType | null
    gradeTable: GradeTableState
  },
): string | null => {
  if (!values.resultType) {
    return 'Please select a result display format'
  }

  const caWeight = Number(values.continuousAssessmentWeight)
  const examWeight = Number(values.examWeight)

  if (Number.isNaN(caWeight) || Number.isNaN(examWeight)) {
    return 'Continuous Assessment and Exams must be valid numbers'
  }

  if (caWeight < 0 || caWeight > 100 || examWeight < 0 || examWeight > 100) {
    return 'Percentages must be between 0 and 100'
  }

  if (caWeight + examWeight !== 100) {
    return 'Continuous Assessment and Exams must add up to 100%'
  }

  if (showsGradeTypeTable(values.resultType)) {
    if (!values.gradeTable.gradeType) {
      return 'Please select a grade type'
    }

    if (!values.gradeTable.rows.length) {
      return 'Please configure grade bands'
    }
  }

  return null
}

export const parseConfigWeight = (value: string | null | undefined): string => {
  if (value === null || value === undefined || value.trim() === '') {
    return ''
  }

  const parsed = Number(value)
  if (Number.isNaN(parsed)) {
    return ''
  }

  return String(parsed)
}

export const buildLevelConfigPayload = (values: LevelFormValues): LevelConfigPayload => ({
  continuous_assessment_weight: values.continuousAssessmentWeight,
  exam_weight: values.examWeight,
  result_type: values.resultType,
  grade_type: values.gradeType,
  grade_bands: values.gradeBands,
})

export const getLevelFormValues = (
  resultType: ResultType | null,
  continuousAssessmentWeight: string,
  examWeight: string,
  gradeTable: GradeTableState,
  existingConfig: LevelConfig | null,
): LevelFormValues | null => {
  if (!resultType) return null

  const gradeType =
    showsGradeTypeTable(resultType) && gradeTable.gradeType
      ? gradeTable.gradeType
      : (existingConfig?.grade_type ?? 'letter')

  const gradeBands =
    showsGradeTypeTable(resultType) && gradeTable.gradeType
      ? rowsToGradeBands(gradeTable.rows, existingConfig?.grade_bands)
      : (existingConfig?.grade_bands ?? [])

  return {
    continuousAssessmentWeight: Number(continuousAssessmentWeight),
    examWeight: Number(examWeight),
    resultType,
    gradeType,
    gradeBands,
  }
}
