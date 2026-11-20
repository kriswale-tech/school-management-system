export const STATUS_LABELS: Record<string, string> = {
  draft: 'Not started',
  uploaded: 'File added',
  mapping: 'Mapping',
  validating: 'Checking',
  preview_ready: 'Ready to check',
  committing: 'Saving',
  partially_committed: 'Partly saved',
  committed: 'Saved',
  failed: 'Failed',
  cancelled: 'Cancelled',
  abandoned: 'Stopped',
  ready: 'Ready',
  blocked: 'Needs attention',
  pending: 'Waiting',
  rejected: 'Could not read',
  inspecting: 'Checking file',
  stored: 'Uploaded',
  exact: 'Same ID',
  probable: 'Possible match',
  ambiguous: 'More than one',
  none: 'New student',
  create: 'New student',
  link: 'Existing student',
  review: 'Needs a choice',
  current: 'This term',
  snapshot: 'Old class',
  historical_existing: 'Existing class',
  needs_year: 'Add year dates',
  needs_operational_class: 'Class not found',
  missing: 'Incomplete',
  already_linked: 'Already linked',
  reuse: 'Existing parent',
  keep: 'Keep current parent',
  add_secondary: 'Extra contact',
  skipped: 'Skipped',
}

export const statusLabel = (value?: string) => STATUS_LABELS[value || ''] || 'Waiting'

export const JOB_LABELS = {
  student_enrollment: 'Students',
  fee_financial_history: 'Opening balances',
} as const

export const TEMPLATE_LABELS: Record<string, string> = {
  student_information: 'Student information',
  enrollment_history: 'Enrollment history',
  opening_balances: 'Opening balances',
  historical_finance: 'Fee history',
}
