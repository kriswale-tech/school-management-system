import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Icon } from '@iconify/react'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import { Pagination, TabComponent } from '@/components/shared'
import { Button, Modal } from '@/components/ui'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks/useCan'
import {
  getTopUpPackages,
  purchaseTopUp,
  verifySaasPayment,
} from '@/features/billing/services'
import type { TopUpPackage } from '@/features/billing/types'
import ParentMessagesPolicies from '../components/ParentMessagesPolicies'
import {
  getMessagingDeliveries,
  getMessagingOverview,
  retryMessagingDelivery,
  verifyMessagingDelivery,
} from '../services'
import type { DeliveryStatus, GuardianDelivery } from '../types'

function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string } | undefined
    return data?.detail || 'Request failed'
  }
  return 'Request failed'
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatGhs(value: string | number | null | undefined) {
  const amount = Number(value ?? 0)
  return `GH₵ ${amount.toLocaleString('en-GH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function redirectToPaystack(authorizationUrl: string) {
  window.location.assign(authorizationUrl)
}

function titleCaseEventType(value: string) {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

const EVENT_TYPE_OPTIONS = [
  { value: 'ward_enrolled', label: 'Ward Enrolled' },
  { value: 'payment_receipt', label: 'Payment Receipt' },
  { value: 'debt_reminder', label: 'Debt Reminder' },
  { value: 'report_ready', label: 'Report Ready' },
  { value: 'next_term_fees', label: 'Next Term Fees' },
] as const

const EVENT_TYPE_BADGE: Record<string, string> = {
  ward_enrolled: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  payment_receipt: 'bg-sky-50 text-sky-800 ring-sky-200',
  debt_reminder: 'bg-amber-50 text-amber-900 ring-amber-200',
  report_ready: 'bg-indigo-50 text-indigo-800 ring-indigo-200',
  next_term_fees: 'bg-violet-50 text-violet-800 ring-violet-200',
}

const STATUS_BADGE: Record<DeliveryStatus, string> = {
  queued: 'bg-slate-100 text-slate-700 ring-slate-200',
  processing: 'bg-sky-50 text-sky-800 ring-sky-200',
  submitted: 'bg-indigo-50 text-indigo-800 ring-indigo-200',
  delivered: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  failed: 'bg-red-50 text-red-800 ring-red-200',
  unknown: 'bg-amber-50 text-amber-900 ring-amber-200',
  skipped: 'bg-slate-100 text-slate-600 ring-slate-200',
  sent: 'bg-indigo-50 text-indigo-800 ring-indigo-200',
}

const STATUS_FILTER_OPTIONS: { value: DeliveryStatus | ''; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: 'queued', label: 'Queued' },
  { value: 'processing', label: 'Processing' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'failed', label: 'Failed' },
  { value: 'unknown', label: 'Unknown' },
  { value: 'skipped', label: 'Skipped' },
]

const CHANNEL_BADGE: Record<GuardianDelivery['channel'], string> = {
  sms: 'bg-teal-50 text-teal-800 ring-teal-200',
  email: 'bg-blue-50 text-blue-800 ring-blue-200',
}

const CHANNEL_ICON: Record<GuardianDelivery['channel'], string> = {
  sms: 'hugeicons:smart-phone-01',
  email: 'hugeicons:mail-01',
}

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'history', label: 'History' },
  { key: 'messages', label: 'Messages' },
] as const

type TabKey = (typeof TABS)[number]['key']

const TAB_KEYS = new Set<string>(TABS.map((item) => item.key))

function parseTab(value: string | null): TabKey {
  // Legacy bookmark support from the old Policies tab.
  if (value === 'policies') return 'messages'
  if (value && TAB_KEYS.has(value)) return value as TabKey
  return 'overview'
}

function parsePage(value: string | null): number {
  const n = Number(value)
  return Number.isFinite(n) && n >= 1 ? Math.floor(n) : 1
}

type MessagingPageProps = {
  embedded?: boolean
}

const MessagingPage = ({ embedded = false }: MessagingPageProps) => {
  const queryClient = useQueryClient()
  const canManageMessaging = useCan(Capability.MESSAGING_MANAGE)
  const canManageBilling = useCan(Capability.BILLING_MANAGE)
  const [searchParams, setSearchParams] = useSearchParams()
  const [resendTarget, setResendTarget] = useState<GuardianDelivery | null>(null)

  const tab = parseTab(searchParams.get('view'))
  const channel = searchParams.get('channel') || ''
  const statusFilter = searchParams.get('status') || ''
  const eventTypeFilter = searchParams.get('type') || ''
  const search = searchParams.get('q') || ''
  const page = parsePage(searchParams.get('page'))

  useEffect(() => {
    if (searchParams.get('view') !== 'policies') return
    const next = new URLSearchParams(searchParams)
    next.set('view', 'messages')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const patchParams = (updates: Record<string, string | null>, replace = false) => {
    const next = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(updates)) {
      if (value == null || value === '') next.delete(key)
      else next.set(key, value)
    }
    setSearchParams(next, { replace })
  }

  const setTab = (nextTab: TabKey) => {
    const next = new URLSearchParams(searchParams)
    if (nextTab === 'overview') next.delete('view')
    else next.set('view', nextTab)
    if (nextTab !== 'history') {
      next.delete('channel')
      next.delete('status')
      next.delete('type')
      next.delete('q')
      next.delete('page')
    }
    setSearchParams(next, { replace: true })
  }

  const overviewQuery = useQuery({
    queryKey: ['messaging-overview'],
    queryFn: getMessagingOverview,
  })

  const topupsQuery = useQuery({
    queryKey: ['billing-topups'],
    queryFn: () => getTopUpPackages(),
    enabled: tab === 'overview' && canManageBilling,
  })

  const deliveriesQuery = useQuery({
    queryKey: [
      'messaging-deliveries',
      channel,
      statusFilter,
      eventTypeFilter,
      search,
      page,
    ],
    queryFn: () =>
      getMessagingDeliveries({
        channel: channel || undefined,
        status: statusFilter || undefined,
        event_type: eventTypeFilter || undefined,
        search: search || undefined,
        page,
      }),
    enabled: tab === 'history',
  })

  const invalidateAfterTopup = () => {
    void queryClient.invalidateQueries({ queryKey: ['messaging-overview'] })
    void queryClient.invalidateQueries({ queryKey: ['billing-upcoming'] })
    void queryClient.invalidateQueries({ queryKey: ['billing-invoices'] })
    void queryClient.invalidateQueries({ queryKey: ['billing-payments'] })
    void queryClient.invalidateQueries({ queryKey: ['communication-credits'] })
  }

  const paymentReference = searchParams.get('reference')
  const paymentReturn = searchParams.get('payment')

  useEffect(() => {
    if (!paymentReference || paymentReturn !== 'return') return
    let cancelled = false
    ;(async () => {
      try {
        await verifySaasPayment(paymentReference)
        if (!cancelled) {
          toast.success('Payment confirmed')
          invalidateAfterTopup()
        }
      } catch (error) {
        if (!cancelled) toast.error(errorMessage(error))
      } finally {
        if (!cancelled) {
          const next = new URLSearchParams(searchParams)
          next.delete('reference')
          next.delete('payment')
          next.delete('trxref')
          setSearchParams(next, { replace: true })
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [paymentReference, paymentReturn])

  const retryMutation = useMutation({
    mutationFn: retryMessagingDelivery,
    onSuccess: () => {
      toast.success('Resend queued')
      setResendTarget(null)
      const next = new URLSearchParams(searchParams)
      next.set('view', 'history')
      next.delete('status')
      next.delete('page')
      setSearchParams(next, { replace: true })
      void queryClient.invalidateQueries({ queryKey: ['messaging-deliveries'] })
      void queryClient.invalidateQueries({ queryKey: ['messaging-overview'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const verifyMutation = useMutation({
    mutationFn: verifyMessagingDelivery,
    onSuccess: (data) => {
      void queryClient.invalidateQueries({ queryKey: ['messaging-deliveries'] })
      void queryClient.invalidateQueries({ queryKey: ['messaging-overview'] })
      if (data.can_resend) {
        toast.success('Status verified as failed — you can resend.')
      } else {
        toast.success(`Status updated: ${data.status}`)
      }
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const topupMutation = useMutation({
    mutationFn: (pkg: TopUpPackage) => purchaseTopUp(pkg.code),
    onSuccess: (payment) => {
      toast.success('Redirecting to Paystack…')
      redirectToPaystack(payment.authorization_url)
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const overview = overviewQuery.data
  const activeTabLabel = useMemo(
    () => TABS.find((item) => item.key === tab)?.label ?? 'Overview',
    [tab],
  )

  const updateHistoryFilter = (key: 'channel' | 'status' | 'type' | 'q', value: string) => {
    patchParams({ [key]: value || null, page: null }, true)
  }

  return (
    <div className="flex flex-col gap-6">
      {embedded ? null : <ActionBar title="Messaging" />}

      <div className={embedded ? 'space-y-6' : 'bg-white p-4 custom-shadow-md'}>
        <TabComponent
          tabs={TABS.map((item) => ({
            label: item.label,
            onClick: () => setTab(item.key),
          }))}
          activeTab={activeTabLabel}
        />

        <div className="mt-6">
          {tab === 'overview' && (
            <div className="space-y-6">
              {overviewQuery.isLoading && (
                <p className="text-sm text-slate-500">Loading overview…</p>
              )}
              {overview && (
                <>
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <StatsCard title="SMS credits" value={String(overview.credits.sms)} />
                    <StatsCard title="Email credits" value={String(overview.credits.email)} />
                    <StatsCard
                      title="Sent (7 days)"
                      value={String(
                        overview.usage_7d.sms_sent + overview.usage_7d.email_sent,
                      )}
                    />
                    <StatsCard
                      title="Open failures"
                      value={String(overview.open_failures)}
                    />
                  </div>

                  <section className="rounded-2xl border border-slate-200 p-5 text-sm">
                    <h2 className="text-base font-semibold text-slate-900">Credit status</h2>
                    {overview.credits.sms <= 0 && overview.credits.email <= 0 ? (
                      <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
                        You have 0 credits. Guardian SMS and email cannot send until you buy a
                        top-up below (or receive credits from a Billing add-on at renewal).
                      </p>
                    ) : overview.credits.sms <= 0 || overview.credits.email <= 0 ? (
                      <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
                        {overview.credits.sms <= 0
                          ? 'SMS balance is 0 — SMS sends are blocked until you top up.'
                          : 'Email balance is 0 — email sends are blocked until you top up.'}
                      </p>
                    ) : (
                      <p className="mt-2 text-slate-600">
                        Guardian SMS/email debit credits after successful sends. Balances roll
                        over.
                      </p>
                    )}
                    <p className="mt-2 text-slate-500">
                      Last 7 days used {overview.usage_7d.sms_credits_used} SMS credits and{' '}
                      {overview.usage_7d.email_credits_used} email credits.
                    </p>
                    <div className="mt-4 flex flex-wrap gap-3">
                      <Link
                        to="/settings/billing"
                        className="text-sm font-medium text-sky-700 hover:underline"
                      >
                        Manage add-ons on Billing →
                      </Link>
                      <button
                        type="button"
                        className="text-sm font-medium text-sky-700 hover:underline"
                        onClick={() => setTab('history')}
                      >
                        View delivery history →
                      </button>
                    </div>
                  </section>

                  {canManageBilling && (topupsQuery.data?.length ?? 0) > 0 && (
                    <section className="rounded-2xl border border-slate-200 p-5">
                      <h2 className="mb-1 text-base font-semibold text-slate-900">Buy top-up</h2>
                      <p className="mb-4 text-sm text-slate-500">
                        One-time SMS or email credit packs. Charged via Paystack; credits apply
                        after payment.
                      </p>
                      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                        {(topupsQuery.data ?? []).map((pkg) => (
                          <button
                            key={pkg.id}
                            type="button"
                            className="cursor-pointer rounded-xl border border-slate-200 px-3 py-3 text-left text-sm transition hover:border-sky-300 hover:bg-sky-50 disabled:cursor-not-allowed disabled:opacity-50"
                            disabled={topupMutation.isPending}
                            onClick={() => topupMutation.mutate(pkg)}
                          >
                            <span className="font-medium text-slate-900">{pkg.name}</span>
                            <span className="mt-1 block text-slate-500">
                              +{pkg.credits.toLocaleString()} {pkg.channel.toUpperCase()} ·{' '}
                              {formatGhs(pkg.price_ghs)}
                            </span>
                          </button>
                        ))}
                      </div>
                    </section>
                  )}
                </>
              )}
            </div>
          )}

          {tab === 'history' && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-3">
                <select
                  value={channel}
                  onChange={(e) => updateHistoryFilter('channel', e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  <option value="">All channels</option>
                  <option value="sms">SMS</option>
                  <option value="email">Email</option>
                </select>
                <select
                  value={eventTypeFilter}
                  onChange={(e) => updateHistoryFilter('type', e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  <option value="">All types</option>
                  {EVENT_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <select
                  value={statusFilter}
                  onChange={(e) => updateHistoryFilter('status', e.target.value)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  {STATUS_FILTER_OPTIONS.map((option) => (
                    <option key={option.value || 'all'} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <input
                  value={search}
                  onChange={(e) => updateHistoryFilter('q', e.target.value)}
                  placeholder="Search recipient or parent"
                  className="min-w-[220px] flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
              </div>

              {deliveriesQuery.isLoading && (
                <p className="text-sm text-slate-500">Loading deliveries…</p>
              )}
              {(deliveriesQuery.data?.results.length ?? 0) === 0 && !deliveriesQuery.isLoading && (
                <p className="text-sm text-slate-500">No deliveries match these filters.</p>
              )}

              <div className="overflow-hidden rounded-2xl border border-slate-200">
                <ul className="divide-y divide-slate-100">
                  {(deliveriesQuery.data?.results ?? []).map((row) => {
                    const statusLabel = row.status_label || titleCaseEventType(row.status)
                    const displayError =
                      row.display_error || row.user_error_message || row.error_message
                    const showResend =
                      canManageMessaging &&
                      Boolean(row.can_resend) &&
                      Boolean(row.body_preview)
                    const showVerify =
                      canManageMessaging &&
                      row.channel === 'sms' &&
                      row.status === 'unknown'
                    return (
                      <li
                        key={row.id}
                        className="flex flex-wrap items-start justify-between gap-3 p-4 text-sm"
                      >
                        <div className="min-w-0 flex-1 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${CHANNEL_BADGE[row.channel]}`}
                            >
                              <Icon icon={CHANNEL_ICON[row.channel]} className="size-3.5" />
                              {row.channel === 'sms' ? 'SMS' : 'Email'}
                            </span>
                            <span
                              className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
                                EVENT_TYPE_BADGE[row.event_type] ??
                                'bg-slate-100 text-slate-700 ring-slate-200'
                              }`}
                            >
                              {titleCaseEventType(row.event_type)}
                            </span>
                            <span
                              className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_BADGE[row.status]}`}
                              title={row.status_description || undefined}
                            >
                              {statusLabel}
                            </span>
                          </div>
                          <p className="font-medium text-slate-900">
                            {row.parent_name}
                            {row.student_name ? ` · ${row.student_name}` : ''}
                          </p>
                          <p className="text-slate-600">{row.recipient_address}</p>
                          {row.body_preview ? (
                            <p className="line-clamp-2 text-slate-500">{row.body_preview}</p>
                          ) : null}
                          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                            <span>{formatDateTime(row.created_at)}</span>
                            {row.channel === 'sms' && (row.segments ?? 0) > 0 ? (
                              <span>
                                {row.segments} segment{row.segments === 1 ? '' : 's'}
                              </span>
                            ) : null}
                            {(row.credits_charged ?? 0) > 0 ? (
                              <span>
                                {row.credits_charged} credit
                                {row.credits_charged === 1 ? '' : 's'} used
                              </span>
                            ) : null}
                          </div>
                          {displayError ? (
                            <p
                              className={
                                row.status === 'failed' || row.status === 'unknown'
                                  ? 'text-red-600'
                                  : 'text-amber-700'
                              }
                            >
                              {displayError}
                            </p>
                          ) : null}
                        </div>
                        {canManageMessaging && (showResend || showVerify) ? (
                          <div className="flex flex-wrap gap-2">
                            {showVerify ? (
                              <Button
                                type="button"
                                variant="outline"
                                className="!w-auto"
                                disabled={verifyMutation.isPending || retryMutation.isPending}
                                onClick={() => verifyMutation.mutate(row.id)}
                              >
                                Verify status
                              </Button>
                            ) : null}
                            {showResend ? (
                              <Button
                                type="button"
                                variant="outline"
                                className="!w-auto"
                                disabled={retryMutation.isPending || verifyMutation.isPending}
                                onClick={() => setResendTarget(row)}
                              >
                                Resend
                              </Button>
                            ) : null}
                          </div>
                        ) : null}
                      </li>
                    )
                  })}
                </ul>
                {deliveriesQuery.data && deliveriesQuery.data.count > 0 ? (
                  <Pagination
                    pagination={deliveriesQuery.data}
                    onPageChange={(nextPage) =>
                      patchParams({ page: nextPage > 1 ? String(nextPage) : null }, true)
                    }
                    isLoading={deliveriesQuery.isFetching}
                  />
                ) : null}
              </div>
            </div>
          )}

          {tab === 'messages' && (
            <div>
              {canManageMessaging ? (
                <ParentMessagesPolicies />
              ) : (
                <p className="text-sm text-slate-500">
                  You can view messaging history, but only admins/staff with manage access can edit
                  parent message templates and send settings.
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      <Modal
        open={resendTarget != null}
        title="Confirm resend"
        onClose={() => {
          if (!retryMutation.isPending) setResendTarget(null)
        }}
      >
        {resendTarget ? (
          <div className="space-y-4 text-sm">
            <p className="text-slate-600">
              Review the message below, then confirm to queue a new send attempt. The original
              history entry is kept.
            </p>
            <dl className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Channel
                </dt>
                <dd className="mt-1 font-medium text-slate-900">
                  {resendTarget.channel === 'sms' ? 'SMS' : 'Email'}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Type
                </dt>
                <dd className="mt-1 font-medium text-slate-900">
                  {titleCaseEventType(resendTarget.event_type)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Recipient
                </dt>
                <dd className="mt-1 font-medium text-slate-900">
                  {resendTarget.parent_name}
                  {resendTarget.student_name ? ` · ${resendTarget.student_name}` : ''}
                </dd>
                <dd className="mt-0.5 text-slate-600">{resendTarget.recipient_address}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Message
                </dt>
                <dd className="mt-1 whitespace-pre-wrap text-slate-800">
                  {resendTarget.body_preview}
                </dd>
              </div>
              {resendTarget.channel === 'sms' && (resendTarget.segments ?? 0) > 0 ? (
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Segments
                  </dt>
                  <dd className="mt-1 text-slate-800">
                    {resendTarget.segments} (credits are charged again if submission succeeds)
                  </dd>
                </div>
              ) : null}
            </dl>
            <div className="grid grid-cols-2 gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => setResendTarget(null)}
                disabled={retryMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={() => retryMutation.mutate(resendTarget.id)}
                loading={retryMutation.isPending}
              >
                Confirm resend
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  )
}

export default MessagingPage
