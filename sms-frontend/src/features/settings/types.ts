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

export interface SchoolSettings {
  fees_alert_enabled: boolean
  fees_alert_threshold: string
  results_alert_enabled: boolean
  enrollments_alert_enabled: boolean
  transition_popup_enabled: boolean
}

export type TransitionUrgency = 'amber' | 'red'

export interface TransitionChecklistItem {
  kind: string
  title: string
  summary: string
  done: boolean
  href: string | null
}

export interface TransitionStatus {
  visible: boolean
  urgency: TransitionUrgency | null
  title: string
  days_remaining: number | null
  term_ends_on: string | null
  popup_enabled: boolean
  unfinished_count: number
  checklist: TransitionChecklistItem[]
  term_label: string | null
}

export interface TransitionStreamOption {
  id: string
  name: string
}

export interface TransitionPlacement {
  source_stream_id: string
  source_label: string
  source_class_name: string
  student_count: number
  destination_class_id: string | null
  destination_class_name: string | null
  destination_stream_id: string | null
  destination_stream_name: string | null
  outcome: 'stay' | 'promote' | 'graduate' | 'needs_stream'
  stream_options: TransitionStreamOption[]
}

export interface TransitionFeeItem {
  id: string
  name: string
  amount: string
  applies_to: string
  student_type: string
}

export interface TransitionPreview {
  can_confirm: boolean
  blockers: string[]
  warnings: string[]
  is_year_change: boolean
  term_id: string | null
  term_label: string | null
  placements: TransitionPlacement[]
  unenrolled_students: { id: string; name: string }[]
  already_enrolled_count: number
  graduate_count: number
  unreleased_reports: number
  unmatched_subjects: string[]
  fees: {
    status: string
    locked: boolean
    items: TransitionFeeItem[]
  }
}

export interface TransitionConfirmPayload {
  acknowledge_warnings: boolean
  stream_choices: { source_stream_id: string; destination_stream_id: string }[]
}

export interface SchoolAlert {
  kind: 'fees' | 'results' | 'enrollments'
  title: string
  summary: string
  count: number
  href: string
}
