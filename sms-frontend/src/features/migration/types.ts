export type MigrationJobType = 'student_enrollment' | 'fee_financial_history'

export type MigrationTransform = {
  step: string
  config: Record<string, unknown>
}

export type FieldMappingInput = {
  source_column: string
  target_field: string
  ignored: boolean
  transforms: MigrationTransform[]
  suggested?: boolean
}

export type MigrationTemplate = 'student_information' | 'enrollment_history' | 'opening_balances' | 'historical_finance'

export type HistoricalSummary = {
  total_rows: number
  valid_rows: number
  blocked_rows: number
  review_rows: number
  skipped_rows: number
  unique_students: number
  charge_total: string
  payment_total: string
  advance_total: string
  payments: number
}

export type OpeningBalanceSummary = {
  total_rows: number
  valid_rows: number
  blocked_rows: number
  review_rows: number
  skipped_rows: number
  unique_students: number
  academic_years: string[]
  terms: string[]
  by_year: { academic_year: string; total: string }[]
  by_term: { academic_year: string; term: string; total: string }[]
  total: string
  duplicates: number
  overlaps: number
}

export type MigrationSheet = {
  id: string
  sheet_name: string
  header_row: number
  detected_headers: string[]
  sample_rows: Record<string, string>[]
  row_count: number
  included: boolean
  mapping_profile: string | null
  mappings: FieldMappingInput[]
}

export type MigrationFile = {
  id: string
  original_filename: string
  file_hash: string
  file_size: number
  detected_encoding: string
  detected_delimiter: string
  status: string
  error: string
  role?: string
  sheets: MigrationSheet[]
}

export type MigrationJob = {
  id: string
  job_type: MigrationJobType
  template?: MigrationTemplate | ''
  status: string
  source_system: string
  file_hash: string
  summary: {
    total_rows?: number
    ready_rows?: number
    blocked_rows?: number
    warning_rows?: number
    unmapped_columns?: { sheet: string; column: string }[]
    plan?: Record<string, number>
    year_plans?: { label: string; start_date: string; end_date: string }[]
    opening?: OpeningBalanceSummary
    history?: HistoricalSummary
  }
  created_at: string
  committed_at?: string | null
  files: MigrationFile[]
}

export type MigrationPreviewRow = {
  id: string
  sheet_name: string
  source_row_number: number
  raw_values: Record<string, string>
  transformed_values: Record<string, string>
  validation_status: string
  commit_status: string
  errors: { column: string; message: string }[]
  warnings: { column: string; message: string }[]
  proposal?: {
    action?: string
    match_kind?: string
    match_reason?: string
    student_label?: string
    blocked?: boolean
    candidates?: { id: string; student_id: string; name: string; date_of_birth: string; reason: string }[]
    fills?: { field: string; imported: string }[]
    conflicts?: { field: string; current: string; imported: string }[]
    guardian?: { action?: string; name?: string; phone?: string; message?: string; current_primary?: string }
    enrollment?: { action?: string; class_name?: string; year?: string; term?: string; message?: string }
    block_reasons?: { column: string; message: string }[]
    duplicate_warning?: string
    amount?: string
    source_reference?: string
    role?: string
    payment_reference?: string
    payment_type?: string
    overlap?: boolean
    lifecycle?: { is_active?: boolean; is_graduated?: boolean; apply?: boolean }
  }
}

export type TargetField = {
  key: string
  label: string
  required: boolean
}
