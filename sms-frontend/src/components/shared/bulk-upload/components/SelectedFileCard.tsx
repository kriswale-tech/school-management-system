import { Icon } from '@iconify/react'
import type { SelectedFileCardProps } from '../types'

const SelectedFileCard = ({ fileName, onRemove }: SelectedFileCardProps) => {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-green-100">
          <Icon icon="hugeicons:file-02" className="size-5 text-green-600" />
        </div>
        <p className="truncate text-sm font-medium text-slate-900">{fileName}</p>
      </div>

      <button
        type="button"
        aria-label="Remove file"
        onClick={onRemove}
        className="shrink-0 rounded p-1 text-red-600 transition-colors hover:bg-red-50"
      >
        <Icon icon="hugeicons:delete-02" className="size-5" />
      </button>
    </div>
  )
}

export default SelectedFileCard
