import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ActionBar from '@/components/shared/ActionBar'
import { ConfirmDialog, Table, TableWrapper } from '@/components/shared'
import { ActionButton, Button, SelectField } from '@/components/ui'
import dayjs from '@/lib/dayjs'
import InputField from '@/components/ui/InputField'
import { getApiErrorMessage } from '@/utils'
import Hint from '../components/Hint'
import { StatusPill } from '../components/StatusPill'
import { JOB_LABELS, TEMPLATE_LABELS } from '../labels'
import { createMigrationJob, deleteMigrationJob, downloadTemplate, listMigrationJobs } from '../services'
import type { MigrationTemplate } from '../types'

const MigrationHome = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [template, setTemplate] = useState<MigrationTemplate>('student_information')
  const [sourceSystem, setSourceSystem] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const jobs = useQuery({ queryKey: ['migration-jobs'], queryFn: listMigrationJobs })
  const deleteJob = useMutation({
    mutationFn: deleteMigrationJob,
    onSuccess: async () => {
      setDeletingId(null)
      await queryClient.invalidateQueries({ queryKey: ['migration-jobs'] })
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'This import could not be deleted')),
  })
  const createJob = useMutation({
    mutationFn: () => createMigrationJob({
      job_type: template === 'opening_balances' || template === 'historical_finance' ? 'fee_financial_history' : 'student_enrollment',
      template,
      source_system: sourceSystem,
    }),
    onSuccess: async (job) => {
      await queryClient.invalidateQueries({ queryKey: ['migration-jobs'] })
      navigate(`/migration/${job.id}/upload`)
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not start the import')),
  })

  return (
    <div className="space-y-6">
      <ActionBar title="Import">
        <Hint text="Bring in students, classes, an outstanding balance, or old charges and payments." />
      </ActionBar>

      <div className="grid gap-4 bg-white p-4 custom-shadow-md md:grid-cols-[1fr_1fr_auto] md:items-end">
        <label className="text-sm text-slate-700">
          Import
          <SelectField
            className="mt-1.5"
            value={template}
            options={[
              { value: 'student_information', label: 'Student information' },
              { value: 'enrollment_history', label: 'Enrollment history' },
              { value: 'opening_balances', label: 'Opening balances' },
              { value: 'historical_finance', label: 'Fee history' },
            ]}
            onChange={(value) => setTemplate(value as MigrationTemplate)}
          />
        </label>
        <label className="text-sm text-slate-700">
          Previous system
          <InputField className="mt-1.5 py-3" value={sourceSystem} placeholder="Optional" onChange={(event) => setSourceSystem(event.target.value)} />
        </label>
        <div className="flex gap-2">
          {template === 'historical_finance' ? (
            <>
              <Button className="max-w-fit py-3" variant="outline" onClick={() => downloadTemplate('historical_charges', 'xlsx')}>
                Charges Excel
              </Button>
              <Button className="max-w-fit py-3" variant="outline" onClick={() => downloadTemplate('historical_payments', 'xlsx')}>
                Payments Excel
              </Button>
            </>
          ) : (
            <>
              <Button className="max-w-fit py-3" variant="outline" onClick={() => downloadTemplate(template, 'xlsx')}>
                Download Excel
              </Button>
              <Button className="max-w-fit py-3" variant="outline" onClick={() => downloadTemplate(template, 'csv')}>
                Download CSV
              </Button>
            </>
          )}
          <Button className="max-w-fit py-3" loading={createJob.isPending} onClick={() => createJob.mutate()}>
            New import
          </Button>
        </div>
      </div>

      <TableWrapper
        isLoading={jobs.isLoading}
        isEmpty={!jobs.isLoading && (jobs.data ?? []).length === 0}
        emptyState={{ title: 'No imports yet', icon: 'hugeicons:database-import' }}
        variant="card"
      >
        <Table>
          <Table.Head>
            <Table.Row>
              <Table.HeaderCell>Import</Table.HeaderCell>
              <Table.HeaderCell>Previous system</Table.HeaderCell>
              <Table.HeaderCell>Started</Table.HeaderCell>
              <Table.HeaderCell>Status</Table.HeaderCell>
              <Table.HeaderCell>Action</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {(jobs.data ?? []).map((job) => {
              const started = dayjs(job.created_at)
              const saved = job.status === 'committed' || job.status === 'partially_committed' || job.status === 'committing'
              return (
                <Table.Row key={job.id}>
                  <Table.Cell variant="primary">{TEMPLATE_LABELS[job.template || ''] || JOB_LABELS[job.job_type]}</Table.Cell>
                  <Table.Cell>{job.source_system || '—'}</Table.Cell>
                  <Table.Cell>{started.isValid() ? started.format('DD MMM YYYY') : '—'}</Table.Cell>
                  <Table.Cell><StatusPill value={job.status} /></Table.Cell>
                  <Table.Cell>
                    <div className="flex items-center gap-2">
                      <ActionButton
                        icon="hugeicons:view"
                        label="Open"
                        onClick={() => navigate(`/migration/${job.id}/${saved ? 'progress' : 'upload'}`)}
                      />
                      {saved ? null : (
                        <ActionButton
                          icon="hugeicons:delete-02"
                          label="Delete"
                          onClick={() => setDeletingId(job.id)}
                        />
                      )}
                    </div>
                  </Table.Cell>
                </Table.Row>
              )
            })}
          </Table.Body>
        </Table>
      </TableWrapper>

      <ConfirmDialog
        open={Boolean(deletingId)}
        title="Delete import"
        message="Nothing has been saved."
        confirmLabel="Delete"
        onClose={() => setDeletingId(null)}
        onConfirm={() => {
          if (deletingId) deleteJob.mutate(deletingId)
        }}
        isLoading={deleteJob.isPending}
      />
    </div>
  )
}

export default MigrationHome
