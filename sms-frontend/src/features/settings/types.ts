export type TermKey = 'first_term' | 'second_term' | 'third_term'

export type AcademicYearStatus = 'past' | 'current' | 'upcoming'

export interface CalendarTerm {
  id: string | null
  term: TermKey
  name: string
  start_date: string | null
  end_date: string | null
  is_active: boolean
  is_ended: boolean
  can_edit_dates: boolean
  is_next: boolean
}

export interface CalendarYear {
  id: string
  academic_year: string
  start_date: string
  end_date: string
  is_active: boolean
  status: AcademicYearStatus
  terms: CalendarTerm[]
}

export interface AcademicYearCalendar {
  years: CalendarYear[]
  next_year_label: string | null
  active_term_id: string | null
}

export interface AcademicYearSchedulePayload {
  academic_year: string
  terms: {
    term: TermKey
    start_date: string
    end_date: string
  }[]
}

export interface TermSwitchPreview {
  can_switch: boolean
  blockers: string[]
  warnings: string[]
  term_id: string
  term_label: string
}

export interface SchoolSettings {
  fees_alert_enabled: boolean
  fees_alert_threshold: string
  results_alert_enabled: boolean
  enrollments_alert_enabled: boolean
}

export interface SchoolAlert {
  kind: 'fees' | 'results' | 'enrollments'
  title: string
  summary: string
  count: number
  href: string
}
