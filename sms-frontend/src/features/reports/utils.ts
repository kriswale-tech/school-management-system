export const REPORTS_FILTERS_QUERY_KEY = 'reports-filters' as const
export const REPORTS_OVERVIEW_QUERY_KEY = 'reports-overview' as const
export const REPORTS_BY_CLASS_QUERY_KEY = 'reports-by-class' as const
export const REPORTS_BY_SUBJECT_QUERY_KEY = 'reports-by-subject' as const
export const REPORTS_GRADE_DIST_QUERY_KEY = 'reports-grade-distribution' as const
export const REPORTS_STUDENT_TRENDS_QUERY_KEY = 'reports-student-trends' as const
export const REPORTS_HEATMAP_QUERY_KEY = 'reports-subject-heatmap' as const
export const REPORTS_WORKFLOW_QUERY_KEY = 'reports-workflow' as const
export const REPORTS_FEES_RISK_QUERY_KEY = 'reports-fees-academic-risk' as const
export const REPORTS_FINANCE_QUERY_KEY = 'reports-finance' as const
export const REPORTS_ENROLLMENT_QUERY_KEY = 'reports-enrollment' as const
export const REPORTS_STAFF_QUERY_KEY = 'reports-staff-capacity' as const
export const REPORTS_TEACHER_DESK_QUERY_KEY = 'reports-teacher-desk' as const

export const CHART_SKY = '#0284c7'
export const CHART_SKY_LIGHT = '#38bdf8'
export const CHART_GRID = '#e2e8f0'
export const CHART_TICK = '#64748b'

/** Distinct fills for pie / multi-series charts (avoid purple-default look). */
export const CHART_SERIES = [
  '#0284c7',
  '#0d9488',
  '#ca8a04',
  '#e11d48',
  '#475569',
  '#ea580c',
  '#15803d',
  '#0891b2',
] as const

export const formatScore = (value: number | null | undefined) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(1)
}

export const formatPercent = (value: number | null | undefined) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${value.toFixed(1)}%`
}

export const formatDelta = (value: number | null | undefined, suffix = '') => {
  if (value === null || value === undefined || Number.isNaN(value)) return null
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}${suffix}`
}

/** "12 of 30 students with results" — clarifies published coverage vs class size. */
export const formatResultsCoverage = (
  withResults: number | null | undefined,
  enrolled: number | null | undefined,
  noun = 'students',
) => {
  const published = withResults ?? 0
  if (enrolled === null || enrolled === undefined) {
    return `${published} ${noun} with results`
  }
  if (enrolled === 0 && published === 0) {
    return `0 ${noun} enrolled`
  }
  return `${published} of ${enrolled} ${noun} with results`
}

/** "18 of 24 published" for subject score counts vs class size. */
export const formatPublishedCoverage = (
  published: number | null | undefined,
  enrolled: number | null | undefined,
) => {
  const count = published ?? 0
  if (enrolled === null || enrolled === undefined) {
    return `${count} published`
  }
  return `${count} of ${enrolled} published`
}

export const formatCompactFee = (amount: number) =>
  new Intl.NumberFormat('en-GH', {
    style: 'currency',
    currency: 'GHS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)

/** Heat-map cell color from 0–100 average (sky scale). */
export const heatColor = (average: number | null) => {
  if (average === null || Number.isNaN(average)) return '#f1f5f9'
  const t = Math.max(0, Math.min(1, average / 100))
  const lightness = 92 - t * 48
  return `hsl(199 84% ${lightness}%)`
}
