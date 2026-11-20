import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import dayjs from '@/lib/dayjs'
import toast from 'react-hot-toast'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ConfirmDialog, Table, TableWrapper } from '@/components/shared'
import { Button, LoadingSpinner } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { StatusPill } from '../components/StatusPill'
import { downloadErrorReport, finishMigration, getMigrationJob, getMigrationResult, resumeMigration } from '../services'
import type { MigrationPreviewRow } from '../types'

const TERMS: Record<string, string> = {
  first_term: 'First term',
  second_term: 'Second term',
  third_term: 'Third term',
}

const studentName = (row: MigrationPreviewRow) => {
  const values = row.transformed_values || {}
  return row.proposal?.student_label || `${values.first_name || ''} ${values.last_name || ''}`.trim() || `Row ${row.source_row_number}`
}

const studentClass = (row: MigrationPreviewRow) =>
  row.proposal?.enrollment?.class_name || row.transformed_values?.class_name || '—'

const rowReason = (row: MigrationPreviewRow, historyFees = false) => {
  const reasons = [
    ...(row.proposal?.block_reasons ?? []),
    ...(row.errors ?? []),
    ...(row.warnings ?? []),
  ]
  return reasons.map((item) => item.message).find(Boolean) || (historyFees ? 'This row was not saved.' : 'This student was not saved.')
}

const historyKind = (row: MigrationPreviewRow) => {
  if (row.proposal?.action === 'advance' || row.proposal?.payment_type === 'advance') return 'Advance'
  if (row.proposal?.role === 'payments' || row.proposal?.action === 'payment') return 'Payment'
  if (row.proposal?.role === 'charges' || row.proposal?.action === 'charge') return 'Charge'
  return '—'
}

const parentLabel = (row: MigrationPreviewRow) => {
  const guardian = row.proposal?.guardian
  if (!guardian || guardian.action === 'none' || guardian.action === 'skipped') return '—'
  return [guardian.name, guardian.phone].filter(Boolean).join(' · ') || '—'
}

const savedAs = (row: MigrationPreviewRow, history: boolean) => {
  if (history) {
    const action = row.proposal?.enrollment?.action
    if (action === 'current') return 'This term'
    if (action === 'snapshot') return 'Old class'
    if (action === 'historical_existing') return 'Past class'
    return 'Saved'
  }
  if (row.proposal?.action === 'create') return 'New student'
  if (row.proposal?.action === 'link') return 'Existing student'
  return 'Saved'
}

const termLabel = (row: MigrationPreviewRow) => {
  const term = row.proposal?.enrollment?.term || row.transformed_values?.term || ''
  return TERMS[term] || term || '—'
}

const MigrationProgress = () => {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [confirmFinish, setConfirmFinish] = useState(false)
  const [savedPage, setSavedPage] = useState(1)
  const [unsavedPage, setUnsavedPage] = useState(1)
  const job = useQuery({
    queryKey: ['migration-job', jobId],
    queryFn: () => getMigrationJob(jobId),
    refetchInterval: (query) => (query.state.data?.status === 'committing' ? 2000 : false),
  })
  const polling = job.data?.status === 'committing' ? 2000 : false
  const savedResult = useQuery({
    queryKey: ['migration-result', jobId, 'saved', savedPage, job.data?.status],
    queryFn: () => getMigrationResult(jobId, 'saved', savedPage),
    refetchInterval: polling,
  })
  const unsavedResult = useQuery({
    queryKey: ['migration-result', jobId, 'unsaved', unsavedPage, job.data?.status],
    queryFn: () => getMigrationResult(jobId, 'unsaved', unsavedPage),
    refetchInterval: polling,
  })
  const saved = savedResult.data?.results ?? []
  const leftOut = unsavedResult.data?.results ?? []
  const savedCount = savedResult.data?.saved_count ?? unsavedResult.data?.saved_count ?? 0
  const totalCount = savedResult.data?.total_count ?? unsavedResult.data?.total_count ?? 0
  const total = Math.max(totalCount, 1)
  const savingNow = job.data?.status === 'committing'
  const partlySaved = job.data?.status === 'partially_committed'
  const finished = job.data?.status === 'committed'
  const history = job.data?.template === 'enrollment_history'
  const opening = job.data?.template === 'opening_balances'
  const historyFees = job.data?.template === 'historical_finance'
  const ledger = opening || historyFees
  const savedOn = dayjs(job.data?.committed_at || job.data?.created_at)
  const fileName = job.data?.files?.[0]?.original_filename || ''

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['migration-job', jobId] })
    await queryClient.invalidateQueries({ queryKey: ['migration-result', jobId] })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3 bg-white p-4 custom-shadow-md">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-700">{savedCount} of {totalCount} saved</p>
          <StatusPill value={job.data?.status} />
        </div>
        <div className="h-2 bg-slate-200">
          <div className="h-full bg-slate-900" style={{ width: `${Math.round((saved.length / total) * 100)}%` }} />
        </div>
        {finished ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-600">
              {[fileName, savedOn.isValid() ? savedOn.format('DD MMM YYYY') : ''].filter(Boolean).join(' · ')}
            </p>
            <Button className="max-w-fit py-2" onClick={() => navigate('/migration')}>
              Finish
            </Button>
          </div>
        ) : null}
        {finished ? null : <div className="flex flex-wrap gap-2">
          {partlySaved ? (
            <Button
              className="max-w-fit py-2"
              loading={saving}
              loadingText="Saving"
              onClick={async () => {
                setSaving(true)
                try {
                  await resumeMigration(jobId)
                  await refresh()
                } catch (error) {
                  toast.error(getApiErrorMessage(error, 'Could not continue'))
                } finally {
                  setSaving(false)
                }
              }}
            >
              Continue
            </Button>
          ) : null}
          {partlySaved && (unsavedResult.data?.count ?? 0) > 0 ? (
            <Button className="max-w-fit py-2" variant="outline" onClick={() => setConfirmFinish(true)}>
              {historyFees ? 'Finish without these rows' : opening ? 'Finish without these balances' : 'Finish without these students'}
            </Button>
          ) : null}
          <Button className="max-w-fit py-2" variant="outline" onClick={() => downloadErrorReport(jobId)}>
            Download errors
          </Button>
        </div>}
      </div>
      {savedCount > 0 ? (
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-900">Saved</p>
          <TableWrapper
            variant="card"
            pagination={savedCount > 50 ? savedResult.data ?? null : null}
            onPageChange={setSavedPage}
          >
            <Table>
              <Table.Head>
                <Table.Row>
                  <Table.HeaderCell>Student ID</Table.HeaderCell>
                  <Table.HeaderCell>Name</Table.HeaderCell>
                  {history || ledger ? <Table.HeaderCell>Year</Table.HeaderCell> : null}
                  {history || ledger ? <Table.HeaderCell>Term</Table.HeaderCell> : null}
                  {historyFees ? <Table.HeaderCell>Kind</Table.HeaderCell> : null}
                  {ledger ? <Table.HeaderCell>Amount</Table.HeaderCell> : <Table.HeaderCell>Class</Table.HeaderCell>}
                  {ledger ? <Table.HeaderCell>Reference</Table.HeaderCell> : null}
                  {history || ledger ? null : <Table.HeaderCell>Parent</Table.HeaderCell>}
                  {ledger ? null : <Table.HeaderCell>{history ? 'Class type' : 'Student'}</Table.HeaderCell>}
                </Table.Row>
              </Table.Head>
              <Table.Body>
                {saved.map((row) => (
                  <Table.Row key={row.id}>
                    <Table.Cell>{row.transformed_values?.student_id || '—'}</Table.Cell>
                    <Table.Cell variant="primary">{studentName(row)}</Table.Cell>
                    {history || ledger ? <Table.Cell>{row.proposal?.enrollment?.year || row.transformed_values?.academic_year || '—'}</Table.Cell> : null}
                    {history || ledger ? <Table.Cell>{termLabel(row)}</Table.Cell> : null}
                    {historyFees ? <Table.Cell>{historyKind(row)}</Table.Cell> : null}
                    {ledger ? <Table.Cell>{row.proposal?.amount ? `GHS ${row.proposal.amount}` : '—'}</Table.Cell> : <Table.Cell>{studentClass(row)}</Table.Cell>}
                    {ledger ? <Table.Cell>{row.proposal?.payment_reference || row.proposal?.source_reference || row.transformed_values?.source_reference || '—'}</Table.Cell> : null}
                    {history || ledger ? null : <Table.Cell>{parentLabel(row)}</Table.Cell>}
                    {ledger ? null : <Table.Cell>{savedAs(row, history)}</Table.Cell>}
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          </TableWrapper>
        </div>
      ) : null}
      {savingNow ? (
        <div className="flex items-center gap-3 bg-white p-4 text-sm text-slate-700 custom-shadow-md">
          <LoadingSpinner size={16} className="text-slate-700" />
          Saving. Rows still waiting are not listed until this finishes.
        </div>
      ) : null}
      {!savingNow && (unsavedResult.data?.count ?? 0) > 0 ? (
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-900">Not saved</p>
          <TableWrapper
            variant="card"
            pagination={(unsavedResult.data?.count ?? 0) > 50 ? unsavedResult.data ?? null : null}
            onPageChange={setUnsavedPage}
          >
            <Table>
              <Table.Head>
                <Table.Row>
                  <Table.HeaderCell>Student ID</Table.HeaderCell>
                  <Table.HeaderCell>Name</Table.HeaderCell>
                  {ledger ? <Table.HeaderCell>Year</Table.HeaderCell> : <Table.HeaderCell>Class</Table.HeaderCell>}
                  {ledger ? <Table.HeaderCell>Term</Table.HeaderCell> : null}
                  <Table.HeaderCell>Reason</Table.HeaderCell>
                </Table.Row>
              </Table.Head>
              <Table.Body>
                {leftOut.map((row) => (
                  <Table.Row key={row.id}>
                    <Table.Cell>{row.transformed_values?.student_id || '—'}</Table.Cell>
                    <Table.Cell variant="primary">{studentName(row)}</Table.Cell>
                    {ledger ? <Table.Cell>{row.proposal?.enrollment?.year || row.transformed_values?.academic_year || '—'}</Table.Cell> : <Table.Cell>{studentClass(row)}</Table.Cell>}
                    {ledger ? <Table.Cell>{termLabel(row)}</Table.Cell> : null}
                    <Table.Cell className="text-red-600">{rowReason(row, historyFees)}</Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          </TableWrapper>
        </div>
      ) : null}
      <ConfirmDialog
        open={confirmFinish}
        title={historyFees ? 'Finish without these rows' : opening ? 'Finish without these balances' : 'Finish without these students'}
        message={historyFees
          ? 'These rows will not be added. Rows already saved stay saved.'
          : opening
            ? 'These balances will not be added. Balances already saved stay saved.'
            : 'These students will not be added. The students already saved stay saved.'}
        confirmLabel="Finish"
        isLoading={finishing}
        onClose={() => setConfirmFinish(false)}
        onConfirm={async () => {
          setFinishing(true)
          try {
            const finishedJob = await finishMigration(jobId)
            queryClient.setQueryData(['migration-job', jobId], finishedJob)
            await queryClient.invalidateQueries({ queryKey: ['migration-result', jobId] })
            await queryClient.invalidateQueries({ queryKey: ['migration-jobs'] })
            setConfirmFinish(false)
          } catch (error) {
            toast.error(getApiErrorMessage(error, 'Could not finish'))
          } finally {
            setFinishing(false)
          }
        }}
      />
    </div>
  )
}

export default MigrationProgress
