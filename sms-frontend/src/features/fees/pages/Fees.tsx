import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import { ActionButton, Button } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import SearchComponent from '@/components/ui/SearchComponent'
import { getClasses } from '@/features/classes/services'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks/useCan'
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

const STATUS_FILTER_OPTIONS = [
  { value: true, label: 'Debtors only' },
  { value: false, label: 'Paid / no balance' },
] as const

const debtorsFromParam = (value: string | null): FilterSelection => {
  if (value === 'true') return true
  if (value === 'false') return false
  return ''
}

const Fees = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const canRecordPayment = useCan(Capability.FEES_RECORD_PAYMENT)
  const canManageSettings = useCan(Capability.FEES_MANAGE_SETTINGS)
  const [search, setSearch] = useState('')
  const [classLevel, setClassLevel] = useState<FilterSelection>('')
  const [termSelection, setTermSelection] = useState<FilterSelection | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [recordOpen, setRecordOpen] = useState(false)

  const debtors = debtorsFromParam(searchParams.get('debtors'))

  const setDebtors = (value: FilterSelection) => {
    const next = new URLSearchParams(searchParams)
    if (value === true) next.set('debtors', 'true')
    else if (value === false) next.set('debtors', 'false')
    else next.delete('debtors')
    setSearchParams(next, { replace: true })
    setPage(1)
  }

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
      debtors: typeof debtors === 'boolean' ? debtors : undefined,
    }),
    [page, search, classLevel, term, debtors],
  )

  const statsParams: FeeDeskQueryParams = useMemo(
    () => ({
      search: queryParams.search,
      class_level: queryParams.class_level,
      term: queryParams.term,
      debtors: queryParams.debtors,
    }),
    [queryParams.search, queryParams.class_level, queryParams.term, queryParams.debtors],
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
        <FilterComponent
          filterName="Status"
          filterKey="debtors"
          options={[...STATUS_FILTER_OPTIONS]}
          value={debtors}
          placeholder="All Students"
          onChange={(value) => {
            setDebtors(value)
          }}
        />
        {canRecordPayment ? (
          <Button
            type="button"
            className="py-2 text-sm max-w-fit"
            onClick={() => setRecordOpen(true)}
          >
            <Icon
              icon="hugeicons:plus-sign"
              className="size-4 bg-white text-black rounded-full p-0.5"
            />
            Record Payment
          </Button>
        ) : null}
        {canManageSettings ? (
          <ActionButton
            icon="hugeicons:settings-02"
            label="Fees Settings"
            tooltipSide="bottom"
            onClick={() => navigate('/fees/settings')}
          />
        ) : null}
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
      {canRecordPayment ? (
        <RecordPaymentSlider open={recordOpen} onClose={() => setRecordOpen(false)} />
      ) : null}
    </div>
  )
}

export default Fees
