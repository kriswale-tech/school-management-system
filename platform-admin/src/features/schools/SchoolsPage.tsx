import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import CreateSchoolModal from './CreateSchoolModal'
import { createSchool, fetchSchoolSummary, listSchools, updateSchoolStatus } from './services'
import type { PlatformSchoolListItem, SchoolStatus } from './types'

function errorMessage(error: unknown) {
  if (!isAxiosError(error)) return 'Request failed'
  const data = error.response?.data
  if (!data || typeof data !== 'object') return 'Request failed'
  if ('detail' in data && typeof data.detail === 'string' && data.detail) return data.detail
  for (const value of Object.values(data as Record<string, unknown>)) {
    if (typeof value === 'string' && value) return value
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  }
  return 'Request failed'
}

const STATUS_OPTIONS: Array<SchoolStatus | ''> = [
  '',
  'pending',
  'active',
  'suspended',
  'archived',
]

const STATUS_ACTIONS: SchoolStatus[] = ['active', 'pending', 'suspended', 'archived']

function statusActionLabel(status: SchoolStatus) {
  if (status === 'active') return 'Activate'
  if (status === 'pending') return 'Mark pending'
  if (status === 'suspended') return 'Suspend'
  return 'Archive'
}

function formatRenewal(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function formatCount(value: number | undefined) {
  if (value === undefined) return '—'
  return value.toLocaleString()
}

export default function SchoolsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<SchoolStatus | ''>('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const [pendingStatus, setPendingStatus] = useState<{
    school: PlatformSchoolListItem
    status: SchoolStatus
  } | null>(null)

  const schoolsQuery = useQuery({
    queryKey: ['platform-schools', status, search, page],
    queryFn: () =>
      listSchools({
        status: status || undefined,
        search: search || undefined,
        page,
        page_size: 100,
      }),
  })

  const summaryQuery = useQuery({
    queryKey: ['platform-school-directory-summary'],
    queryFn: fetchSchoolSummary,
  })

  const createMutation = useMutation({
    mutationFn: createSchool,
    onSuccess: (school) => {
      toast.success('School created')
      setShowCreate(false)
      void queryClient.invalidateQueries({ queryKey: ['platform-schools'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-directory-summary'] })
      navigate(`/schools/${school.id}`)
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status: next }: { id: string; status: SchoolStatus }) =>
      updateSchoolStatus(id, next),
    onSuccess: () => {
      toast.success('School status updated')
      setPendingStatus(null)
      void queryClient.invalidateQueries({ queryKey: ['platform-schools'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-directory-summary'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  function requestStatus(school: PlatformSchoolListItem, next: SchoolStatus) {
    if (next === school.status) return
    if (next === 'suspended' || next === 'archived') {
      setPendingStatus({ school, status: next })
      return
    }
    statusMutation.mutate({ id: school.id, status: next })
  }

  const summary = summaryQuery.data
  const summaryCards = [
    { label: 'Schools', value: summary?.school_count },
    { label: 'Active', value: summary?.active_school_count },
    { label: 'Students', value: summary?.student_count },
    { label: 'Staff', value: summary?.staff_count },
    { label: 'Overdue', value: summary?.overdue_school_count },
  ]

  return (
    <div>
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.18em] text-[var(--color-accent)] uppercase">
            Schools
          </p>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold">
            School directory
          </h1>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          className="rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-sm font-semibold text-white"
        >
          Create school
        </button>
      </header>

      <section className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {summaryCards.map((card) => (
          <div
            key={card.label}
            className="rounded-2xl border border-[var(--color-line)] bg-white/90 px-4 py-3"
          >
            <p className="text-xs font-medium tracking-wide text-[var(--color-ink)]/60 uppercase">
              {card.label}
            </p>
            <p
              className={`mt-1 text-2xl font-semibold ${
                card.label === 'Overdue' && (card.value ?? 0) > 0 ? 'text-red-700' : ''
              }`}
            >
              {summaryQuery.isLoading ? '…' : formatCount(card.value)}
            </p>
          </div>
        ))}
      </section>

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          placeholder="Search schools"
          className="min-w-[220px] flex-1 rounded-xl border border-[var(--color-line)] bg-white px-3 py-2 text-sm"
        />
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as SchoolStatus | '')
            setPage(1)
          }}
          className="rounded-xl border border-[var(--color-line)] bg-white px-3 py-2 text-sm"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option || 'all'} value={option}>
              {option ? option : 'All statuses'}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-[var(--color-line)] bg-white/90">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="border-b border-[var(--color-line)] bg-[var(--color-panel)] text-[var(--color-ink)]/70">
            <tr>
              <th className="px-4 py-3 font-medium">School</th>
              <th className="px-4 py-3 font-medium">Admin</th>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium">Renewal</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Payment</th>
              <th
                className="px-4 py-3 font-medium"
                title="Active school accounts: admins, teachers, accountants, staff"
              >
                Staff
              </th>
              <th className="px-4 py-3 font-medium" title="Active student records">
                Students
              </th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {schoolsQuery.isLoading && (
              <tr>
                <td colSpan={9} className="px-4 py-6 text-[var(--color-ink)]/60">
                  Loading…
                </td>
              </tr>
            )}
            {schoolsQuery.data?.results.map((school) => {
              const admin = school.admins[0]
              return (
                <tr key={school.id} className="border-t border-[var(--color-line)] align-top">
                  <td className="px-4 py-3">
                    <Link
                      to={`/schools/${school.id}`}
                      className="font-semibold text-[var(--color-accent)] hover:underline"
                    >
                      {school.name}
                    </Link>
                    <p className="text-xs text-[var(--color-ink)]/60">{school.region || '—'}</p>
                  </td>
                  <td className="px-4 py-3">
                    {admin ? (
                      <>
                        <p className="font-medium">{admin.full_name || admin.phone_number}</p>
                        <p className="text-xs text-[var(--color-ink)]/60">{admin.phone_number}</p>
                        {admin.email ? (
                          <p className="text-xs text-[var(--color-ink)]/60">{admin.email}</p>
                        ) : null}
                        {school.admins.length > 1 ? (
                          <p className="text-xs text-[var(--color-ink)]/60">
                            +{school.admins.length - 1} more
                          </p>
                        ) : null}
                      </>
                    ) : (
                      <span className="text-[var(--color-ink)]/50">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {school.plan_name || school.plan_code ? (
                      <>
                        <p>{school.plan_name || school.plan_code}</p>
                        {school.subscription_interval ? (
                          <p className="text-xs text-[var(--color-ink)]/60 capitalize">
                            {school.subscription_interval}
                          </p>
                        ) : null}
                      </>
                    ) : (
                      <span className="text-[var(--color-ink)]/50">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {formatRenewal(school.next_renewal_at)}
                  </td>
                  <td className="px-4 py-3 capitalize">{school.status}</td>
                  <td className="px-4 py-3">
                    {school.payment_overdue ? (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">
                        Overdue
                      </span>
                    ) : school.subscription_status === 'active' ? (
                      <span className="text-[var(--color-ink)]/70">Current</span>
                    ) : (
                      <span className="text-[var(--color-ink)]/50">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">{school.staff_count}</td>
                  <td className="px-4 py-3">{school.student_count}</td>
                  <td className="px-4 py-3">
                    <select
                      aria-label={`Actions for ${school.name}`}
                      value=""
                      disabled={statusMutation.isPending}
                      onChange={(event) => {
                        const next = event.target.value as SchoolStatus
                        if (!next) return
                        requestStatus(school, next)
                      }}
                      className="rounded-lg border border-[var(--color-line)] bg-white px-2 py-1.5 text-xs"
                    >
                      <option value="">Actions</option>
                      {STATUS_ACTIONS.filter((option) => option !== school.status).map((option) => (
                        <option key={option} value={option}>
                          {statusActionLabel(option)}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              )
            })}
            {schoolsQuery.data && schoolsQuery.data.results.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-6 text-[var(--color-ink)]/60">
                  No schools found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {schoolsQuery.data && schoolsQuery.data.count > schoolsQuery.data.results.length && (
        <div className="mt-3 flex items-center justify-between gap-3 text-sm text-[var(--color-ink)]/70">
          <p>
            Showing {schoolsQuery.data.results.length} of {schoolsQuery.data.count}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!schoolsQuery.data.previous}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              className="rounded-lg border border-[var(--color-line)] bg-white px-3 py-1.5 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={!schoolsQuery.data.next}
              onClick={() => setPage((current) => current + 1)}
              className="rounded-lg border border-[var(--color-line)] bg-white px-3 py-1.5 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}

      <CreateSchoolModal
        open={showCreate}
        pending={createMutation.isPending}
        onClose={() => setShowCreate(false)}
        onCreate={(payload) => createMutation.mutate(payload)}
      />

      {pendingStatus && (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/30 px-4">
          <div className="w-full max-w-md rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
              {pendingStatus.status === 'archived' ? 'Archive' : 'Suspend'}{' '}
              {pendingStatus.school.name}?
            </h2>
            <p className="mt-2 text-sm text-[var(--color-ink)]/70">
              {pendingStatus.status === 'archived'
                ? 'The school stays in the directory and can be activated again later.'
                : 'The school loses access until it is activated again.'}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPendingStatus(null)}
                className="rounded-xl border border-[var(--color-line)] px-3 py-2 text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={statusMutation.isPending}
                onClick={() =>
                  statusMutation.mutate({
                    id: pendingStatus.school.id,
                    status: pendingStatus.status,
                  })
                }
                className="rounded-xl bg-[var(--color-accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {statusMutation.isPending
                  ? 'Saving…'
                  : statusActionLabel(pendingStatus.status)}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
