import { useNavigate } from 'react-router-dom'
import type { TeacherClassRow } from '../types'

type TeacherClassesCardProps = {
  classes: TeacherClassRow[]
  showAcademic: boolean
}

const share = (count: number, total: number) => (total > 0 ? (count / total) * 100 : 0)

const TeacherClassesCard = ({ classes, showAcademic }: TeacherClassesCardProps) => {
  const navigate = useNavigate()

  return (
    <div className="bg-white p-4 custom-shadow-md flex flex-col max-h-80">
      <div className="mb-4 shrink-0">
        <h3 className="text-sm font-medium text-slate-800">My Classes</h3>
        {showAcademic ? (
          <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 shrink-0 bg-slate-700" aria-hidden />
              Ready from subject teachers
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 shrink-0 bg-emerald-500" aria-hidden />
              Approved by you
            </span>
          </div>
        ) : null}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {classes.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">No classes assigned this term.</p>
        ) : (
          <ul className="space-y-4">
            {classes.map((row) => {
              const ready = share(row.awaiting_approval_count, row.students_count)
              const approved = share(row.approved_count, row.students_count)
              return (
                <li key={row.id}>
                  <button
                    type="button"
                    onClick={() => navigate(row.href)}
                    className="w-full cursor-pointer space-y-1.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-slate-50"
                  >
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span className="font-medium text-slate-900 truncate">{row.display_name}</span>
                      <span className="text-xs text-slate-500 shrink-0">
                        {row.students_count} {row.students_count === 1 ? 'student' : 'students'}
                      </span>
                    </div>
                    {showAcademic ? (
                      <>
                        <div className="flex h-2 overflow-hidden bg-slate-100">
                          <div
                            className="h-full bg-slate-700 transition-all"
                            style={{ width: `${Math.min(ready, 100)}%` }}
                            title={`${row.awaiting_approval_count} ready from subject teachers`}
                          />
                          <div
                            className="h-full bg-emerald-500 transition-all"
                            style={{ width: `${Math.min(approved, 100)}%` }}
                            title={`${row.approved_count} approved by you`}
                          />
                        </div>
                        <p className="text-xs text-slate-500">
                          {row.awaiting_approval_count} ready · {row.approved_count} approved ·{' '}
                          {row.pending_count} with subject teachers
                        </p>
                      </>
                    ) : null}
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

export default TeacherClassesCard
