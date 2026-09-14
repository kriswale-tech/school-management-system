import { useEffect, useState } from 'react'
import { Button, Modal } from '@/components/ui'

type BulkReleaseModalProps = {
  open: boolean
  readyCount: number
  isSubmitting?: boolean
  onClose: () => void
  onConfirm: (_remarks: string) => void
}

const BulkReleaseModal = ({
  open,
  readyCount,
  isSubmitting = false,
  onClose,
  onConfirm,
}: BulkReleaseModalProps) => {
  const [remarks, setRemarks] = useState('')

  useEffect(() => {
    if (open) setRemarks('')
  }, [open])

  if (!open) return null

  return (
    <Modal open={open} title="Release ready students" onClose={onClose} className="max-w-lg">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Apply an optional shared head teacher remark and release all{' '}
          <span className="font-medium text-slate-900">{readyCount}</span> student
          {readyCount === 1 ? '' : 's'} the class teacher has approved.
        </p>
        <div>
          <label htmlFor="bulk-release-remarks" className="mb-1.5 block text-sm text-slate-700">
            Head teacher remarks (optional)
          </label>
          <textarea
            id="bulk-release-remarks"
            rows={4}
            value={remarks}
            onChange={(event) => setRemarks(event.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
            placeholder="Remark applied to each released student"
          />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="ghost"
            className="max-w-fit py-2 text-sm"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="max-w-fit py-2 text-sm"
            loading={isSubmitting}
            loadingText="Releasing"
            disabled={readyCount === 0}
            onClick={() => onConfirm(remarks.trim())}
          >
            Release {readyCount} student{readyCount === 1 ? '' : 's'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default BulkReleaseModal
