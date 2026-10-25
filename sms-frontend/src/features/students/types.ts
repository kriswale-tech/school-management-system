export type StudentQueryParams = {
  page?: number
  page_size?: number
  search?: string
  sort?: string
  order?: string
  class_level?: string
  stream?: string
  term?: string
}

export interface StudentClassLevel {
  id: string
  name: string
}

export interface StudentStream {
  id: string
  name: string
  full_name: string
  is_default: boolean
}

export interface PrimaryParent {
  id: string
  name: string
  relationship: string
  phone_number: string
  email: string
  phone_number_alt: string
}


export interface Student {
  id: string
  student_id: string
  first_name: string
  last_name: string
  other_names: string
  gender: string
  date_of_birth: string
  admission_date: string
  class_level: StudentClassLevel
  stream: StudentStream
  is_new_student: boolean
  payment_status: string
  primary_parent: PrimaryParent
}

export interface StudentStats {
  term_id: string
  total_students: number
  new_students: number
  continuing_students: number
  boys: number
  girls: number
  fully_paid: number
  partially_paid: number
  owing: number
  no_fees: number
}

export type StudentGender = 'male' | 'female' | 'other'

export type GuardianRelationship =
  | 'father'
  | 'mother'
  | 'guardian'
  | 'other'
  | 'uncle'
  | 'aunt'
  | 'cousin'
  | 'sibling'
  | 'grandparent'

export type Parent = {
  id: string
  name: string
  phone_number: string
  email: string
}

export type ParentQueryParams = {
  page?: number
  page_size?: number
  search?: string
}

export type GuardianInput =
  | {
      parent_id: string
      relationship: GuardianRelationship
    }
  | {
      name: string
      phone_number: string
      email: string
      relationship: GuardianRelationship
    }

export type StudentOnboardPayload = {
  first_name: string
  last_name: string
  other_names: string
  gender: StudentGender
  date_of_birth: string
  admission_date: string
  guardians: GuardianInput[]
  stream_id: string
  is_new_student: boolean
}

export type StudentClassAssignment = {
  id: string
  class_level_id: string
  display_name: string
  is_default: boolean
}

export type StudentGuardian = {
  id: string
  parent_id: string
  name: string
  phone_number: string
  phone_number_alt: string
  email: string
  address: string
  relationship: GuardianRelationship
  is_primary: boolean
  is_emergency_contact: boolean
}

export type StudentLeaveReason = 'dropout' | 'transfer' | 'other'

export type StudentDetail = {
  id: string
  student_id: string
  full_name: string
  first_name: string
  last_name: string
  other_names: string
  gender: StudentGender
  date_of_birth: string
  age: number
  admission_date: string
  address: string
  is_active: boolean
  is_graduated: boolean
  left_at: string | null
  leave_reason: StudentLeaveReason | null
  leave_notes: string
  left_by_name: string | null
  is_new_student: boolean | null
  class_assignment: StudentClassAssignment | null
  guardians: StudentGuardian[]
  term_id: string
}

export type MarkStudentLeftPayload = {
  reason: StudentLeaveReason
  notes?: string
}

export type StudentBioUpdatePayload = {
  first_name?: string
  last_name?: string
  other_names?: string
  gender?: StudentGender
  date_of_birth?: string
  admission_date?: string
  address?: string
}

export type GuardianCreatePayload =
  | {
      parent_id: string
      relationship: GuardianRelationship
      is_primary?: boolean
      is_emergency_contact?: boolean
    }
  | {
      name: string
      phone_number: string
      email?: string
      relationship: GuardianRelationship
      is_primary?: boolean
      is_emergency_contact?: boolean
    }

export type GuardianUpdatePayload = {
  name?: string
  phone_number?: string
  phone_number_alt?: string
  email?: string
  address?: string
  relationship?: GuardianRelationship
  is_primary?: boolean
  is_emergency_contact?: boolean
}

export type FeePaymentStatus = 'fully_paid' | 'partially_paid' | 'owing' | 'no_fees'

export type StudentFeeItem = {
  id: string
  name: string
  amount: string
}

export type StudentTermFees = {
  term_id: string
  term: string
  term_name: string
  total_billed: string
  total_paid: string
  balance: string
  payment_status: FeePaymentStatus
  fee_items: StudentFeeItem[]
}

export type StudentYearFees = {
  student_id: string
  academic_year_id: string
  academic_year: string
  total_billed: string
  total_paid: string
  balance: string
  payment_status: FeePaymentStatus
  terms: StudentTermFees[]
}

export type StudentFeeHistory = {
  student_id: string
  years: StudentYearFees[]
}

export type StudentPaymentReceipt = {
  id: string
  receipt_number: string
}

export type StudentPayment = {
  id: string
  term_id: string
  term: string
  term_name: string
  academic_year_id: string
  academic_year: string
  amount: string
  payment_method: string
  payment_method_display: string
  paid_at: string
  payment_reference: string
  receipt: StudentPaymentReceipt | null
}

export type StudentFeesQueryParams = {
  academic_year?: string
  term?: string
}

export type StudentAssessmentsQueryParams = {
  term?: string
}

export type SubjectRating = 'strong' | 'secure' | 'borderline' | 'at_risk'

export type StudentPerformanceSubject = {
  rank: number
  subject_id: string | null
  subject_name: string
  total: number
  grade: string | null
  rating: SubjectRating
  terms_with_score?: number
  terms_enrolled?: number
  incomplete?: boolean
}

export type StudentPerformanceGradeRow = {
  grade: string
  count: number
  percent: number
}

export type StudentPerformanceTerm = {
  term_id: string
  term_label: string
  class_display_name: string
  overall_average: number | null
  pass_mark: number
  mode: 'grades' | 'score_bands'
  result_type: string
  subjects: StudentPerformanceSubject[]
  total_graded: number
  grade_distribution: StudentPerformanceGradeRow[]
  expected_subjects_count: number
  published_subjects_count: number
  missing_subjects_count: number
  results_incomplete: boolean
}

export type StudentPerformanceOverallPoint = {
  term_id: string
  term_label: string
  average_score: number
}

export type StudentSubjectTrend = {
  subject_name: string
  points: Array<{
    term_id: string
    term_label: string
    total: number
  }>
}

export type StudentPerformance = {
  student_id: string
  full_name: string
  terms: StudentPerformanceTerm[]
  overall_trend: StudentPerformanceOverallPoint[]
  subject_trends: StudentSubjectTrend[]
  all_time_ranking: StudentPerformanceSubject[]
  all_time_pass_mark: number
  all_time_incomplete: boolean
  enrolled_term_count: number
}