import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import toast from 'react-hot-toast'
import BulkUpload from '@/components/shared/bulk-upload/BulkUpload'
import type {
  BulkUploadFailureInfo,
  BulkUploadPreviewResult,
} from '@/components/shared/bulk-upload'
import { getApiErrorMessage } from '@/utils'
import {
  confirmStudentBulkImport,
  downloadStudentImportFailures,
  downloadStudentImportTemplate,
  previewStudentBulkImport,
} from '@/features/students/bulk-upload'
import {
  STUDENT_BULK_UPLOAD_PREVIEW_HINT,
  STUDENT_BULK_UPLOAD_TEMPLATE_HINT,
} from '@/features/students/bulk-upload/constants'
import type { StudentBulkImportFailuresInfo } from '@/features/students/bulk-upload/types'
import {
  getFailureDownloadLabel,
  mapPreviewResponseToBulkUploadResult,
} from '@/features/students/bulk-upload/utils'

type BulkUploadStudentsProps = {
  onSuccess?: () => void
}

const BulkUploadStudents = ({ onSuccess }: BulkUploadStudentsProps) => {
  const queryClient = useQueryClient()
  const [previewResult, setPreviewResult] = useState<BulkUploadPreviewResult | null>(null)
  const [failures, setFailures] = useState<StudentBulkImportFailuresInfo | null>(null)
  const [failureInfo, setFailureInfo] = useState<BulkUploadFailureInfo | null>(null)
  const [selectionResetKey, setSelectionResetKey] = useState(0)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const resetResults = () => {
    setPreviewResult(null)
    setFailures(null)
    setFailureInfo(null)
    setSuccessMessage(null)
  }

  const downloadTemplateMutation = useMutation({
    mutationFn: downloadStudentImportTemplate,
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to download template'))
    },
  })

  const previewMutation = useMutation({
    mutationFn: previewStudentBulkImport,
    onSuccess: (response) => {
      setPreviewResult(mapPreviewResponseToBulkUploadResult(response))
      setFailures(null)
      setFailureInfo(null)
      setSuccessMessage(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to validate file'))
    },
  })

  const confirmMutation = useMutation({
    mutationFn: confirmStudentBulkImport,
    onSuccess: async (response) => {
      const { summary, failures: importFailures } = response
      const skipped = summary.students_skipped ?? 0

      if (importFailures) {
        setFailures(importFailures)
        setFailureInfo({
          label: getFailureDownloadLabel(importFailures.count, importFailures.format),
        })
        toast.error(`${summary.rows_failed} row(s) failed to import`)
        setSuccessMessage(
          `Imported ${summary.students_created} student(s)` +
            (skipped ? `, skipped ${skipped} existing` : '') +
            `. Download failed rows to review the rest.`,
        )
      } else {
        setFailures(null)
        setFailureInfo(null)
        const message =
          `Imported ${summary.students_created} student(s)` +
          (summary.guardians_linked
            ? ` with ${summary.guardians_linked} guardian(s) linked`
            : '') +
          (skipped ? `, skipped ${skipped} existing` : '')
        setSuccessMessage(`${message}. Choose another file to continue.`)
        toast.success(message)
      }

      setPreviewResult(null)
      setSelectionResetKey((value) => value + 1)
      await queryClient.invalidateQueries({ queryKey: ['students'] })
      onSuccess?.()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to upload file'))
    },
  })

  const downloadFailuresMutation = useMutation({
    mutationFn: ({
      downloadUrl,
      format,
    }: {
      downloadUrl: string
      format: StudentBulkImportFailuresInfo['format']
    }) => downloadStudentImportFailures(downloadUrl, format),
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to download failed rows'))
    },
  })

  return (
    <BulkUpload
      title="Bulk Upload Students"
      templateHint={STUDENT_BULK_UPLOAD_TEMPLATE_HINT}
      onDownloadTemplate={() => downloadTemplateMutation.mutate()}
      onValidate={(file) => previewMutation.mutate(file)}
      onUpload={(file) => confirmMutation.mutate(file)}
      onFileChange={() => resetResults()}
      onDownloadFailedRows={() => {
        if (!failures?.download_url) return
        downloadFailuresMutation.mutate({
          downloadUrl: failures.download_url,
          format: failures.format,
        })
      }}
      previewResult={previewResult}
      previewHint={STUDENT_BULK_UPLOAD_PREVIEW_HINT}
      failureInfo={failureInfo}
      selectionResetKey={selectionResetKey}
      successMessage={successMessage}
      validateLoading={previewMutation.isPending}
      uploadLoading={confirmMutation.isPending}
      downloadFailedRowsLoading={downloadFailuresMutation.isPending}
    />
  )
}

export default BulkUploadStudents
