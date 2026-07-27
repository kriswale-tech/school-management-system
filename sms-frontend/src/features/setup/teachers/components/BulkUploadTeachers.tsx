import toast from 'react-hot-toast'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import BulkUpload from '@/components/shared/bulk-upload/BulkUpload'
import type {
  BulkUploadFailureInfo,
  BulkUploadPreviewResult,
} from '@/components/shared/bulk-upload'
import { getApiErrorMessage } from '@/utils'
import {
  confirmTeacherBulkImport,
  downloadTeacherImportFailures,
  downloadTeacherImportTemplate,
  previewTeacherBulkImport,
} from '../bulk-upload'
import { TEACHER_BULK_UPLOAD_PREVIEW_HINT } from '../bulk-upload/constants'
import type { TeacherBulkImportFailuresInfo } from '../bulk-upload/types'
import {
  getFailureDownloadLabel,
  mapPreviewResponseToBulkUploadResult,
} from '../bulk-upload/utils'

type BulkUploadTeachersProps = {
  onSuccess?: () => void
}

const BulkUploadTeachers = ({ onSuccess }: BulkUploadTeachersProps) => {
  const [previewResult, setPreviewResult] = useState<BulkUploadPreviewResult | null>(null)
  const [failures, setFailures] = useState<TeacherBulkImportFailuresInfo | null>(null)
  const [failureInfo, setFailureInfo] = useState<BulkUploadFailureInfo | null>(null)

  const resetResults = () => {
    setPreviewResult(null)
    setFailures(null)
    setFailureInfo(null)
  }

  const downloadTemplateMutation = useMutation({
    mutationFn: downloadTeacherImportTemplate,
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to download template'))
    },
  })

  const previewMutation = useMutation({
    mutationFn: previewTeacherBulkImport,
    onSuccess: (response) => {
      setPreviewResult(mapPreviewResponseToBulkUploadResult(response))
      setFailures(null)
      setFailureInfo(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to validate file'))
    },
  })

  const confirmMutation = useMutation({
    mutationFn: confirmTeacherBulkImport,
    onSuccess: (response) => {
      const { summary, failures: importFailures } = response

      if (importFailures) {
        setFailures(importFailures)
        setFailureInfo({
          label: getFailureDownloadLabel(importFailures.count, importFailures.format),
        })
        toast.error(`${summary.rows_failed} row(s) failed to import`)
      } else {
        setFailures(null)
        setFailureInfo(null)
        toast.success(
          `Imported ${summary.rows_succeeded} row(s): ${summary.teachers_created} created, ${summary.teachers_updated} updated`,
        )
      }

      setPreviewResult(null)
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
      format: TeacherBulkImportFailuresInfo['format']
    }) => downloadTeacherImportFailures(downloadUrl, format),
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to download failed rows'))
    },
  })

  return (
    <BulkUpload
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
      previewHint={TEACHER_BULK_UPLOAD_PREVIEW_HINT}
      failureInfo={failureInfo}
      validateLoading={previewMutation.isPending}
      uploadLoading={confirmMutation.isPending}
      downloadFailedRowsLoading={downloadFailuresMutation.isPending}
    />
  )
}

export default BulkUploadTeachers
