export type TeacherAssignmentType = 'class_teacher' | 'teaching'

export type BulkImportFileFormat = 'xlsx' | 'csv'

export type BulkImportRowStatus = 'valid' | 'error' | 'warning'

export interface TeacherBulkImportRow {
  first_name: string
  last_name: string
  phone_number: string
  email?: string
  assignment_type?: TeacherAssignmentType | ''
  class_name?: string
  subject_name?: string
  stream_name?: string
  subject_group_name?: string
}

export interface TeacherBulkImportPreviewSummary {
  rows_total: number
  rows_valid: number
  rows_with_errors: number
  rows_with_warnings: number
  teachers_to_create: number
  teachers_to_update: number
  assignments_to_create: number
  assignments_to_replace: number
}

export interface TeacherBulkImportPreviewRow {
  row_number: number
  status: BulkImportRowStatus
  messages: string[]
  data: Partial<TeacherBulkImportRow>
}

export interface TeacherBulkImportPreviewResponse {
  dry_run: true
  summary: TeacherBulkImportPreviewSummary
  rows: TeacherBulkImportPreviewRow[]
}

export interface TeacherBulkImportConfirmSummary {
  rows_total?: number
  rows_processed: number
  rows_succeeded: number
  rows_failed: number
  teachers_created: number
  teachers_updated: number
  assignments_created: number
  assignments_replaced: number
}

export interface TeacherBulkImportFailuresInfo {
  count: number
  download_url: string
  expires_at: string
  format: BulkImportFileFormat
}

export interface TeacherBulkImportConfirmResponse {
  dry_run: false
  summary: TeacherBulkImportConfirmSummary
  failures: TeacherBulkImportFailuresInfo | null
}

export type TeacherBulkImportResponse =
  | TeacherBulkImportPreviewResponse
  | TeacherBulkImportConfirmResponse

export interface TeacherBulkImportFailedRow extends TeacherBulkImportRow {
  row_number: number
  failure_reason: string
}

export interface ApiValidationError {
  detail?: string
  file?: string[]
  dry_run?: string[]
  [field: string]: string | string[] | undefined
}
