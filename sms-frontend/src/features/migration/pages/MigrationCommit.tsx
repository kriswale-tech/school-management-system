import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, CheckboxField } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { commitMigration, getMigrationJob, getMigrationPlan } from '../services'

const MigrationCommit = () => {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const job = useQuery({ queryKey: ['migration-job', jobId], queryFn: () => getMigrationJob(jobId) })
  const plan = useQuery({ queryKey: ['migration-plan', jobId], queryFn: () => getMigrationPlan(jobId) })
  const [confirmed, setConfirmed] = useState(false)
  const [saving, setSaving] = useState(false)
  const counts = plan.data?.summary.plan ?? {}
  const opening = plan.data?.summary.opening
  const history = plan.data?.summary.history
  const isOpening = job.data?.template === 'opening_balances'
  const isHistory = job.data?.template === 'historical_finance'

  return (
    <div className="max-w-xl space-y-4 bg-white p-4 custom-shadow-md">
      {isHistory && history ? (
        <ul className="space-y-1 text-sm text-slate-800">
          <li>GHS {history.charge_total} in charges</li>
          <li>GHS {history.payment_total} in payments</li>
          <li>GHS {history.advance_total} held as advance</li>
          <li>{history.unique_students} students</li>
          <li>{history.blocked_rows} left out</li>
        </ul>
      ) : isOpening && opening ? (
        <ul className="space-y-1 text-sm text-slate-800">
          <li>GHS {opening.total} will be added to the ledger</li>
          <li>{opening.valid_rows} balances</li>
          <li>{opening.unique_students} students</li>
          <li>{opening.blocked_rows} left out</li>
          <li>{opening.skipped_rows} zero balances left out</li>
        </ul>
      ) : (
        <ul className="space-y-1 text-sm text-slate-800">
          <li>{counts.new_students ?? 0} new students</li>
          <li>{counts.linked_students ?? 0} existing students</li>
          <li>{counts.guardians_created ?? 0} new parents</li>
          <li>{counts.current_enrollments ?? 0} classes this term</li>
          <li>{counts.historical_enrollments ?? 0} past classes</li>
          <li>{counts.blocked ?? 0} left out</li>
        </ul>
      )}
      <CheckboxField checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)}>
        {isHistory ? 'Save these charges and payments' : isOpening && opening ? `Add GHS ${opening.total} as opening balances` : 'Save these students and classes'}
      </CheckboxField>
      <Button
        className="max-w-fit py-2"
        disabled={!confirmed}
        loading={saving}
        loadingText="Saving"
        onClick={async () => {
          setSaving(true)
          try {
            const saved = await commitMigration(jobId, isOpening ? opening?.total : undefined)
            queryClient.setQueryData(['migration-job', jobId], saved)
            navigate(`/migration/${jobId}/progress`)
          } catch (error) {
            setSaving(false)
            toast.error(getApiErrorMessage(error, 'Nothing was saved'))
          }
        }}
      >
        {isHistory ? 'Save history' : isOpening ? 'Save balances' : 'Save students'}
      </Button>
    </div>
  )
}

export default MigrationCommit
