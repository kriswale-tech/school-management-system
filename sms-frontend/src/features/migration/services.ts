import api from '@/app/api/api'
import type { PaginatedResponse } from '@/types/generalTypes'
import type {
  FieldMappingInput,
  MigrationJob,
  MigrationJobType,
  MigrationPreviewRow,
  MigrationTemplate,
  TargetField,
} from './types'

export async function listMigrationJobs() {
  const response = await api.get<MigrationJob[]>('/migration/jobs/')
  return response.data
}

export async function createMigrationJob(payload: {
  job_type: MigrationJobType
  template?: MigrationTemplate
  source_system: string
}) {
  const response = await api.post<MigrationJob>('/migration/jobs/', payload)
  return response.data
}

export async function deleteMigrationJob(jobId: string) {
  await api.delete(`/migration/jobs/${jobId}/`)
}

export async function getMigrationJob(jobId: string) {
  const response = await api.get<MigrationJob>(`/migration/jobs/${jobId}/`)
  return response.data
}

export async function uploadMigrationFile(jobId: string, file: File, role?: string) {
  const body = new FormData()
  body.append('file', file)
  if (role) body.append('role', role)
  const response = await api.post(`/migration/jobs/${jobId}/files/`, body)
  return response.data
}

export async function suggestMapping(jobId: string, sheetId: string) {
  const response = await api.get<{
    suggestions: FieldMappingInput[]
    targets: TargetField[]
    unmapped_required: { key: string; label: string }[]
  }>(`/migration/jobs/${jobId}/sheets/${sheetId}/suggestions/`)
  return response.data
}

export async function saveMapping(jobId: string, sheetId: string, mappings: FieldMappingInput[]) {
  const response = await api.put<MigrationJob>(`/migration/jobs/${jobId}/sheets/${sheetId}/mapping/`, {
    mappings,
  })
  return response.data
}

export async function saveMappingProfile(
  jobId: string,
  sheetId: string,
  payload: { name: string; source_system: string; mappings: FieldMappingInput[] },
) {
  const response = await api.post(`/migration/jobs/${jobId}/sheets/${sheetId}/profiles/`, payload)
  return response.data
}

export async function applyMappingProfile(jobId: string, sheetId: string, profileId: string) {
  const response = await api.post<MigrationJob>(
    `/migration/jobs/${jobId}/sheets/${sheetId}/apply-profile/`,
    { profile_id: profileId },
  )
  return response.data
}

export async function listMappingProfiles(jobType: MigrationJobType) {
  const response = await api.get(`/migration/profiles/?job_type=${jobType}`)
  return response.data as { id: string; name: string }[]
}

export async function validateMigration(jobId: string) {
  const response = await api.post(`/migration/jobs/${jobId}/validate/`)
  return response.data
}

export async function previewMigration(jobId: string) {
  const response = await api.get<{
    summary: MigrationJob['summary']
    rows: MigrationPreviewRow[]
  }>(`/migration/jobs/${jobId}/preview/`)
  return response.data
}

export async function setHeaderRow(jobId: string, sheetId: string, headerRow: number) {
  const response = await api.post<MigrationJob>(
    `/migration/jobs/${jobId}/sheets/${sheetId}/header/`,
    { header_row: headerRow },
  )
  return response.data
}

export async function setSheetIncluded(jobId: string, sheetId: string, included: boolean) {
  const response = await api.post(`/migration/jobs/${jobId}/sheets/${sheetId}/include/`, { included })
  return response.data
}

export async function getMigrationResult(jobId: string, outcome: 'saved' | 'unsaved', page: number) {
  const response = await api.get<PaginatedResponse<MigrationPreviewRow> & { saved_count: number; total_count: number }>(
    `/migration/jobs/${jobId}/plan/`,
    { params: { outcome, page, page_size: 50 } },
  )
  return response.data
}

export async function getMigrationPlan(jobId: string, attention = false, all = false) {
  const params = new URLSearchParams()
  if (attention) params.set('attention', '1')
  if (all) params.set('all', '1')
  const query = params.toString()
  const response = await api.get<{
    summary: MigrationJob['summary']
    rows: MigrationPreviewRow[]
  }>(`/migration/jobs/${jobId}/plan/${query ? `?${query}` : ''}`)
  return response.data
}

export async function decideMatch(jobId: string, rowId: string, decision: 'link' | 'create', studentId?: string) {
  const response = await api.post<MigrationPreviewRow>(`/migration/jobs/${jobId}/rows/${rowId}/match/`, {
    decision,
    student_id: studentId ?? '',
  })
  return response.data
}

export async function reviewRow(
  jobId: string,
  rowId: string,
  payload: { resolutions?: Record<string, 'keep' | 'use_imported'>; guardian_decision?: string },
) {
  const response = await api.post<MigrationPreviewRow>(`/migration/jobs/${jobId}/rows/${rowId}/review/`, payload)
  return response.data
}

export async function saveYearPlan(jobId: string, payload: { label: string; start_date: string; end_date: string }) {
  const response = await api.post(`/migration/jobs/${jobId}/years/`, payload)
  return response.data
}

export async function commitMigration(jobId: string, confirmedTotal?: string) {
  const response = await api.post<MigrationJob>(`/migration/jobs/${jobId}/commit/`, {
    confirm: true,
    ...(confirmedTotal !== undefined ? { confirmed_total: confirmedTotal } : {}),
  })
  return response.data
}

export async function resumeMigration(jobId: string) {
  const response = await api.post<MigrationJob>(`/migration/jobs/${jobId}/resume/`)
  return response.data
}

export async function finishMigration(jobId: string) {
  const response = await api.post<MigrationJob>(`/migration/jobs/${jobId}/finish/`)
  return response.data
}

export async function downloadTemplate(template: string, format: 'xlsx' | 'csv' = 'xlsx') {
  const response = await api.get<Blob>(`/migration/templates/${template}/`, {
    responseType: 'blob',
    params: format === 'csv' ? { file: 'csv' } : undefined,
  })
  const names: Record<string, string> = {
    student_information: 'student-information',
    enrollment_history: 'enrollment-history',
    opening_balances: 'opening-balances',
    historical_charges: 'historical-charges',
    historical_payments: 'historical-payments',
  }
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = `${names[template]}.${format}`
  link.click()
  URL.revokeObjectURL(url)
}

export type ValueGroup = {
  field: string
  label: string
  distinct: number
  total: number
  options: { value: string; label: string }[]
  can_omit?: boolean
  values: {
    source_value: string
    label: string
    count: number
    status: string
    canonical_value: string
    needs_confirmation: boolean
  }[]
}

export async function getValueGroups(jobId: string) {
  const response = await api.get<{ fields: ValueGroup[] }>(`/migration/jobs/${jobId}/values/`)
  return response.data.fields
}

export async function approveValues(jobId: string, values: { field: string; source_value: string; label: string; canonical_value: string }[]) {
  const response = await api.post<{ fields: ValueGroup[] }>(`/migration/jobs/${jobId}/values/`, { values })
  return response.data.fields
}

export type ClassGroup = {
  source_value: string
  label: string
  count: number
  status: string
  message: string
  class_label: string
  stream_label: string
  stream_id: string
  needs_confirmation: boolean
  options: { stream_id: string; label: string }[]
}

export async function getClassGroups(jobId: string) {
  const response = await api.get<{ classes: ClassGroup[] }>(`/migration/jobs/${jobId}/classes/`)
  return response.data.classes
}

export async function confirmClass(jobId: string, payload: { source_value: string; stream_id?: string; use_snapshot?: boolean }) {
  const response = await api.post<{ classes: ClassGroup[] }>(`/migration/jobs/${jobId}/classes/`, payload)
  return response.data.classes
}

export type CorrectionField = {
  key: string
  label: string
  kind: 'text' | 'select' | 'date'
  value: string
  options: { value: string; label: string }[]
}

export async function getRowCorrection(jobId: string, rowId: string) {
  const response = await api.get<{ reasons: { column: string; message: string }[]; fields: CorrectionField[] }>(
    `/migration/jobs/${jobId}/rows/${rowId}/correction/`,
  )
  return response.data
}

export async function saveRowCorrection(jobId: string, rowId: string, values: Record<string, string>) {
  const response = await api.post(`/migration/jobs/${jobId}/rows/${rowId}/correction/`, { values })
  return response.data
}

export async function downloadAttentionReport(jobId: string) {
  const response = await api.get<Blob>(`/migration/jobs/${jobId}/attention.csv`, { responseType: 'blob' })
  const match = String(response.headers['content-disposition'] || '').match(/filename="?([^";]+)"?/)
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = match?.[1] || 'needs-attention.csv'
  link.click()
  URL.revokeObjectURL(url)
}

export async function downloadErrorReport(jobId: string) {
  const response = await api.get<Blob>(`/migration/jobs/${jobId}/errors.csv`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = 'migration-errors.csv'
  link.click()
  URL.revokeObjectURL(url)
}
