import type { PaginatedResponse } from '@/types/generalTypes'
import type { QueryParamValue } from '@/utils/get-query-url'

export type FeePaymentStatus = 'fully_paid' | 'partially_paid' | 'owing' | 'no_fees'

export type FeeDeskClassLevel = {
  id: string
  name: string
}

export type FeeDeskStream = {
  id: string
  name: string | null
  full_name: string
  is_default: boolean
}

export type FeeDeskRow = {
  id: string
  student_id: string
  first_name: string
  last_name: string
  other_names: string
  class_level: FeeDeskClassLevel
  stream: FeeDeskStream
  amount_paid: string
  remaining_balance: string
  advance_balance: string
  last_transaction_at: string | null
  payment_status: FeePaymentStatus
}

export type FeeDeskListResponse = PaginatedResponse<FeeDeskRow>

export type FeeDeskStats = {
  total_expected: string
  total_collected: string
  outstanding: string
  debtors_count: number
  total_students: number
  students_in_credit: number
  total_advances: string
}

export type FeeDeskTermOption = {
  id: string
  term: string
  term_name: string
  label: string
  is_active: boolean
  is_ended: boolean
  has_fee_structure: boolean
  academic_year_id: string
  academic_year: string
}

export type FeeDeskAcademicYear = {
  id: string
  academic_year: string
  is_active: boolean
  terms: FeeDeskTermOption[]
}

export type FeeDeskFilterOptions = {
  academic_years: FeeDeskAcademicYear[]
  terms: FeeDeskTermOption[]
  active_term_id: string | null
}

export type FeeDeskQueryParams = {
  page?: number
  page_size?: number
  search?: string
  class_level?: string
  stream?: string
  term?: string
} & Record<string, QueryParamValue>

export type PaymentMethod =
  | 'cash'
  | 'cheque'
  | 'bank_transfer'
  | 'mobile_money'
  | 'other'

export type PaymentTargetStudent = {
  id: string
  student_id: string
  full_name: string
  class_display: string | null
}

export type PaymentTargetTerm = {
  id: string
  term: string
  term_name: string
  academic_year_id: string
  academic_year: string
  label: string
}

export type StudentPaymentTarget = {
  student_id: string
  student: PaymentTargetStudent
  target_term: PaymentTargetTerm | null
  outstanding_balance: string
  has_outstanding: boolean
  advance_balance: string
  has_advance: boolean
}

export type RecordPaymentPayload = {
  student_id: string
  amount: string | number
  payment_method: PaymentMethod
  paid_at: string
  payment_reference?: string
  payment_notes?: string
}

export type RecordPaymentResponse = {
  payment_id: string
  receipt_id: string
  receipt_number: string
  term_id: string
  term_label: string
  amount: string
  amount_applied: string
  advance_created: string
  outstanding_after: string
  advance_balance: string
  credit_id: string | null
  paid_at: string
}

export type FeeStructureStatus = 'draft' | 'published' | 'applied' | 'carried_forward'

export type FeeItemAppliesTo = 'level' | 'class' | 'school'

export type FeeItemStudentType = 'new_student' | 'continuing_student' | 'all_students'

export type FeeStructure = {
  id: string
  name: string
  status: FeeStructureStatus
  status_display: string
  is_editable: boolean
  is_locked: boolean
  term_ended: boolean
  can_apply: boolean
  item_count: number
  term_id: string
  term_name: string
  academic_year: string
  applied_at: string | null
}

export type FeeStructureItem = {
  id: string
  name: string
  amount: string
  description: string
  applies_to_type: FeeItemAppliesTo
  applies_to_type_display: string
  applies_to_id: string | null
  applies_to_name: string
  student_type: FeeItemStudentType
  student_type_display: string
  term_id: string
  term_name: string
  academic_year: string
}

export type FeeStructureDetail = {
  fee_structure: FeeStructure
  fee_items: FeeStructureItem[]
}

export type FeeStructureItemPayload = {
  name: string
  amount: string
  description?: string
  applies_to_type: FeeItemAppliesTo
  applies_to_id: string | null
  student_type: FeeItemStudentType
  term?: string
}
