import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, CheckboxField, Modal } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'
import { ADMIN_DASHBOARD_QUERY_KEY } from '@/features/dashboard/utils'
import { formatFeeAmount } from '@/features/fees/utils'
import {
  ACADEMIC_CALENDAR_QUERY_KEY,
  confirmTransition,
  getTransitionPreview,
  TRANSITION_PREVIEW_QUERY_KEY,
  TRANSITION_STATUS_QUERY_KEY,
} from '../services'
import type { TransitionPlacement, TransitionPreview } from '../types'

type TransitionWizardProps = {
  open: boolean
  onClose: () => void
}

const ClassName = ({ children }: { children: ReactNode }) => (
  <span className="font-semibold text-slate-900">{children}</span>
)

const draftKey = (termId: string) => `sms-transition-draft:${termId}`

type TransitionDraft = {
  step: string
  streamChoices: Record<string, string>
}

const readDraft = (termId: string): TransitionDraft | null => {
  try {
    const raw = sessionStorage.getItem(draftKey(termId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as TransitionDraft
    if (!parsed || typeof parsed.step !== 'string' || typeof parsed.streamChoices !== 'object' || parsed.streamChoices === null) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

const writeDraft = (termId: string, draft: TransitionDraft) => {
  try {
    sessionStorage.setItem(draftKey(termId), JSON.stringify(draft))
  } catch {
    // The wizard still keeps the current visit in memory.
  }
}

const clearDraft = (termId: string) => {
  try {
    sessionStorage.removeItem(draftKey(termId))
  } catch {
    // Opening the term already reset the in-memory step.
  }
}

const pruneStreamChoices = (
  choices: Record<string, string>,
  placements: TransitionPlacement[],
) => {
  const next: Record<string, string> = {}
  for (const row of placements) {
    if (row.outcome !== 'needs_stream') continue
    const chosen = choices[row.source_stream_id]
    if (chosen && row.stream_options.some((option) => option.id === chosen)) {
      next[row.source_stream_id] = chosen
    }
  }
  return next
}

const outcomeLine = (row: TransitionPlacement) => {
  if (row.outcome === 'graduate') {
    return (
      <>
        {row.student_count} in <ClassName>{row.source_label}</ClassName> will be marked graduated
      </>
    )
  }
  if (row.outcome === 'stay') {
    return (
      <>
        {row.student_count} stay in <ClassName>{row.source_label}</ClassName>
      </>
    )
  }
  if (row.outcome === 'needs_stream') {
    return (
      <>
        {row.student_count} in <ClassName>{row.source_label}</ClassName> need a stream on{' '}
        <ClassName>{row.destination_class_name}</ClassName>
      </>
    )
  }
  return (
    <>
      {row.student_count} move from <ClassName>{row.source_label}</ClassName> to{' '}
      <ClassName>
        {row.destination_class_name}
        {row.destination_stream_name ? ` ${row.destination_stream_name}` : ''}
      </ClassName>
    </>
  )
}

const TransitionWizard = ({ open, onClose }: TransitionWizardProps) => {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { data, isLoading, isError, error } = useQuery({
    queryKey: [TRANSITION_PREVIEW_QUERY_KEY],
    queryFn: getTransitionPreview,
    enabled: open,
  })
  const [draftStep, setDraftStep] = useState('Pupils')
  const [streamChoices, setStreamChoices] = useState<Record<string, string>>({})
  const [acknowledge, setAcknowledge] = useState(false)
  const [extraWarnings, setExtraWarnings] = useState<string[]>([])
  const [hydratedTermId, setHydratedTermId] = useState<string | null>(null)

  const steps = useMemo(() => {
    const next = ['Pupils']
    if (data?.placements.some((row) => row.outcome === 'needs_stream')) next.push('Streams')
    next.push('Fees', 'Confirm')
    return next
  }, [data])

  const stepName = steps.includes(draftStep)
    ? draftStep
    : draftStep === 'Streams' && steps.includes('Fees')
      ? 'Fees'
      : (steps[0] ?? 'Pupils')
  const stepIndex = Math.max(0, steps.indexOf(stepName))

  const effectiveStreamChoices = useMemo(
    () => (data ? pruneStreamChoices(streamChoices, data.placements) : streamChoices),
    [data, streamChoices],
  )

  useEffect(() => {
    if (!data?.term_id || hydratedTermId !== data.term_id) return
    writeDraft(data.term_id, { step: stepName, streamChoices: effectiveStreamChoices })
  }, [data?.term_id, hydratedTermId, stepName, effectiveStreamChoices])
  const warnings = [...(data?.warnings ?? []), ...extraWarnings.filter(
    (warning) => !(data?.warnings ?? []).includes(warning),
  )]
  const streamReady = (data?.placements ?? [])
    .filter((row) => row.outcome === 'needs_stream')
    .every((row) => row.stream_options.length > 0 && effectiveStreamChoices[row.source_stream_id])

  const { mutate: confirm, isPending } = useMutation({
    mutationFn: () =>
      confirmTransition({
        acknowledge_warnings: acknowledge || warnings.length === 0,
        stream_choices: Object.entries(effectiveStreamChoices).map(([source_stream_id, destination_stream_id]) => ({
          source_stream_id,
          destination_stream_id,
        })),
      }),
    onSuccess: (calendar) => {
      if (data?.term_id) clearDraft(data.term_id)
      setHydratedTermId(null)
      setDraftStep('Pupils')
      setStreamChoices({})
      setAcknowledge(false)
      queryClient.setQueryData([ACADEMIC_CALENDAR_QUERY_KEY], calendar)
      void queryClient.invalidateQueries({ queryKey: ['academicYearAndTerm'] })
      void queryClient.invalidateQueries({ queryKey: [TRANSITION_STATUS_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: [TRANSITION_PREVIEW_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: [ADMIN_DASHBOARD_QUERY_KEY] })
      toast.success(data?.term_label ? `${data.term_label} is now the current term` : 'Next term is open')
      onClose()
    },
    onError: (confirmError) => {
      const response = (confirmError as { response?: { data?: { warnings?: string[] } } }).response?.data
      if (Array.isArray(response?.warnings) && response.warnings.length > 0) {
        setExtraWarnings(response.warnings)
        setAcknowledge(false)
        return
      }
      toast.error(getApiErrorMessage(confirmError, 'Unable to open the next term'))
    },
  })

  const goNext = () => setDraftStep(steps[Math.min(stepIndex + 1, steps.length - 1)] ?? stepName)
  const goBack = () => setDraftStep(steps[Math.max(stepIndex - 1, 0)] ?? 'Pupils')
  const editFees = () => {
    const termId = data?.term_id
    onClose()
    navigate(termId ? `/fees/settings?term=${termId}` : '/fees/settings')
  }

  if (open && data?.term_id && hydratedTermId !== data.term_id) {
    const draft = readDraft(data.term_id)
    setHydratedTermId(data.term_id)
    if (draft) {
      setDraftStep(draft.step)
      setStreamChoices(pruneStreamChoices(draft.streamChoices, data.placements))
    } else if (hydratedTermId !== null) {
      setDraftStep('Pupils')
      setStreamChoices({})
      setAcknowledge(false)
      setExtraWarnings([])
    }
  }

  return (
    <Modal
      open={open}
      title={data?.term_label ? `Open ${data.term_label}` : 'Open the next term'}
      onClose={onClose}
      scrollable
      className="max-w-xl"
    >
      {isLoading ? <LoadingSpinner className="mx-auto" /> : null}
      {isError ? (
        <p className="text-sm text-red-600">{getApiErrorMessage(error, 'Unable to prepare this transition.')}</p>
      ) : null}
      {data ? (
        <div className="space-y-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Step {stepIndex + 1} of {steps.length}: {stepName}
          </p>
          {stepName === 'Pupils' ? <PupilsStep preview={data} /> : null}
          {stepName === 'Streams' ? (
            <StreamsStep
              placements={data.placements}
              choices={effectiveStreamChoices}
              onChange={(sourceId, destinationId) =>
                setStreamChoices((current) => ({ ...current, [sourceId]: destinationId }))
              }
            />
          ) : null}
          {stepName === 'Fees' ? <FeesStep preview={data} onEditFees={editFees} /> : null}
          {stepName === 'Confirm' ? (
            <ConfirmStep
              preview={data}
              warnings={warnings}
              acknowledge={acknowledge}
              onAcknowledge={setAcknowledge}
            />
          ) : null}
          {data.blockers.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-red-700">
              {data.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          ) : null}
          <div className="grid grid-cols-2 gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => (stepIndex === 0 ? onClose() : goBack())}
              disabled={isPending}
            >
              {stepIndex === 0 ? 'Close' : 'Back'}
            </Button>
            {stepName === 'Confirm' ? (
              <Button
                type="button"
                onClick={() => confirm()}
                loading={isPending}
                disabled={
                  data.blockers.length > 0
                  || !streamReady
                  || (warnings.length > 0 && !acknowledge)
                }
              >
                Open term
              </Button>
            ) : (
              <Button
                type="button"
                onClick={goNext}
                disabled={stepName === 'Streams' && !streamReady}
              >
                Continue
              </Button>
            )}
          </div>
        </div>
      ) : null}
    </Modal>
  )
}

const PupilsStep = ({ preview }: { preview: TransitionPreview }) => (
  <div className="space-y-3">
    <p className="text-sm text-slate-600">
      {preview.is_year_change
        ? 'Each class moves to the next class. Pupils in the last class are marked graduated.'
        : 'Everyone stays in the same class for the next term.'}
    </p>
    {preview.placements.length === 0 ? (
      <p className="text-sm text-slate-500">No pupils are waiting to move.</p>
    ) : (
      <ul className="space-y-2">
        {preview.placements.map((row) => (
          <li key={row.source_stream_id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800">
            {outcomeLine(row)}
          </li>
        ))}
      </ul>
    )}
    {preview.already_enrolled_count > 0 ? (
      <p className="text-sm text-slate-500">
        {preview.already_enrolled_count} already placed on the next term stay where they are.
      </p>
    ) : null}
  </div>
)

const StreamsStep = ({
  placements,
  choices,
  onChange,
}: {
  placements: TransitionPlacement[]
  choices: Record<string, string>
  onChange: (_sourceId: string, _destinationId: string) => void
}) => (
  <div className="space-y-4">
    {placements.filter((row) => row.outcome === 'needs_stream').map((row) => (
      <div key={row.source_stream_id} className="space-y-2">
        <p className="text-sm text-slate-800">
          {row.student_count} in <ClassName>{row.source_label}</ClassName>.{' '}
          <ClassName>{row.destination_class_name}</ClassName> has no stream with the same name.
        </p>
        {row.stream_options.length === 0 ? (
          <p className="text-sm text-amber-800">
            Add a stream on <ClassName>{row.destination_class_name}</ClassName> first.{' '}
            <Link to="/settings/classes" className="underline">Open classes</Link>
          </p>
        ) : (
          <select
            className="w-full rounded-lg border border-slate-300 bg-white p-2 text-sm"
            value={choices[row.source_stream_id] ?? ''}
            onChange={(event) => onChange(row.source_stream_id, event.target.value)}
          >
            <option value="">Choose a stream</option>
            {row.stream_options.map((option) => (
              <option key={option.id} value={option.id}>{option.name}</option>
            ))}
          </select>
        )}
      </div>
    ))}
  </div>
)

const FeesStep = ({
  preview,
  onEditFees,
}: {
  preview: TransitionPreview
  onEditFees: () => void
}) => {
  const term = preview.term_label ?? 'the next term'
  return (
    <div className="space-y-3">
      {preview.fees.items.length === 0 ? (
        <p className="text-sm text-slate-600">
          {term} has no fee items yet. Add them before you open the term.
        </p>
      ) : (
        <>
          <p className="text-sm text-slate-600">
            {preview.fees.locked
              ? `These fees are already applied on ${term}. Opening the term bills pupils who match them.`
              : `These fees go into ${term}. Opening the term applies this list and locks it.`}
          </p>
          <ul className="space-y-2">
            {preview.fees.items.map((item) => (
              <li
                key={item.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <div>
                  <p className="text-slate-900">{item.name}</p>
                  <p className="text-slate-500">
                    <ClassName>{item.applies_to}</ClassName>
                    {' · '}
                    {item.student_type}
                  </p>
                </div>
                <p className="shrink-0 text-slate-800">{formatFeeAmount(item.amount)}</p>
              </li>
            ))}
          </ul>
        </>
      )}
      <Button type="button" variant="outline" onClick={onEditFees}>
        {preview.fees.locked ? 'View in Fees settings' : 'Edit in Fees settings'}
      </Button>
    </div>
  )
}

const ConfirmStep = ({
  preview,
  warnings,
  acknowledge,
  onAcknowledge,
}: {
  preview: TransitionPreview
  warnings: string[]
  acknowledge: boolean
  onAcknowledge: (_value: boolean) => void
}) => (
  <div className="space-y-3">
    <p className="text-sm text-slate-700">
      {preview.term_label} becomes the current term. Past marks and bills stay on the term you are leaving.
    </p>
    <p className="text-sm text-slate-700">
      {preview.fees.locked
        ? `Fees for ${preview.term_label ?? 'this term'} are already applied and locked. Newly placed pupils will be billed from that list.`
        : `Opening applies the fee list for ${preview.term_label ?? 'this term'} and locks it. Edit those items in Fees settings before you open if anything still needs to change.`}
    </p>
    {preview.graduate_count > 0 ? (
      <p className="text-sm text-slate-700">
        {preview.graduate_count} will be marked graduated and will not be enrolled.
      </p>
    ) : null}
    {warnings.length > 0 ? (
      <>
        <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
        <CheckboxField checked={acknowledge} onChange={(event) => onAcknowledge(event.target.checked)}>
          Continue with these warnings
        </CheckboxField>
      </>
    ) : null}
  </div>
)

export default TransitionWizard
