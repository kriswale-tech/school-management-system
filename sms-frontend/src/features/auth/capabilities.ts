/** Capability codes — keep in sync with sms-backend/accounts/capabilities.py */

export const Capability = {
  NAV_DASHBOARD: 'nav.dashboard',
  NAV_STUDENTS: 'nav.students',
  NAV_CLASSES: 'nav.classes',
  NAV_ASSESSMENTS: 'nav.assessments',
  NAV_FEES: 'nav.fees',
  NAV_STAFF: 'nav.staff',
  NAV_REPORTS: 'nav.reports',

  CLASSES_VIEW: 'classes.view',
  CLASSES_MANAGE: 'classes.manage',

  STUDENTS_VIEW: 'students.view',
  STUDENTS_CREATE: 'students.create',
  STUDENTS_MARK_LEFT: 'students.mark_left',
  STUDENTS_REACTIVATE: 'students.reactivate',

  ASSESSMENTS_RECORD: 'assessments.record',
  ASSESSMENTS_APPROVE: 'assessments.approve',
  ASSESSMENTS_RELEASE: 'assessments.release',

  FEES_VIEW: 'fees.view',
  FEES_RECORD_PAYMENT: 'fees.record_payment',
  FEES_MANAGE_SETTINGS: 'fees.manage_settings',

  STAFF_VIEW: 'staff.view',
  STAFF_MANAGE: 'staff.manage',

  REPORTS_VIEW: 'reports.view',
} as const

export type CapabilityCode = (typeof Capability)[keyof typeof Capability]
