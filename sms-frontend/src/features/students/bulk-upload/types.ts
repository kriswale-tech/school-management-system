export type BulkImportFileFormat = 'xlsx' | 'csv'

export type BulkImportRowStatus = 'valid' | 'error' | 'warning'

export interface StudentBulkImportRow {
  first_name: string
  last_name: string
  other_names?: string
  gender: string
  date_of_birth: string
  admission_date: string
  is_new_student?: string
  class_name: string
  guardian_name?: string
  guardian_phone?: string
  guardian_email?: string
  guardian_relationship?: string
}

export interface StudentBulkImportPreviewSummary {
  rows_total: number
  rows_valid: number
  rows_with_errors: number
  rows_with_warnings: number
  students_to_create: number
  guardians_to_link: number
}

export interface StudentBulkImportPreviewRow {
  row_number: number
  status: BulkImportRowStatus
  messages: string[]
  data: Partial<StudentBulkImportRow>
}

export interface StudentBulkImportPreviewResponse {
  dry_run: true
  summary: StudentBulkImportPreviewSummary
  rows: StudentBulkImportPreviewRow[]
}

export interface StudentBulkImportConfirmSummary {
  rows_total?: number
  rows_processed: number
  rows_succeeded: number
  rows_failed: number
  students_created: number
  guardians_linked: number
}

export interface StudentBulkImportFailuresInfo {
  count: number
  download_url: string
  expires_at: string
  format: BulkImportFileFormat
}

export interface StudentBulkImportConfirmResponse {
  dry_run: false
  summary: StudentBulkImportConfirmSummary
  failures: StudentBulkImportFailuresInfo | null
}
