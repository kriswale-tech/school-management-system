import { useEffect, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import {
  assignSchoolDiscount,
  capacityUpgradeSchool,
  extendSchoolGrace,
  getSchoolCredits,
  getSchoolFinance,
  getSchoolSubscription,
  listAddonSkus,
  listDiscounts,
  listPlans,
  listSchoolInvoices,
  listSchoolPayments,
  listTopUpPackages,
  markInvoicePaid,
  quoteSchoolUpgrade,
  recordSchoolTopUp,
  revokeDiscount,
  verifyPayment,
  scheduleSchoolAddon,
  scheduleSchoolPlanChange,
  startSchoolSubscription,
} from '@/features/billing/services'
import { ListPager } from '@/features/billing/ListPager'
import { StatusBadge } from '@/features/billing/StatusBadge'
import {
  paymentForLabel,
  paymentKindLabel,
  paymentProviderLabel,
} from '@/features/billing/paymentDisplay'
import type { AddonSku, Invoice, Plan, PlatformDiscount, Subscription, TopUpPackage } from '@/features/billing/types'
import { formatGhs } from '@/features/messages/lib'
import dayjs from '@/lib/dayjs'
import { formatDate, formatDateTime } from '@/lib/dates'

function errorMessage(error: unknown) {
  if (!isAxiosError(error)) return 'Request failed'
  const data = error.response?.data
  if (!data || typeof data !== 'object') return 'Request failed'
  const record = data as Record<string, unknown>
  if (typeof record.detail === 'string' && record.detail) return record.detail
  for (const value of Object.values(record)) {
    if (typeof value === 'string' && value) return value
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  }
  return 'Request failed'
}

function earliestGraceDate(subscription: Subscription) {
  const tomorrow = dayjs().add(1, 'day').startOf('day')
  const afterCurrent = subscription.grace_period_ends_at
    ? dayjs(subscription.grace_period_ends_at).add(1, 'day').startOf('day')
    : tomorrow
  return (afterCurrent.isAfter(tomorrow) ? afterCurrent : tomorrow).format('YYYY-MM-DD')
}

function graceCanExtend(status: string) {
  return status === 'past_due' || status === 'suspended'
}

function planFits(plan: Plan, subscription: Subscription) {
  const students = subscription.capacity.active_students
  const staff = subscription.capacity.active_staff
  if (plan.student_max != null && students > plan.student_max) return false
  if (plan.staff_max != null && staff > plan.staff_max) return false
  return true
}

function planLimit(max: number | null) {
  return max == null ? 'no limit' : max.toLocaleString()
}

function scheduleLabel(schedule: string) {
  if (schedule === 'recurring') return 'Every invoice'
  if (schedule === 'introductory') return 'Introductory'
  if (schedule === 'date_range') return 'Date range'
  return schedule
}

function percent(ratio: number | null | undefined) {
  if (ratio == null || !Number.isFinite(ratio)) return null
  return Math.round(ratio * 100)
}

function barClass(ratio: number | null, over: boolean) {
  if (over || (ratio != null && ratio >= 1)) return 'bg-red-600'
  if (ratio != null && ratio >= 0.8) return 'bg-amber-500'
  return 'bg-[var(--color-accent)]'
}

function FillBar({
  ratio,
  over,
  colorClass,
}: {
  ratio: number | null
  over?: boolean
  colorClass?: string
}) {
  const width = ratio == null ? 0 : Math.min(Math.max(ratio, 0), 1) * 100
  return (
    <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-[var(--color-panel)]">
      <div
        className={`h-full rounded-full ${colorClass ?? barClass(ratio, Boolean(over))}`}
        style={{ width: `${width}%` }}
      />
    </div>
  )
}

type Prompt = {
  title: string
  body: string
  confirmLabel: string
  run: () => void
}

const btn =
  'rounded-xl border border-[var(--color-line)] bg-white px-3 py-1.5 text-xs font-medium disabled:opacity-50'
const btnSolid =
  'rounded-xl bg-[var(--color-accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60'

export default function SchoolBillingPanel({ schoolId }: { schoolId: string }) {
  const queryClient = useQueryClient()
  const [prompt, setPrompt] = useState<Prompt | null>(null)
  const [planDialog, setPlanDialog] = useState(false)
  const [selectedPlanId, setSelectedPlanId] = useState('')
  const [topupOpen, setTopupOpen] = useState(false)
  const [selectedPackageId, setSelectedPackageId] = useState('')
  const [discountChoice, setDiscountChoice] = useState<PlatformDiscount | null>(null)
  const [addonChoice, setAddonChoice] = useState<{
    channel: 'sms' | 'email'
    enabled: boolean
    skuCode: string
  } | null>(null)
  const [financeTab, setFinanceTab] = useState<'invoices' | 'payments'>('invoices')
  const [invoicePage, setInvoicePage] = useState(1)
  const [paymentPage, setPaymentPage] = useState(1)
  const [graceUntil, setGraceUntil] = useState('')

  useEffect(() => {
    setInvoicePage(1)
    setPaymentPage(1)
  }, [schoolId])

  const subscriptionQuery = useQuery({
    queryKey: ['platform-school-subscription', schoolId],
    queryFn: () => getSchoolSubscription(schoolId),
    retry: false,
  })
  const plansQuery = useQuery({
    queryKey: ['platform-billing-plans'],
    queryFn: listPlans,
  })
  const topupsQuery = useQuery({
    queryKey: ['platform-billing-topups'],
    queryFn: listTopUpPackages,
  })
  const skusQuery = useQuery({
    queryKey: ['platform-addon-skus'],
    queryFn: listAddonSkus,
  })
  const discountsQuery = useQuery({
    queryKey: ['platform-billing-discounts'],
    queryFn: listDiscounts,
  })
  const invoicesQuery = useQuery({
    queryKey: ['platform-school-invoices', schoolId, invoicePage],
    queryFn: () => listSchoolInvoices(schoolId, invoicePage),
  })
  const paymentsQuery = useQuery({
    queryKey: ['platform-school-payments', schoolId, paymentPage],
    queryFn: () => listSchoolPayments(schoolId, paymentPage),
  })
  const creditsQuery = useQuery({
    queryKey: ['platform-school-credits', schoolId],
    queryFn: () => getSchoolCredits(schoolId),
  })
  const financeQuery = useQuery({
    queryKey: ['platform-school-finance', schoolId],
    queryFn: () => getSchoolFinance(schoolId),
  })

  function refreshBilling() {
    void queryClient.invalidateQueries({ queryKey: ['platform-school-subscription', schoolId] })
    void queryClient.invalidateQueries({ queryKey: ['platform-school-invoices', schoolId] })
    void queryClient.invalidateQueries({ queryKey: ['platform-school-payments', schoolId] })
    void queryClient.invalidateQueries({ queryKey: ['platform-school-credits', schoolId] })
    void queryClient.invalidateQueries({ queryKey: ['platform-school-finance', schoolId] })
    void queryClient.invalidateQueries({ queryKey: ['platform-school-audit', schoolId] })
  }

  function closePrompts() {
    setPrompt(null)
    setPlanDialog(false)
    setSelectedPlanId('')
    setTopupOpen(false)
    setSelectedPackageId('')
    setDiscountChoice(null)
    setAddonChoice(null)
  }

  const startMutation = useMutation({
    mutationFn: () => startSchoolSubscription(schoolId, { apply_first_year_free: true }),
    onSuccess: () => {
      toast.success('Subscription started')
      closePrompts()
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const scheduleMutation = useMutation({
    mutationFn: (payload: { plan_code?: string; interval?: 'monthly' | 'annual' }) =>
      scheduleSchoolPlanChange(schoolId, payload),
    onSuccess: () => {
      toast.success('Change scheduled for the next renewal')
      closePrompts()
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const upgradeMutation = useMutation({
    mutationFn: (planCode: string) =>
      capacityUpgradeSchool(schoolId, { plan_code: planCode, mark_paid: true }),
    onSuccess: () => {
      toast.success('Plan upgraded and recorded as paid')
      closePrompts()
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const addonMutation = useMutation({
    mutationFn: (payload: { channel: 'sms' | 'email'; enabled: boolean; sku_code?: string }) =>
      scheduleSchoolAddon(schoolId, payload),
    onSuccess: () => {
      toast.success('Add-on change scheduled')
      closePrompts()
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const discountMutation = useMutation({
    mutationFn: (campaignId: string) => assignSchoolDiscount(schoolId, campaignId),
    onSuccess: () => {
      toast.success('Discount updated')
      closePrompts()
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const revokeMutation = useMutation({
    mutationFn: (discount: { campaignId: string; redemptionId: string }) =>
      revokeDiscount(discount.campaignId, discount.redemptionId),
    onSuccess: () => {
      toast.success('Discount cancelled for future invoices')
      closePrompts()
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const markPaidMutation = useMutation({
    mutationFn: (invoiceId: string) => markInvoicePaid(invoiceId),
    onSuccess: () => {
      toast.success('Invoice marked paid')
      closePrompts()
      refreshBilling()
      void queryClient.invalidateQueries({ queryKey: ['platform-school', schoolId] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const graceMutation = useMutation({
    mutationFn: (until: string) => extendSchoolGrace(schoolId, until),
    onSuccess: () => {
      toast.success('Grace period extended')
      setGraceUntil('')
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const verifyMutation = useMutation({
    mutationFn: (paymentId: string) => verifyPayment(paymentId),
    onSuccess: () => {
      toast.success('Payment verified')
      closePrompts()
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const topupMutation = useMutation({
    mutationFn: (packageCode: string) => recordSchoolTopUp(schoolId, packageCode),
    onSuccess: (result) => {
      toast.success(`${result.package_name} recorded as paid`)
      closePrompts()
      refreshBilling()
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const subscription = subscriptionQuery.data
  const otherPlans = (plansQuery.data ?? []).filter(
    (plan) => plan.is_active && plan.code !== subscription?.plan.code,
  )
  const selectedPlan = otherPlans.find((plan) => plan.id === selectedPlanId) ?? null
  const selectedCanUpgrade = Boolean(
    subscription && selectedPlan && selectedPlan.sort_order > subscription.plan.sort_order && planFits(selectedPlan, subscription),
  )
  const quoteQuery = useQuery({
    queryKey: ['platform-upgrade-quote', schoolId, selectedPlan?.code],
    queryFn: () => quoteSchoolUpgrade(schoolId, selectedPlan?.code ?? ''),
    enabled: planDialog && selectedCanUpgrade,
  })
  const busy =
    startMutation.isPending ||
    scheduleMutation.isPending ||
    upgradeMutation.isPending ||
    addonMutation.isPending ||
    discountMutation.isPending ||
    revokeMutation.isPending ||
    markPaidMutation.isPending ||
    graceMutation.isPending ||
    topupMutation.isPending ||
    verifyMutation.isPending
  const activeDiscounts = (discountsQuery.data ?? []).filter((discount) => discount.is_active)
  const currentCampaignIds = new Set((subscription?.discounts ?? []).map((row) => row.campaign_id))

  return (
    <div className="mt-4 space-y-4">
      <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
              Subscription
            </h2>
            <p className="mt-1 text-sm text-[var(--color-ink)]/70">
              Plan, billing interval, and what is scheduled for the next renewal.
            </p>
          </div>
          {!subscription && !subscriptionQuery.isLoading && (
            <button
              type="button"
              className={btnSolid}
              onClick={() =>
                setPrompt({
                  title: 'Start the complimentary first year?',
                  body: 'This starts an annual Starter subscription with the first year free. Add-ons stay off.',
                  confirmLabel: 'Start subscription',
                  run: () => startMutation.mutate(),
                })
              }
            >
              Start first-year free
            </button>
          )}
        </div>

        {subscriptionQuery.isLoading && (
          <p className="mt-4 text-sm text-[var(--color-ink)]/60">Loading subscription…</p>
        )}
        {subscriptionQuery.isError && !subscription && (
          <p className="mt-4 text-sm text-[var(--color-ink)]/60">
            No current subscription for this school.
          </p>
        )}

        {subscription && (
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <PlanCard
              subscription={subscription}
              busy={busy}
              onScheduleInterval={() => {
                const next = subscription.interval === 'annual' ? 'monthly' : 'annual'
                const pending =
                  subscription.pending_interval &&
                  subscription.pending_interval !== subscription.interval
                setPrompt({
                  title: pending
                    ? 'Cancel the scheduled interval change?'
                    : `Switch to ${next} at the next renewal?`,
                  body: pending
                    ? `The school stays on ${subscription.interval} billing. The next renewal is ${formatDate(subscription.current_period_end)}.`
                    : `Nothing changes today. ${next} billing starts at the next renewal on ${formatDate(subscription.current_period_end)}.`,
                  confirmLabel: pending ? 'Cancel schedule' : `Switch to ${next}`,
                  run: () =>
                    scheduleMutation.mutate({
                      interval: pending ? subscription.interval : next,
                    }),
                })
              }}
              onChangePlan={() => setPlanDialog(true)}
              onExtendGrace={() => setGraceUntil(earliestGraceDate(subscription))}
            />
            <DiscountCard
              subscription={subscription}
              busy={busy}
              canSwitch={activeDiscounts.some((row) => !currentCampaignIds.has(row.id))}
              onCancel={(discount) =>
                setPrompt({
                  title: `Cancel ${discount.name}?`,
                  body: 'Future invoices will not use this discount. Invoices already issued stay as they are.',
                  confirmLabel: 'Cancel discount',
                  run: () =>
                    revokeMutation.mutate({
                      campaignId: discount.campaign_id,
                      redemptionId: discount.id,
                    }),
                })
              }
              onChange={() => {
                const next = activeDiscounts.find(
                  (row) => discountFits(row, subscription) && !currentCampaignIds.has(row.id),
                )
                if (next) setDiscountChoice(next)
              }}
            />
            <CapacityCard subscription={subscription} />
            <AddonCard
              subscription={subscription}
              busy={busy}
              onChange={(channel) => {
                const current =
                  channel === 'sms'
                    ? subscription.sms_addon_enabled
                    : subscription.email_addon_enabled
                const pending =
                  channel === 'sms'
                    ? subscription.pending_sms_enabled
                    : subscription.pending_email_enabled
                const match = matchingSkus(skusQuery.data ?? [], subscription, channel)
                setAddonChoice({
                  channel,
                  enabled: pending != null ? current : !current,
                  skuCode: match[0]?.code ?? '',
                })
              }}
            />
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">Credits</h2>
            <p className="mt-1 text-sm text-[var(--color-ink)]/70">
              Remaining balance, and how much of this period’s allowance has been used.
            </p>
          </div>
          {subscription && (
            <button type="button" className={btn} disabled={busy} onClick={() => setTopupOpen(true)}>
              Add credits
            </button>
          )}
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <CreditMeter channel="SMS" usage={creditsQuery.data?.usage?.sms} fallback={creditsQuery.data?.sms ?? 0} />
          <CreditMeter channel="Email" usage={creditsQuery.data?.usage?.email} fallback={creditsQuery.data?.email ?? 0} />
        </div>
      </section>

      <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">Finance</h2>
          {financeQuery.data?.payment_overdue && (
            <StatusBadge status="overdue" />
          )}
        </div>
        <p className="mt-1 text-sm text-[var(--color-ink)]/70">
          What this school has been billed, paid, and still owes. Void invoices stay in the list and are left out of these totals.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <FinanceStat label="Paid" value={formatGhs(financeQuery.data?.total_paid_ghs)} tone="text-emerald-800" hint={`${financeQuery.data?.successful_payments ?? 0} successful payments`} />
          <FinanceStat label="Outstanding" value={formatGhs(financeQuery.data?.outstanding_ghs)} tone="text-amber-900" hint={`${financeQuery.data?.open_invoices ?? 0} pending invoices`} />
          <FinanceStat label="Billed" value={formatGhs(financeQuery.data?.billed_ghs)} tone="text-[var(--color-ink)]" hint={`${financeQuery.data?.invoice_count ?? 0} paid and pending invoices`} />
          <FinanceStat label="Discounts" value={formatGhs(financeQuery.data?.discount_ghs)} tone="text-[var(--color-accent)]" hint="Taken off paid and pending invoices" />
        </div>

        <div className="mt-6 flex gap-2" role="tablist">
          {(['invoices', 'payments'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={financeTab === tab}
              className={`rounded-full px-3 py-1 text-sm font-semibold capitalize ${
                financeTab === tab
                  ? 'bg-[var(--color-ink)] text-white'
                  : 'bg-[var(--color-panel)] text-[var(--color-ink)]/70'
              }`}
              onClick={() => setFinanceTab(tab)}
            >
              {tab}
            </button>
          ))}
        </div>

        {financeTab === 'invoices' && (
        <>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="text-xs tracking-wide text-[var(--color-ink)]/55 uppercase">
              <tr>
                <th className="px-3 py-2 font-semibold">Period</th>
                <th className="px-3 py-2 font-semibold">Amount</th>
                <th className="px-3 py-2 font-semibold">State</th>
                <th className="px-3 py-2 font-semibold">Issued</th>
                <th className="px-3 py-2 font-semibold" />
              </tr>
            </thead>
            <tbody>
              {(invoicesQuery.data?.results ?? []).length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-4 text-[var(--color-ink)]/60">
                    No invoices yet.
                  </td>
                </tr>
              )}
              {(invoicesQuery.data?.results ?? []).map((invoice) => (
                <InvoiceRow
                  key={invoice.id}
                  invoice={invoice}
                  busy={busy}
                  onMarkPaid={() =>
                    setPrompt({
                      title: 'Mark this invoice paid?',
                      body: `${formatGhs(invoice.total_ghs)} will be recorded as paid. This does not charge a card.`,
                      confirmLabel: 'Mark paid',
                      run: () => markPaidMutation.mutate(invoice.id),
                    })
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
        <ListPager
          count={invoicesQuery.data?.count ?? 0}
          page={invoicePage}
          onPage={setInvoicePage}
        />
        </>
        )}

        {financeTab === 'payments' && (
          <>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[64rem] text-left text-sm">
              <thead className="text-xs tracking-wide text-[var(--color-ink)]/55 uppercase">
                <tr>
                  <th className="px-3 py-2 font-semibold">Amount</th>
                  <th className="px-3 py-2 font-semibold">For</th>
                  <th className="px-3 py-2 font-semibold">Provider</th>
                  <th className="px-3 py-2 font-semibold">State</th>
                  <th className="px-3 py-2 font-semibold">Reference</th>
                  <th className="px-3 py-2 font-semibold">Paystack id</th>
                  <th className="px-3 py-2 font-semibold">When</th>
                  <th className="px-3 py-2 font-semibold" />
                </tr>
              </thead>
              <tbody>
                {(paymentsQuery.data?.results ?? []).length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-3 py-4 text-[var(--color-ink)]/60">
                      No payments yet.
                    </td>
                  </tr>
                )}
                {(paymentsQuery.data?.results ?? []).map((payment) => (
                  <tr key={payment.id} className="border-t border-[var(--color-line)]">
                    <td className="px-3 py-3 font-medium">{formatGhs(payment.amount_ghs)}</td>
                    <td className="px-3 py-3">
                      <p className="font-medium">{paymentKindLabel(payment)}</p>
                      <p className="max-w-xs text-[var(--color-ink)]/65">{paymentForLabel(payment)}</p>
                    </td>
                    <td className="px-3 py-3">{paymentProviderLabel(payment.provider)}</td>
                    <td className="px-3 py-3">
                      <StatusBadge status={payment.status} />
                    </td>
                    <td className="px-3 py-3 font-mono text-xs">{payment.reference}</td>
                    <td className="px-3 py-3 font-mono text-xs">
                      {payment.provider_transaction_id || '—'}
                    </td>
                    <td className="px-3 py-3 text-[var(--color-ink)]/70">
                      {formatDateTime(payment.paid_at || payment.created_at)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      {payment.status === 'pending' && payment.provider === 'paystack' && (
                        <button
                          type="button"
                          className={btn}
                          disabled={busy}
                          onClick={() =>
                            setPrompt({
                              title: 'Verify this payment?',
                              body: `Paystack will be checked for ${payment.reference}. If Paystack confirms it, the invoice is completed. If not, the payment stays as it is.`,
                              confirmLabel: 'Verify',
                              run: () => verifyMutation.mutate(payment.id),
                            })
                          }
                        >
                          Verify
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ListPager
            count={paymentsQuery.data?.count ?? 0}
            page={paymentPage}
            onPage={setPaymentPage}
          />
          </>
        )}
      </section>

      {graceUntil && subscription && (
        <Modal
          title="Extend grace"
          body={`The platform default stays as it is. This school stays past due until the end of ${formatDate(graceUntil)}, then the nightly check can suspend the subscription.`}
        >
          <label className="mr-auto text-sm">
            <span className="mb-1 block text-[var(--color-ink)]/70">Grace ends</span>
            <input
              type="date"
              className="rounded-xl border border-[var(--color-line)] px-3 py-2"
              min={earliestGraceDate(subscription)}
              value={graceUntil}
              onChange={(event) => setGraceUntil(event.target.value)}
            />
          </label>
          <button type="button" className={btn} disabled={busy} onClick={() => setGraceUntil('')}>
            Back
          </button>
          <button
            type="button"
            className={btnSolid}
            disabled={busy || !graceUntil}
            onClick={() => graceMutation.mutate(graceUntil)}
          >
            Extend grace
          </button>
        </Modal>
      )}

      {prompt && (
        <Modal title={prompt.title} body={prompt.body}>
          <button type="button" className={btn} disabled={busy} onClick={() => setPrompt(null)}>
            Back
          </button>
          <button type="button" className={btnSolid} disabled={busy} onClick={prompt.run}>
            {busy ? 'Saving…' : prompt.confirmLabel}
          </button>
        </Modal>
      )}

      {planDialog && subscription && (
        <ChangePlanDialog
          subscription={subscription}
          plans={otherPlans}
          selectedPlan={selectedPlan}
          quoteAmount={quoteQuery.data?.amount_ghs}
          quoteLoading={quoteQuery.isFetching}
          quoteError={quoteQuery.isError ? errorMessage(quoteQuery.error) : ''}
          busy={busy}
          onSelect={setSelectedPlanId}
          onClose={() => {
            setPlanDialog(false)
            setSelectedPlanId('')
          }}
          onSchedule={() => {
            if (!selectedPlan) return
            scheduleMutation.mutate({ plan_code: selectedPlan.code })
          }}
          onUpgrade={() => {
            if (!selectedPlan) return
            upgradeMutation.mutate(selectedPlan.code)
          }}
        />
      )}

      {topupOpen && (
        <TopUpDialog
          packages={(topupsQuery.data ?? []).filter((pkg) => pkg.is_active)}
          selectedId={selectedPackageId}
          busy={busy}
          onSelect={setSelectedPackageId}
          onClose={() => {
            setTopupOpen(false)
            setSelectedPackageId('')
          }}
          onConfirm={() => {
            const chosen = (topupsQuery.data ?? []).find((pkg) => pkg.id === selectedPackageId)
            if (chosen) topupMutation.mutate(chosen.code)
          }}
        />
      )}

      {discountChoice && subscription && (
        <Modal
          title="Subscribe to a different discount?"
          body="The school keeps one active discount. Choosing this one cancels the others for future invoices."
        >
          <label className="col-span-2 block text-sm">
            <span className="mb-1 block font-medium">Discount</span>
            <select
              className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
              value={discountChoice.id}
              onChange={(event) => {
                const next = activeDiscounts.find((row) => row.id === event.target.value)
                if (next) setDiscountChoice(next)
              }}
            >
              {activeDiscounts
                .filter((row) => discountFits(row, subscription))
                .map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name} · {Number(row.discount_percent)}% · {scheduleLabel(row.schedule)}
                  </option>
                ))}
            </select>
          </label>
          <button type="button" className={btn} disabled={busy} onClick={() => setDiscountChoice(null)}>
            Back
          </button>
          <button
            type="button"
            className={btnSolid}
            disabled={busy || currentCampaignIds.has(discountChoice.id)}
            onClick={() => discountMutation.mutate(discountChoice.id)}
          >
            {busy ? 'Saving…' : 'Use this discount'}
          </button>
        </Modal>
      )}

      {addonChoice && subscription && (
        <AddonModal
          choice={addonChoice}
          subscription={subscription}
          skus={skusQuery.data ?? []}
          busy={busy}
          onClose={() => setAddonChoice(null)}
          onSku={(skuCode) => setAddonChoice({ ...addonChoice, skuCode })}
          onConfirm={() => {
            const currently =
              addonChoice.channel === 'sms'
                ? subscription.sms_addon_enabled
                : subscription.email_addon_enabled
            const clearing = addonChoice.enabled === currently
            addonMutation.mutate({
              channel: addonChoice.channel,
              enabled: addonChoice.enabled,
              sku_code: clearing || !addonChoice.enabled ? undefined : addonChoice.skuCode || undefined,
            })
          }}
        />
      )}
    </div>
  )
}

function matchingSkus(skus: AddonSku[], subscription: Subscription, channel: 'sms' | 'email') {
  return skus.filter(
    (sku) =>
      sku.is_active &&
      sku.channel === channel &&
      sku.interval === subscription.interval &&
      (sku.available_plans ?? []).some((plan) => plan.id === subscription.plan.id),
  )
}

function discountFits(discount: PlatformDiscount, subscription: Subscription) {
  if (!discount.billing_interval) return true
  return discount.billing_interval === subscription.interval
}

function PlanCard({
  subscription,
  busy,
  onScheduleInterval,
  onChangePlan,
  onExtendGrace,
}: {
  subscription: Subscription
  busy: boolean
  onScheduleInterval: () => void
  onChangePlan: () => void
  onExtendGrace: () => void
}) {
  const price =
    subscription.interval === 'annual'
      ? subscription.plan.price_annual_ghs
      : subscription.plan.price_monthly_ghs
  const pendingInterval =
    subscription.pending_interval && subscription.pending_interval !== subscription.interval
      ? subscription.pending_interval
      : ''
  return (
    <article className="rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)]/60 p-4">
      <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">Plan</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-[family-name:var(--font-display)] text-2xl font-semibold">
            {subscription.plan.name}
          </p>
          <p className="mt-1 text-sm capitalize text-[var(--color-ink)]/70">
            {subscription.interval} · {formatGhs(price)}
          </p>
        </div>
        <StatusBadge status={subscription.status} />
      </div>
      <p className="mt-3 text-sm text-[var(--color-ink)]/70">
        Renews {formatDate(subscription.current_period_end)}
        {subscription.billing_suspended_school ? ' · billing has locked the school' : ''}
      </p>
      <p className="mt-1 text-sm text-[var(--color-ink)]/70">
        {graceCanExtend(subscription.status)
          ? subscription.grace_period_ends_at
            ? `Grace ends ${formatDateTime(subscription.grace_period_ends_at)}`
            : 'Grace has not been set'
          : 'Grace starts when a renewal goes unpaid'}
      </p>
      {(subscription.pending_plan || pendingInterval) && (
        <p className="mt-2 rounded-xl bg-sky-50 px-3 py-2 text-sm text-sky-900">
          Scheduled
          {subscription.pending_plan ? ` ${subscription.pending_plan.name}` : ''}
          {pendingInterval ? ` ${pendingInterval}` : ''} on{' '}
          {formatDate(subscription.pending_change_effective_at)}
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {graceCanExtend(subscription.status) && (
          <button type="button" className={btn} disabled={busy} onClick={onExtendGrace}>
            Extend grace
          </button>
        )}
        <button type="button" className={btn} disabled={busy} onClick={onScheduleInterval}>
          {pendingInterval
            ? `Cancel scheduled ${pendingInterval}`
            : `Switch to ${subscription.interval === 'annual' ? 'monthly' : 'annual'} at the next renewal`}
        </button>
        <button type="button" className={btn} disabled={busy} onClick={onChangePlan}>
          Change plan
        </button>
      </div>
    </article>
  )
}

function DiscountCard({
  subscription,
  busy,
  canSwitch,
  onCancel,
  onChange,
}: {
  subscription: Subscription
  busy: boolean
  canSwitch: boolean
  onCancel: (discount: NonNullable<Subscription['discounts']>[number]) => void
  onChange: () => void
}) {
  const discounts = subscription.discounts ?? []
  return (
    <article className="rounded-2xl border border-[var(--color-line)] bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">
          Discount
        </p>
        <button type="button" className={btn} disabled={busy || !canSwitch} onClick={onChange}>
          {discounts.length ? 'Change discount' : 'Add discount'}
        </button>
      </div>
      {discounts.length === 0 && (
        <p className="mt-3 text-sm text-[var(--color-ink)]/60">
          No discount is reducing future invoices.
        </p>
      )}
      <ul className="mt-3 space-y-3">
        {discounts.map((discount) => (
          <li key={discount.id} className="rounded-xl bg-emerald-50 px-3 py-3 text-emerald-950">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-lg font-semibold">
                  {Number(discount.discount_percent)}% off
                </p>
                <p className="text-sm">{discount.name}</p>
                <p className="mt-1 text-xs opacity-80">
                  {scheduleLabel(discount.schedule)}
                  {discount.ends_at ? ` · until ${formatDate(discount.ends_at)}` : ''}
                  {discount.applies_to === 'application' ? ' · plan price' : ''}
                  {discount.applies_to === 'communication' ? ' · add-ons' : ''}
                  {discount.applies_to === 'all' ? ' · plan and add-ons' : ''}
                </p>
              </div>
              <button type="button" className={btn} disabled={busy} onClick={() => onCancel(discount)}>
                Cancel
              </button>
            </div>
          </li>
        ))}
      </ul>
    </article>
  )
}

function CapacityCard({ subscription }: { subscription: Subscription }) {
  const capacity = subscription.capacity
  return (
    <article className="rounded-2xl border border-[var(--color-line)] bg-white p-4">
      <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">
        Capacity
      </p>
      <div className="mt-4 space-y-4">
        <CapacityMeter
          label="Students"
          used={capacity.active_students}
          max={capacity.capacity_max}
          ratio={capacity.usage_ratio}
          over={capacity.at_or_over_student_capacity}
          colorClass="bg-[#1d4e89]"
        />
        <CapacityMeter
          label="Staff"
          used={capacity.active_staff}
          max={capacity.staff_capacity_max}
          ratio={capacity.staff_usage_ratio}
          over={capacity.at_or_over_staff_capacity}
        />
      </div>
    </article>
  )
}

function CapacityMeter({
  label,
  used,
  max,
  ratio,
  over,
  colorClass,
}: {
  label: string
  used: number
  max: number | null
  ratio: number | null
  over: boolean
  colorClass?: string
}) {
  const pct = percent(ratio)
  return (
    <div>
      <div className="flex items-end justify-between gap-3">
        <p className="text-sm font-medium">{label}</p>
        <p className="font-[family-name:var(--font-display)] text-2xl font-semibold">
          {pct == null ? used.toLocaleString() : `${pct}%`}
        </p>
      </div>
      <p className="text-xs text-[var(--color-ink)]/60">
        {used.toLocaleString()}
        {max == null ? ' · no limit' : ` of ${max.toLocaleString()}`}
      </p>
      {max != null && <FillBar ratio={ratio} over={over} colorClass={over ? undefined : colorClass} />}
    </div>
  )
}

function AddonCard({
  subscription,
  busy,
  onChange,
}: {
  subscription: Subscription
  busy: boolean
  onChange: (channel: 'sms' | 'email') => void
}) {
  return (
    <article className="rounded-2xl border border-[var(--color-line)] bg-white p-4">
      <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">
        Add-ons
      </p>
      <div className="mt-3 space-y-3">
        <AddonRow
          label="SMS"
          enabled={subscription.sms_addon_enabled}
          skuName={subscription.sms_sku?.name}
          pending={subscription.pending_sms_enabled}
          pendingSku={subscription.pending_sms_sku?.name}
          busy={busy}
          onChange={() => onChange('sms')}
        />
        <AddonRow
          label="Email"
          enabled={subscription.email_addon_enabled}
          skuName={subscription.email_sku?.name}
          pending={subscription.pending_email_enabled}
          pendingSku={subscription.pending_email_sku?.name}
          busy={busy}
          onChange={() => onChange('email')}
        />
      </div>
      {(subscription.pending_plan || subscription.pending_interval || subscription.pending_sms_enabled != null || subscription.pending_email_enabled != null) && (
        <p className="mt-3 text-xs text-[var(--color-ink)]/60">
          Scheduled changes take effect {formatDate(subscription.pending_change_effective_at)}.
        </p>
      )}
    </article>
  )
}

function AddonRow({
  label,
  enabled,
  skuName,
  pending,
  pendingSku,
  busy,
  onChange,
}: {
  label: string
  enabled: boolean
  skuName?: string | null
  pending: boolean | null
  pendingSku?: string | null
  busy: boolean
  onChange: () => void
}) {
  const scheduled =
    pending == null
      ? ''
      : pending
        ? `Turns on${pendingSku ? ` · ${pendingSku}` : ''}`
        : 'Turns off'
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[var(--color-line)] px-3 py-3">
      <div>
        <p className="font-medium">{label}</p>
        <p className="text-sm text-[var(--color-ink)]/70">
          {enabled ? skuName || 'On' : 'Off'}
          {scheduled ? ` · Scheduled: ${scheduled}` : ''}
        </p>
      </div>
      <button type="button" className={btn} disabled={busy} onClick={onChange}>
        {pending != null && pending !== enabled ? 'Review schedule' : enabled ? `Turn ${label} off` : `Turn ${label} on`}
      </button>
    </div>
  )
}

function CreditMeter({
  channel,
  usage,
  fallback,
}: {
  channel: string
  usage?: { balance: number; used: number; allowance: number; exhaustion_ratio: number | null }
  fallback: number
}) {
  const balance = usage?.balance ?? fallback
  const pct = percent(usage?.exhaustion_ratio)
  return (
    <article className="rounded-2xl border border-[var(--color-line)] p-4">
      <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">
        {channel}
      </p>
      <p className="mt-1 font-[family-name:var(--font-display)] text-3xl font-semibold">
        {balance.toLocaleString()}
      </p>
      <p className="text-xs text-[var(--color-ink)]/60">remaining</p>
      {usage && usage.allowance > 0 ? (
        <>
          <FillBar ratio={usage.exhaustion_ratio} />
          <p className="mt-2 text-sm">
            {pct ?? 0}% used · {usage.used.toLocaleString()} of {usage.allowance.toLocaleString()} this period
          </p>
        </>
      ) : (
        <p className="mt-3 text-sm text-[var(--color-ink)]/70">
          {usage ? `${usage.used.toLocaleString()} used this period` : 'No period allowance'}
          {' · add-on is off'}
        </p>
      )}
    </article>
  )
}

function FinanceStat({
  label,
  value,
  hint,
  tone,
}: {
  label: string
  value: string
  hint: string
  tone: string
}) {
  return (
    <article className="rounded-2xl border border-[var(--color-line)] px-4 py-3">
      <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">{label}</p>
      <p className={`mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold ${tone}`}>
        {value}
      </p>
      <p className="mt-1 text-xs text-[var(--color-ink)]/60">{hint}</p>
    </article>
  )
}

function InvoiceRow({
  invoice,
  busy,
  onMarkPaid,
}: {
  invoice: Invoice
  busy: boolean
  onMarkPaid: () => void
}) {
  const payable = invoice.status === 'open' && Number(invoice.total_ghs) > 0
  return (
    <tr className="border-t border-[var(--color-line)]">
      <td className="px-3 py-3">
        <div>
          {formatDate(invoice.period_start)} – {formatDate(invoice.period_end)}
        </div>
        {invoice.notes ? <div className="text-xs text-[var(--color-ink)]/55">{invoice.notes}</div> : null}
      </td>
      <td className="px-3 py-3 font-medium">{formatGhs(invoice.total_ghs)}</td>
      <td className="px-3 py-3">
        <StatusBadge status={invoice.status} />
      </td>
      <td className="px-3 py-3 text-[var(--color-ink)]/70">{formatDate(invoice.created_at)}</td>
      <td className="px-3 py-3 text-right">
        {payable && (
          <button type="button" className={btn} disabled={busy} onClick={onMarkPaid}>
            Mark paid
          </button>
        )}
      </td>
    </tr>
  )
}

function ChangePlanDialog({
  subscription,
  plans,
  selectedPlan,
  quoteAmount,
  quoteLoading,
  quoteError,
  busy,
  onSelect,
  onClose,
  onSchedule,
  onUpgrade,
}: {
  subscription: Subscription
  plans: Plan[]
  selectedPlan: Plan | null
  quoteAmount?: string
  quoteLoading: boolean
  quoteError: string
  busy: boolean
  onSelect: (planId: string) => void
  onClose: () => void
  onSchedule: () => void
  onUpgrade: () => void
}) {
  const students = subscription.capacity.active_students
  const staff = subscription.capacity.active_staff
  const fits = selectedPlan ? planFits(selectedPlan, subscription) : false
  const higher = Boolean(selectedPlan && selectedPlan.sort_order > subscription.plan.sort_order)
  const price = selectedPlan
    ? subscription.interval === 'annual'
      ? selectedPlan.price_annual_ghs
      : selectedPlan.price_monthly_ghs
    : ''
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg">
        <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold">Change plan</h3>
        <p className="mt-2 text-sm text-[var(--color-ink)]/70">
          This school has {students.toLocaleString()} students and {staff.toLocaleString()} staff.
          A plan that is too small stays disabled.
        </p>
        <div className="mt-4 space-y-2">
          {plans.map((plan) => {
            const allowed = planFits(plan, subscription)
            const planPrice =
              subscription.interval === 'annual' ? plan.price_annual_ghs : plan.price_monthly_ghs
            return (
              <label
                key={plan.id}
                className={`flex items-start gap-3 rounded-xl border px-3 py-2 text-sm ${
                  allowed ? 'border-[var(--color-line)]' : 'border-dashed border-[var(--color-line)] opacity-60'
                }`}
              >
                <input
                  type="radio"
                  name="plan"
                  className="mt-1"
                  disabled={!allowed}
                  checked={selectedPlan?.id === plan.id}
                  onChange={() => onSelect(plan.id)}
                />
                <span>
                  <span className="font-semibold">{plan.name}</span>
                  <span className="text-[var(--color-ink)]/70">
                    {' '}
                    · {formatGhs(planPrice)} {subscription.interval}
                  </span>
                  <span className="mt-0.5 block text-[var(--color-ink)]/60">
                    {planLimit(plan.student_max)} students · {planLimit(plan.staff_max)} staff
                    {allowed ? '' : ` · too small for ${students.toLocaleString()} students`}
                  </span>
                </span>
              </label>
            )
          })}
        </div>
        {selectedPlan && fits && (
          <p className="mt-4 text-sm text-[var(--color-ink)]/75">
            {higher
              ? quoteLoading
                ? 'Calculating today’s prorated amount…'
                : quoteError
                  ? quoteError
                  : `At the next renewal on ${formatDate(subscription.current_period_end)}, nothing is charged today. Applying today records ${formatGhs(quoteAmount)} as paid for the rest of this period. The school is not charged.`
              : `${selectedPlan.name} starts at the next renewal on ${formatDate(subscription.current_period_end)}. Nothing is charged today. The renewal price will be ${formatGhs(price)}.`}
          </p>
        )}
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className={btn} disabled={busy} onClick={onClose}>
            Back
          </button>
          <button
            type="button"
            className={btn}
            disabled={busy || !fits}
            onClick={onSchedule}
          >
            Start at next renewal
          </button>
          {higher && (
            <button
              type="button"
              className={btnSolid}
              disabled={busy || !fits || quoteLoading || Boolean(quoteError)}
              onClick={onUpgrade}
            >
              Apply today, record as paid
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function TopUpDialog({
  packages,
  selectedId,
  busy,
  onSelect,
  onClose,
  onConfirm,
}: {
  packages: TopUpPackage[]
  selectedId: string
  busy: boolean
  onSelect: (packageId: string) => void
  onClose: () => void
  onConfirm: () => void
}) {
  const selected = packages.find((pkg) => pkg.id === selectedId) ?? null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg">
        <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold">Add credits</h3>
        <p className="mt-2 text-sm text-[var(--color-ink)]/70">
          This records the package as paid and adds the credits now. The school is not charged through Paystack.
        </p>
        {packages.length === 0 && (
          <p className="mt-4 text-sm text-[var(--color-ink)]/60">
            No active top-up packages. Activate one on the Plans page.
          </p>
        )}
        <div className="mt-4 space-y-2">
          {packages.map((pkg) => (
            <label key={pkg.id} className="flex items-start gap-3 rounded-xl border border-[var(--color-line)] px-3 py-2 text-sm">
              <input
                type="radio"
                name="topup"
                className="mt-1"
                checked={selectedId === pkg.id}
                onChange={() => onSelect(pkg.id)}
              />
              <span>
                <span className="font-semibold">{pkg.name}</span>
                <span className="text-[var(--color-ink)]/70">
                  {' '}
                  · {pkg.channel.toUpperCase()} · {pkg.credits.toLocaleString()} credits · {formatGhs(pkg.price_ghs)}
                </span>
              </span>
            </label>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button type="button" className={btn} disabled={busy} onClick={onClose}>
            Back
          </button>
          <button type="button" className={btnSolid} disabled={busy || !selected} onClick={onConfirm}>
            {selected ? `Record ${formatGhs(selected.price_ghs)} as paid` : 'Record as paid'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Modal({
  title,
  body,
  children,
}: {
  title: string
  body: string
  children: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg">
        <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold">{title}</h3>
        <p className="mt-3 text-sm text-[var(--color-ink)]/70">{body}</p>
        <div className="mt-5 grid grid-cols-2 gap-3">{children}</div>
      </div>
    </div>
  )
}

function AddonModal({
  choice,
  subscription,
  skus,
  busy,
  onClose,
  onSku,
  onConfirm,
}: {
  choice: { channel: 'sms' | 'email'; enabled: boolean; skuCode: string }
  subscription: Subscription
  skus: AddonSku[]
  busy: boolean
  onClose: () => void
  onSku: (skuCode: string) => void
  onConfirm: () => void
}) {
  const label = choice.channel === 'sms' ? 'SMS' : 'Email'
  const currently = choice.channel === 'sms' ? subscription.sms_addon_enabled : subscription.email_addon_enabled
  const clearing = choice.enabled === currently
  const options = matchingSkus(skus, subscription, choice.channel)
  const when = formatDate(subscription.current_period_end)
  const title = clearing
    ? `Cancel the scheduled ${label} change?`
    : choice.enabled
      ? `Turn ${label} on at the next renewal?`
      : `Turn ${label} off at the next renewal?`
  const body = clearing
    ? `${label} stays ${currently ? 'on' : 'off'} through the renewal on ${when}.`
    : `Nothing changes today. ${label} ${choice.enabled ? 'starts' : 'stops'} on ${when}.`
  return (
    <Modal title={title} body={body}>
      {choice.enabled && !clearing && (
        <label className="col-span-2 block text-sm">
          <span className="mb-1 block font-medium">Package</span>
          <select
            className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
            value={choice.skuCode}
            onChange={(event) => onSku(event.target.value)}
          >
            {options.length === 0 && <option value="">No package for this plan</option>}
            {options.map((sku) => (
              <option key={sku.id} value={sku.code}>
                {sku.name} · {formatGhs(sku.price_ghs)} · {sku.credits_per_period.toLocaleString()} credits
              </option>
            ))}
          </select>
        </label>
      )}
      <button type="button" className={btn} disabled={busy} onClick={onClose}>
        Back
      </button>
      <button
        type="button"
        className={btnSolid}
        disabled={busy || (choice.enabled && !clearing && !choice.skuCode)}
        onClick={onConfirm}
      >
        {busy ? 'Saving…' : clearing ? 'Cancel schedule' : 'Confirm'}
      </button>
    </Modal>
  )
}
