import api from '@/app/api/api'
import { STUDENT_BULK_UPLOAD_BASE_URL } from './constants'
import type {
  BulkImportFileFormat,
  StudentBulkImportConfirmResponse,
  StudentBulkImportPreviewResponse,
} from './types'
import {
  createImportFormData,
  downloadBlob,
  getFailureDownloadFilename,
  getTemplateFilenameFromResponse,
  resolveApiDownloadPath,
} from './utils'

export const downloadStudentImportTemplate = async () => {
  const response = await api.get<Blob>(`${STUDENT_BULK_UPLOAD_BASE_URL}template/`, {
    responseType: 'blob',
  })

  const filename = getTemplateFilenameFromResponse(
    response.headers['content-disposition'] as string | undefined,
  )

  downloadBlob(response.data, filename)
}

export const previewStudentBulkImport = async (
  file: File,
): Promise<StudentBulkImportPreviewResponse> => {
  const response = await api.post<StudentBulkImportPreviewResponse>(
    STUDENT_BULK_UPLOAD_BASE_URL,
    createImportFormData(file),
    { params: { dry_run: true } },
  )

  return response.data
}

export const confirmStudentBulkImport = async (
  file: File,
): Promise<StudentBulkImportConfirmResponse> => {
  const response = await api.post<StudentBulkImportConfirmResponse>(
    STUDENT_BULK_UPLOAD_BASE_URL,
    createImportFormData(file),
    { params: { dry_run: false } },
  )

  return response.data
}

export const downloadStudentImportFailures = async (
  downloadUrl: string,
  format: BulkImportFileFormat,
) => {
  const response = await api.get<Blob>(resolveApiDownloadPath(downloadUrl), {
    responseType: 'blob',
  })

  downloadBlob(response.data, getFailureDownloadFilename(format))
}
