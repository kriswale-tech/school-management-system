import { useEffect, useState } from 'react'
import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import { ActionButton } from '@/components/ui'
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

const STATUS_FILTER_OPTIONS = [
  { value: 'with_class_teacher', label: 'With class teachers' },
  { value: 'ready_for_you', label: 'Ready for you' },
  { value: 'released', label: 'Released' },
] as const

type StatusFilter = (typeof STATUS_FILTER_OPTIONS)[number]['value']

const statusFromParam = (value: string | null): FilterSelection => {
  if (
    value === 'with_class_teacher' ||
    value === 'ready_for_you' ||
    value === 'released'
  ) {
    return value
  }
  return ''
}

const AdminAssessments = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [termSelection, setTermSelection] = useState<FilterSelection | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [inboxOpen, setInboxOpen] = useState(searchParams.get('inbox') === '1')

  const statusFilter = statusFromParam(searchParams.get('status'))

  const setStatusFilter = (value: FilterSelection) => {
    const next = new URLSearchParams(searchParams)
    if (typeof value === 'string' && value !== '') next.set('status', value)
    else next.delete('status')
    setSearchParams(next, { replace: true })
    setPage(1)
  }

  useEffect(() => {
    if (searchParams.get('inbox') === '1') {
      setInboxOpen(true)
    }
  }, [searchParams])

  const handleInboxOpenChange = (open: boolean) => {
    setInboxOpen(open)
    const next = new URLSearchParams(searchParams)
    if (open) next.set('inbox', '1')
    else next.delete('inbox')
    setSearchParams(next, { replace: true })
  }

  const { data: filters, isLoading: filtersLoading } = useQuery({
    queryKey: FILTERS_QUERY_KEY,
    queryFn: getAdminAssessmentFilterOptions,
  })

  const defaultTermId = filters?.active_term_id ?? filters?.terms[0]?.id ?? ''
  const term: FilterSelection = termSelection !== undefined ? termSelection : defaultTermId
  const termId = term === '' ? undefined : String(term)
  const status =
    typeof statusFilter === 'string' && statusFilter !== ''
      ? (statusFilter as StatusFilter)
      : undefined

  const queryParams = {
    termId,
    search: search.trim() || undefined,
    status,
    page,
  }

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['assessments', 'admin', 'classes', queryParams],
    queryFn: () => getAdminAssessmentOverview(queryParams),
    enabled: Boolean(filters) && Boolean(termId),
  })

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
  const classCount = data?.count ?? 0
  const studentCount = data?.filtered_students_count ?? 0

  return (
    <div className="space-y-6">
      <ActionBar title="Assessments">
        <SearchComponent
          value={search}
          onChange={(value) => {
            setSearch(value)
            setPage(1)
          }}
          placeholder="Search classes"
        />
        <FilterComponent
          filterName="Academic year and term"
          filterKey="term"
          options={termOptions}
          value={term}
          placeholder={filtersLoading ? 'Loading…' : 'Academic year & term'}
          onChange={(value) => {
            setTermSelection(value)
            setPage(1)
          }}
        />
        <FilterComponent
          filterName="Status"
          filterKey="status"
          options={[...STATUS_FILTER_OPTIONS]}
          value={statusFilter}
          placeholder="All statuses"
          onChange={(value) => {
            setStatusFilter(value)
          }}
        />
        <ActionButton
          icon="hugeicons:settings-02"
          label="Assessment Settings"
          tooltipSide="bottom"
          onClick={() => navigate('/assessments/settings')}
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
              onClick={() => handleInboxOpenChange(true)}
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
          onClose={() => handleInboxOpenChange(false)}
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
            rows={data?.results ?? []}
            isLoading={isLoading}
            pagination={data ?? null}
            onPageChange={setPage}
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
