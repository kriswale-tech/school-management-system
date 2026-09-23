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
  needs_correction?: boolean
  correction_reason?: string
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
  needs_correction_count: number
}

export type ClassAssessmentStudentStatus =
  | 'pending'
  | 'awaiting_approval'
  | 'approved'
  | 'needs_correction'

export type CorrectionSubject = {
  teaching_assignment_id: string
  subject_label: string
}

export type CorrectionRequest = {
  id: string
  kind: 'reject' | 'reopen' | 'reopen_request'
  status: 'open' | 'declined' | 'applied' | 'resolved'
  reason: string
  previous_result_status: string | null
  student_id: string
  stream_id: string
  term_id: string
  subjects: CorrectionSubject[]
  raised_by_name: string
  raised_at: string | null
  reviewed_by_name: string
  reviewed_at: string | null
  applied_at: string | null
  resolved_at: string | null
}

export type CorrectionInboxItem = CorrectionRequest & {
  student_name: string
  student_code: string
  class_name: string
  class_teacher_id: string | null
  term_label: string | null
}

export type ClassTeacherAssessmentOverview = {
  term_id: string
  pending_count: number
  awaiting_approval_count: number
  approved_count: number
  needs_correction_count: number
  corrections_inbox_count: number
  corrections_inbox: CorrectionInboxItem[]
  results: ClassTeacherAssessmentOverviewRow[]
}

export type ClassAssessmentSubjectRow = {
  teaching_assignment_id: string | null
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
  is_released: boolean
  subjects_published_count: number
  subjects_required_count: number
  class_teacher_remarks: string
  conduct: string
  attitude: string
  interest: string
  overall_position: number | null
  overall_average: number | null
  overall_cohort_size: number | null
  subjects: ClassAssessmentSubjectRow[]
  active_correction: CorrectionRequest | null
}

export type AdminAssessmentTermOption = {
  id: string
  label: string
  is_active: boolean
  academic_year_id: string
  academic_year: string
}

export type AdminAssessmentFilterOptions = {
  terms: AdminAssessmentTermOption[]
  active_term_id: string | null
}

export type AdminAssessmentClassRow = {
  id: string
  class_level_id: string
  stream_id: string
  display_name: string
  class_teacher_id: string | null
  class_teacher_name: string | null
  students_count: number
  with_class_teacher_count: number
  ready_for_you_count: number
  released_count: number
}

export type AdminAssessmentStudentStatus =
  | 'with_class_teacher'
  | 'ready_for_you'
  | 'released'
  | 'needs_correction'

export type AdminAssessmentDetailStudent = {
  id: string
  full_name: string
  student_id: string
  status: AdminAssessmentStudentStatus
  subjects_published_count: number
  subjects_required_count: number
  class_teacher_remarks: string
  conduct: string
  attitude: string
  interest: string
  head_teacher_remarks: string
  overall_position: number | null
  overall_average: number | null
  overall_cohort_size: number | null
  subjects: ClassAssessmentSubjectRow[]
  active_correction: CorrectionRequest | null
}

export type AdminAssessmentDetail = {
  id: string
  term_id: string
  term_label: string
  display_name: string
  class_teacher_name: string | null
  with_class_teacher_count: number
  ready_for_you_count: number
  released_count: number
  needs_correction_count: number
  pending_reopen_requests_count: number
  students_count: number
  weights: AssessmentWeights
  result_type: string
  uses_grades: boolean
  uses_position: boolean
  students: AdminAssessmentDetailStudent[]
}

export type AdminAssessmentOverview = {
  term_id: string
  term_label: string
  with_class_teacher_count: number
  ready_for_you_count: number
  released_count: number
  needs_correction_count?: number
  classes_fully_ready_count: number
  corrections_inbox_count: number
  corrections_inbox: CorrectionInboxItem[]
  results: AdminAssessmentClassRow[]
}

export type StudentReportPreview = {
  student_id: string
  stream_id: string
  term_id: string
  school: {
    name: string
    box_address: string
    address: string
    phone_number: string
    phone_number_alt: string
    email: string
    motto: string
    logo_url: string | null
  }
  report_title: string
  student_name: string
  class_name: string
  academic_year: string
  term_label: string
  next_term_begins: string | null
  students_on_roll: number
  position: number | null
  position_label: string | null
  uses_position: boolean
  uses_grades: boolean
  weights: AssessmentWeights
  subjects: Array<{
    subject_label: string
    class_score: number
    exam_score: number
    total: number
    grade: string | null
    remark: string | null
  }>
  totals: {
    class_score: number | null
    exam_score: number | null
    total: number | null
    max_class_score: number | null
    max_exam_score: number | null
    max_total: number | null
  }
  conduct: string
  attitude: string
  interest: string
  class_teacher_remarks: string
  head_teacher_remarks: string
  class_teacher_name: string
  grade_bands: GradeBand[]
}

export type StoredStudentReport = {
  id: string
  student_id: string
  stream_id: string
  term_id: string
  generated_at: string | null
  url: string | null
  url_expires_in: number
  status: 'ready'
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
  needs_correction_count: number
  students_count: number
  weights: AssessmentWeights
  result_type: string
  uses_grades: boolean
  uses_position: boolean
  students: ClassAssessmentDetailStudent[]
}
