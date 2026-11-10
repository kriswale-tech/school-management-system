import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listSchools } from '@/features/schools/services'
import type { Channel, Classification, RangeParams, RangePreset } from '../types'

export const RANGE_PRESETS: Array<{ value: RangePreset; label: string }> = [
  { value: 'today', label: 'Today' },
  { value: 'last_7', label: 'Last 7 days' },
  { value: 'last_30', label: 'Last 30 days' },
  { value: 'this_month', label: 'This month' },
  { value: 'last_month', label: 'Last month' },
  { value: 'custom', label: 'Custom…' },
]

export type MessagesFilters = {
  range: RangePreset
  dateFrom: string
  dateTo: string
  channel: Channel | ''
  classification: Classification | ''
  school: string
  q: string
  page: number
}

const DEFAULTS: MessagesFilters = {
  range: 'last_30',
  dateFrom: '',
  dateTo: '',
  channel: '',
  classification: '',
  school: '',
  q: '',
  page: 1,
}

/** Map legacy UI values that predated the API contract. */
const RANGE_ALIASES: Record<string, RangePreset> = {
  '7d': 'last_7',
  '30d': 'last_30',
  last_7: 'last_7',
  last_30: 'last_30',
  today: 'today',
  this_month: 'this_month',
  last_month: 'last_month',
  custom: 'custom',
}

function normalizeRange(raw: string | null): RangePreset {
  if (!raw) return DEFAULTS.range
  return RANGE_ALIASES[raw] ?? DEFAULTS.range
}

/**
 * Filter state lives in the URL so a Messages view can be shared or reloaded
 * without losing the range the number was computed for.
 */
export function useMessagesFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  const filters = useMemo<MessagesFilters>(
    () => ({
      range: normalizeRange(searchParams.get('range')),
      dateFrom: searchParams.get('from') || '',
      dateTo: searchParams.get('to') || '',
      channel: (searchParams.get('channel') as Channel | '') || '',
      classification: (searchParams.get('classification') as Classification | '') || '',
      school: searchParams.get('school') || '',
      q: searchParams.get('q') || '',
      page: Number(searchParams.get('page')) || 1,
    }),
    [searchParams],
  )

  const setFilter = useCallback(
    (patch: Partial<MessagesFilters>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          const keys: Record<keyof MessagesFilters, string> = {
            range: 'range',
            dateFrom: 'from',
            dateTo: 'to',
            channel: 'channel',
            classification: 'classification',
            school: 'school',
            q: 'q',
            page: 'page',
          }
          for (const [key, value] of Object.entries(patch)) {
            const param = keys[key as keyof MessagesFilters]
            if (value === '' || value == null || value === DEFAULTS[key as keyof MessagesFilters]) {
              next.delete(param)
            } else {
              next.set(param, String(value))
            }
          }
          // Any filter change invalidates the current page offset.
          if (!('page' in patch)) next.delete('page')
          return next
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const params = useMemo<RangeParams>(() => {
    const base: RangeParams = { range: filters.range }
    if (filters.range === 'custom') {
      if (filters.dateFrom) base.from = filters.dateFrom
      if (filters.dateTo) base.to = filters.dateTo
    }
    if (filters.channel) base.channel = filters.channel
    if (filters.classification) base.classification = filters.classification
    if (filters.school) base.school = filters.school
    return base
  }, [filters])

  return { filters, setFilter, params }
}

export function rangeLabel(filters: MessagesFilters) {
  if (filters.range === 'custom') {
    return `${filters.dateFrom || 'start'} → ${filters.dateTo || 'today'}`
  }
  return RANGE_PRESETS.find((preset) => preset.value === filters.range)?.label ?? 'Last 30 days'
}

const selectClass =
  'rounded-xl border border-[var(--color-line)] bg-white px-3 py-2 text-sm'

export function FilterBar({
  filters,
  setFilter,
  show = {},
}: {
  filters: MessagesFilters
  setFilter: (patch: Partial<MessagesFilters>) => void
  show?: {
    channel?: boolean
    classification?: boolean
    school?: boolean
    search?: boolean
  }
}) {
  const schoolsQuery = useQuery({
    queryKey: ['platform-schools', 'filter-options'],
    queryFn: () => listSchools({ status: 'active' }),
    enabled: Boolean(show.school),
    staleTime: 1000 * 60 * 10,
  })

  return (
    <div className="mb-5 flex flex-wrap items-center gap-2">
      <select
        value={filters.range}
        onChange={(e) => setFilter({ range: e.target.value as RangePreset })}
        className={selectClass}
        aria-label="Date range"
      >
        {RANGE_PRESETS.map((preset) => (
          <option key={preset.value} value={preset.value}>
            {preset.label}
          </option>
        ))}
      </select>

      {filters.range === 'custom' && (
        <>
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(e) => setFilter({ dateFrom: e.target.value })}
            className={selectClass}
            aria-label="From date"
          />
          <input
            type="date"
            value={filters.dateTo}
            onChange={(e) => setFilter({ dateTo: e.target.value })}
            className={selectClass}
            aria-label="To date"
          />
        </>
      )}

      {show.channel && (
        <select
          value={filters.channel}
          onChange={(e) => setFilter({ channel: e.target.value as Channel | '' })}
          className={selectClass}
          aria-label="Channel"
        >
          <option value="">All channels</option>
          <option value="sms">SMS</option>
          <option value="email">Email</option>
        </select>
      )}

      {show.classification && (
        <select
          value={filters.classification}
          onChange={(e) =>
            setFilter({ classification: e.target.value as Classification | '' })
          }
          className={selectClass}
          aria-label="Billing classification"
        >
          <option value="">All classifications</option>
          <option value="paid">Paid</option>
          <option value="free">Free</option>
          <option value="sponsored">Sponsored</option>
        </select>
      )}

      {show.school && (
        <select
          value={filters.school}
          onChange={(e) => setFilter({ school: e.target.value })}
          className={selectClass}
          aria-label="School"
        >
          <option value="">All schools</option>
          {(schoolsQuery.data?.results ?? []).map((school) => (
            <option key={school.id} value={school.id}>
              {school.name}
            </option>
          ))}
        </select>
      )}

      {show.search && (
        <input
          value={filters.q}
          onChange={(e) => setFilter({ q: e.target.value })}
          placeholder="Search schools"
          className="min-w-[200px] flex-1 rounded-xl border border-[var(--color-line)] bg-white px-3 py-2 text-sm"
          aria-label="Search"
        />
      )}
    </div>
  )
}
