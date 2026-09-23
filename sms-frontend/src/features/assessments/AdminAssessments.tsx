import { useMemo, useState } from 'react'
import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import SearchComponent from '@/components/ui/SearchComponent'
import {
  getAdminAssessmentFilterOptions,
  getAdminAssessmentOverview,
} from '@/features/classes/services'
import { getApiErrorMessage } from '@/utils'
import AdminAssessmentsTable from './components/AdminAssessmentsTable'
import CorrectionsInbox from './components/CorrectionsInbox'

const FILTERS_QUERY_KEY = ['assessments', 'admin', 'filters'] as const

const AdminAssessments = () => {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [termSelection, setTermSelection] = useState<FilterSelection | undefined>(undefined)
  const [inboxOpen, setInboxOpen] = useState(false)

  const { data: filters, isLoading: filtersLoading } = useQuery({
    queryKey: FILTERS_QUERY_KEY,
    queryFn: getAdminAssessmentFilterOptions,
  })

  const defaultTermId = filters?.active_term_id ?? filters?.terms[0]?.id ?? ''
  const term: FilterSelection = termSelection !== undefined ? termSelection : defaultTermId
  const termId = term === '' ? undefined : String(term)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['assessments', 'admin', 'classes', termId],
    queryFn: () => getAdminAssessmentOverview(termId),
    enabled: Boolean(filters) && Boolean(termId),
  })

  const rows = useMemo(() => {
    const termText = search.trim().toLowerCase()
    return (data?.results ?? []).filter((row) => {
      if (
        row.ready_for_you_count === 0 &&
        row.released_count === 0 &&
        (row.needs_correction_count ?? 0) === 0
      ) {
        return false
      }
      if (!termText) return true
      const teacher = row.class_teacher_name?.toLowerCase() ?? ''
      return row.display_name.toLowerCase().includes(termText) || teacher.includes(termText)
    })
  }, [data?.results, search])

  const classCount = rows.length
  const studentCount = rows.reduce(
    (total, row) =>
      total + row.ready_for_you_count + row.released_count + (row.needs_correction_count ?? 0),
    0,
  )
  const fullyReady = data?.classes_fully_ready_count ?? 0
  const readyDescription =
    fullyReady === 0
      ? 'Class teacher approved these. No class is fully ready yet.'
      : fullyReady === 1
        ? 'Class teacher approved these. 1 class is fully ready to release.'
        : `Class teacher approved these. ${fullyReady} classes are fully ready to release.`

  const termOptions = (filters?.terms ?? []).map((item) => ({
    value: item.id,
    label: item.label,
  }))
  const inbox = data?.corrections_inbox ?? []
  const inboxCount = data?.corrections_inbox_count ?? inbox.length

  return (
    <div className="space-y-6">
      <ActionBar title="Assessments">
        <SearchComponent value={search} onChange={setSearch} placeholder="Search classes" />
        <FilterComponent
          filterName="Academic year and term"
          filterKey="term"
          options={termOptions}
          value={term}
          placeholder={filtersLoading ? 'Loading…' : 'Academic year & term'}
          onChange={setTermSelection}
        />
      </ActionBar>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatsCard
          title="With class teachers"
          value={String(data?.with_class_teacher_count ?? 0)}
          description="Still with the class teacher. These students are not shown in class details."
        />
        <StatsCard
          title="Ready for you"
          value={String(data?.ready_for_you_count ?? 0)}
          description={readyDescription}
        />
        <StatsCard
          title="Released"
          value={String(data?.released_count ?? 0)}
          description="Results you have released for this term."
        />
      </div>

      <div className="bg-white p-4 custom-shadow-md space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-medium text-slate-900">Classes</h2>
            <button
              type="button"
              onClick={() => setInboxOpen(true)}
              className="rounded-full bg-orange-50 px-3 py-1 text-xs font-medium text-orange-800 hover:bg-orange-100 cursor-pointer"
            >
              Reopen requests {inboxCount}
            </button>
          </div>
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

        <CorrectionsInbox
          open={inboxOpen}
          onClose={() => setInboxOpen(false)}
          items={inbox}
          title="Reopen requests"
          emptyLabel="No reopen requests from class teachers right now."
          onOpenItem={(item) => {
            const query = termId ? `?term=${termId}` : ''
            navigate(`/assessments/classes/${item.stream_id}${query}`)
          }}
        />

        {isError ? (
          <p className="text-sm text-red-600 py-6" role="alert">
            {getApiErrorMessage(error, 'Unable to load assessments.')}
          </p>
        ) : !filters || !termId ? (
          <p className="text-sm text-slate-500 py-6">Set an academic year and term first.</p>
        ) : (
          <AdminAssessmentsTable
            rows={rows}
            isLoading={isLoading}
            onViewClass={(row) => {
              const query = termId ? `?term=${termId}` : ''
              navigate(`/assessments/classes/${row.id}${query}`)
            }}
          />
        )}
      </div>
    </div>
  )
}

export default AdminAssessments
