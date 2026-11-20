import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import StatsCard from '@/components/shared/StatsCard'
import { Button, Modal } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { StatusPill } from '../components/StatusPill'
import { downloadAttentionReport, getMigrationJob, getMigrationPlan, getRowCorrection, saveRowCorrection, type CorrectionField } from '../services'

const CARDS = [
  ['new_students', 'New students'],
  ['linked_students', 'Existing students'],
  ['empty_fills', 'Blank fields'],
  ['match_reviews', 'Matches to check'],
  ['guardians_created', 'New parents'],
  ['guardians_reused', 'Existing parents'],
  ['current_enrollments', 'This term'],
  ['historical_enrollments', 'Past classes'],
  ['blocked', 'Needs attention'],
  ['ready', 'Ready'],
] as const

const MigrationSummary = () => {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const job = useQuery({ queryKey: ['migration-job', jobId], queryFn: () => getMigrationJob(jobId) })
  const plan = useQuery({ queryKey: ['migration-plan', jobId], queryFn: () => getMigrationPlan(jobId) })
  const opening = plan.data?.summary.opening
  const history = plan.data?.summary.history
  const isOpening = job.data?.template === 'opening_balances'
  const isHistory = job.data?.template === 'historical_finance'
  const [filter, setFilter] = useState<'all' | 'blocked' | 'ready'>('all')
  const [editingId, setEditingId] = useState('')
  const [fields, setFields] = useState<CorrectionField[]>([])
  const [reasons, setReasons] = useState<string[]>([])
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const counts = plan.data?.summary.plan ?? {}
  const openEdit = async (rowId: string) => {
    try {
      const form = await getRowCorrection(jobId, rowId)
      setEditingId(rowId)
      setFields(form.fields)
      setReasons(form.reasons.map((reason) => reason.message).filter(Boolean))
      setDraft(Object.fromEntries(form.fields.map((field) => [field.key, field.value])))
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not open this row'))
    }
  }

  const saveEdit = async () => {
    setSaving(true)
    try {
      await saveRowCorrection(jobId, editingId, draft)
      await queryClient.invalidateQueries({ queryKey: ['migration-plan', jobId] })
      setEditingId('')
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not save this row'))
    } finally {
      setSaving(false)
    }
  }

  const rows = (plan.data?.rows ?? []).filter((row) => {
    if (filter === 'blocked') return row.validation_status === 'blocked' || row.proposal?.blocked
    if (filter === 'ready') return row.validation_status === 'ready'
    return true
  })

  return (
    <div className="space-y-6">
      {isHistory && history ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatsCard title="Rows" value={String(history.total_rows)} />
          <StatsCard title="Ready" value={String(history.valid_rows)} />
          <StatsCard title="Needs attention" value={String(history.blocked_rows)} />
          <StatsCard title="Students" value={String(history.unique_students)} />
          <StatsCard title="Charges" value={`GHS ${history.charge_total}`} />
          <StatsCard title="Payments" value={`GHS ${history.payment_total}`} />
          <StatsCard title="Advances" value={`GHS ${history.advance_total}`} />
          <StatsCard title="Left out (zero)" value={String(history.skipped_rows)} />
        </div>
      ) : isOpening && opening ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatsCard title="Rows" value={String(opening.total_rows)} />
            <StatsCard title="Ready" value={String(opening.valid_rows)} />
            <StatsCard title="Needs attention" value={String(opening.blocked_rows)} />
            <StatsCard title="Students" value={String(opening.unique_students)} />
            <StatsCard title="Total to add" value={`GHS ${opening.total}`} />
            <StatsCard title="Left out (zero)" value={String(opening.skipped_rows)} />
            <StatsCard title="Duplicates" value={String(opening.duplicates)} />
            <StatsCard title="Already has fees" value={String(opening.overlaps)} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="bg-white p-4 text-sm custom-shadow-md">
              <p className="font-medium text-slate-900">By academic year</p>
              {opening.by_year.length === 0 ? <p className="mt-2 text-slate-500">None ready</p> : opening.by_year.map((item) => (
                <p key={item.academic_year} className="mt-2 text-slate-700">{item.academic_year}: GHS {item.total}</p>
              ))}
            </div>
            <div className="bg-white p-4 text-sm custom-shadow-md">
              <p className="font-medium text-slate-900">By term</p>
              {opening.by_term.length === 0 ? <p className="mt-2 text-slate-500">None ready</p> : opening.by_term.map((item) => (
                <p key={`${item.academic_year}-${item.term}`} className="mt-2 text-slate-700">{item.academic_year} {item.term.replaceAll('_', ' ')}: GHS {item.total}</p>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {CARDS.map(([key, label]) => (
            <StatsCard key={key} title={label} value={String(counts[key] ?? 0)} />
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        {(['all', 'ready', 'blocked'] as const).map((item) => (
          <button key={item} type="button" className={`px-3 py-1 text-sm capitalize ${filter === item ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 custom-shadow-sm'}`} onClick={() => setFilter(item)}>
            {item === 'blocked' ? 'Needs attention' : item === 'all' ? 'All' : 'Ready'}
          </button>
        ))}
        <Button className="max-w-fit py-2" variant="outline" onClick={() => downloadAttentionReport(jobId)}>
          Download needs attention
        </Button>
      </div>
      <div className="bg-white custom-shadow-md">
        {rows.map((row) => (
          <div key={row.id} className="flex items-start justify-between gap-3 border-b border-slate-200 px-4 py-3 text-sm last:border-b-0">
            <div>
              <p className="font-medium text-slate-900">{row.proposal?.student_label || `Row ${row.source_row_number}`}</p>
              {(row.proposal?.block_reasons ?? row.errors).slice(0, 2).map((error) => (
                <p key={error.message} className="text-red-600">{error.message}</p>
              ))}
            </div>
            <div className="flex items-center gap-2">
              {row.validation_status === 'blocked' || row.proposal?.blocked ? (
                <Button className="max-w-fit py-1" variant="outline" onClick={() => openEdit(row.id)}>Edit</Button>
              ) : null}
              <StatusPill value={row.validation_status} />
            </div>
          </div>
        ))}
        {rows.length === 0 ? <p className="px-4 py-6 text-sm text-slate-500">Nothing in this list.</p> : null}
      </div>
      <Button className="max-w-fit py-2" onClick={() => navigate(`/migration/${jobId}/commit`)}>Next</Button>
      <Modal open={Boolean(editingId)} title="Edit student" onClose={() => setEditingId('')} scrollable className="max-w-lg">
        <div className="space-y-3">
          {reasons.map((reason) => (
            <p key={reason} className="text-sm text-red-600">{reason}</p>
          ))}
          {fields.length === 0 ? (
            <p className="text-sm text-slate-600">This row needs a choice on Check possible matches.</p>
          ) : fields.map((field) => (
            <label key={field.key} className="block text-sm text-slate-700">
              {field.label}
              {field.kind === 'select' ? (
                <select
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2"
                  value={draft[field.key] || ''}
                  onChange={(event) => setDraft((current) => ({ ...current, [field.key]: event.target.value }))}
                >
                  <option value="">Choose</option>
                  {field.options.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.kind === 'date' ? 'date' : 'text'}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2"
                  value={draft[field.key] || ''}
                  onChange={(event) => setDraft((current) => ({ ...current, [field.key]: event.target.value }))}
                />
              )}
            </label>
          ))}
          <div className="grid grid-cols-2 gap-3">
            <Button type="button" variant="outline" onClick={() => setEditingId('')}>Cancel</Button>
            <Button type="button" loading={saving} disabled={fields.length === 0} onClick={saveEdit}>Save</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default MigrationSummary
