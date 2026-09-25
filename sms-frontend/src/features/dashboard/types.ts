export type AdminDashboardNeedsAttentionItem = {
  code: string
  label: string
  count: number
  href: string
}

export type AdminDashboardTopDebtor = {
  student_id: string
  student_code: string
  full_name: string
  class_display: string
  outstanding_amount: string
}

export type AdminDashboardAcademicProgress = {
  stream_id: string
  class_level_id: string
  level_id: string | null
  level_name: string | null
  display_name: string
  students_count: number
  ready_count: number
  released_count: number
  completed_count: number
  ready_percent: number
  released_percent: number
  percent_complete: number
}

export type AdminDashboardLevel = {
  id: string
  name: string
}

export type AdminDashboardSetupHealthMetric = {
  label: string
  assigned: number
  total: number
  percent: number
  href: string
}

export type AdminDashboardSetupHealth = {
  class_teachers: AdminDashboardSetupHealthMetric
  subject_teachers: AdminDashboardSetupHealthMetric
  classes_with_students: AdminDashboardSetupHealthMetric
  subject_groups_with_students: AdminDashboardSetupHealthMetric
  students_in_subject_groups: AdminDashboardSetupHealthMetric
}

export type AdminDashboard = {
  term_id: string | null
  term_label: string | null
  show_academic_widgets: boolean
  school_overview: {
    total_students: number
    total_classes: number
    staff_members: number
  }
  fees_overview: {
    fees_collected: string
    outstanding_balance: string
    debtors_count: number
  }
  academic_overview: {
    reports_ready: number
    pending_reports: number
    released_reports: number
    needs_correction: number
  }
  coverage_overview: {
    unassigned_classes: number
    unassigned_subjects: number
    empty_classes: number
  }
  needs_attention: AdminDashboardNeedsAttentionItem[]
  top_debtors: AdminDashboardTopDebtor[]
  setup_health: AdminDashboardSetupHealth
  academic_progress: AdminDashboardAcademicProgress[]
  levels: AdminDashboardLevel[]
}

export type OverviewMetric = {
  label: string
  value: string
}
