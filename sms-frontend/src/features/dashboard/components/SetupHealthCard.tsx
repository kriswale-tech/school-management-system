import { useNavigate } from 'react-router-dom'
import type { AdminDashboardSetupHealth, AdminDashboardSetupHealthMetric } from '../types'

type SetupHealthCardProps = {
  health: AdminDashboardSetupHealth
}

export const getSetupHealthMetrics = (
  health: AdminDashboardSetupHealth,
): AdminDashboardSetupHealthMetric[] => {
  const metrics = [
    health.class_teachers,
    health.subject_teachers,
    health.classes_with_students,
    health.subject_groups_with_students,
    health.students_in_subject_groups,
  ]
  return metrics.filter((metric) => {
    if (
      metric === health.subject_groups_with_students ||
      metric === health.students_in_subject_groups
    ) {
      return metric.total > 0
    }
    return true
  })
}

/** True when any applicable coverage bar is incomplete. */
export const isSetupHealthIncomplete = (health: AdminDashboardSetupHealth) =>
  getSetupHealthMetrics(health).some((metric) => metric.percent < 100)

const SetupHealthCard = ({ health }: SetupHealthCardProps) => {
  const navigate = useNavigate()
  const metrics = getSetupHealthMetrics(health)

  return (
    <div className="bg-white p-4 custom-shadow-md flex flex-col max-h-80">
      <div className="mb-4 shrink-0">
        <h3 className="text-sm font-medium text-slate-800">Setup Health</h3>
        <p className="text-xs text-slate-500 mt-0.5">Active term coverage</p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <ul className="space-y-4">
          {metrics.map((metric) => (
            <li key={metric.label}>
              <button
                type="button"
                onClick={() => navigate(metric.href)}
                className="w-full cursor-pointer space-y-1.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-slate-50"
              >
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-slate-700 truncate">{metric.label}</span>
                  <span className="text-slate-500 shrink-0">
                    {metric.assigned}/{metric.total} · {metric.percent}%
                  </span>
                </div>
                <div className="h-2 overflow-hidden bg-slate-100">
                  <div
                    className="h-full bg-slate-700 transition-all"
                    style={{ width: `${Math.min(metric.percent, 100)}%` }}
                  />
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default SetupHealthCard
