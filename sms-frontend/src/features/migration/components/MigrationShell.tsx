import { useQuery } from '@tanstack/react-query'
import { NavLink, Navigate, Outlet, useLocation, useParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { useAuth } from '@/features/auth/hooks'
import { getMigrationJob } from '../services'
import type { MigrationJob } from '../types'
import Hint from './Hint'

const STEPS = [
  { key: 'upload', title: 'File', hint: 'Excel or CSV. You can leave out sheets you do not need.' },
  { key: 'map', title: 'Map columns', hint: 'Match your column names to SCHOOLASST fields. Required fields are marked with *.' },
  { key: 'values', title: 'Check values', hint: 'Each different value is decided once and applied to every row that uses it.' },
  { key: 'enrollments', title: 'Classes', hint: 'An exact class name is used automatically. A combined name such as JHS 1A needs confirmation.' },
  { key: 'match', title: 'Check possible matches', hint: 'A matching ID is linked automatically. Similar names need your choice.' },
  { key: 'summary', title: 'Review', hint: 'Only ready rows are saved.' },
  { key: 'commit', title: 'Save students', hint: 'This adds students, parents, and classes. Fees are not changed.' },
  { key: 'progress', title: 'Results', hint: 'Students that were not saved are listed with the reason. You can try them again, or finish without them.' },
]

const RESULT_STATUSES = new Set(['committing', 'partially_committed', 'committed', 'failed'])

const furthestKey = (job: MigrationJob) => {
  if (RESULT_STATUSES.has(job.status)) return 'progress'
  const mapped = job.files.some((file) =>
    file.sheets.some((sheet) => sheet.mappings.some((mapping) => mapping.target_field && !mapping.ignored)),
  )
  if (mapped) return 'commit'
  const hasFile = job.files.some((file) => file.sheets.length > 0)
  if (hasFile) return 'map'
  return 'upload'
}

const MigrationShell = () => {
  const { user } = useAuth({ requireAuth: true })
  const { jobId } = useParams()
  const { pathname } = useLocation()
  const job = useQuery({
    queryKey: ['migration-job', jobId],
    queryFn: () => getMigrationJob(jobId || ''),
    enabled: Boolean(jobId),
  })
  const finished = job.data?.status === 'committed'
  const opening = job.data?.template === 'opening_balances'
  const historyFees = job.data?.template === 'historical_finance'
  const ledger = opening || historyFees
  const steps = STEPS
    .filter((item) => item.key !== 'match' || job.data?.template !== 'enrollment_history')
    .map((item) => {
      if (!ledger) return item
      if (item.key === 'enrollments') {
        return { ...item, title: 'Years', hint: 'Enter dates for a year that is not on the calendar yet. The year stays inactive.' }
      }
      if (item.key === 'upload' && historyFees) {
        return { ...item, title: 'Files', hint: 'Upload the charges file and the payments file.' }
      }
      if (item.key === 'commit') {
        return historyFees
          ? { ...item, title: 'Save history', hint: 'Confirm the totals. Nothing is added to the ledger until you do.' }
          : { ...item, title: 'Save balances', hint: 'Confirm the total. Nothing is added to the ledger until you do.' }
      }
      if (item.key === 'progress') {
        return historyFees
          ? { ...item, title: 'Results', hint: 'Rows that were not saved are listed with the reason.' }
          : { ...item, title: 'Results', hint: 'Balances that were not saved are listed with the reason.' }
      }
      return item
    })
  const step = steps.find((item) => pathname.endsWith(`/${item.key}`))
  const allowedIndex = job.data ? steps.findIndex((item) => item.key === furthestKey(job.data)) : 0
  const stepIndex = Math.max(0, steps.findIndex((item) => item.key === step?.key))

  if (!user) return null
  if (user.role !== 'admin' && user.role !== 'staff') return <Navigate to="/dashboard" replace />
  if (job.data && finished && step && step.key !== 'progress') {
    return <Navigate to={`/migration/${jobId}/progress`} replace />
  }
  if (job.data && step && stepIndex > allowedIndex) {
    return <Navigate to={`/migration/${jobId}/${steps[allowedIndex].key}`} replace />
  }

  return (
    <div className="space-y-6">
      {jobId ? (
        <>
          <ActionBar title={finished ? 'Report' : step?.title ?? 'Import'} back backTo="/migration">
            {finished ? <Hint text="This import is finished." /> : step ? <Hint text={step.hint} /> : null}
          </ActionBar>
          {finished ? null : <nav className="flex gap-5 overflow-x-auto border-b border-slate-200">
            {steps.map((item, index) =>
              index <= allowedIndex ? (
                <NavLink
                  key={item.key}
                  to={`/migration/${jobId}/${item.key}`}
                  className={({ isActive }) =>
                    `pb-2 text-sm whitespace-nowrap ${
                      isActive ? 'border-b-2 border-slate-900 font-medium text-slate-900' : 'text-slate-500'
                    }`
                  }
                >
                  {item.title}
                </NavLink>
              ) : (
                <span key={item.key} className="pb-2 text-sm whitespace-nowrap text-slate-300">
                  {item.title}
                </span>
              ),
            )}
          </nav>}
        </>
      ) : null}
      <Outlet />
    </div>
  )
}

export default MigrationShell
