import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import dayjs from '@/lib/dayjs'
import { formatDateTime } from '@/lib/dates'
import { ACTION_FILTERS, TARGET_FILTERS, actionLabel, auditSummary, detailRows } from './labels'
import { listAudit } from './services'

const WHEN_OPTIONS = [
  { value: '', label: 'Any time' },
  { value: 'today', label: 'Today' },
  { value: 'last_7', label: 'Last 7 days' },
  { value: 'last_30', label: 'Last 30 days' },
  { value: 'this_month', label: 'This month' },
]

function rangeBounds(preset: string) {
  const today = dayjs()
  if (preset === 'today') {
    const day = today.format('YYYY-MM-DD')
    return { start: day, end: day }
  }
  if (preset === 'last_7') {
    return { start: today.subtract(6, 'day').format('YYYY-MM-DD'), end: today.format('YYYY-MM-DD') }
  }
  if (preset === 'last_30') {
    return { start: today.subtract(29, 'day').format('YYYY-MM-DD'), end: today.format('YYYY-MM-DD') }
  }
  if (preset === 'this_month') {
    return { start: today.startOf('month').format('YYYY-MM-DD'), end: today.format('YYYY-MM-DD') }
  }
  return {}
}

const fieldClass =
  'rounded-lg border border-[var(--color-line)] bg-white px-3 py-2 text-sm text-[var(--color-ink)]'

export default function AuditPage() {
  const [search, setSearch] = useState('')
  const [action, setAction] = useState('')
  const [targetType, setTargetType] = useState('')
  const [when, setWhen] = useState('last_7')
  const [page, setPage] = useState(1)
  const [openId, setOpenId] = useState<string | null>(null)
  const bounds = rangeBounds(when)

  const auditQuery = useQuery({
    queryKey: ['platform-audit', search, action, targetType, when, page],
    queryFn: () =>
      listAudit({
        q: search.trim() || undefined,
        action: action || undefined,
        target_type: targetType || undefined,
        start: bounds.start,
        end: bounds.end,
        page,
      }),
    retry: false,
  })

  const rows = auditQuery.data?.results ?? []

  function resetPage() {
    setPage(1)
    setOpenId(null)
  }

  return (
    <div>
      <header className="mb-8">
        <p className="text-sm font-semibold tracking-[0.18em] text-[var(--color-accent)] uppercase">
          Platform
        </p>
        <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold">Audit log</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--color-ink)]/70">
          Every platform action. Entries cannot be edited or deleted.
        </p>
      </header>

      <div className="mb-4 flex flex-wrap gap-2">
        <label className="flex min-w-56 flex-1 flex-col gap-1 text-sm">
          Search
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              resetPage()
            }}
            placeholder="Email, action, or target id"
            className={fieldClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Action
          <select
            value={action}
            onChange={(event) => {
              setAction(event.target.value)
              resetPage()
            }}
            className={fieldClass}
          >
            {ACTION_FILTERS.map((option) => (
              <option key={option.value || 'all-actions'} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Target
          <select
            value={targetType}
            onChange={(event) => {
              setTargetType(event.target.value)
              resetPage()
            }}
            className={fieldClass}
          >
            {TARGET_FILTERS.map((option) => (
              <option key={option.value || 'all-targets'} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          When
          <select
            value={when}
            onChange={(event) => {
              setWhen(event.target.value)
              resetPage()
            }}
            className={fieldClass}
          >
            {WHEN_OPTIONS.map((option) => (
              <option key={option.value || 'any-time'} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-[var(--color-line)] bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-[var(--color-panel)] text-[var(--color-ink)]/70">
            <tr>
              <th className="px-4 py-3 font-medium">When</th>
              <th className="px-4 py-3 font-medium">Who</th>
              <th className="px-4 py-3 font-medium">Action</th>
              <th className="px-4 py-3 font-medium">Target</th>
              <th className="px-4 py-3 font-medium">Summary</th>
            </tr>
          </thead>
          <tbody>
            {auditQuery.isLoading && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-[var(--color-ink)]/60">
                  Loading audit log…
                </td>
              </tr>
            )}
            {auditQuery.isError && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-red-700">
                  Could not load the audit log.
                </td>
              </tr>
            )}
            {auditQuery.data && rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-[var(--color-ink)]/60">
                  No audit entries match these filters.
                </td>
              </tr>
            )}
            {rows.map((entry) => {
              const open = openId === entry.id
              const summary = auditSummary(entry.detail)
              const target =
                entry.target_type === 'school' && entry.target_id ? (
                  <Link to={`/schools/${entry.target_id}`} className="text-[var(--color-accent)]">
                    {entry.target_label || 'School'}
                  </Link>
                ) : (
                  entry.target_label || entry.target_id || '—'
                )
              return (
                <tr key={entry.id} className="border-t border-[var(--color-line)] align-top">
                  <td className="px-4 py-3 whitespace-nowrap">{formatDateTime(entry.created_at)}</td>
                  <td className="px-4 py-3">
                    <span className="block">{entry.actor_name || 'System'}</span>
                    {entry.actor_email && (
                      <span className="block text-xs text-[var(--color-ink)]/60">{entry.actor_email}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => setOpenId(open ? null : entry.id)}
                      className="text-left font-medium"
                      aria-expanded={open}
                    >
                      {actionLabel(entry.action)}
                    </button>
                    {open && (
                      <div className="mt-2 space-y-1 text-xs text-[var(--color-ink)]/75">
                        <p>{entry.action}</p>
                        {entry.ip_address && <p>IP {entry.ip_address}</p>}
                        {detailRows(entry.detail).map((row) => (
                          <p key={row.key}>
                            <span className="capitalize">{row.key}:</span> {row.value}
                          </p>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">{target}</td>
                  <td className="px-4 py-3 text-[var(--color-ink)]/80">{summary || '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {auditQuery.data && auditQuery.data.count > rows.length && (
        <div className="mt-3 flex items-center justify-between gap-3 text-sm text-[var(--color-ink)]/70">
          <p>
            Showing {rows.length} of {auditQuery.data.count}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!auditQuery.data.previous}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              className="rounded-lg border border-[var(--color-line)] bg-white px-3 py-1.5 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={!auditQuery.data.next}
              onClick={() => setPage((current) => current + 1)}
              className="rounded-lg border border-[var(--color-line)] bg-white px-3 py-1.5 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
