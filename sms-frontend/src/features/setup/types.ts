export interface Step {
  step: string
  name: string
  completed: boolean
}

export interface Setup {
  id: number
  steps: Step[]
  current_step: string
  progress_percentage: number
  started_at: string
  completed_at: string
  updated_at: string
  school: string
}

export interface SetupProgressResponse {
  next_step: string
  completed_steps: string[]
  is_complete: boolean
  progress_percentage: number
}

// SCHOOL PROFILE
export interface SchoolProfileFormData {
  school_name: string
  motto: string
  address: string
  gps_address: string
  po_box?: string
  phone_number: string
  phone_number_alt?: string
  email: string
}
export interface SchoolProfile {
  id: string
  created_at: string
  updated_at: string
  name: string
  address: string
  gps_address: string
  box_address: string
  phone_number: string
  phone_number_alt: string
  email: string
  logo: string
  motto: string
  setup_completed: boolean
  setup_completed_at: string
}

// ACADEMIC YEAR AND TERM
export type TermApiKey = 'first_term' | 'second_term' | 'third_term'

export type TermName = 'First term' | 'Second term' | 'Third term'

export interface Term {
  term: TermApiKey
  name: string
  start_date: string
  end_date: string
  is_active: boolean
}

export interface AcademicYearAndTerm {
  academic_year: string | null
  start_date: string | null
  end_date: string | null
  is_active: boolean
  current_term: TermApiKey | null
  terms: Term[]
}

export interface AcademicYearAndTermFormData {
  academic_year: string
  current_term: TermName
  terms: {
    name: TermName
    start_date: string
    end_date: string
  }[]
}

export interface AcademicYearAndTermPayload {
  academic_year: string
  current_term: TermApiKey
  terms: {
    term: TermApiKey
    start_date: string
    end_date: string
  }[]
}

// CLASS AND SUBJECTS

export type SubjectScope = 'class' | 'level'

export interface StreamForSetup {
  id: string
  name: string
  full_name: string
  description: string | null
  is_default: boolean
  is_active: boolean
  capacity: number | null
}

export interface SubjectGroupForSetup {
  id?: string
  name: string
  is_active?: boolean
}

export interface SubjectForSetup {
  id?: string
  name: string
  is_active?: boolean
  is_system_generated?: boolean
  is_editable: boolean
  groups: SubjectGroupForSetup[]
}

export interface ClassSubjectForSetup extends SubjectForSetup {
  id: string
  class_subject_id: string
}

export interface ClassForSetup {
  id?: string
  name: string
  description?: string | null
  order?: number
  is_active?: boolean
  is_system_generated?: boolean
  is_editable: boolean
  streams?: StreamForSetup[]
  subjects?: ClassSubjectForSetup[]
}

export interface LevelForSetup {
  id?: string
  name: string
  description?: string | null
  order?: number
  is_active?: boolean
  is_system_generated?: boolean
  subject_scope: SubjectScope
  allows_custom_classes: boolean
  classes: ClassForSetup[]
  subjects: SubjectForSetup[]
}

export type LevelWithRelatedClassesAndSubjects = LevelForSetup[]
