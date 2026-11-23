import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Table, TableWrapper } from '@/components/shared'
import { Button } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { confirmClass, getClassGroups, getMigrationJob, getMigrationPlan, saveYearPlan } from '../services'

const CLASS_STATUS: Record<string, string> = {
  exact: 'Exact match',
  approved: 'Saved for this school',
  confirmed: 'Confirmed',
  inferred: 'Needs confirmation',
  unresolved: 'Choose a class',
  snapshot: 'Old class',
}

const yearBounds = (label: string) => {
  const parts = label.split('/').map((part) => part.trim())
  if (parts.length !== 2 || parts.some((part) => !/^\d{4}$/.test(part))) return null
  const startYear = Number(parts[0])
  const endYear = Number(parts[1])
  if (endYear < startYear) return null
  return {
    startMin: `${startYear}-01-01`,
    startMax: `${startYear}-12-31`,
    endMin: `${endYear}-01-01`,
    endMax: `${endYear}-12-31`,
  }
}

const MigrationEnrollments = () => {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const job = useQuery({ queryKey: ['migration-job', jobId], queryFn: () => getMigrationJob(jobId) })
  const classes = useQuery({ queryKey: ['migration-classes', jobId], queryFn: () => getClassGroups(jobId) })
  const plan = useQuery({ queryKey: ['migration-plan', jobId], queryFn: () => getMigrationPlan(jobId) })
  const [picked, setPicked] = useState<Record<string, string>>({})
  const [dates, setDates] = useState<Record<string, { start: string; end: string }>>({})
  const years = (plan.data?.rows ?? [])
    .map((row) => row.proposal?.enrollment)
    .filter((item) => item?.action === 'needs_year' && item.year)
  const yearLabels = [...new Set(years.map((item) => item?.year || ''))]

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['migration-classes', jobId] })
    await queryClient.invalidateQueries({ queryKey: ['migration-plan', jobId] })
  }

  const choose = async (source: string, payload: { stream_id?: string; use_snapshot?: boolean }) => {
    try {
      const next = await confirmClass(jobId, { source_value: source, ...payload })
      queryClient.setQueryData(['migration-classes', jobId], next)
      await queryClient.invalidateQueries({ queryKey: ['migration-plan', jobId] })
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not save that class'))
    }
  }

  const next = job.data?.template === 'enrollment_history' ? 'summary' : 'match'
  const opening = job.data?.template === 'opening_balances' || job.data?.template === 'historical_finance'

  return (
    <div className="space-y-6">
      {opening ? null : <TableWrapper
        isLoading={classes.isLoading}
        isEmpty={!classes.isLoading && (classes.data ?? []).length === 0}
        emptyState={{ title: 'No classes in this file', icon: 'hugeicons:student' }}
        variant="card"
      >
        <Table>
          <Table.Head>
            <Table.Row>
              <Table.HeaderCell>In the file</Table.HeaderCell>
              <Table.HeaderCell>Rows</Table.HeaderCell>
              <Table.HeaderCell>Class</Table.HeaderCell>
              <Table.HeaderCell>Status</Table.HeaderCell>
              <Table.HeaderCell>
                <span className="sr-only">Actions</span>
              </Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {(classes.data ?? []).map((item) => {
              const selected = picked[item.source_value] || (item.needs_confirmation ? '' : item.stream_id)
              return (
                <Table.Row key={item.source_value}>
                  <Table.Cell variant="primary">{item.label}</Table.Cell>
                  <Table.Cell>{item.count}</Table.Cell>
                  <Table.Cell>
                    <select
                      className="w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm"
                      value={selected}
                      aria-label={`Class for ${item.label}`}
                      onChange={(event) => setPicked((current) => ({ ...current, [item.source_value]: event.target.value }))}
                    >
                      <option value="">{item.class_label ? `${item.class_label}${item.stream_label ? ` ${item.stream_label}` : ''}` : 'Choose'}</option>
                      {item.options.map((option) => (
                        <option key={option.stream_id} value={option.stream_id}>{option.label}</option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-slate-500">{item.message}</p>
                  </Table.Cell>
                  <Table.Cell>{CLASS_STATUS[item.status] || item.status}</Table.Cell>
                  <Table.Cell>
                    <div className="flex flex-wrap gap-2">
                      {item.needs_confirmation && item.stream_id ? (
                        <Button className="max-w-fit py-1" variant="outline" onClick={() => choose(item.source_value, { stream_id: item.stream_id })}>
                          Use suggestion
                        </Button>
                      ) : null}
                      <Button className="max-w-fit py-1" disabled={!selected} onClick={() => choose(item.source_value, { stream_id: selected })}>
                        Apply to all
                      </Button>
                      {job.data?.template === 'enrollment_history' && item.status !== 'exact' ? (
                        <Button className="max-w-fit py-1" variant="ghost" onClick={() => choose(item.source_value, { use_snapshot: true })}>
                          Keep as old class
                        </Button>
                      ) : null}
                    </div>
                  </Table.Cell>
                </Table.Row>
              )
            })}
          </Table.Body>
        </Table>
      </TableWrapper>}

      {opening && yearLabels.length === 0 ? (
        <p className="bg-white p-4 text-sm text-slate-600 custom-shadow-md">Every academic year in this file is already on the calendar.</p>
      ) : null}

      {yearLabels.map((label) => {
        const bounds = yearBounds(label)
        return (
        <form
          key={label}
          className="flex flex-wrap items-end gap-2 bg-white p-4 custom-shadow-md"
          onSubmit={async (event) => {
            event.preventDefault()
            const value = dates[label] || { start: '', end: '' }
            try {
              await saveYearPlan(jobId, { label, start_date: value.start, end_date: value.end })
              await refresh()
            } catch (error) {
              toast.error(getApiErrorMessage(error, 'Enter the year dates'))
            }
          }}
        >
          <p className="w-full text-sm text-slate-800">{label} is not on the calendar yet.</p>
          <input aria-label="Start date" type="date" min={bounds?.startMin} max={bounds?.startMax} className="rounded-lg border border-slate-300 bg-slate-100 px-2 py-2 text-sm" onChange={(event) => setDates((current) => ({ ...current, [label]: { start: event.target.value, end: current[label]?.end || '' } }))} />
          <input aria-label="End date" type="date" min={bounds?.endMin} max={bounds?.endMax} className="rounded-lg border border-slate-300 bg-slate-100 px-2 py-2 text-sm" onChange={(event) => setDates((current) => ({ ...current, [label]: { start: current[label]?.start || '', end: event.target.value } }))} />
          <Button className="max-w-fit py-2" type="submit">Save dates</Button>
        </form>
        )
      })}

      <Button className="max-w-fit py-2" onClick={() => navigate(`/migration/${jobId}/${next}`)}>Next</Button>
    </div>
  )
}

export default MigrationEnrollments
