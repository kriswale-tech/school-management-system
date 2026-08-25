import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import { Button } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import SearchComponent from '@/components/ui/SearchComponent'
import { getClasses } from '@/features/classes/services'
import FeesTable from '../components/FeesTable'
import RecordPaymentSlider from '../components/RecordPaymentSlider'
import { getFeeDeskFilterOptions, getFeeDeskList, getFeeDeskStats } from '../services'
import type { FeeDeskQueryParams } from '../types'
import {
  FEE_DESK_FILTERS_QUERY_KEY,
  FEE_DESK_QUERY_KEY,
  FEE_DESK_STATS_QUERY_KEY,
  formatDebtorsStat,
  formatFeeAmount,
} from '../utils'

const Fees = () => {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [classLevel, setClassLevel] = useState<FilterSelection>('')
  const [termSelection, setTermSelection] = useState<FilterSelection | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [recordOpen, setRecordOpen] = useState(false)

  const { data: filterOptions, isLoading: filtersLoading } = useQuery({
    queryKey: [FEE_DESK_FILTERS_QUERY_KEY],
    queryFn: getFeeDeskFilterOptions,
  })

  const term: FilterSelection =
    termSelection !== undefined ? termSelection : (filterOptions?.active_term_id ?? '')

  const filtersReady = Boolean(filterOptions)

  const { data: classes = [] } = useQuery({
    queryKey: ['classes'],
    queryFn: getClasses,
  })

  const queryParams: FeeDeskQueryParams = useMemo(
    () => ({
      page,
      search: search || undefined,
      class_level: classLevel === '' ? undefined : String(classLevel),
      term: term === '' ? undefined : String(term),
    }),
    [page, search, classLevel, term],
  )

  const statsParams: FeeDeskQueryParams = useMemo(
    () => ({
      search: queryParams.search,
      class_level: queryParams.class_level,
      term: queryParams.term,
    }),
    [queryParams.search, queryParams.class_level, queryParams.term],
  )

  const { data, isLoading } = useQuery({
    queryKey: [FEE_DESK_QUERY_KEY, queryParams],
    queryFn: () => getFeeDeskList(queryParams),
    enabled: filtersReady,
  })

  const { data: stats } = useQuery({
    queryKey: [FEE_DESK_STATS_QUERY_KEY, statsParams],
    queryFn: () => getFeeDeskStats(statsParams),
    enabled: filtersReady,
  })

  const classOptions = classes.map((item) => ({
    value: item.id,
    label: item.name,
  }))

  const termOptions = (filterOptions?.terms ?? []).map((item) => ({
    value: item.id,
    label: item.label,
  }))

  return (
    <div className="space-y-6">
      <ActionBar title="Fees">
        <SearchComponent
          value={search}
          onChange={(value) => {
            setSearch(value)
            setPage(1)
          }}
        />
        <FilterComponent
          filterName="Class"
          filterKey="class_level"
          options={classOptions}
          value={classLevel}
          placeholder="All Classes"
          onChange={(value) => {
            setClassLevel(value)
            setPage(1)
          }}
        />
        <FilterComponent
          filterName="Term"
          filterKey="term"
          options={termOptions}
          value={term}
          placeholder={filtersLoading ? 'Loading…' : 'Academic Year & Term'}
          onChange={(value) => {
            setTermSelection(value)
            setPage(1)
          }}
        />
        <Button type="button" className="py-2 text-sm max-w-fit" onClick={() => setRecordOpen(true)}>
          <Icon
            icon="hugeicons:plus-sign"
            className="size-4 bg-white text-black rounded-full p-0.5"
          />
          Record Payment
        </Button>
        <Button
          type="button"
          variant="outline"
          className="py-2 text-sm max-w-fit"
          onClick={() => navigate('/fees/settings')}
        >
          <Icon icon="hugeicons:settings-02" className="size-4" />
          Fees Settings
        </Button>
      </ActionBar>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Fees Expected"
          value={formatFeeAmount(stats?.total_expected ?? 0)}
        />
        <StatsCard
          title="Total Fees Collected"
          value={formatFeeAmount(stats?.total_collected ?? 0)}
        />
        <StatsCard title="Outstanding Fees" value={formatFeeAmount(stats?.outstanding ?? 0)} />
        <StatsCard
          title="Number of Debtors"
          value={formatDebtorsStat(stats?.debtors_count ?? 0, stats?.total_students ?? 0)}
        />
      </div>

      <FeesTable
        rows={data?.results ?? []}
        isLoading={!filtersReady || isLoading}
        pagination={data ?? null}
        onPageChange={setPage}
        onViewRow={(row) => {
          navigate(`/fees/${row.id}`)
        }}
      />
      <RecordPaymentSlider open={recordOpen} onClose={() => setRecordOpen(false)} />
    </div>
  )
}

export default Fees
