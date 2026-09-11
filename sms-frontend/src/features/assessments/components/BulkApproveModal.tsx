import { useEffect, useState } from 'react'
import { Button, Modal } from '@/components/ui'

type BulkApproveModalProps = {
  open: boolean
  awaitingCount: number
  isSubmitting?: boolean
  onClose: () => void
  onConfirm: (_remarks: string) => void
}

const BulkApproveModal = ({
  open,
  awaitingCount,
  isSubmitting = false,
  onClose,
  onConfirm,
}: BulkApproveModalProps) => {
  const [remarks, setRemarks] = useState('')

  useEffect(() => {
    if (open) setRemarks('')
  }, [open])

  if (!open) return null

  return (
    <Modal open={open} title="Approve awaiting students" onClose={onClose} className="max-w-lg">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Apply an optional shared remark and approve all{' '}
          <span className="font-medium text-slate-900">{awaitingCount}</span> student
          {awaitingCount === 1 ? '' : 's'} awaiting approval.
        </p>
        <div>
          <label htmlFor="bulk-approve-remarks" className="mb-1.5 block text-sm text-slate-700">
            Shared remarks (optional)
          </label>
          <textarea
            id="bulk-approve-remarks"
            rows={4}
            value={remarks}
            onChange={(event) => setRemarks(event.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
            placeholder="Remark applied to each approved student"
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
            loadingText="Approving"
            disabled={awaitingCount === 0}
            onClick={() => onConfirm(remarks.trim())}
          >
            Approve {awaitingCount} student{awaitingCount === 1 ? '' : 's'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default BulkApproveModal
