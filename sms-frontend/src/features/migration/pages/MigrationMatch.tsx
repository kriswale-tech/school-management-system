import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Table, TableWrapper } from '@/components/shared'
import { Button } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { StatusPill } from '../components/StatusPill'
import { decideMatch, getMigrationJob, getMigrationPlan, reviewRow } from '../services'

const MigrationMatch = () => {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const job = useQuery({ queryKey: ['migration-job', jobId], queryFn: () => getMigrationJob(jobId) })
  const plan = useQuery({ queryKey: ['migration-plan', jobId], queryFn: () => getMigrationPlan(jobId) })
  const opening = job.data?.template === 'opening_balances' || job.data?.template === 'historical_finance'
  const rows = (plan.data?.rows ?? []).filter((row) => (
    row.proposal?.action === 'review'
    || (row.proposal?.conflicts?.length ?? 0) > 0
    || row.proposal?.guardian?.action === 'review'
  ))

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['migration-plan', jobId] })

  const choose = async (action: () => Promise<unknown>) => {
    try {
      await action()
      await refresh()
    } catch (error) {
      toast.error(getApiErrorMessage(error, 'Could not save that choice'))
    }
  }

  return (
    <div className="space-y-6">
      <TableWrapper
        isLoading={plan.isLoading}
        isEmpty={!plan.isLoading && rows.length === 0}
        emptyState={{ title: 'No matches to check', icon: 'hugeicons:student' }}
        variant="card"
      >
        <Table>
          <Table.Head>
            <Table.Row>
              <Table.HeaderCell>Imported</Table.HeaderCell>
              <Table.HeaderCell>Possible student</Table.HeaderCell>
              <Table.HeaderCell>Why</Table.HeaderCell>
              <Table.HeaderCell>Choice</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {rows.map((row) => (
              <Table.Row key={row.id}>
                <Table.Cell variant="primary">
                  {row.proposal?.student_label || `Row ${row.source_row_number}`}
                  {row.proposal?.duplicate_warning ? <p className="text-xs text-amber-700">Same ID appears more than once</p> : null}
                </Table.Cell>
                <Table.Cell>
                  {(row.proposal?.candidates ?? []).map((candidate) => (
                    <p key={candidate.id}>{candidate.name} · {candidate.student_id}</p>
                  ))}
                </Table.Cell>
                <Table.Cell><StatusPill value={row.proposal?.match_kind} /></Table.Cell>
                <Table.Cell>
                  <div className="flex flex-wrap gap-2">
                    {(row.proposal?.candidates ?? []).map((candidate) => (
                      <Button key={candidate.id} className="max-w-fit py-2" variant="outline" onClick={() => choose(() => decideMatch(jobId, row.id, 'link', candidate.id))}>
                        Same student
                      </Button>
                    ))}
                    {opening ? null : (
                      <Button className="max-w-fit py-2" onClick={() => choose(() => decideMatch(jobId, row.id, 'create'))}>
                        New student
                      </Button>
                    )}
                  </div>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>

      {rows.some((row) => (row.proposal?.conflicts?.length ?? 0) > 0 || row.proposal?.guardian?.action === 'review') ? (
        <div className="space-y-3 bg-white p-4 custom-shadow-md">
          {rows.map((row) => (
            <div key={`${row.id}-detail`} className="space-y-2">
              {(row.proposal?.conflicts ?? []).map((conflict) => (
                <div key={conflict.field} className="flex flex-wrap items-center gap-3 text-sm">
                  <span className="font-medium">{row.proposal?.student_label}</span>
                  <span className="text-slate-500">{conflict.field.replaceAll('_', ' ')}</span>
                  <span>Now: {conflict.current}</span>
                  <span>File: {conflict.imported}</span>
                  <Button className="max-w-fit py-1" variant="ghost" onClick={() => choose(() => reviewRow(jobId, row.id, { resolutions: { [conflict.field]: 'keep' } }))}>Keep current</Button>
                  <Button className="max-w-fit py-1" variant="ghost" onClick={() => choose(() => reviewRow(jobId, row.id, { resolutions: { [conflict.field]: 'use_imported' } }))}>Use file</Button>
                </div>
              ))}
              {row.proposal?.guardian?.action === 'review' ? (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span>{row.proposal.student_label} already has {row.proposal.guardian.current_primary}</span>
                  <Button className="max-w-fit py-1" variant="ghost" onClick={() => choose(() => reviewRow(jobId, row.id, { guardian_decision: 'keep' }))}>Keep parent</Button>
                  <Button className="max-w-fit py-1" variant="ghost" onClick={() => choose(() => reviewRow(jobId, row.id, { guardian_decision: 'add_secondary' }))}>Add extra contact</Button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      <Button className="max-w-fit py-2" onClick={() => navigate(`/migration/${jobId}/summary`)}>Next</Button>
    </div>
  )
}

export default MigrationMatch
