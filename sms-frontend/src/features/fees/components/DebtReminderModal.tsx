import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Button, Modal } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'
import { previewDebtReminders, sendDebtReminders } from '../services'
import type { DebtReminderPreview } from '../types'

type DebtReminderModalProps = {
  open: boolean
  termId: string | null
  studentIds: string[]
  onClose: () => void
  onSent: () => void
}

const audienceLabel = (value: DebtReminderPreview['audience']) =>
  value === 'all' ? 'All linked guardians' : 'Primary guardians only'

const channelsLabel = (value: DebtReminderPreview['channels']) => {
  if (value === 'sms') return 'SMS only'
  if (value === 'email') return 'Email only'
  if (value === 'both') return 'SMS and email'
  return '—'
}

const DebtReminderModal = ({
  open,
  termId,
  studentIds,
  onClose,
  onSent,
}: DebtReminderModalProps) => {
  const [preview, setPreview] = useState<DebtReminderPreview | null>(null)

  const { mutate: loadPreview, isPending: isPreviewing } = useMutation({
    mutationFn: previewDebtReminders,
    onSuccess: (data) => setPreview(data),
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to preview reminders'))
      onClose()
    },
  })

  const { mutate: send, isPending: isSending } = useMutation({
    mutationFn: sendDebtReminders,
    onSuccess: (result) => {
      toast.success(
        `Queued reminders for ${result.students_notified} student${result.students_notified === 1 ? '' : 's'} (${result.sms_sent} SMS, ${result.email_sent} email)`,
      )
      onSent()
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to send reminders'))
    },
  })

  const studentIdsKey = studentIds.join(',')

  useEffect(() => {
    if (!open) {
      setPreview(null)
      return
    }
    if (!studentIdsKey) return
    loadPreview({
      term_id: termId || undefined,
      student_ids: studentIdsKey.split(','),
    })
  }, [open, termId, studentIdsKey, loadPreview])

  return (
    <Modal open={open} title="Remind parents" onClose={onClose} scrollable className="max-w-lg">
      {isPreviewing || !preview ? (
        <LoadingSpinner className="mx-auto my-8" />
      ) : (
        <div className="space-y-5">
          {!preview.enabled ? (
            <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Debt reminders are turned off. Enable them under Settings → Parent messages before
              sending.
            </p>
          ) : null}

          <p className="text-sm text-slate-600">
            Remind guardians for{' '}
            <span className="font-medium text-slate-900">{preview.eligible_count}</span> eligible
            student{preview.eligible_count === 1 ? '' : 's'} with outstanding fees (
            {preview.term_label}).
          </p>

          <dl className="grid grid-cols-[140px_1fr] gap-x-3 gap-y-2 text-sm">
            <dt className="text-slate-500">Audience</dt>
            <dd>{audienceLabel(preview.audience)}</dd>
            <dt className="text-slate-500">Channels</dt>
            <dd>{channelsLabel(preview.channels)}</dd>
            <dt className="text-slate-500">Estimated SMS</dt>
            <dd>{preview.sms_count}</dd>
            <dt className="text-slate-500">Estimated email</dt>
            <dd>{preview.email_count}</dd>
            <dt className="text-slate-500">Skipped</dt>
            <dd>{preview.skipped_count}</dd>
          </dl>

          {preview.eligible.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-800">Eligible students</p>
              <ul className="max-h-40 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                {preview.eligible.map((row) => (
                  <li key={row.student_id} className="py-1">
                    {row.full_name} — GHS {row.balance}
                  </li>
                ))}
                {preview.eligible_truncated ? (
                  <li className="py-1 text-slate-500">…and more</li>
                ) : null}
              </ul>
            </div>
          ) : null}

          {preview.skipped.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-800">Skipped</p>
              <ul className="max-h-32 overflow-y-auto rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600">
                {preview.skipped.map((row) => (
                  <li key={`${row.student_id}-${row.reason}`} className="py-1">
                    {row.full_name ?? row.student_id}: {row.reason}
                  </li>
                ))}
                {preview.skipped_truncated ? (
                  <li className="py-1 text-slate-500">…and more</li>
                ) : null}
              </ul>
            </div>
          ) : null}

          <div className="grid grid-cols-2 gap-3 pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSending}>
              Cancel
            </Button>
            <Button
              type="button"
              loading={isSending}
              loadingText="Sending..."
              disabled={!preview.enabled || preview.eligible_count === 0}
              onClick={() =>
                send({
                  term_id: termId || undefined,
                  student_ids: studentIds,
                })
              }
            >
              Send reminders
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}

export default DebtReminderModal
