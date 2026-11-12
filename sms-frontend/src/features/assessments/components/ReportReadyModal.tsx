import { useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Button, Modal } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import {
  previewReportReadyNotices,
  sendReportReadyNotices,
} from '@/features/classes/services'
import type { ReportReadyPreview } from '@/features/classes/assessment/types'
import CreditShortfallNotice from '@/features/messaging/components/CreditShortfallNotice'
import { getApiErrorMessage } from '@/utils'

type ReportReadyModalProps = {
  open: boolean
  streamId: string
  termId?: string
  studentIds: string[]
  onClose: () => void
  onSent: () => void
}

const audienceLabel = (value: ReportReadyPreview['audience']) =>
  value === 'all' ? 'All linked guardians' : 'Primary guardians only'

const channelsLabel = (value: ReportReadyPreview['channels']) => {
  if (value === 'sms') return 'SMS only'
  if (value === 'email') return 'Email only'
  if (value === 'both') return 'SMS and email'
  return '—'
}

const ReportReadyModal = ({
  open,
  streamId,
  termId,
  studentIds,
  onClose,
  onSent,
}: ReportReadyModalProps) => {
  const [preview, setPreview] = useState<ReportReadyPreview | null>(null)
  const studentIdsKey = studentIds.join(',')

  const { mutate: loadPreview, isPending: isPreviewing } = useMutation({
    mutationFn: () =>
      previewReportReadyNotices(
        streamId,
        { student_ids: studentIds, term_id: termId },
        termId,
      ),
    onSuccess: (data) => setPreview(data),
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to preview guardian messages'))
      onClose()
    },
  })

  const { mutate: send, isPending: isSending } = useMutation({
    mutationFn: () =>
      sendReportReadyNotices(
        streamId,
        { student_ids: studentIds, term_id: termId },
        termId,
      ),
    onSuccess: (result) => {
      toast.success(
        `Queued guardian messages for ${result.students_notified} student${result.students_notified === 1 ? '' : 's'} (${result.sms_sent} SMS, ${result.email_sent} email)`,
      )
      onSent()
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to send to guardians'))
    },
  })

  useEffect(() => {
    if (!open || !studentIdsKey) return
    loadPreview()
  }, [open, studentIdsKey, loadPreview])

  const displayPreview = open ? preview : null

  return (
    <Modal open={open} title="Send to guardians — report ready" onClose={onClose} scrollable className="max-w-lg">
      {isPreviewing || !displayPreview ? (
        <LoadingSpinner className="mx-auto my-8" />
      ) : (
        <div className="space-y-5">
          {!displayPreview.enabled ? (
            <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Report-ready messages are turned off. Enable them under Settings → Messaging → Messages config.
            </p>
          ) : null}

          <p className="text-sm text-slate-600">
            Send download links for{' '}
            <span className="font-medium text-slate-900">{displayPreview.eligible_count}</span> student
            {displayPreview.eligible_count === 1 ? '' : 's'} with generated reports (
            {displayPreview.class_name} · {displayPreview.term_label}).
          </p>

          <dl className="grid grid-cols-[140px_1fr] gap-x-3 gap-y-2 text-sm">
            <dt className="text-slate-500">Mode setting</dt>
            <dd>
              {displayPreview.notify_mode === 'auto'
                ? 'Automatic on generate'
                : 'Staff triggered'}
            </dd>
            <dt className="text-slate-500">Audience</dt>
            <dd>{audienceLabel(displayPreview.audience)}</dd>
            <dt className="text-slate-500">Channels</dt>
            <dd>{channelsLabel(displayPreview.channels)}</dd>
            <dt className="text-slate-500">Estimated SMS</dt>
            <dd>{displayPreview.sms_count}</dd>
            <dt className="text-slate-500">Estimated email</dt>
            <dd>{displayPreview.email_count}</dd>
            <dt className="text-slate-500">Skipped</dt>
            <dd>{displayPreview.skipped_count}</dd>
          </dl>

          <CreditShortfallNotice credits={displayPreview.credits} />

          {displayPreview.eligible.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-800">Eligible students</p>
              <ul className="max-h-40 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                {displayPreview.eligible.map((row) => (
                  <li key={row.student_id} className="py-1">
                    {row.full_name}
                  </li>
                ))}
                {displayPreview.eligible_truncated ? (
                  <li className="py-1 text-slate-500">…and more</li>
                ) : null}
              </ul>
            </div>
          ) : null}

          {displayPreview.skipped.length > 0 ? (
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-800">Skipped</p>
              <ul className="max-h-32 overflow-y-auto rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600">
                {displayPreview.skipped.map((row) => (
                  <li key={`${row.student_id}-${row.reason}`} className="py-1">
                    {row.full_name || row.student_id}: {row.reason}
                  </li>
                ))}
                {displayPreview.skipped_truncated ? (
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
              disabled={!displayPreview.enabled || displayPreview.eligible_count === 0}
              onClick={() => send()}
            >
              Send to guardians
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}

export default ReportReadyModal
