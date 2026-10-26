import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Pagination } from '@/components/shared'
import dayjs from '@/lib/dayjs'
import { getActivities } from '@/features/dashboard/services'
import { getApiErrorMessage } from '@/utils'
import { REPORTS_ACTIVITIES_QUERY_KEY } from '../utils'

const VERB_LABELS: Record<string, string> = {
  scores_published: 'Scores published',
  students_approved: 'Students approved',
  student_rejected: 'Student rejected',
  reopen_requested: 'Reopen requested',
  reports_released: 'Reports released',
  correction_sent: 'Correction sent',
  correction_applied: 'Correction applied',
  reopen_declined: 'Reopen declined',
  payment_recorded: 'Payment recorded',
  fee_structure_published: 'Fee catalog published',
  fee_structure_applied: 'Fee catalog applied',
  advance_created: 'Advance created',
  class_teacher_assigned: 'Class teacher assigned',
  subject_teacher_assigned: 'Subject teacher assigned',
  subject_group_placed: 'Subject group placed',
  student_enrolled: 'Student enrolled',
  student_left: 'Student left',
  student_reactivated: 'Student reactivated',
}

type ActivityTabProps = {
  termId: string
}

const ActivityTab = ({ termId }: ActivityTabProps) => {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: [REPORTS_ACTIVITIES_QUERY_KEY, termId, page],
    queryFn: () => getActivities({ term: termId || undefined, page, page_size: 20 }),
    enabled: Boolean(termId),
  })

  const activities = data?.results ?? []

  return (
    <div className="bg-white custom-shadow-md">
      <div className="border-b border-slate-100 px-4 py-4 sm:px-6">
        <h2 className="text-base font-medium text-slate-900">Activity</h2>
        <p className="mt-1 text-sm text-slate-500">
          Recent changes this term, and who made them.
        </p>
      </div>

      {!termId || isLoading ? (
        <p className="px-4 py-10 text-center text-sm text-slate-500 sm:px-6">
          Loading activities…
        </p>
      ) : isError ? (
        <p className="px-4 py-10 text-center text-sm text-rose-600 sm:px-6" role="alert">
          {getApiErrorMessage(error, 'Could not load activities.')}
        </p>
      ) : activities.length === 0 ? (
        <p className="px-4 py-10 text-center text-sm text-slate-500 sm:px-6">
          No activity recorded for this term yet.
        </p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {activities.map((activity) => {
            const when = dayjs(activity.created_at)
            const verbLabel = VERB_LABELS[activity.verb] ?? activity.verb.replaceAll('_', ' ')
            const clickable = Boolean(activity.href)

            return (
              <li key={activity.id}>
                <button
                  type="button"
                  disabled={!clickable}
                  onClick={() => {
                    if (activity.href) navigate(activity.href)
                  }}
                  className={`w-full px-4 py-4 text-left transition-colors sm:px-6 ${
                    clickable
                      ? 'cursor-pointer hover:bg-slate-50'
                      : 'cursor-default'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                      {verbLabel}
                    </span>
                    <span className="text-xs text-slate-500">
                      {when.isValid() ? when.fromNow() : ''}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-900">{activity.summary}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {activity.actor_name
                      ? `By ${activity.actor_name}`
                      : 'By system'}
                    {activity.target_kind ? ` · ${activity.target_kind}` : ''}
                    {when.isValid() ? ` · ${when.format('D MMM YYYY, HH:mm')}` : ''}
                  </p>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {data && data.count > 0 ? (
        <Pagination
          pagination={data}
          onPageChange={setPage}
          isLoading={isFetching}
        />
      ) : null}
    </div>
  )
}

export default ActivityTab
