import { useNavigate } from 'react-router-dom'
import type { TeacherSubjectRow } from '../types'

type TeacherSubjectsCardProps = {
  subjects: TeacherSubjectRow[]
}

const TeacherSubjectsCard = ({ subjects }: TeacherSubjectsCardProps) => {
  const navigate = useNavigate()

  return (
    <div className="bg-white p-4 custom-shadow-md flex flex-col max-h-80">
      <h3 className="text-sm font-medium text-slate-800 mb-4 shrink-0">My Subjects</h3>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {subjects.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">No subjects assigned this term.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {subjects.map((row) => {
              const group = row.subject_group_name ? ` · ${row.subject_group_name}` : ''
              const status = row.needs_correction_count > 0
                ? 'Review correction'
                : row.students_count === 0
                  ? 'No students'
                  : row.is_open
                    ? 'Not published'
                    : 'Published'
              return (
                <li key={row.id}>
                  <button
                    type="button"
                    onClick={() => navigate(row.href)}
                    className="w-full cursor-pointer rounded-md px-2 py-3 text-left transition-colors hover:bg-slate-50"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-slate-900 truncate">{row.subject_name}</p>
                      <p className="text-xs text-slate-500 shrink-0">{status}</p>
                    </div>
                    <p className="mt-1 text-xs text-slate-500 truncate">
                      {row.display_class_name}
                      {group}
                      {row.needs_correction_count > 0
                        ? ` · ${row.needs_correction_count} correction${row.needs_correction_count === 1 ? '' : 's'}`
                        : ''}
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

export default TeacherSubjectsCard
