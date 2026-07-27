import type { BulkUploadPreviewResult } from '@/components/shared/bulk-upload'
import type {
  BulkImportFileFormat,
  TeacherBulkImportPreviewResponse,
} from './types'
import { TEACHER_IMPORT_TEMPLATE_FILENAME } from './constants'

export const createImportFormData = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return formData
}

export const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export const resolveApiDownloadPath = (downloadUrl: string) => {
  if (downloadUrl.startsWith('http')) {
    const { pathname } = new URL(downloadUrl)
    return pathname.replace(/^\/api\/v1/, '')
  }

  return downloadUrl.replace(/^\/api\/v1/, '')
}

export const getFailureDownloadFilename = (format: BulkImportFileFormat) => {
  return `teacher-import-failures.${format}`
}

export const getFailureDownloadLabel = (count: number, format: BulkImportFileFormat) => {
  const rowLabel = count === 1 ? 'row' : 'rows'
  return `${count} failed ${rowLabel} (${format.toUpperCase()})`
}

export const mapPreviewResponseToBulkUploadResult = (
  response: TeacherBulkImportPreviewResponse,
): BulkUploadPreviewResult => ({
  summary: {
    rows_total: response.summary.rows_total,
    rows_valid: response.summary.rows_valid,
    rows_with_errors: response.summary.rows_with_errors,
    rows_with_warnings: response.summary.rows_with_warnings,
  },
  rows: response.rows.map((row) => ({
    row_number: row.row_number,
    status: row.status,
    messages: row.messages,
    data: row.data as Record<string, string | undefined>,
  })),
})

export const getTemplateFilenameFromResponse = (contentDisposition?: string) => {
  if (!contentDisposition) return TEACHER_IMPORT_TEMPLATE_FILENAME

  const match = contentDisposition.match(/filename="?([^";]+)"?/)
  return match?.[1] ?? TEACHER_IMPORT_TEMPLATE_FILENAME
}
