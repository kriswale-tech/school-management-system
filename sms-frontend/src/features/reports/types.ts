export type TermOption = {
  id: string
  label: string
  is_active: boolean
}

export type LevelOption = {
  id: string
  name: string
}

export type ClassLevelOption = {
  id: string
  name: string
  level_id: string
}

export type ReportsFilterOptions = {
  active_term_id: string | null
  terms: TermOption[]
  levels: LevelOption[]
  class_levels: ClassLevelOption[]
}

export type ReportsQueryParams = {
  term_id?: string
  level_id?: string
  class_level_id?: string
  compare_term_id?: string
  limit?: number
}

export type OverviewCompare = {
  term_id: string
  term_label: string
  students_count: number
  students_with_results: number
  published_subject_scores: number
  average_score: number | null
  subject_average: number | null
  pass_rate: number | null
  pass_mark: number
  average_score_delta: number | null
  pass_rate_delta: number | null
}

export type ReportsOverview = {
  term_id: string
  term_label: string
  terms: TermOption[]
  scope_mode: 'school' | 'scoped'
  students_count: number
  students_with_results: number
  published_subject_scores: number
  average_score: number | null
  subject_average: number | null
  pass_rate: number | null
  pass_mark: number
  classes_count: number
  distinct_subjects_count: number
  class_subjects_count: number
  teaching_assignments_count: number
  unassigned_class_subjects: number
  compare: OverviewCompare | null
}

export type ClassInsightRow = {
  class_level_id: string
  stream_id: string | null
  display_name: string
  students_count: number
  students_with_results: number
  published_subject_scores: number
  average_score: number | null
  pass_rate: number | null
}

export type ByClassResponse = {
  term_id: string
  term_label: string
  students_count: number
  students_with_results: number
  results: ClassInsightRow[]
}

export type SubjectInsightRow = {
  subject_id: string
  subject_name: string
  score_count: number
  average_score: number | null
  pass_rate: number | null
}

export type BySubjectResponse = {
  term_id: string
  term_label: string
  results: SubjectInsightRow[]
}

export type GradeDistributionRow = {
  grade: string
  count: number
  percent: number
}

export type GradeDistributionMode = 'grades' | 'score_bands'

export type GradeDistributionResponse = {
  term_id: string
  term_label: string
  class_level_id: string
  class_level_name: string
  level_id: string
  level_name: string
  mode: GradeDistributionMode
  result_type: string
  pass_mark: number
  students_count: number
  students_with_results: number
  total_graded: number
  results: GradeDistributionRow[]
}

export type StudentHistoryPoint = {
  term_id: string
  term_label: string
  average_score: number
}

export type StudentTrendRow = {
  id: string
  full_name: string
  student_id: string
  class_display_name: string | null
  average_score: number
  is_passing: boolean
  history: StudentHistoryPoint[]
}

export type StudentTrendsResponse = {
  term_id: string
  term_label: string
  pass_mark?: number
  students_count: number
  students_with_results: number
  below_pass_count: number
  top_students: StudentTrendRow[]
  at_risk_students: StudentTrendRow[]
}

export type HeatmapCell = {
  class_display_name: string
  subject_name: string
  average_score: number | null
  score_count: number
}

export type HeatmapClassSize = {
  display_name: string
  students_count: number
}

export type SubjectHeatmapResponse = {
  term_id: string
  term_label: string
  level_id: string
  level_name: string
  students_count: number
  classes: string[]
  class_sizes: HeatmapClassSize[]
  subjects: string[]
  cells: HeatmapCell[]
}

export type WorkflowRow = {
  display_name: string
  class_level_id: string
  stream_id: string
  students_count: number
  pending_count: number
  ready_count: number
  released_count: number
  needs_correction_count: number
  percent_complete: number
  percent_released: number
}

export type WorkflowResponse = {
  term_id: string
  term_label: string
  pending_count: number
  ready_count: number
  released_count: number
  needs_correction_count: number
  total_students: number
  percent_complete: number | null
  percent_released: number | null
  results: WorkflowRow[]
}

export type FeesRiskRow = {
  id: string
  full_name: string
  student_id: string
  class_display_name: string | null
  average_score: number
  outstanding_amount: number
}

export type FeesAcademicRiskResponse = {
  term_id: string
  term_label: string
  available: boolean
  pass_mark?: number
  debtors_count: number
  at_risk_count: number
  results: FeesRiskRow[]
}

export type FinanceResponse = {
  term_id: string
  term_label: string
  available: boolean
  total_expected: number
  total_collected: number
  outstanding: number
  collection_rate: number | null
  debtors_count: number
  debtors_by_class: Array<{
    display_name: string
    debtors_count: number
    outstanding_amount: number
  }>
  top_debtors: Array<{
    id: string
    full_name: string
    student_id: string
    class_display_name: string
    outstanding_amount: number
  }>
}

export type EnrollmentResponse = {
  term_id: string
  term_label: string
  previous_term_id: string | null
  previous_term_label: string | null
  enrolled_count: number
  new_students: number
  retained_count: number | null
  graduated_count: number | null
  left_count: number | null
  left_by_reason: Array<{ reason: string; count: number }>
  retention_rate: number | null
  by_class: Array<{ display_name: string; students_count: number }>
}

export type TeacherInsightRow = {
  teacher_id: string
  full_name: string
  is_class_teacher: boolean
  is_subject_teacher: boolean
  class_teacher_count: number
  class_teacher_classes: string[]
  class_teacher_students: number
  subjects_taught_count: number
  subject_names: string[]
  teaching_assignments_count: number
  classes_taught_count: number
  teaching_classes: string[]
  assignments: string[]
}

export type StaffCapacityResponse = {
  term_id: string
  term_label: string
  teachers_count: number
  class_teachers_count: number
  subject_teachers_count: number
  both_roles_count: number
  classes_count: number
  classes_without_class_teacher: number
  average_assignments: number | null
  results: TeacherInsightRow[]
}

export type TeacherDeskStudent = {
  id: string
  full_name: string
  student_id: string
  average_score: number
  grade: string | null
  is_passing: boolean
}

export type TeacherDeskClass = {
  class_level_id: string
  stream_id: string | null
  display_name: string
  level_id: string
  students_count: number
  students_with_results: number
  average_score: number | null
  pass_rate: number | null
  pass_mark: number
  mode: GradeDistributionMode
  result_type: string
  total_graded: number
  grade_distribution: GradeDistributionRow[]
  students: TeacherDeskStudent[]
}

export type TeacherDeskSubject = {
  teaching_assignment_id: string
  subject_id: string
  subject_name: string
  class_level_id: string
  stream_id: string | null
  display_name: string
  students_count: number
  score_count: number
  average_score: number | null
  pass_rate: number | null
  pass_mark: number
  mode: GradeDistributionMode
  result_type: string
  total_graded: number
  grade_distribution: GradeDistributionRow[]
  term_history: StudentHistoryPoint[]
  students: TeacherDeskStudent[]
}

export type TeacherDeskResponse = {
  term_id: string
  term_label: string
  scope_mode: 'school' | 'scoped'
  is_class_teacher: boolean
  is_subject_teacher: boolean
  classes: TeacherDeskClass[]
  subjects: TeacherDeskSubject[]
}

export type ClassStreamPerformance = TeacherDeskClass & {
  term_id: string
  term_label: string
}

export type TeachingAssignmentPerformance = TeacherDeskSubject & {
  term_id: string
  term_label: string
}
