import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import {
  adjustSchoolCredits,
  capacityUpgradeSchool,
  getSchoolCredits,
  getSchoolSubscription,
  listPlans,
  listSchoolInvoices,
  listSchoolPayments,
  markInvoicePaid,
  scheduleSchoolAddon,
  scheduleSchoolPlanChange,
  startSchoolSubscription,
} from '@/features/billing/services'
import {
  getSchool,
  inviteSchoolAdmin,
  resendSchoolAdminInvite,
  updateSchoolStatus,
} from './services'
import type { SchoolStatus } from './types'

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
  const [inviteForm, setInviteForm] = useState({
    first_name: '',
    last_name: '',
    phone_number: '',
    email: '',
  })
  const [intervalConfirm, setIntervalConfirm] = useState<{
    kind: 'schedule' | 'cancel'
    interval: 'monthly' | 'annual'
  } | null>(null)

  const schoolQuery = useQuery({
    queryKey: ['platform-school', id],
    queryFn: () => getSchool(id),
    enabled: Boolean(id),
  })

  const subscriptionQuery = useQuery({
    queryKey: ['platform-school-subscription', id],
    queryFn: () => getSchoolSubscription(id),
    enabled: Boolean(id),
    retry: false,
  })

  const plansQuery = useQuery({
    queryKey: ['platform-billing-plans'],
    queryFn: listPlans,
  })

  const invoicesQuery = useQuery({
    queryKey: ['platform-school-invoices', id],
    queryFn: () => listSchoolInvoices(id),
    enabled: Boolean(id),
  })

  const paymentsQuery = useQuery({
    queryKey: ['platform-school-payments', id],
    queryFn: () => listSchoolPayments(id),
    enabled: Boolean(id),
  })

  const creditsQuery = useQuery({
    queryKey: ['platform-school-credits', id],
    queryFn: () => getSchoolCredits(id),
    enabled: Boolean(id),
  })

  const statusMutation = useMutation({
    mutationFn: (status: SchoolStatus) => updateSchoolStatus(id, status),
    onSuccess: () => {
      toast.success('Status updated')
      void queryClient.invalidateQueries({ queryKey: ['platform-school', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const inviteMutation = useMutation({
    mutationFn: () => inviteSchoolAdmin(id, inviteForm),
    onSuccess: (invite) => {
      toast.success('Invite sent')
      if (invite.accept_url) {
        toast(`Invite link: ${invite.accept_url}`, { duration: 8000 })
      }
      setInviteForm({ first_name: '', last_name: '', phone_number: '', email: '' })
      void queryClient.invalidateQueries({ queryKey: ['platform-school', id] })
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
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const startSubMutation = useMutation({
    mutationFn: () => startSchoolSubscription(id, { apply_first_year_free: true }),
    onSuccess: () => {
      toast.success('Subscription started')
      void queryClient.invalidateQueries({ queryKey: ['platform-school-subscription', id] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-invoices', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const scheduleMutation = useMutation({
    mutationFn: (planCode: string) => scheduleSchoolPlanChange(id, { plan_code: planCode }),
    onSuccess: () => {
      toast.success('Plan change scheduled')
      void queryClient.invalidateQueries({ queryKey: ['platform-school-subscription', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const upgradeMutation = useMutation({
    mutationFn: (planCode: string) =>
      capacityUpgradeSchool(id, { plan_code: planCode, mark_paid: true }),
    onSuccess: () => {
      toast.success('Capacity upgraded')
      void queryClient.invalidateQueries({ queryKey: ['platform-school-subscription', id] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-invoices', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const addonMutation = useMutation({
    mutationFn: (payload: { channel: 'sms' | 'email'; enabled: boolean }) =>
      scheduleSchoolAddon(id, payload),
    onSuccess: () => {
      toast.success('Add-on change scheduled')
      void queryClient.invalidateQueries({ queryKey: ['platform-school-subscription', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const creditAdjustMutation = useMutation({
    mutationFn: (payload: { channel: 'sms' | 'email'; delta: number }) =>
      adjustSchoolCredits(id, { ...payload, reason: 'platform_manual_adjust' }),
    onSuccess: () => {
      toast.success('Credits adjusted')
      void queryClient.invalidateQueries({ queryKey: ['platform-school-credits', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const markPaidMutation = useMutation({
    mutationFn: (invoiceId: string) => markInvoicePaid(invoiceId),
    onSuccess: () => {
      toast.success('Invoice marked paid')
      void queryClient.invalidateQueries({ queryKey: ['platform-school-invoices', id] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-subscription', id] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-credits', id] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const intervalMutation = useMutation({
    mutationFn: (interval: 'monthly' | 'annual') =>
      scheduleSchoolPlanChange(id, { interval }),
    onSuccess: (data) => {
      toast.success(
        data.pending_interval
          ? 'Interval change scheduled for next renewal'
          : 'Scheduled interval change cancelled',
      )
      setIntervalConfirm(null)
      void queryClient.invalidateQueries({ queryKey: ['platform-school-subscription', id] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  function onInvite(event: FormEvent) {
    event.preventDefault()
    inviteMutation.mutate()
  }

  const school = schoolQuery.data
  const subscription = subscriptionQuery.data

  return (
    <div>
      <Link to="/schools" className="text-sm text-[var(--color-accent)] hover:underline">
        ← Back to schools
      </Link>

      {schoolQuery.isLoading && <p className="mt-6 text-sm text-[var(--color-ink)]/60">Loading…</p>}
      {schoolQuery.isError && (
        <p className="mt-6 text-sm text-red-700">Could not load this school.</p>
      )}

      {school && (
        <>
          <header className="mt-4 mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold">
                {school.name}
              </h1>
              <p className="mt-2 text-sm text-[var(--color-ink)]/70">
                {school.phone_number}
                {school.email ? ` · ${school.email}` : ''}
                {school.region ? ` · ${school.region}` : ''}
              </p>
              <p className="mt-1 text-sm capitalize">
                Status: <strong>{school.status}</strong>
                {school.setup_completed ? ' · Setup complete' : ' · Setup incomplete'}
                {typeof school.staff_count === 'number' ? ` · Staff ${school.staff_count}` : ''}
                {typeof school.student_count === 'number'
                  ? ` · Students ${school.student_count}`
                  : ''}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {(['active', 'pending', 'suspended', 'archived'] as SchoolStatus[]).map((status) => (
                <button
                  key={status}
                  type="button"
                  disabled={statusMutation.isPending || school.status === status}
                  onClick={() => statusMutation.mutate(status)}
                  className="rounded-xl border border-[var(--color-line)] bg-white px-3 py-2 text-xs font-medium capitalize disabled:opacity-50"
                >
                  Mark {status}
                </button>
              ))}
            </div>
          </header>

          <div className="grid gap-4 md:grid-cols-2">
            <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
              <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
                Admins
              </h2>
              <ul className="mt-3 space-y-2 text-sm">
                {school.admins.length === 0 && (
                  <li className="text-[var(--color-ink)]/60">No admins yet.</li>
                )}
                {school.admins.map((admin) => (
                  <li key={admin.membership_id}>
                    <span className="font-medium">{admin.full_name || admin.phone_number}</span>
                    <span className="text-[var(--color-ink)]/60"> · {admin.phone_number}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
              <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
                Invite admin
              </h2>
              <form onSubmit={onInvite} className="mt-3 space-y-3">
                {(
                  [
                    ['first_name', 'First name'],
                    ['last_name', 'Last name'],
                    ['phone_number', 'Phone'],
                    ['email', 'Email'],
                  ] as const
                ).map(([key, label]) => (
                  <label key={key} className="block text-sm">
                    <span className="mb-1 block font-medium">{label}</span>
                    <input
                      required={key !== 'last_name'}
                      value={inviteForm[key]}
                      onChange={(e) =>
                        setInviteForm((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
                    />
                  </label>
                ))}
                <button
                  type="submit"
                  disabled={inviteMutation.isPending}
                  className="rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {inviteMutation.isPending ? 'Sending…' : 'Send invite'}
                </button>
              </form>
            </section>
          </div>

          <section className="mt-4 rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
                  Subscription
                </h2>
                <p className="mt-1 text-sm text-[var(--color-ink)]/70">
                  Application plan, capacity, and renewal.
                </p>
              </div>
              {!subscription && !subscriptionQuery.isLoading && (
                <button
                  type="button"
                  onClick={() => startSubMutation.mutate()}
                  disabled={startSubMutation.isPending}
                  className="rounded-xl bg-[var(--color-accent)] px-3 py-2 text-xs font-semibold text-white disabled:opacity-60"
                >
                  Start first-year free
                </button>
              )}
            </div>

            {subscriptionQuery.isLoading && (
              <p className="mt-3 text-sm text-[var(--color-ink)]/60">Loading subscription…</p>
            )}
            {subscriptionQuery.isError && !subscription && (
              <p className="mt-3 text-sm text-[var(--color-ink)]/60">
                No current subscription for this school.
              </p>
            )}
            {subscription && (
              <div className="mt-4 space-y-3 text-sm">
                <p>
                  <strong>{subscription.plan.name}</strong> · {subscription.interval} ·{' '}
                  <span className="capitalize">{subscription.status}</span>
                  {subscription.billing_suspended_school ? ' · school locked by billing' : ''}
                </p>
                <div className="text-[var(--color-ink)]/80">
                  {(subscription.discounts ?? []).length === 0 ? (
                    <p>No discount is currently reducing this school's invoices.</p>
                  ) : (
                    <ul className="space-y-1">
                      {(subscription.discounts ?? []).map((discount) => (
                        <li key={discount.id}>
                          <strong>{discount.name}</strong> · {Number(discount.discount_percent)}% off
                          {discount.schedule === 'recurring'
                            ? ' · every invoice'
                            : discount.ends_at
                              ? ` · until ${new Date(discount.ends_at).toLocaleDateString('en-GB')}`
                              : ''}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <p className="text-[var(--color-ink)]/70">
                  Students {subscription.capacity.active_students}
                  {subscription.capacity.capacity_max != null
                    ? ` / ${subscription.capacity.capacity_max}`
                    : ' (open)'}
                  {' · '}Staff {subscription.capacity.active_staff}
                  {subscription.capacity.staff_capacity_max != null
                    ? ` / ${subscription.capacity.staff_capacity_max}`
                    : ' (open)'}
                  {' · '}Renews{' '}
                  {new Date(subscription.current_period_end).toLocaleDateString('en-GB')}
                </p>
                {subscription.grace_period_ends_at && (
                  <p className="text-amber-800">
                    Grace ends{' '}
                    {new Date(subscription.grace_period_ends_at).toLocaleDateString('en-GB')}
                  </p>
                )}
                <div className="flex flex-wrap gap-2 pt-1">
                  {subscription.pending_interval &&
                  subscription.pending_interval !== subscription.interval ? (
                    <button
                      type="button"
                      onClick={() =>
                        setIntervalConfirm({
                          kind: 'cancel',
                          interval: subscription.interval,
                        })
                      }
                      disabled={intervalMutation.isPending}
                      className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                    >
                      Cancel scheduled {subscription.pending_interval}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() =>
                        setIntervalConfirm({
                          kind: 'schedule',
                          interval:
                            subscription.interval === 'annual' ? 'monthly' : 'annual',
                        })
                      }
                      disabled={intervalMutation.isPending}
                      className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                    >
                      Schedule{' '}
                      {subscription.interval === 'annual' ? 'monthly' : 'annual'} at renewal
                    </button>
                  )}
                </div>
                {(subscription.pending_plan || subscription.pending_interval) && (
                  <p className="text-amber-800">
                    Pending:
                    {subscription.pending_plan ? ` ${subscription.pending_plan.name}` : ''}
                    {subscription.pending_interval
                      ? ` ${subscription.pending_interval}`
                      : ''}{' '}
                    on{' '}
                    {subscription.pending_change_effective_at
                      ? new Date(subscription.pending_change_effective_at).toLocaleDateString(
                          'en-GB',
                        )
                      : 'next period'}
                  </p>
                )}
                <p className="text-[var(--color-ink)]/70">
                  SMS add-on: {subscription.sms_addon_enabled ? 'on' : 'off'}
                  {' · '}Email add-on: {subscription.email_addon_enabled ? 'on' : 'off'}
                </p>
                <div className="flex flex-wrap gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() =>
                      addonMutation.mutate({
                        channel: 'sms',
                        enabled: !subscription.sms_addon_enabled,
                      })
                    }
                    disabled={addonMutation.isPending}
                    className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                  >
                    {subscription.sms_addon_enabled ? 'Schedule SMS off' : 'Schedule SMS on'}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      addonMutation.mutate({
                        channel: 'email',
                        enabled: !subscription.email_addon_enabled,
                      })
                    }
                    disabled={addonMutation.isPending}
                    className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                  >
                    {subscription.email_addon_enabled
                      ? 'Schedule email off'
                      : 'Schedule email on'}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {(plansQuery.data ?? [])
                    .filter((plan) => plan.code !== subscription.plan.code)
                    .map((plan) => (
                      <div key={plan.id} className="flex gap-1">
                        <button
                          type="button"
                          onClick={() => scheduleMutation.mutate(plan.code)}
                          disabled={scheduleMutation.isPending}
                          className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                        >
                          Schedule {plan.name}
                        </button>
                        {plan.sort_order > subscription.plan.sort_order && (
                          <button
                            type="button"
                            onClick={() => upgradeMutation.mutate(plan.code)}
                            disabled={upgradeMutation.isPending}
                            className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                          >
                            Upgrade now
                          </button>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            )}

            <div className="mt-5 border-t border-[var(--color-line)] pt-4">
              <h3 className="text-sm font-semibold">Messaging credits</h3>
              <p className="mt-1 text-sm text-[var(--color-ink)]/70">
                SMS {creditsQuery.data?.sms ?? 0} · Email {creditsQuery.data?.email ?? 0}
                {' · credits metered'}
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => creditAdjustMutation.mutate({ channel: 'sms', delta: 100 })}
                  disabled={creditAdjustMutation.isPending}
                  className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                >
                  +100 SMS
                </button>
                <button
                  type="button"
                  onClick={() => creditAdjustMutation.mutate({ channel: 'email', delta: 100 })}
                  disabled={creditAdjustMutation.isPending}
                  className="rounded-xl border border-[var(--color-line)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                >
                  +100 email
                </button>
              </div>
            </div>

            <div className="mt-5 border-t border-[var(--color-line)] pt-4">
              <h3 className="text-sm font-semibold">Invoices</h3>
              <ul className="mt-2 space-y-2 text-sm">
                {(invoicesQuery.data?.results ?? []).length === 0 && (
                  <li className="text-[var(--color-ink)]/60">No invoices yet.</li>
                )}
                {(invoicesQuery.data?.results ?? []).map((invoice) => (
                  <li key={invoice.id} className="flex flex-wrap items-center justify-between gap-3">
                    <span>
                      GH₵ {invoice.total_ghs} · {invoice.status}
                      {invoice.notes ? ` · ${invoice.notes}` : ''}
                    </span>
                    <span className="flex items-center gap-2 text-[var(--color-ink)]/60">
                      {new Date(invoice.created_at).toLocaleDateString('en-GB')}
                      {invoice.status === 'open' && Number(invoice.total_ghs) > 0 && (
                        <button
                          type="button"
                          onClick={() => markPaidMutation.mutate(invoice.id)}
                          disabled={markPaidMutation.isPending}
                          className="rounded-lg border border-[var(--color-line)] px-2 py-1 text-xs font-medium text-[var(--color-ink)] disabled:opacity-50"
                        >
                          Mark paid
                        </button>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-5 border-t border-[var(--color-line)] pt-4">
              <h3 className="text-sm font-semibold">Payments</h3>
              <ul className="mt-2 space-y-2 text-sm">
                {(paymentsQuery.data?.results ?? []).length === 0 && (
                  <li className="text-[var(--color-ink)]/60">No Paystack payments yet.</li>
                )}
                {(paymentsQuery.data?.results ?? []).map((payment) => (
                  <li key={payment.id} className="flex justify-between gap-3">
                    <span>
                      GH₵ {payment.amount_ghs} · {payment.purpose} · {payment.status}
                    </span>
                    <span className="font-mono text-xs text-[var(--color-ink)]/60">
                      {payment.reference}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="mt-4 rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
              Invites
            </h2>
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
                      {invite.email} · <span className="capitalize">{invite.status}</span>
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
          </section>
        </>
      )}

      {intervalConfirm && subscription && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg">
            <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold">
              {intervalConfirm.kind === 'cancel'
                ? 'Cancel scheduled interval change?'
                : 'Schedule billing interval change?'}
            </h3>
            <p className="mt-3 text-sm text-[var(--color-ink)]/70">
              {intervalConfirm.kind === 'cancel'
                ? `This cancels the pending switch. The school stays on ${subscription.interval} billing through the next renewal (${new Date(subscription.current_period_end).toLocaleDateString('en-GB')}).`
                : `Schedule a switch from ${subscription.interval} to ${intervalConfirm.interval}. Nothing changes today — the new interval starts at the next renewal on ${new Date(subscription.current_period_end).toLocaleDateString('en-GB')}.`}
            </p>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <button
                type="button"
                className="rounded-xl border border-[var(--color-line)] px-3 py-2 text-sm font-medium disabled:opacity-50"
                disabled={intervalMutation.isPending}
                onClick={() => setIntervalConfirm(null)}
              >
                Back
              </button>
              <button
                type="button"
                className="rounded-xl bg-[var(--color-accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                disabled={intervalMutation.isPending}
                onClick={() => intervalMutation.mutate(intervalConfirm.interval)}
              >
                {intervalConfirm.kind === 'cancel' ? 'Cancel schedule' : 'Confirm schedule'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
