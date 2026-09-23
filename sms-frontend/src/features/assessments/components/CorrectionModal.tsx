import { useEffect, useMemo, useState } from 'react'
import { Button, Modal } from '@/components/ui'
import type { ClassAssessmentSubjectRow } from '@/features/classes/assessment/types'

type CorrectionModalProps = {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  subjects: ClassAssessmentSubjectRow[]
  isSubmitting?: boolean
  onClose: () => void
  onConfirm: (_payload: { teaching_assignment_ids: string[]; reason: string }) => void
}

const CorrectionModal = ({
  open,
  title,
  description,
  confirmLabel,
  subjects,
  isSubmitting = false,
  onClose,
  onConfirm,
}: CorrectionModalProps) => {
  const selectable = useMemo(
    () =>
      subjects.filter(
        (subject) => subject.teaching_assignment_id && subject.is_published,
      ),
    [subjects],
  )
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [reason, setReason] = useState('')

  useEffect(() => {
    if (!open) return
    setSelectedIds(selectable.map((subject) => subject.teaching_assignment_id!))
    setReason('')
  }, [open, selectable])

  if (!open) return null

  const toggle = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  const canSubmit = selectedIds.length > 0 && reason.trim().length > 0

  return (
    <Modal open={open} title={title} onClose={onClose} className="max-w-lg">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">{description}</p>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-800">Subjects to send back</p>
          {selectable.length === 0 ? (
            <p className="text-sm text-slate-500">No published subjects available.</p>
          ) : (
            <ul className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-slate-200 p-3">
              {selectable.map((subject) => {
                const id = subject.teaching_assignment_id!
                return (
                  <li key={id}>
                    <label className="flex cursor-pointer items-start gap-2 text-sm text-slate-800">
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={selectedIds.includes(id)}
                        onChange={() => toggle(id)}
                      />
                      <span>{subject.subject_label}</span>
                    </label>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <div>
          <label htmlFor="correction-reason" className="mb-1.5 block text-sm text-slate-700">
            Reason <span className="text-red-600">*</span>
          </label>
          <textarea
            id="correction-reason"
            rows={4}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
            placeholder="Explain what needs to be fixed"
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
            loadingText="Saving"
            disabled={!canSubmit}
            onClick={() =>
              onConfirm({
                teaching_assignment_ids: selectedIds,
                reason: reason.trim(),
              })
            }
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default CorrectionModal
