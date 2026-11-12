import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import InviteAdminModal, { type InviteAdminPayload } from './InviteAdminModal'
import SchoolBillingPanel from './SchoolBillingPanel'
import CurriculumAdoptionPanel from './CurriculumAdoptionPanel'
import StatusChangeDialog from './StatusChangeDialog'
import {
  getSchool,
  inviteSchoolAdmin,
  listSchoolAudit,
  resendSchoolAdminInvite,
  updateSchoolStatus,
} from './services'
import { StatusBadge } from '@/features/billing/StatusBadge'
import { statusSurfaceClass } from '@/features/billing/statusTone'
import { useMessagesAccess } from '@/features/messages/permissions'
import { formatDateTime } from '@/lib/dates'
import type { PlatformSchoolAuditEntry, SchoolStatus } from './types'

const ACTION_LABELS: Record<string, string> = {
  'platform.school.created': 'School created',
  'platform.school.updated': 'School updated',
  'platform.school.status_changed': 'Status changed',
  'platform.school.invite_sent': 'Admin invite sent',
  'platform.school.invite_resent': 'Admin invite resent',
  'platform.school.invite_accepted': 'Admin invite accepted',
  'billing.subscription.started': 'Subscription started',
  'billing.subscription.change_scheduled': 'Plan change scheduled',
  'billing.subscription.capacity_upgrade': 'Plan upgraded',
  'billing.topup.recorded_paid': 'Credits added',
  'billing.payment.verified': 'Payment verified',
  'billing.dunning.grace_extended': 'Grace period extended',
}

function displayReason(reason: string) {
  if (reason === 'admin_invite_accepted') return 'Admin accepted their invite'
  return reason
}

function actionLabel(action: string) {
  return ACTION_LABELS[action] ?? action.replaceAll('.', ' ').replaceAll('_', ' ')
}

function auditSummary(entry: PlatformSchoolAuditEntry) {
  const detail = entry.detail ?? {}
  if (entry.action === 'billing.subscription.capacity_upgrade') {
    const amount = typeof detail.amount_ghs === 'string' ? detail.amount_ghs : ''
    const paid = detail.recorded_as_paid ? ` · GH₵ ${amount} recorded as paid` : ''
    return `${detail.old_plan ?? ''} → ${detail.new_plan ?? ''}${paid}`
  }
  if (entry.action === 'billing.payment.verified') {
    const reference = typeof detail.reference === 'string' ? detail.reference : ''
    const outcome = typeof detail.outcome === 'string' ? detail.outcome : ''
    if (outcome === 'success') return `${reference} · Paystack confirmed`
    return `${reference} · Paystack says ${outcome || 'unconfirmed'}`
  }
  if (entry.action === 'billing.topup.recorded_paid') {
    return `${detail.package_name} · +${detail.credits} ${detail.channel} · GH₵ ${detail.amount_ghs} recorded as paid`
  }
  if (typeof detail.pending_plan === 'string' || typeof detail.pending_interval === 'string') {
    const parts = [detail.pending_plan, detail.pending_interval].filter(
      (part): part is string => typeof part === 'string' && part.length > 0,
    )
    return parts.length > 0 ? `Next renewal · ${parts.join(' · ')}` : ''
  }
  const reason = typeof detail.reason === 'string' ? displayReason(detail.reason) : ''
  const from = typeof detail.from === 'string' ? detail.from : ''
  const to = typeof detail.to === 'string' ? detail.to : ''
  const titled = (value: string) => value.charAt(0).toUpperCase() + value.slice(1)
  if (from && to) {
    return `${titled(from)} → ${titled(to)}${reason ? `. ${reason}` : ''}`
  }
  if (reason) return reason
  if (Array.isArray(detail.fields) && detail.fields.length > 0) {
    return `Updated ${detail.fields.join(', ')}`
  }
  if (typeof detail.plan_code === 'string' && detail.plan_code) {
    const interval = typeof detail.interval === 'string' ? detail.interval : ''
    return interval ? `${detail.plan_code} · ${interval}` : detail.plan_code
  }
  if (typeof detail.email === 'string' && detail.email) return detail.email
  return ''
}

function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string } | undefined
    return data?.detail || 'Request failed'
  }
  return 'Request failed'
}

export default function SchoolDetailPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const { can } = useMessagesAccess()
  const showMessaging = can('messages.view') && Boolean(id)
  const [showInvite, setShowInvite] = useState(false)
  const [pendingStatus, setPendingStatus] = useState<SchoolStatus | null>(null)
  const [auditOpen, setAuditOpen] = useState(false)
  const [auditPage, setAuditPage] = useState(1)

  const schoolQuery = useQuery({
    queryKey: ['platform-school', id],
    queryFn: () => getSchool(id),
    enabled: Boolean(id),
  })

  const auditQuery = useQuery({
    queryKey: ['platform-school-audit', id, auditPage],
    queryFn: () => listSchoolAudit(id, auditPage),
    enabled: Boolean(id) && auditOpen,
  })

  const statusMutation = useMutation({
    mutationFn: ({ status, reason }: { status: SchoolStatus; reason: string }) =>
      updateSchoolStatus(id, status, reason),
    onSuccess: () => {
      toast.success('Status updated')
      setPendingStatus(null)
      void queryClient.invalidateQueries({ queryKey: ['platform-school', id] })
      void queryClient.invalidateQueries({ queryKey: ['platform-schools'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-directory-summary'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-audit', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const inviteMutation = useMutation({
    mutationFn: (payload: InviteAdminPayload) => inviteSchoolAdmin(id, payload),
    onSuccess: (invite) => {
      toast.success('Invite sent')
      if (invite.accept_url) {
        toast(`Invite link: ${invite.accept_url}`, { duration: 8000 })
      }
      setShowInvite(false)
      void queryClient.invalidateQueries({ queryKey: ['platform-school', id] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-audit', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const resendMutation = useMutation({
    mutationFn: (inviteId: string) => resendSchoolAdminInvite(id, inviteId),
    onSuccess: (invite) => {
      toast.success('Invite resent')
      if (invite.accept_url) {
        toast(`Invite link: ${invite.accept_url}`, { duration: 8000 })
      }
      void queryClient.invalidateQueries({ queryKey: ['platform-school', id] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-audit', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const school = schoolQuery.data

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4">
        <Link to="/schools" className="text-sm text-[var(--color-accent)] hover:underline">
          ← Back to schools
        </Link>
        {showMessaging ? (
          <Link
            to={`/messages/schools/${id}`}
            className="text-sm font-medium text-[var(--color-accent)] hover:underline"
          >
            Messaging report
          </Link>
        ) : null}
      </div>

      {schoolQuery.isLoading && <p className="mt-6 text-sm text-[var(--color-ink)]/60">Loading…</p>}
      {schoolQuery.isError && (
        <p className="mt-6 text-sm text-red-700">Could not load this school.</p>
      )}

      {school && (
        <>
          <header className="mt-4 mb-4 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold">
                {school.name}
              </h1>
              <p className="mt-2 text-sm text-[var(--color-ink)]/70">
                {school.phone_number}
                {school.email ? ` · ${school.email}` : ''}
                {school.region ? ` · ${school.region}` : ''}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {(['active', 'pending', 'suspended', 'archived'] as SchoolStatus[]).map((status) => (
                <button
                  key={status}
                  type="button"
                  disabled={statusMutation.isPending || school.status === status}
                  onClick={() => setPendingStatus(status)}
                  className="rounded-xl border border-[var(--color-line)] bg-white px-3 py-2 text-xs font-medium capitalize disabled:opacity-50"
                >
                  Mark {status}
                </button>
              ))}
            </div>
          </header>

          <div className="mb-8 flex flex-wrap gap-3">
            <div className={`min-w-36 rounded-2xl border px-4 py-3 ${statusSurfaceClass(school.status)}`}>
              <p className="text-xs font-semibold tracking-wide uppercase opacity-70">Status</p>
              <p className="mt-1 text-xl font-semibold capitalize">{school.status}</p>
            </div>
            <div
              className={`min-w-36 rounded-2xl border px-4 py-3 ${statusSurfaceClass(
                school.setup_completed ? 'complete' : 'incomplete',
              )}`}
            >
              <p className="text-xs font-semibold tracking-wide uppercase opacity-70">Setup</p>
              <p className="mt-1 text-xl font-semibold">
                {school.setup_completed ? 'Complete' : 'Incomplete'}
              </p>
            </div>
            <div className="min-w-28 rounded-2xl border border-[var(--color-line)] bg-white px-4 py-3">
              <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">
                Staff
              </p>
              <p className="mt-1 font-[family-name:var(--font-display)] text-3xl font-semibold text-[var(--color-accent)]">
                {(school.staff_count ?? 0).toLocaleString()}
              </p>
            </div>
            <div className="min-w-28 rounded-2xl border border-[var(--color-line)] bg-white px-4 py-3">
              <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">
                Students
              </p>
              <p className="mt-1 font-[family-name:var(--font-display)] text-3xl font-semibold text-[#1d4e89]">
                {(school.student_count ?? 0).toLocaleString()}
              </p>
            </div>
          </div>
          {school.status_reason ? (
            <p className="-mt-5 mb-8 text-sm text-[var(--color-ink)]/70">
              Last status change: {displayReason(school.status_reason)}
            </p>
          ) : null}

          <CurriculumAdoptionPanel schoolId={school.id} />

          <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
                Admins
              </h2>
              <button
                type="button"
                onClick={() => setShowInvite(true)}
                className="rounded-xl bg-[var(--color-accent)] px-3 py-2 text-xs font-semibold text-white"
              >
                Invite admin
              </button>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left text-sm">
                <thead className="text-xs tracking-wide text-[var(--color-ink)]/55 uppercase">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Name</th>
                    <th className="px-3 py-2 font-semibold">Phone</th>
                    <th className="px-3 py-2 font-semibold">Email</th>
                    <th className="px-3 py-2 font-semibold">Role</th>
                  </tr>
                </thead>
                <tbody>
                  {school.admins.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-3 py-4 text-[var(--color-ink)]/60">
                        No admins yet.
                      </td>
                    </tr>
                  )}
                  {school.admins.map((admin) => (
                    <tr key={admin.membership_id} className="border-t border-[var(--color-line)]">
                      <td className="px-3 py-3 font-medium">
                        {admin.full_name || admin.phone_number}
                      </td>
                      <td className="px-3 py-3">{admin.phone_number}</td>
                      <td className="px-3 py-3">{admin.email || '—'}</td>
                      <td className="px-3 py-3 capitalize">{admin.role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-6 border-t border-[var(--color-line)] pt-4">
              <h3 className="text-sm font-semibold">Invites</h3>
              <ul className="mt-3 space-y-3 text-sm">
                {school.invites.length === 0 && (
                  <li className="text-[var(--color-ink)]/60">No invites yet.</li>
                )}
                {school.invites.map((invite) => (
                  <li
                    key={invite.id}
                    className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-line)] pt-3 first:border-t-0 first:pt-0"
                  >
                    <div>
                      <p className="font-medium">
                        {invite.first_name} {invite.last_name} · {invite.phone_number}
                      </p>
                      <p className="text-[var(--color-ink)]/60">
                        {invite.email} · <StatusBadge status={invite.status} />
                      </p>
                    </div>
                    {(invite.status === 'pending' || invite.status === 'expired') && (
                      <button
                        type="button"
                        onClick={() => resendMutation.mutate(invite.id)}
                        className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium"
                      >
                        Resend
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <SchoolBillingPanel schoolId={id} />

          <section className="mt-4 rounded-2xl border border-[var(--color-line)] bg-white/90">
            <button
              type="button"
              onClick={() => setAuditOpen((open) => !open)}
              className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
              aria-expanded={auditOpen}
            >
              <span>
                <span className="block font-[family-name:var(--font-display)] text-lg font-semibold">
                  Audit log
                </span>
                <span className="mt-0.5 block text-sm text-[var(--color-ink)]/60">
                  Status changes, invites, and billing events for this school.
                </span>
              </span>
              <span className="text-sm font-medium text-[var(--color-accent)]">
                {auditOpen ? 'Hide' : 'Show'}
              </span>
            </button>
            {auditOpen && (
              <div className="border-t border-[var(--color-line)] px-5 py-4">
                {auditQuery.isLoading && (
                  <p className="text-sm text-[var(--color-ink)]/60">Loading audit log…</p>
                )}
                {auditQuery.isError && (
                  <p className="text-sm text-red-700">Could not load the audit log.</p>
                )}
                {auditQuery.data && auditQuery.data.results.length === 0 && (
                  <p className="text-sm text-[var(--color-ink)]/60">No audit entries yet.</p>
                )}
                {auditQuery.data && auditQuery.data.results.length > 0 && (
                  <ul className="space-y-3 text-sm">
                    {auditQuery.data.results.map((entry) => {
                      const summary = auditSummary(entry)
                      return (
                        <li key={entry.id} className="border-t border-[var(--color-line)] pt-3 first:border-t-0 first:pt-0">
                          <p className="font-medium">{actionLabel(entry.action)}</p>
                          {summary ? (
                            <p className="text-[var(--color-ink)]/75">{summary}</p>
                          ) : null}
                          <p className="text-xs text-[var(--color-ink)]/55">
                            {entry.actor_name || entry.actor_email || 'System'}
                            {' · '}
                            {formatDateTime(entry.created_at)}
                          </p>
                        </li>
                      )
                    })}
                  </ul>
                )}
                {auditQuery.data && auditQuery.data.count > auditQuery.data.results.length && (
                  <div className="mt-4 flex gap-2">
                    <button
                      type="button"
                      disabled={!auditQuery.data.previous}
                      onClick={() => setAuditPage((page) => Math.max(1, page - 1))}
                      className="rounded-lg border border-[var(--color-line)] px-3 py-1.5 text-xs disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      disabled={!auditQuery.data.next}
                      onClick={() => setAuditPage((page) => page + 1)}
                      className="rounded-lg border border-[var(--color-line)] px-3 py-1.5 text-xs disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>
        </>
      )}

      {school && pendingStatus && (
        <StatusChangeDialog
          schoolName={school.name}
          status={pendingStatus}
          pending={statusMutation.isPending}
          onClose={() => {
            if (!statusMutation.isPending) setPendingStatus(null)
          }}
          onConfirm={(reason) => statusMutation.mutate({ status: pendingStatus, reason })}
        />
      )}

      {school && (
        <InviteAdminModal
          open={showInvite}
          pending={inviteMutation.isPending}
          onClose={() => {
            if (!inviteMutation.isPending) setShowInvite(false)
          }}
          onInvite={(payload) => inviteMutation.mutate(payload)}
        />
      )}

    </div>
  )
}
