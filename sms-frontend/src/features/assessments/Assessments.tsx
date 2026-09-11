import { useMemo, useState } from 'react'
import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import SearchComponent from '@/components/ui/SearchComponent'
import { getClassTeacherAssessmentOverview } from '@/features/classes/services'
import { getApiErrorMessage } from '@/utils'
import ClassTeacherAssessmentsTable, {
  type ClassTeacherAssessmentRow,
} from './components/ClassTeacherAssessmentsTable'

const OVERVIEW_QUERY_KEY = ['assessments', 'my-classes'] as const

const Assessments = () => {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: OVERVIEW_QUERY_KEY,
    queryFn: getClassTeacherAssessmentOverview,
  })

  const rows: ClassTeacherAssessmentRow[] = useMemo(() => {
    const results = data?.results ?? []
    const term = search.trim().toLowerCase()
    return results
      .filter((item) => !term || item.display_name.toLowerCase().includes(term))
      .map((item) => ({
        id: item.id,
        class_level_id: item.class_level_id,
        class_level_name: item.class_level_name,
        stream_id: item.stream_id,
        stream_name: item.stream_name,
        display_name: item.display_name,
        students_count: item.students_count,
        view_stream_id: item.view_stream_id,
        pending_count: item.pending_count,
        ready_count: item.awaiting_approval_count,
        approved_count: item.approved_count,
      }))
  }, [data?.results, search])

  const classCount = rows.length
  const studentCount = rows.reduce((total, row) => total + row.students_count, 0)

  return (
    <div className="space-y-6">
      <ActionBar title="Assessments">
        <SearchComponent value={search} onChange={setSearch} placeholder="Search classes" />
      </ActionBar>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatsCard
          title="Pending"
          value={String(data?.pending_count ?? 0)}
          description="Students still waiting on one or more subject teachers to publish results."
        />
        <StatsCard
          title="Awaiting approval"
          value={String(data?.awaiting_approval_count ?? 0)}
          description="All subjects published; waiting for you to approve as class teacher."
        />
        <StatsCard
          title="Approved"
          value={String(data?.approved_count ?? 0)}
          description="You approved these results; they are with admin for final review."
        />
      </div>

      <div className="bg-white p-4 custom-shadow-md space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-medium text-slate-900">My classes</h2>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <div className="flex items-center gap-1.5">
              <Icon icon="hugeicons:notebook-01" className="size-4" aria-hidden />
              <span>
                {classCount} {classCount === 1 ? 'Class' : 'Classes'}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <Icon icon="hugeicons:user-group" className="size-4" aria-hidden />
              <span>
                {studentCount} {studentCount === 1 ? 'Student' : 'Students'}
              </span>
            </div>
          </div>
        </div>

        {isError ? (
          <p className="text-sm text-red-600 py-6" role="alert">
            {getApiErrorMessage(error, 'Unable to load your classes.')}
          </p>
        ) : (
          <ClassTeacherAssessmentsTable
            rows={rows}
            isLoading={isLoading}
            onViewClass={(row) => {
              navigate(`/assessments/${row.id}`)
            }}
          />
        )}
      </div>
    </div>
  )
}

export default Assessments
