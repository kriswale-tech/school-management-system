import { Icon } from '@iconify/react'
import { LoadingSpinner } from '@/components/ui'
import type { FailedRowsDownloadProps } from '../types'

const FailedRowsDownload = ({ label, onDownload, loading = false }: FailedRowsDownloadProps) => {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-red-100">
          <Icon icon="hugeicons:file-remove" className="size-5 text-red-600" />
        </div>
        <p className="truncate text-sm font-medium text-slate-900">{label}</p>
      </div>

      <button
        type="button"
        onClick={onDownload}
        disabled={!onDownload || loading}
        className="inline-flex shrink-0 items-center gap-1.5 text-sm font-medium text-slate-900 transition-colors enabled:hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? (
          <LoadingSpinner size={16} className="text-current" />
        ) : (
          <Icon icon="hugeicons:download-01" className="size-4" />
        )}
        Download failed rows
      </button>
    </div>
  )
}

export default FailedRowsDownload
