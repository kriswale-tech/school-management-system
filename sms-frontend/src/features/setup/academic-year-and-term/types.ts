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
