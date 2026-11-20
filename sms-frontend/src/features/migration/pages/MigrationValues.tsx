import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Table, TableWrapper } from '@/components/shared'
import { Button } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { approveValues, getValueGroups, type ValueGroup } from '../services'

const STATUS = {
  exact: 'Already matches',
  approved: 'Approved',
  suggested: 'Suggestion',
  unmapped: 'Needs a choice',
  omitted: 'Left out',
}

const OMITTED = '__omit__'

const MigrationValues = () => {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const groups = useQuery({ queryKey: ['migration-values', jobId], queryFn: () => getValueGroups(jobId) })
  const [choices, setChoices] = useState<Record<string, string>>({})

  const pending = (groups.data ?? []).flatMap((group) => group.values.filter((value) => value.needs_confirmation).map((value) => ({ group, value })))

  const approve = async (items: { field: string; source_value: string; label: string; canonical_value: string }[]) => {
    try {
      const next = await approveValues(jobId, items)
      queryClient.setQueryData(['migration-values', jobId], next)
      await queryClient.invalidateQueries({ queryKey: ['migration-plan', jobId] })
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not save those choices'))
    }
  }

  return (
    <div className="space-y-6">
      {(groups.data ?? []).map((group) => (
        <section key={group.field} className="space-y-3">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-sm font-medium text-slate-900">{group.label}</h2>
            <p className="text-xs text-slate-500">{group.distinct} values · {group.total} rows</p>
          </div>
          <ValueTable
            group={group}
            choices={choices}
            onChoose={(key, canonical) => setChoices((current) => ({ ...current, [key]: canonical }))}
            onApprove={(value, canonical) => approve([{ field: group.field, source_value: value.source_value, label: value.label, canonical_value: canonical }])}
            onOmit={(value) => approve([{ field: group.field, source_value: value.source_value, label: value.label, canonical_value: OMITTED }])}
          />
        </section>
      ))}
      {!groups.isLoading && (groups.data ?? []).length === 0 ? (
        <p className="bg-white p-4 text-sm text-slate-500 custom-shadow-md">No values need a choice. Dates, phone numbers, and names are cleaned automatically.</p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {pending.length > 0 ? (
          <Button
            className="max-w-fit py-2"
            variant="outline"
            onClick={() => approve(pending.filter((item) => item.value.canonical_value).map((item) => ({
              field: item.group.field,
              source_value: item.value.source_value,
              label: item.value.label,
              canonical_value: choices[`${item.group.field}:${item.value.source_value}`] || item.value.canonical_value,
            })))}
          >
            Approve suggestions
          </Button>
        ) : null}
        <Button className="max-w-fit py-2" onClick={() => navigate(`/migration/${jobId}/enrollments`)}>Next</Button>
      </div>
    </div>
  )
}

function ValueTable({
  group,
  choices,
  onChoose,
  onApprove,
  onOmit,
}: {
  group: ValueGroup
  choices: Record<string, string>
  onChoose: (key: string, canonical: string) => void
  onApprove: (value: ValueGroup['values'][number], canonical: string) => void
  onOmit: (value: ValueGroup['values'][number]) => void
}) {
  return (
    <TableWrapper isEmpty={group.values.length === 0} emptyState={{ title: 'No values', icon: 'hugeicons:inbox' }} variant="card">
      <Table>
        <Table.Head>
          <Table.Row>
            <Table.HeaderCell>In the file</Table.HeaderCell>
            <Table.HeaderCell>Rows</Table.HeaderCell>
            <Table.HeaderCell>SCHOOLASST</Table.HeaderCell>
            <Table.HeaderCell>Status</Table.HeaderCell>
            <Table.HeaderCell />
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {group.values.map((value) => {
            const key = `${group.field}:${value.source_value}`
            const selected = choices[key] || value.canonical_value
            return (
              <Table.Row key={key}>
                <Table.Cell variant="primary">{value.label}</Table.Cell>
                <Table.Cell>{value.count}</Table.Cell>
                <Table.Cell>
                  <select
                    className="w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm"
                    value={selected}
                    aria-label={`${group.label} for ${value.label}`}
                    onChange={(event) => onChoose(key, event.target.value)}
                  >
                    <option value="">Choose</option>
                    {group.options.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </Table.Cell>
                <Table.Cell>{STATUS[value.status as keyof typeof STATUS] || value.status}</Table.Cell>
                <Table.Cell>
                  <div className="flex flex-wrap gap-2">
                    {value.needs_confirmation ? (
                      <Button className="max-w-fit py-1" variant="outline" disabled={!selected} onClick={() => onApprove(value, selected)}>
                        Use this
                      </Button>
                    ) : null}
                    {group.can_omit && value.needs_confirmation ? (
                      <Button className="max-w-fit py-1" variant="ghost" onClick={() => onOmit(value)}>
                        Leave out
                      </Button>
                    ) : null}
                  </div>
                </Table.Cell>
              </Table.Row>
            )
          })}
        </Table.Body>
      </Table>
    </TableWrapper>
  )
}

export default MigrationValues
