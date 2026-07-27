import { useState } from 'react'
import { Button } from '@/components/ui'
import { mergeClasses } from '@/utils'
import DropZone from './components/DropZone'
import FailedRowsDownload from './components/FailedRowsDownload'
import PreviewResults from './components/PreviewResults'
import SelectedFileCard from './components/SelectedFileCard'
import TemplateSection from './components/TemplateSection'
import {
  DEFAULT_ACCEPTED_EXTENSIONS,
  DEFAULT_MAX_FILE_SIZE_MB,
  DEFAULT_TEMPLATE_HINT,
  DEFAULT_TITLE,
} from './constants'
import type { BulkUploadProps } from './types'

const BulkUpload = ({
  title = DEFAULT_TITLE,
  templateHint = DEFAULT_TEMPLATE_HINT,
  onDownloadTemplate,
  acceptedExtensions = DEFAULT_ACCEPTED_EXTENSIONS,
  maxFileSizeMb = DEFAULT_MAX_FILE_SIZE_MB,
  onValidate,
  onUpload,
  onFileChange,
  onDownloadFailedRows,
  validateLoading = false,
  uploadLoading = false,
  downloadFailedRowsLoading = false,
  uploadDisabled = false,
  previewResult = null,
  previewHint,
  failureInfo = null,
  className,
}: BulkUploadProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState('')

  const handleFileSelect = (file: File) => {
    setSelectedFile(file)
    onFileChange?.(file)
  }

  const handleFileRemove = () => {
    setSelectedFile(null)
    setError('')
    onFileChange?.(null)
  }

  const handleValidate = () => {
    if (!selectedFile || !onValidate) return
    onValidate(selectedFile)
  }

  const handleUpload = () => {
    if (!selectedFile || !onUpload) return
    onUpload(selectedFile)
  }

  const isUploadDisabled = !selectedFile || !onUpload || uploadDisabled

  return (
    <div className={mergeClasses('space-y-6', className)}>
      <h3 className="text-base font-medium text-slate-900">{title}</h3>

      <TemplateSection hint={templateHint} onDownloadTemplate={onDownloadTemplate} />

      <DropZone
        acceptedExtensions={acceptedExtensions}
        maxFileSizeMb={maxFileSizeMb}
        error={error}
        onFileSelect={handleFileSelect}
        onError={setError}
      />

      {selectedFile ? (
        <SelectedFileCard fileName={selectedFile.name} onRemove={handleFileRemove} />
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          type="button"
          variant="outline"
          className="sm:flex-1"
          disabled={!selectedFile || !onValidate}
          loading={validateLoading}
          loadingText="Validating"
          onClick={handleValidate}
        >
          Validate file
        </Button>
        <Button
          type="button"
          variant="solid"
          className="sm:flex-1"
          disabled={isUploadDisabled}
          loading={uploadLoading}
          loadingText="Uploading"
          onClick={handleUpload}
        >
          Upload file
        </Button>
      </div>

      {previewResult ? <PreviewResults preview={previewResult} hint={previewHint} /> : null}

      {failureInfo ? (
        <FailedRowsDownload
          label={failureInfo.label}
          onDownload={onDownloadFailedRows}
          loading={downloadFailedRowsLoading}
        />
      ) : null}
    </div>
  )
}

export default BulkUpload
