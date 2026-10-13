import { useNavigate } from 'react-router-dom'
import dayjs from '@/lib/dayjs'
import type { ActivityItem } from '../types'

type RecentActivitiesCardProps = {
  activities: ActivityItem[]
  isLoading?: boolean
}

const RecentActivitiesCard = ({ activities, isLoading = false }: RecentActivitiesCardProps) => {
  const navigate = useNavigate()

  return (
    <div className="bg-white p-4 custom-shadow-md flex flex-col max-h-80">
      <h3 className="text-sm font-medium text-slate-800 mb-4 shrink-0">Recent Activities</h3>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {isLoading ? (
          <p className="text-sm text-slate-500 py-6 text-center">Loading activities…</p>
        ) : activities.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">No recent activity this term.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {activities.map((activity) => {
              const when = dayjs(activity.created_at)
              return (
                <li key={activity.id}>
                  <button
                    type="button"
                    onClick={() => {
                      if (activity.href) navigate(activity.href)
                    }}
                    className="w-full cursor-pointer rounded-md px-2 py-3 text-left transition-colors hover:bg-slate-50"
                  >
                    <p className="text-sm text-slate-800">{activity.summary}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {when.isValid() ? when.fromNow() : ''}
                    </p>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

export default RecentActivitiesCard
