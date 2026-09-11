export type AssessmentStatus = 'Incomplete' | 'Complete' | 'Published'

export type CaItem = {
  id: string
  name: string
  max_marks: number
  order?: number
}

export type AssessmentWeights = {
  continuous_assessment_weight: number
  exam_weight: number
}

export type GradeBand = {
  grade: string
  min_score: number
  max_score: number
  remark?: string
  order?: number
}

/** Per-student marks; `null` means empty / not entered. */
export type StudentAssessmentMarks = {
  student_id: string
  ca: Record<string, number | null>
  exam: number | null
}

export type ComputedStudentResult = {
  student_id: string
  class_score: number | null
  exam_score: number | null
  total: number | null
  grade: string | null
  status: AssessmentStatus
}

export type AssessmentWorkspaceStudent = {
  id: string
  full_name: string
  student_id: string
  admission_date: string
  ca: Record<string, number | null>
  exam: number | null
  class_score: number | null
  exam_contribution: number | null
  total: number | null
  grade: string | null
  status: AssessmentStatus
  is_published: boolean
}

export type AssessmentWorkspace = {
  term_id: string
  weights: AssessmentWeights
  grade_bands: GradeBand[]
  result_type: string
  uses_grades: boolean
  ca_items: CaItem[]
  students: AssessmentWorkspaceStudent[]
}

export type SaveMarksPayload = {
  students: Array<{
    student_id: string
    ca: Record<string, number>
    exam: number | null
  }>
}

export type CaItemWritePayload = {
  name: string
  max_marks: number
}

export type ClassTeacherAssessmentOverviewRow = {
  id: string
  class_level_id: string
  class_level_name: string
  stream_id: string | null
  stream_name: string | null
  display_name: string
  students_count: number
  view_stream_id: string | null
  pending_count: number
  awaiting_approval_count: number
  approved_count: number
}

export type ClassTeacherAssessmentOverview = {
  term_id: string
  pending_count: number
  awaiting_approval_count: number
  approved_count: number
  results: ClassTeacherAssessmentOverviewRow[]
}

export type ClassAssessmentStudentStatus =
  | 'pending'
  | 'awaiting_approval'
  | 'approved'

export type ClassAssessmentSubjectRow = {
  subject_label: string
  subject_name: string
  group_name: string | null
  teacher_name: string | null
  is_published: boolean
  status: string
  class_score: number | null
  exam: number | null
  total: number | null
  grade: string | null
  band_remark: string | null
  position: number | null
  position_cohort_size?: number | null
}

export type ClassAssessmentDetailStudent = {
  id: string
  full_name: string
  student_id: string
  status: ClassAssessmentStudentStatus
  subjects_published_count: number
  subjects_required_count: number
  class_teacher_remarks: string
  overall_position: number | null
  overall_average: number | null
  overall_cohort_size: number | null
  subjects: ClassAssessmentSubjectRow[]
}

export type ClassTeacherAssessmentDetail = {
  id: string
  term_id: string
  display_name: string
  class_level_name: string
  stream_name: string | null
  class_teacher_name: string
  pending_count: number
  awaiting_approval_count: number
  approved_count: number
  students_count: number
  weights: AssessmentWeights
  result_type: string
  uses_grades: boolean
  uses_position: boolean
  students: ClassAssessmentDetailStudent[]
}
