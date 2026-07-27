export type BulkImportRowStatus = 'valid' | 'error' | 'warning'

export type BulkUploadPreviewSummary = {
  rows_total: number
  rows_valid: number
  rows_with_errors: number
  rows_with_warnings: number
}

export type BulkUploadPreviewRow = {
  row_number: number
  status: BulkImportRowStatus
  messages: string[]
  data?: Record<string, string | undefined>
}

export type BulkUploadPreviewResult = {
  summary: BulkUploadPreviewSummary
  rows: BulkUploadPreviewRow[]
}

export type BulkUploadFailureInfo = {
  label: string
}

export type BulkUploadProps = {
  title?: string
  templateHint?: string
  onDownloadTemplate?: () => void
  acceptedExtensions?: string[]
  maxFileSizeMb?: number
  onValidate?: (file: File) => void
  onUpload?: (file: File) => void
  onFileChange?: (file: File | null) => void
  onDownloadFailedRows?: () => void
  validateLoading?: boolean
  uploadLoading?: boolean
  downloadFailedRowsLoading?: boolean
  uploadDisabled?: boolean
  previewResult?: BulkUploadPreviewResult | null
  previewHint?: string
  failureInfo?: BulkUploadFailureInfo | null
  className?: string
}

export type TemplateSectionProps = {
  hint: string
  onDownloadTemplate?: () => void
}

export type DropZoneProps = {
  acceptedExtensions: string[]
  maxFileSizeMb: number
  error: string
  onFileSelect: (file: File) => void
  onError: (message: string) => void
}

export type SelectedFileCardProps = {
  fileName: string
  onRemove: () => void
}

export type FailedRowsDownloadProps = {
  label: string
  onDownload?: () => void
  loading?: boolean
}

export type PreviewResultsProps = {
  preview: BulkUploadPreviewResult
  hint?: string
}
