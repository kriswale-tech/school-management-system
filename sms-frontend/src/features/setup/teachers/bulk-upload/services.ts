import api from '@/app/api/api'
import { TEACHER_BULK_UPLOAD_BASE_URL } from './constants'
import type {
  TeacherBulkImportConfirmResponse,
  TeacherBulkImportPreviewResponse,
} from './types'
import type { BulkImportFileFormat } from './types'
import {
  createImportFormData,
  downloadBlob,
  getFailureDownloadFilename,
  getTemplateFilenameFromResponse,
  resolveApiDownloadPath,
} from './utils'

export const downloadTeacherImportTemplate = async () => {
  const response = await api.get<Blob>(`${TEACHER_BULK_UPLOAD_BASE_URL}template/`, {
    responseType: 'blob',
  })

  const filename = getTemplateFilenameFromResponse(
    response.headers['content-disposition'] as string | undefined,
  )

  downloadBlob(response.data, filename)
}

export const previewTeacherBulkImport = async (
  file: File,
): Promise<TeacherBulkImportPreviewResponse> => {
  const response = await api.post<TeacherBulkImportPreviewResponse>(
    TEACHER_BULK_UPLOAD_BASE_URL,
    createImportFormData(file),
    { params: { dry_run: true } },
  )

  return response.data
}

export const confirmTeacherBulkImport = async (
  file: File,
): Promise<TeacherBulkImportConfirmResponse> => {
  const response = await api.post<TeacherBulkImportConfirmResponse>(
    TEACHER_BULK_UPLOAD_BASE_URL,
    createImportFormData(file),
    { params: { dry_run: false } },
  )

  return response.data
}

export const downloadTeacherImportFailures = async (
  downloadUrl: string,
  format: BulkImportFileFormat,
) => {
  const response = await api.get<Blob>(resolveApiDownloadPath(downloadUrl), {
    responseType: 'blob',
  })

  downloadBlob(response.data, getFailureDownloadFilename(format))
}
