import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import type { AdminDashboardAcademicProgress, AdminDashboardLevel } from '../types'

type AcademicProgressCardProps = {
  progress: AdminDashboardAcademicProgress[]
  levels: AdminDashboardLevel[]
}

const AcademicProgressCard = ({ progress, levels }: AcademicProgressCardProps) => {
  const navigate = useNavigate()
  const [levelId, setLevelId] = useState<FilterSelection>('')

  const levelOptions = levels.map((level) => ({
    value: level.id,
    label: level.name,
  }))

  const filtered = useMemo(() => {
    if (levelId === '') return progress
    return progress.filter((row) => row.level_id === String(levelId))
  }, [progress, levelId])

  return (
    <div className="bg-white p-4 custom-shadow-md flex flex-col max-h-80">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-3 shrink-0">
        <div>
          <h3 className="text-sm font-medium text-slate-800">Academic Progress</h3>
          <p className="text-xs text-slate-500 mt-0.5">Report completion by class</p>
        </div>
        {levelOptions.length > 0 ? (
          <FilterComponent
            filterName="Level"
            filterKey="level"
            options={levelOptions}
            value={levelId}
            placeholder="All levels"
            onChange={setLevelId}
            className="max-w-[11rem]"
            selectClassName="py-1.5 text-xs"
          />
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-4 mb-4 shrink-0 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2.5 shrink-0 bg-slate-700" aria-hidden />
          Ready for you
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2.5 shrink-0 bg-emerald-500" aria-hidden />
          Released
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">No class progress to show yet.</p>
        ) : (
          <ul className="space-y-4">
            {filtered.map((row) => (
              <li key={row.stream_id}>
                <button
                  type="button"
                  onClick={() => navigate(`/assessments/classes/${row.stream_id}`)}
                  className="w-full cursor-pointer space-y-1.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-slate-50"
                >
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-slate-700 truncate">{row.display_name}</span>
                    <span className="text-slate-500 shrink-0">{row.percent_complete}%</span>
                  </div>
                  <div className="flex h-2 overflow-hidden bg-slate-100">
                    <div
                      className="h-full bg-slate-700 transition-all"
                      style={{ width: `${Math.min(row.ready_percent, 100)}%` }}
                      title={`${row.ready_count} ready for you`}
                    />
                    <div
                      className="h-full bg-emerald-500 transition-all"
                      style={{ width: `${Math.min(row.released_percent, 100)}%` }}
                      title={`${row.released_count} released`}
                    />
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default AcademicProgressCard
