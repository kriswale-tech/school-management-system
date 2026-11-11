import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import ActionBar from '@/components/shared/ActionBar'
import { ConfirmDialog, TabComponent } from '@/components/shared'
import StatsCard from '@/components/shared/StatsCard'
import { Button } from '@/components/ui'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks/useCan'
import { BILLING_PAGE_SIZE } from '../services'
import {
  getBillingInvoices,
  getBillingPaymentStats,
  getBillingPayments,
  getBillingPlans,
  getBillingSubscription,
  getCommunicationSkus,
  getUpcomingBill,
  payInvoice,
  requestCapacityUpgrade,
  scheduleAddonChange,
  schedulePlanChange,
  verifySaasPayment,
} from '../services'
import { openPaystackCheckout } from '../openPaystackCheckout'

const PAGE_TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'payments', label: 'Payments' },
] as const

type PageTab = (typeof PAGE_TABS)[number]['key']

function BillingPager({
  count,
  page,
  onPage,
}: {
  count: number
  page: number
  onPage: (page: number) => void
}) {
  if (count <= BILLING_PAGE_SIZE) return null
  const pages = Math.max(1, Math.ceil(count / BILLING_PAGE_SIZE))
  const from = (page - 1) * BILLING_PAGE_SIZE + 1
  const to = Math.min(count, page * BILLING_PAGE_SIZE)
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
      <p>
        {from}–{to} of {count}
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          className="!w-auto px-3 py-1.5"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          Previous
        </Button>
        <span className="text-xs">
          Page {page} of {pages}
        </span>
        <Button
          type="button"
          variant="outline"
          className="!w-auto px-3 py-1.5"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}

function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string; plan?: string } | undefined
    if (typeof data?.detail === 'string') return data.detail
    if (typeof data?.plan === 'string') return data.plan
    return 'Request failed'
  }
  return 'Request failed'
}

function formatGhs(value: string | number | null | undefined) {
  const amount = Number(value ?? 0)
  return `GH₵ ${amount.toLocaleString('en-GH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

type BillingPageProps = {
  embedded?: boolean
}

type BillingConfirm =
  | { type: 'interval-schedule'; nextInterval: 'monthly' | 'annual' }
  | { type: 'interval-cancel'; currentInterval: 'monthly' | 'annual' }
  | {
      type: 'plan-schedule'
      planCode: string
      planName: string
      replacesPendingName?: string
    }
  | {
      type: 'plan-cancel'
      currentPlanCode: string
      currentPlanName: string
      pendingPlanName: string
    }
  | {
      type: 'addon-schedule'
      channel: 'sms' | 'email'
      enabled: boolean
      skuCode?: string
      priceLabel?: string
    }
  | {
      type: 'addon-cancel'
      channel: 'sms' | 'email'
      currentEnabled: boolean
      pendingEnabled: boolean
    }
  | null

const BillingPage = ({ embedded = false }: BillingPageProps) => {
  const queryClient = useQueryClient()
  const canManage = useCan(Capability.BILLING_MANAGE)
  const [searchParams, setSearchParams] = useSearchParams()
  const [confirm, setConfirm] = useState<BillingConfirm>(null)
  const [pageTab, setPageTab] = useState<PageTab>('overview')
  const [invoicePage, setInvoicePage] = useState(1)
  const [paymentPage, setPaymentPage] = useState(1)

  const subscriptionQuery = useQuery({
    queryKey: ['billing-subscription'],
    queryFn: getBillingSubscription,
  })
  const plansQuery = useQuery({
    queryKey: ['billing-plans'],
    queryFn: getBillingPlans,
  })
  const invoicesQuery = useQuery({
    queryKey: ['billing-invoices', invoicePage],
    queryFn: () => getBillingInvoices(invoicePage),
  })
  const upcomingQuery = useQuery({
    queryKey: ['billing-upcoming'],
    queryFn: getUpcomingBill,
  })
  const paymentsQuery = useQuery({
    queryKey: ['billing-payments', paymentPage],
    queryFn: () => getBillingPayments(paymentPage),
    enabled: pageTab === 'payments',
  })
  const paymentStatsQuery = useQuery({
    queryKey: ['billing-payment-stats'],
    queryFn: getBillingPaymentStats,
    enabled: pageTab === 'payments',
  })
  const skusQuery = useQuery({
    queryKey: ['communication-skus', subscriptionQuery.data?.interval],
    queryFn: () => getCommunicationSkus(subscriptionQuery.data?.interval),
    enabled: Boolean(subscriptionQuery.data?.interval),
  })
  const invalidateBilling = () => {
    void queryClient.invalidateQueries({ queryKey: ['billing-subscription'] })
    void queryClient.invalidateQueries({ queryKey: ['billing-invoices'] })
    void queryClient.invalidateQueries({ queryKey: ['billing-upcoming'] })
    void queryClient.invalidateQueries({ queryKey: ['billing-payments'] })
    void queryClient.invalidateQueries({ queryKey: ['billing-payment-stats'] })
    void queryClient.invalidateQueries({ queryKey: ['messaging-overview'] })
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
          invalidateBilling()
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

  const scheduleMutation = useMutation({
    mutationFn: schedulePlanChange,
    onSuccess: (data) => {
      toast.success(
        data.pending_plan
          ? 'Plan change scheduled for next renewal'
          : 'Scheduled plan change cancelled',
      )
      setConfirm(null)
      invalidateBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const confirmPayment = async (reference: string) => {
    try {
      await verifySaasPayment(reference)
      toast.success('Payment confirmed')
      invalidateBilling()
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  const checkoutOpenInvoice = async (invoice: {
    id: string
    status: string
    total_ghs: string
  }) => {
    if (invoice.status === 'open' && Number(invoice.total_ghs) > 0) {
      const payment = await payInvoice(invoice.id)
      openPaystackCheckout(payment, {
        onSuccess: confirmPayment,
        onCancel: () => toast('Checkout closed'),
        onError: (message) => toast.error(message),
      })
      return true
    }
    return false
  }

  const upgradeMutation = useMutation({
    mutationFn: requestCapacityUpgrade,
    onSuccess: async (data) => {
      void queryClient.invalidateQueries({ queryKey: ['billing-invoices'] })
      try {
        if (await checkoutOpenInvoice(data.invoice)) return
      } catch (error) {
        toast.error(errorMessage(error))
        return
      }
      toast.success('Capacity upgraded')
      void queryClient.invalidateQueries({ queryKey: ['billing-subscription'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const intervalMutation = useMutation({
    mutationFn: (interval: 'monthly' | 'annual') => schedulePlanChange({ interval }),
    onSuccess: (data) => {
      toast.success(
        data.pending_interval
          ? 'Interval change scheduled for next renewal'
          : 'Scheduled interval change cancelled',
      )
      setConfirm(null)
      invalidateBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const payMutation = useMutation({
    mutationFn: payInvoice,
    onSuccess: (payment) => {
      openPaystackCheckout(payment, {
        onSuccess: confirmPayment,
        onCancel: () => toast('Checkout closed'),
        onError: (message) => toast.error(message),
      })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const verifyMutation = useMutation({
    mutationFn: verifySaasPayment,
    onSuccess: () => {
      toast.success('Payment confirmed')
      invalidateBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const addonMutation = useMutation({
    mutationFn: scheduleAddonChange,
    onSuccess: (data, variables) => {
      const pending =
        variables.channel === 'sms' ? data.pending_sms_enabled : data.pending_email_enabled
      toast.success(
        pending == null
          ? 'Scheduled add-on change cancelled'
          : 'Add-on change scheduled for next renewal',
      )
      setConfirm(null)
      invalidateBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const confirmBusy =
    intervalMutation.isPending || scheduleMutation.isPending || addonMutation.isPending

  const confirmCopy = (() => {
    if (!confirm) {
      return { title: '', message: '', confirmLabel: 'Confirm' }
    }
    const renewal = formatDate(subscriptionQuery.data?.current_period_end)
    if (confirm.type === 'interval-cancel') {
      return {
        title: 'Cancel scheduled interval change?',
        message: `This cancels the pending switch. You will stay on ${subscriptionQuery.data?.interval ?? 'your current'} billing through the next renewal (${renewal}).`,
        confirmLabel: 'Cancel schedule',
      }
    }
    if (confirm.type === 'interval-schedule') {
      return {
        title: 'Schedule billing interval change?',
        message: `You are scheduling a switch from ${subscriptionQuery.data?.interval ?? 'current'} to ${confirm.nextInterval} billing. Nothing changes today — the new interval starts at your next renewal on ${renewal}. You can cancel this schedule anytime before then.`,
        confirmLabel: 'Confirm schedule',
      }
    }
    if (confirm.type === 'plan-cancel') {
      return {
        title: 'Cancel scheduled plan change?',
        message: `This cancels the pending switch to ${confirm.pendingPlanName}. You will stay on ${confirm.currentPlanName} through the next renewal (${renewal}).`,
        confirmLabel: 'Cancel schedule',
      }
    }
    if (confirm.type === 'plan-schedule') {
      const replaceBit = confirm.replacesPendingName
        ? ` This replaces your pending change to ${confirm.replacesPendingName}.`
        : ''
      return {
        title: `Schedule ${confirm.planName}?`,
        message: `This schedules a change to the ${confirm.planName} plan at your next renewal on ${renewal}. Your current plan stays active until then. No charge is taken now.${replaceBit}`,
        confirmLabel: 'Confirm schedule',
      }
    }
    const channelLabel = confirm.channel.toUpperCase()
    if (confirm.type === 'addon-cancel') {
      return {
        title: `Cancel scheduled ${channelLabel} add-on change?`,
        message: `This cancels the pending ${confirm.pendingEnabled ? 'enable' : 'disable'}. The ${channelLabel} add-on stays ${confirm.currentEnabled ? 'enabled' : 'disabled'} through the next renewal (${renewal}).`,
        confirmLabel: 'Cancel schedule',
      }
    }
    const action = confirm.enabled ? 'enable' : 'disable'
    const priceBit =
      confirm.enabled && confirm.priceLabel ? ` (${confirm.priceLabel} per period)` : ''
    return {
      title: `Schedule ${channelLabel} add-on ${action}?`,
      message: confirm.enabled
        ? `This schedules enabling the ${channelLabel} add-on${priceBit} from your next renewal on ${renewal}. Messaging stays as-is until then. Recurring add-on charges appear on that renewal invoice.`
        : `This schedules disabling the ${channelLabel} add-on at your next renewal on ${renewal}. It stays enabled until then. Existing credit balances are kept.`,
      confirmLabel: 'Confirm schedule',
    }
  })()

  const subscription = subscriptionQuery.data
  const capacity = subscription?.capacity
  const upcoming = upcomingQuery.data
  const usagePct =
    capacity?.usage_ratio != null ? Math.min(100, Math.round(capacity.usage_ratio * 100)) : null
  const staffUsagePct =
    capacity?.staff_usage_ratio != null
      ? Math.min(100, Math.round(capacity.staff_usage_ratio * 100))
      : null
  const nextHigher = (plansQuery.data ?? []).find(
    (plan) =>
      subscription &&
      plan.sort_order > subscription.plan.sort_order &&
      plan.is_active &&
      (plan.student_max == null ||
        (capacity?.active_students ?? 0) <= plan.student_max) &&
      (plan.staff_max == null || (capacity?.active_staff ?? 0) <= plan.staff_max),
  )
  const smsSku = (skusQuery.data ?? []).find((sku) => sku.channel === 'sms')
  const emailSku = (skusQuery.data ?? []).find((sku) => sku.channel === 'email')

  return (
    <div className="flex flex-col gap-6">
      {embedded ? null : <ActionBar title="Billing" />}

      {subscriptionQuery.isLoading && (
        <p className="text-sm text-slate-500">Loading subscription…</p>
      )}
      {subscriptionQuery.isError && (
        <p className="text-sm text-red-600">
          No subscription found yet. Contact SCHOOLASST support if this persists.
        </p>
      )}

      {subscription && capacity && (
        <>
          {upcoming && (
            <section className="rounded-2xl border border-sky-200 bg-sky-50/60 p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">
                    Next bill
                  </p>
                  <h2 className="mt-1 text-xl font-semibold text-slate-900">
                    {formatDate(upcoming.due_at)}
                  </h2>
                  <p className="mt-1 text-sm text-slate-600">
                    {upcoming.plan_name} · {upcoming.interval}
                    {upcoming.includes_pending_changes
                      ? ' · includes scheduled changes'
                      : ''}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-semibold text-slate-900">
                    {formatGhs(upcoming.total_ghs)}
                  </p>
                  {Number(upcoming.discount_ghs) > 0 && (
                    <p className="text-sm text-emerald-700">
                      {upcoming.discount_label
                        ? `${upcoming.discount_label}: `
                        : 'Discount: '}
                      −{formatGhs(upcoming.discount_ghs)}
                    </p>
                  )}
                </div>
              </div>
              <ul className="mt-4 space-y-2 border-t border-sky-100 pt-4 text-sm">
                {upcoming.lines.map((line, index) => (
                  <li
                    key={`${line.kind}-${index}`}
                    className="flex justify-between gap-3 text-slate-700"
                  >
                    <span>
                      {line.kind === 'discount' ? (
                        <span className="text-emerald-700">{line.description}</span>
                      ) : (
                        line.description
                      )}
                    </span>
                    <span
                      className={
                        line.kind === 'discount' ? 'text-emerald-700' : 'text-slate-900'
                      }
                    >
                      {line.kind === 'discount' ? '−' : ''}
                      {formatGhs(line.amount_ghs)}
                    </span>
                  </li>
                ))}
              </ul>
              {upcoming.open_invoice_id && Number(upcoming.open_invoice_total_ghs) > 0 && canManage && (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm">
                  <p className="text-amber-900">
                    Open invoice due now: {formatGhs(upcoming.open_invoice_total_ghs)}
                    {upcoming.open_invoice_notes ? ` · ${upcoming.open_invoice_notes}` : ''}
                  </p>
                  <Button
                    type="button"
                    className="!w-auto"
                    disabled={payMutation.isPending}
                    onClick={() => payMutation.mutate(upcoming.open_invoice_id!)}
                  >
                    Pay now
                  </Button>
                </div>
              )}
            </section>
          )}

          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <TabComponent
              tabs={PAGE_TABS.map((item) => ({
                label: item.label,
                onClick: () => setPageTab(item.key),
              }))}
              activeTab={PAGE_TABS.find((item) => item.key === pageTab)?.label ?? 'Overview'}
            />
          </div>

          {pageTab === 'payments' && (
            <div className="flex flex-col gap-6">
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatsCard
                  title="Total paid"
                  value={formatGhs(paymentStatsQuery.data?.total_paid_ghs)}
                />
                <StatsCard
                  title="Open balance"
                  value={formatGhs(paymentStatsQuery.data?.open_balance_ghs)}
                />
                <StatsCard
                  title="Successful payments"
                  value={String(paymentStatsQuery.data?.successful_payments ?? 0)}
                />
                <StatsCard
                  title="Paid invoices"
                  value={String(paymentStatsQuery.data?.paid_invoices ?? 0)}
                />
              </div>
              {(paymentStatsQuery.data?.by_purpose &&
                Object.keys(paymentStatsQuery.data.by_purpose).length > 0) && (
                <section className="rounded-2xl border border-slate-200 bg-white p-5">
                  <h2 className="mb-3 text-base font-semibold text-slate-900">
                    Where money went
                  </h2>
                  <ul className="space-y-2 text-sm">
                    {Object.entries(paymentStatsQuery.data.by_purpose).map(([purpose, amount]) => (
                      <li key={purpose} className="flex justify-between gap-3">
                        <span className="text-slate-600">
                          {purpose === 'topup'
                            ? 'Top-ups'
                            : purpose === 'invoice'
                              ? 'Invoices'
                              : purpose}
                        </span>
                        <span className="font-medium text-slate-900">{formatGhs(amount)}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              <section className="rounded-2xl border border-slate-200 bg-white p-5">
                <h2 className="mb-1 text-base font-semibold text-slate-900">Payment history</h2>
                <p className="mb-4 text-sm text-slate-500">
                  Each row is a Paystack charge. Confirm a pending charge after the money has
                  been taken. A credit top-up is not paid again from an open invoice.
                </p>
                {paymentsQuery.isLoading && (
                  <p className="text-sm text-slate-500">Loading payments…</p>
                )}
                {(paymentsQuery.data?.results.length ?? 0) === 0 && !paymentsQuery.isLoading && (
                  <p className="text-sm text-slate-500">
                    No Paystack payments yet. Invoices can exist before anyone pays; top-ups and
                    invoice checkouts show up here once Paystack is started.
                  </p>
                )}
                <ul className="divide-y divide-slate-100">
                  {(paymentsQuery.data?.results ?? []).map((payment) => {
                    const tag =
                      payment.tag ||
                      (payment.purpose === 'topup' ? 'Top-up' : 'Invoice')
                    const tagClass =
                      payment.purpose === 'topup'
                        ? 'bg-violet-50 text-violet-800 ring-violet-200'
                        : 'bg-sky-50 text-sky-800 ring-sky-200'
                    const statusClass =
                      payment.status === 'success'
                        ? 'text-emerald-700'
                        : payment.status === 'failed'
                          ? 'text-red-700'
                          : payment.status === 'pending'
                            ? 'text-amber-700'
                            : 'text-slate-600'
                    return (
                      <li
                        key={payment.id}
                        className="flex flex-wrap items-start justify-between gap-3 py-3 text-sm"
                      >
                        <div className="min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${tagClass}`}
                            >
                              {tag}
                            </span>
                            <span className={`text-xs font-medium capitalize ${statusClass}`}>
                              {payment.status}
                            </span>
                          </div>
                          <p className="font-medium text-slate-900">
                            {payment.label ||
                              (payment.purpose === 'topup' ? 'Credit top-up' : 'Invoice payment')}
                          </p>
                          <p className="font-mono text-xs text-slate-500">{payment.reference}</p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-slate-900">
                            {formatGhs(payment.amount_ghs)}
                          </p>
                          <p className="text-slate-500">
                            {formatDate(payment.paid_at || payment.created_at)}
                          </p>
                          {canManage && payment.status === 'pending' && (
                            <Button
                              type="button"
                              variant="outline"
                              className="mt-2 !w-auto px-3 py-1.5"
                              loading={
                                verifyMutation.isPending &&
                                verifyMutation.variables === payment.reference
                              }
                              loadingText="Confirming"
                              disabled={verifyMutation.isPending}
                              onClick={() => verifyMutation.mutate(payment.reference)}
                            >
                              Confirm payment
                            </Button>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ul>
                <BillingPager
                  count={paymentsQuery.data?.count ?? 0}
                  page={paymentPage}
                  onPage={setPaymentPage}
                />
              </section>
            </div>
          )}

          {pageTab === 'overview' && (
            <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatsCard title="Plan" value={subscription.plan.name} />
            <StatsCard
              title="Billing interval"
              value={subscription.interval === 'annual' ? 'Annual' : 'Monthly'}
            />
            <StatsCard
              title="Renews"
              value={formatDate(subscription.current_period_end)}
            />
            <StatsCard
              title="List price"
              value={formatGhs(subscription.app_price_snapshot_ghs)}
            />
          </div>

          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Billing interval</h2>
                <p className="text-sm text-slate-500">
                  Interval changes take effect at the next renewal (
                  {formatDate(subscription.current_period_end)}).
                </p>
                {subscription.pending_interval ? (
                  <p className="mt-2 text-sm text-amber-700">
                    Pending: switch to {subscription.pending_interval} on{' '}
                    {formatDate(subscription.pending_change_effective_at)}
                  </p>
                ) : null}
              </div>
              {canManage &&
                (!subscription.pending_interval ||
                  subscription.pending_interval === subscription.interval) && (
                  <Button
                    type="button"
                    variant="outline"
                    className="!w-auto"
                    disabled={intervalMutation.isPending}
                    onClick={() =>
                      setConfirm({
                        type: 'interval-schedule',
                        nextInterval:
                          subscription.interval === 'annual' ? 'monthly' : 'annual',
                      })
                    }
                  >
                    Schedule{' '}
                    {subscription.interval === 'annual' ? 'monthly' : 'annual'}
                  </Button>
                )}
              {canManage &&
                subscription.pending_interval &&
                subscription.pending_interval !== subscription.interval && (
                  <Button
                    type="button"
                    variant="outline"
                    className="!w-auto"
                    disabled={intervalMutation.isPending}
                    onClick={() =>
                      setConfirm({
                        type: 'interval-cancel',
                        currentInterval: subscription.interval,
                      })
                    }
                  >
                    Cancel scheduled change
                  </Button>
                )}
            </div>
            {subscription.status === 'past_due' && (
              <p className="mt-3 text-sm text-amber-700">
                Subscription is past due
                {subscription.grace_period_ends_at
                  ? ` · grace until ${formatDate(subscription.grace_period_ends_at)}`
                  : ''}
                . Pay open invoices to avoid suspension.
              </p>
            )}
            {subscription.status === 'suspended' && (
              <p className="mt-3 text-sm text-red-700">
                Subscription suspended for non-payment. Pay open invoices to restore access.
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Plan capacity</h2>
                <p className="text-sm text-slate-500">
                  Students and staff seats for {subscription.plan.name}.
                </p>
              </div>
              {capacity.at_or_over_capacity && canManage && nextHigher && (
                <Button
                  type="button"
                  className="!w-auto"
                  onClick={() =>
                    upgradeMutation.mutate({ plan_code: nextHigher.code, mark_paid: false })
                  }
                  disabled={upgradeMutation.isPending || payMutation.isPending}
                >
                  Upgrade to {nextHigher.name}
                </Button>
              )}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-sm text-slate-500">
                  Students {capacity.active_students}
                  {capacity.capacity_max != null ? ` / ${capacity.capacity_max}` : ' (open)'}
                </p>
                {usagePct != null && (
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full ${
                        capacity.at_or_over_student_capacity
                          ? 'bg-red-500'
                          : (capacity.triggered_warnings?.length ?? 0) > 0
                            ? 'bg-amber-500'
                            : 'bg-sky-500'
                      }`}
                      style={{ width: `${usagePct}%` }}
                    />
                  </div>
                )}
              </div>
              <div>
                <p className="text-sm text-slate-500">
                  Staff {capacity.active_staff}
                  {capacity.staff_capacity_max != null
                    ? ` / ${capacity.staff_capacity_max}`
                    : ' (open)'}
                </p>
                {staffUsagePct != null && (
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className={`h-full rounded-full ${
                        capacity.at_or_over_staff_capacity
                          ? 'bg-red-500'
                          : (capacity.triggered_warnings?.length ?? 0) > 0
                            ? 'bg-amber-500'
                            : 'bg-sky-500'
                      }`}
                      style={{ width: `${staffUsagePct}%` }}
                    />
                  </div>
                )}
              </div>
            </div>
            {capacity.at_or_over_capacity && (
              <p className="mt-3 text-sm text-red-700">
                Capacity reached. Upgrade before adding students or staff
                {capacity.at_or_over_student_capacity ? ' (students)' : ''}
                {capacity.at_or_over_staff_capacity ? ' (staff)' : ''}.
              </p>
            )}
            {subscription.pending_plan && (
              <p className="mt-3 text-sm text-slate-600">
                Pending change to {subscription.pending_plan.name}
                {subscription.pending_interval
                  ? ` (${subscription.pending_interval})`
                  : ''}{' '}
                on {formatDate(subscription.pending_change_effective_at)}.
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-1 text-base font-semibold text-slate-900">
              SMS &amp; email add-ons
            </h2>
            <p className="mb-4 text-sm text-slate-500">
              Recurring messaging credits. Changes apply at the next renewal. Buy one-time
              top-ups from Messaging.
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              {(
                [
                  {
                    channel: 'sms' as const,
                    label: 'SMS',
                    enabled: subscription.sms_addon_enabled,
                    sku: subscription.sms_sku,
                    pendingEnabled: subscription.pending_sms_enabled,
                    catalogSku: smsSku,
                  },
                  {
                    channel: 'email' as const,
                    label: 'Email',
                    enabled: subscription.email_addon_enabled,
                    sku: subscription.email_sku,
                    pendingEnabled: subscription.pending_email_enabled,
                    catalogSku: emailSku,
                  },
                ] as const
              ).map((item) => {
                const priceSku = item.sku ?? item.catalogSku
                const intervalLabel =
                  subscription.interval === 'annual' ? 'year' : 'month'
                return (
                  <div key={item.channel} className="rounded-xl border border-slate-200 p-4 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <p className="font-medium text-slate-900">{item.label} add-on</p>
                      {priceSku ? (
                        <p className="shrink-0 text-sm font-semibold text-slate-900">
                          {formatGhs(priceSku.price_ghs)}
                          <span className="font-normal text-slate-500"> / {intervalLabel}</span>
                        </p>
                      ) : null}
                    </div>
                    <p className="mt-1 text-slate-500">
                      {item.enabled ? `Enabled · ${item.sku?.name ?? 'SKU'}` : 'Not enabled'}
                      {priceSku
                        ? ` · ${priceSku.credits_per_period.toLocaleString()} credits / ${intervalLabel}`
                        : ''}
                    </p>
                    {item.pendingEnabled != null && (
                      <p className="mt-1 text-amber-700">
                        Pending: {item.pendingEnabled ? 'enable' : 'disable'} on{' '}
                        {formatDate(subscription.pending_change_effective_at)}
                      </p>
                    )}
                    {canManage && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.pendingEnabled != null ? (
                          <Button
                            type="button"
                            variant="outline"
                            className="!w-auto"
                            disabled={addonMutation.isPending}
                            onClick={() =>
                              setConfirm({
                                type: 'addon-cancel',
                                channel: item.channel,
                                currentEnabled: item.enabled,
                                pendingEnabled: item.pendingEnabled,
                              })
                            }
                          >
                            Cancel schedule
                          </Button>
                        ) : (
                          <Button
                            type="button"
                            variant="outline"
                            className="!w-auto"
                            disabled={
                              addonMutation.isPending || (!item.enabled && !item.catalogSku)
                            }
                            onClick={() =>
                              setConfirm({
                                type: 'addon-schedule',
                                channel: item.channel,
                                enabled: !item.enabled,
                                skuCode: item.catalogSku?.code,
                                priceLabel: item.catalogSku
                                  ? formatGhs(item.catalogSku.price_ghs)
                                  : undefined,
                              })
                            }
                          >
                            {item.enabled ? 'Schedule disable' : 'Schedule enable'}
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </section>

          {canManage && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-1 text-base font-semibold text-slate-900">Change plan</h2>
              <p className="mb-4 text-sm text-slate-500">
                Ordinary upgrades and downgrades take effect at the next renewal. Capacity
                upgrades apply immediately with a prorated charge.
              </p>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {(plansQuery.data ?? []).map((plan) => {
                  const isCurrent = plan.code === subscription.plan.code
                  const isPending = subscription.pending_plan?.code === plan.code
                  return (
                    <div
                      key={plan.id}
                      className="rounded-xl border border-slate-200 p-4"
                    >
                      <div className="flex items-baseline justify-between gap-2">
                        <h3 className="font-medium text-slate-900">{plan.name}</h3>
                        <span className="text-sm text-slate-500">
                          {plan.student_max != null
                            ? `${plan.student_min}–${plan.student_max} students`
                            : `${plan.student_min}+ students`}
                          {' · '}
                          {plan.staff_max != null
                            ? `≤${plan.staff_max} staff`
                            : 'open staff'}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-slate-600">
                        {formatGhs(plan.price_annual_ghs)} / year ·{' '}
                        {formatGhs(plan.price_monthly_ghs)} / month
                      </p>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {isCurrent ? (
                          <span className="text-xs font-medium text-sky-700">Current plan</span>
                        ) : null}
                        {isPending ? (
                          <>
                            <span className="text-xs font-medium text-amber-700">Scheduled</span>
                            <Button
                              type="button"
                              variant="outline"
                              className="!w-auto"
                              disabled={scheduleMutation.isPending}
                              onClick={() =>
                                setConfirm({
                                  type: 'plan-cancel',
                                  currentPlanCode: subscription.plan.code,
                                  currentPlanName: subscription.plan.name,
                                  pendingPlanName: plan.name,
                                })
                              }
                            >
                              Cancel schedule
                            </Button>
                          </>
                        ) : null}
                        {!isCurrent && !isPending ? (
                          <Button
                            type="button"
                            variant="outline"
                            className="!w-auto"
                            disabled={scheduleMutation.isPending}
                            onClick={() =>
                              setConfirm({
                                type: 'plan-schedule',
                                planCode: plan.code,
                                planName: plan.name,
                                replacesPendingName: subscription.pending_plan?.name,
                              })
                            }
                          >
                            {subscription.pending_plan ? 'Replace schedule' : 'Schedule'}
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-4 text-base font-semibold text-slate-900">Invoices</h2>
            {invoicesQuery.isLoading && (
              <p className="text-sm text-slate-500">Loading invoices…</p>
            )}
            {(invoicesQuery.data?.results.length ?? 0) === 0 && !invoicesQuery.isLoading && (
              <p className="text-sm text-slate-500">No invoices yet.</p>
            )}
            <ul className="divide-y divide-slate-100">
              {(invoicesQuery.data?.results ?? []).map((invoice) => (
                <li key={invoice.id} className="py-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-900">
                        {formatGhs(invoice.total_ghs)} · {invoice.status}
                        {Number(invoice.discount_ghs) > 0
                          ? ` · discount −${formatGhs(invoice.discount_ghs)}`
                          : ''}
                      </p>
                      <p className="text-slate-500">
                        {formatDate(invoice.period_start)} – {formatDate(invoice.period_end)}
                        {invoice.notes ? ` · ${invoice.notes}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="text-slate-500">{formatDate(invoice.created_at)}</p>
                      {canManage &&
                        invoice.status === 'open' &&
                        Number(invoice.total_ghs) > 0 && (
                          <Button
                            type="button"
                            variant="outline"
                            className="!w-auto"
                            disabled={payMutation.isPending}
                            onClick={() => payMutation.mutate(invoice.id)}
                          >
                            Pay
                          </Button>
                        )}
                    </div>
                  </div>
                  {invoice.lines?.length > 0 && (
                    <ul className="mt-2 space-y-1 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                      {invoice.lines.map((line) => (
                        <li key={line.id} className="flex justify-between gap-3">
                          <span
                            className={
                              line.kind === 'discount' ? 'text-emerald-700' : undefined
                            }
                          >
                            {line.description}
                          </span>
                          <span
                            className={
                              line.kind === 'discount'
                                ? 'text-emerald-700'
                                : 'text-slate-800'
                            }
                          >
                            {line.kind === 'discount' ? '−' : ''}
                            {formatGhs(line.amount_ghs)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
            <BillingPager
              count={invoicesQuery.data?.count ?? 0}
              page={invoicePage}
              onPage={setInvoicePage}
            />
          </section>
            </>
          )}
        </>
      )}

      <ConfirmDialog
        open={confirm != null}
        title={confirmCopy.title}
        message={confirmCopy.message}
        confirmLabel={confirmCopy.confirmLabel}
        isLoading={confirmBusy}
        onClose={() => {
          if (!confirmBusy) setConfirm(null)
        }}
        onConfirm={() => {
          if (!confirm) return
          if (confirm.type === 'interval-schedule') {
            intervalMutation.mutate(confirm.nextInterval)
            return
          }
          if (confirm.type === 'interval-cancel') {
            intervalMutation.mutate(confirm.currentInterval)
            return
          }
          if (confirm.type === 'plan-schedule') {
            scheduleMutation.mutate({ plan_code: confirm.planCode })
            return
          }
          if (confirm.type === 'plan-cancel') {
            scheduleMutation.mutate({ plan_code: confirm.currentPlanCode })
            return
          }
          if (confirm.type === 'addon-cancel') {
            addonMutation.mutate({
              channel: confirm.channel,
              enabled: confirm.currentEnabled,
            })
            return
          }
          addonMutation.mutate({
            channel: confirm.channel,
            enabled: confirm.enabled,
            sku_code: confirm.skuCode,
          })
        }}
      />
    </div>
  )
}

export default BillingPage
