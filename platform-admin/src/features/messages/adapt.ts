/**
 * Maps `/platform/messages/*` payloads onto the view models the pages render.
 * The API keeps each money layer in its own object; the pages read flat fields.
 */
import type {
  CashLayer,
  Channel,
  DeliveryStats,
  FreeUsageStats,
  MessagesOverview,
  MessagingTransaction,
  Paginated,
  Profitability,
  ProviderLayer,
  SchoolCreditLayer,
  SchoolMessagingReport,
  SchoolUsageRow,
  SmsVolume,
  TransactionType,
  UsageLayer,
} from './types'

type Dict = Record<string, unknown>

function asRecord(value: unknown): Dict | undefined {
  if (value && typeof value === 'object' && !Array.isArray(value)) return value as Dict
  return undefined
}

function asNumber(value: unknown): number | null {
  if (value == null || value === '') return null
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function asString(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function money(value: unknown): number {
  return asNumber(value) ?? 0
}

function moneyText(value: number): string {
  return value.toFixed(2)
}

function sumMoney(values: unknown[]): string {
  return moneyText(values.reduce<number>((total, value) => total + money(value), 0))
}

function marginPct(profit: number, revenue: number): number | null {
  if (revenue === 0) return null
  return (profit / revenue) * 100
}

function accountStatus(accounts: unknown, provider: string): string | null {
  if (!Array.isArray(accounts)) return null
  const match = accounts.find((row) => asRecord(row)?.provider === provider)
  return asString(asRecord(match)?.api_status)
}

/* ------------------------------------------------------------------ */
/* Overview                                                            */
/* ------------------------------------------------------------------ */

type ClassSplit = { units?: number; messages?: number; provider_cost_ghs?: string }
type ChannelBlock = {
  layer_5_usage?: {
    messages?: number
    segments?: number
    units?: number
    provider_cost_ghs?: string
    usage_valued_revenue_ghs?: string
    unpriced_rows?: number
    provider_cost_is_estimated?: boolean
  }
  filtered_usage?: { messages?: number; units?: number; segments?: number; provider_cost_ghs?: string }
  delivery_statuses?: Partial<DeliveryStats>
  layer_2_school_credits?: {
    allocated_units?: number
    consumed_units?: number
    remaining_units?: number
  }
  classification?: { paid?: ClassSplit; free?: ClassSplit; sponsored?: ClassSplit }
}
type OverviewPayload = {
  filters?: { classification?: string | null }
  channels?: { sms?: ChannelBlock; email?: ChannelBlock }
  layer_3_cash_from_schools?: {
    topup_cash_ghs?: string
    addon_cash_ghs?: string
    total_cash_ghs?: string
  }
  providers?: {
    accounts?: unknown
    layer_1_provider_wallet?: {
      arkesel_balance?: { sms_balance?: number | null; captured_at?: string | null }
      ses_usage?: {
        monthly_used?: number | null
        monthly_limit?: number | null
        captured_at?: string | null
      }
      resend_usage?: {
        monthly_used?: number | null
        monthly_limit?: number | null
        captured_at?: string | null
      }
    }
    layer_4_cash_to_providers?: {
      total_ghs?: string
      total_purchases_ghs?: string
      total_expenses_ghs?: string
    }
  }
  trend?: Array<{ date?: string; sms_segments?: number; emails?: number; email_credits?: number }>
}

function bucketUnits(block: ChannelBlock | undefined, name: 'paid' | 'free' | 'sponsored', active: string | null) {
  if (!block) return null
  if (active && active !== name) return 0
  return asNumber(block.classification?.[name]?.units) ?? 0
}

function volumeFrom(block: ChannelBlock | undefined, active: string | null) {
  if (!block) return undefined
  if (active && block.filtered_usage) return block.filtered_usage
  return block.layer_5_usage
}

function smsVolume(block: ChannelBlock | undefined, active: string | null): SmsVolume | undefined {
  if (!block) return undefined
  const usage = volumeFrom(block, active)
  const statuses = block.delivery_statuses ?? {}
  return {
    segments_total: usage?.units ?? usage?.segments ?? 0,
    segments_paid: bucketUnits(block, 'paid', active) ?? 0,
    segments_free: bucketUnits(block, 'free', active) ?? 0,
    segments_sponsored: bucketUnits(block, 'sponsored', active) ?? 0,
    messages_total: usage?.messages ?? 0,
    recipients_total: usage?.messages ?? 0,
    submitted: statuses.submitted ?? 0,
    delivered: statuses.delivered ?? 0,
    failed: statuses.failed ?? 0,
    skipped: statuses.skipped ?? 0,
    unknown: statuses.unknown ?? 0,
  }
}

function emailVolume(block: ChannelBlock | undefined, active: string | null) {
  if (!block) return undefined
  const usage = volumeFrom(block, active)
  const statuses = block.delivery_statuses ?? {}
  return {
    credits_total: usage?.units ?? usage?.messages ?? 0,
    credits_paid: bucketUnits(block, 'paid', active) ?? 0,
    credits_free: bucketUnits(block, 'free', active) ?? 0,
    credits_sponsored: bucketUnits(block, 'sponsored', active) ?? 0,
    accepted: usage?.messages ?? 0,
    submitted: statuses.submitted ?? 0,
    delivered: statuses.delivered ?? 0,
    failed: statuses.failed ?? 0,
    skipped: statuses.skipped ?? 0,
    unknown: statuses.unknown ?? 0,
  }
}

export function adaptOverview(payload: unknown): MessagesOverview {
  const data = payload as OverviewPayload
  if (!data?.channels && !data?.providers) return (payload ?? {}) as MessagesOverview

  const active = asString(data.filters?.classification)
  const smsBlock = data.channels?.sms
  const emailBlock = data.channels?.email
  const wallet = data.providers?.layer_1_provider_wallet
  const ses = wallet?.ses_usage ?? wallet?.resend_usage
  const cashOut = data.providers?.layer_4_cash_to_providers
  const cashIn = data.layer_3_cash_from_schools

  const provider: ProviderLayer = {
    arkesel_sms_balance: wallet?.arkesel_balance?.sms_balance ?? null,
    arkesel_captured_at: wallet?.arkesel_balance?.captured_at ?? null,
    arkesel_api_status: accountStatus(data.providers?.accounts, 'arkesel'),
    ses_monthly_used: ses?.monthly_used ?? null,
    ses_monthly_limit: ses?.monthly_limit ?? null,
    ses_captured_at: ses?.captured_at ?? null,
    ses_api_status: accountStatus(data.providers?.accounts, 'ses') ?? accountStatus(data.providers?.accounts, 'resend'),
    resend_monthly_used: ses?.monthly_used ?? null,
    resend_monthly_limit: ses?.monthly_limit ?? null,
    resend_captured_at: ses?.captured_at ?? null,
    resend_api_status: accountStatus(data.providers?.accounts, 'resend'),
  }

  const present = [smsBlock, emailBlock].filter(Boolean) as ChannelBlock[]
  const credits: SchoolCreditLayer = {
    sms_outstanding_units: smsBlock
      ? (smsBlock.layer_2_school_credits?.remaining_units ?? 0)
      : null,
    email_outstanding_units: emailBlock
      ? (emailBlock.layer_2_school_credits?.remaining_units ?? 0)
      : null,
    allocated_units: present.reduce(
      (total, block) => total + (block.layer_2_school_credits?.allocated_units ?? 0),
      0,
    ),
    consumed_units: present.reduce(
      (total, block) => total + (block.layer_2_school_credits?.consumed_units ?? 0),
      0,
    ),
  }

  const cash: CashLayer = {
    received_from_schools_ghs: cashIn?.total_cash_ghs ?? '0.00',
    topup_cash_ghs: cashIn?.topup_cash_ghs ?? '0.00',
    addon_cash_ghs: cashIn?.addon_cash_ghs ?? '0.00',
    paid_to_providers_ghs: cashOut?.total_ghs ?? '0.00',
    provider_purchases_ghs: cashOut?.total_purchases_ghs ?? '0.00',
    provider_expenses_ghs: cashOut?.total_expenses_ghs ?? '0.00',
  }

  const revenue = money(smsBlock?.layer_5_usage?.usage_valued_revenue_ghs) + money(emailBlock?.layer_5_usage?.usage_valued_revenue_ghs)
  const cost = money(smsBlock?.layer_5_usage?.provider_cost_ghs) + money(emailBlock?.layer_5_usage?.provider_cost_ghs)
  const profit = revenue - cost
  const freeSponsored = sumMoney([
    smsBlock?.classification?.free?.provider_cost_ghs,
    smsBlock?.classification?.sponsored?.provider_cost_ghs,
    emailBlock?.classification?.free?.provider_cost_ghs,
    emailBlock?.classification?.sponsored?.provider_cost_ghs,
  ])
  const usage: UsageLayer = {
    usage_valued_revenue_ghs: moneyText(revenue),
    provider_cost_ghs: moneyText(cost),
    gross_profit_ghs: moneyText(profit),
    gross_margin_pct: marginPct(profit, revenue),
    free_sponsored_expense_ghs: freeSponsored,
    unpriced_units: (smsBlock?.layer_5_usage?.unpriced_rows ?? 0) + (emailBlock?.layer_5_usage?.unpriced_rows ?? 0),
    email_cost_is_estimated: Boolean(emailBlock?.layer_5_usage?.provider_cost_is_estimated),
  }

  return {
    sms: smsVolume(smsBlock, active),
    email: emailVolume(emailBlock, active),
    provider_layer: provider,
    school_credit_layer: credits,
    cash_layer: cash,
    usage_layer: usage,
    trend: (data.trend ?? []).map((point) => ({
      date: point.date ?? '',
      sms_segments: point.sms_segments ?? 0,
      email_credits: point.email_credits ?? point.emails ?? 0,
    })),
  }
}

/* ------------------------------------------------------------------ */
/* Profitability                                                       */
/* ------------------------------------------------------------------ */

type ProfitChannel = {
  cash_view?: {
    provider_purchases_ghs?: string
    provider_subscription_ghs?: string
    provider_overage_ghs?: string
    provider_other_ghs?: string
  }
  usage_view?: {
    paid_units_consumed?: number
    free_units?: number
    sponsored_units?: number
    usage_valued_revenue_ghs?: string
    provider_cost_ghs?: string
    gross_profit_ghs?: string
    gross_margin_pct?: string | number | null
    free_sponsored_expense_ghs?: string
    provider_cost_is_estimated?: boolean
  }
  credits_view?: { remaining_units?: number }
}

type ProfitPayload = {
  channels?: { sms?: ProfitChannel; email?: ProfitChannel }
  combined?: {
    cash_view?: {
      cash_received_from_schools_ghs?: string
      cash_paid_to_providers_ghs?: string
      net_cash_ghs?: string
    }
    usage_view?: {
      usage_valued_revenue_ghs?: string
      provider_cost_ghs?: string
      gross_profit_ghs?: string
      gross_margin_pct?: string | number | null
      free_sponsored_expense_ghs?: string
      overall_contribution_ghs?: string
      email_provider_cost_is_estimated?: boolean
    }
  }
}

function channelPnl(block: ProfitChannel | undefined) {
  const usage = block?.usage_view
  const cash = block?.cash_view
  if (!usage && !cash) return undefined
  const units = [usage?.paid_units_consumed, usage?.free_units, usage?.sponsored_units]
  return {
    provider_purchases_ghs: cash?.provider_purchases_ghs,
    subscription_expense_ghs: cash?.provider_subscription_ghs,
    overage_expense_ghs: cash?.provider_overage_ghs,
    provider_expenses_ghs: cash
      ? sumMoney([
          cash.provider_subscription_ghs,
          cash.provider_overage_ghs,
          cash.provider_other_ghs,
        ])
      : undefined,
    provider_cost_ghs: usage?.provider_cost_ghs,
    credit_revenue_ghs: usage?.usage_valued_revenue_ghs,
    usage_valued_revenue_ghs: usage?.usage_valued_revenue_ghs,
    gross_profit_ghs: usage?.gross_profit_ghs,
    gross_margin_pct: asNumber(usage?.gross_margin_pct),
    units_consumed: usage ? units.reduce<number>((total, value) => total + (value ?? 0), 0) : undefined,
    cost_is_estimated: usage?.provider_cost_is_estimated,
  }
}

export function adaptProfitability(payload: unknown): Profitability {
  const data = payload as ProfitPayload
  if (!data?.channels && !data?.combined) return (payload ?? {}) as Profitability

  const cashView = data.combined?.cash_view
  const usageView = data.combined?.usage_view
  const purchases = sumMoney([
    data.channels?.sms?.cash_view?.provider_purchases_ghs,
    data.channels?.email?.cash_view?.provider_purchases_ghs,
  ])
  const expenses = sumMoney([
    data.channels?.sms?.cash_view?.provider_subscription_ghs,
    data.channels?.sms?.cash_view?.provider_overage_ghs,
    data.channels?.sms?.cash_view?.provider_other_ghs,
    data.channels?.email?.cash_view?.provider_subscription_ghs,
    data.channels?.email?.cash_view?.provider_overage_ghs,
    data.channels?.email?.cash_view?.provider_other_ghs,
  ])
  const unused =
    (data.channels?.sms?.credits_view?.remaining_units ?? 0) +
    (data.channels?.email?.credits_view?.remaining_units ?? 0)

  return {
    cash: cashView
      ? {
          received_from_schools_ghs: cashView.cash_received_from_schools_ghs ?? '0.00',
          topup_cash_ghs: '',
          addon_cash_ghs: '',
          paid_to_providers_ghs: cashView.cash_paid_to_providers_ghs ?? '0.00',
          provider_purchases_ghs: purchases,
          provider_expenses_ghs: expenses,
          net_cash_ghs: cashView.net_cash_ghs ?? '0.00',
        }
      : undefined,
    sms: channelPnl(data.channels?.sms),
    email: channelPnl(data.channels?.email),
    combined: usageView
      ? {
          usage_valued_revenue_ghs: usageView.usage_valued_revenue_ghs,
          provider_cost_ghs: usageView.provider_cost_ghs,
          gross_profit_ghs: usageView.gross_profit_ghs,
          gross_margin_pct: asNumber(usageView.gross_margin_pct),
          free_sponsored_expense_ghs: usageView.free_sponsored_expense_ghs,
          overall_contribution_ghs: usageView.overall_contribution_ghs,
          cost_is_estimated: usageView.email_provider_cost_is_estimated,
          unused_credits_units: unused,
        }
      : { unused_credits_units: unused },
  }
}

/* ------------------------------------------------------------------ */
/* Schools                                                             */
/* ------------------------------------------------------------------ */

export function adaptSchoolUsage(payload: Paginated<Dict> | null | undefined): Paginated<SchoolUsageRow> {
  const results = (payload?.results ?? []).map((row) => {
    const sms = asRecord(row.sms)
    const email = asRecord(row.email)
    const economics = asRecord(row.economics)
    const addons = asRecord(row.addons)
    return {
      school: String(row.school_id ?? row.school ?? ''),
      school_name: String(row.school_name ?? ''),
      paid_sms_segments: asNumber(sms?.paid_segments ?? row.paid_sms_segments) ?? 0,
      free_sms_segments: asNumber(sms?.free_segments ?? row.free_sms_segments) ?? 0,
      sponsored_sms_segments: asNumber(sms?.sponsored_segments ?? row.sponsored_sms_segments) ?? 0,
      sms_balance: asNumber(sms?.balance_units ?? row.sms_balance) ?? 0,
      paid_email_credits: asNumber(email?.paid_emails ?? row.paid_email_credits) ?? 0,
      free_email_credits: asNumber(email?.free_emails ?? row.free_email_credits) ?? 0,
      sponsored_email_credits: asNumber(email?.sponsored_emails ?? row.sponsored_email_credits) ?? 0,
      email_balance: asNumber(email?.balance_units ?? row.email_balance) ?? 0,
      provider_cost_ghs: asString(economics?.provider_cost_ghs ?? row.provider_cost_ghs) ?? undefined,
      revenue_ghs: asString(economics?.usage_valued_revenue_ghs ?? row.revenue_ghs) ?? undefined,
      gross_profit_ghs:
        asString(economics?.gross_profit_contribution_ghs ?? row.gross_profit_ghs) ?? undefined,
      sms_addon_enabled: Boolean(addons?.sms_addon_enabled ?? row.sms_addon_enabled),
      email_addon_enabled: Boolean(addons?.email_addon_enabled ?? row.email_addon_enabled),
    }
  })
  return {
    count: payload?.count ?? results.length,
    next: payload?.next ?? null,
    previous: payload?.previous ?? null,
    results,
  }
}

function deliveryStats(raw: unknown): DeliveryStats | undefined {
  const statuses = asRecord(raw)
  if (!statuses) return undefined
  const submitted = asNumber(statuses.submitted) ?? 0
  const delivered = asNumber(statuses.delivered) ?? 0
  const failed = asNumber(statuses.failed) ?? 0
  const skipped = asNumber(statuses.skipped) ?? 0
  const unknown = asNumber(statuses.unknown) ?? 0
  const total = submitted + delivered + failed + skipped + unknown
  return {
    submitted,
    delivered,
    failed,
    skipped,
    unknown,
    success_rate_pct: total === 0 ? null : (delivered / total) * 100,
  }
}

export function adaptSchoolReport(payload: unknown): SchoolMessagingReport {
  const data = asRecord(payload)
  if (!data) return {}
  if (data.balances || data.credits || data.delivery_stats) return payload as SchoolMessagingReport

  const channels = asRecord(data.channels)
  const sms = asRecord(channels?.sms)
  const email = asRecord(channels?.email)
  const smsCredits = asRecord(sms?.credits)
  const emailCredits = asRecord(email?.credits)
  const smsClass = asRecord(sms?.classification)
  const emailClass = asRecord(email?.classification)
  const smsUsage = asRecord(sms?.usage)
  const emailUsage = asRecord(email?.usage)
  const cash = asRecord(data.layer_3_cash_from_school)
  const school = asRecord(data.school)

  const credit = (key: string) =>
    (asNumber(smsCredits?.[key]) ?? 0) + (asNumber(emailCredits?.[key]) ?? 0)

  return {
    school: school
      ? { id: String(school.id ?? ''), name: String(school.name ?? ''), status: asString(school.status) ?? undefined }
      : undefined,
    balances: {
      sms: asNumber(sms?.balance_units) ?? 0,
      email: asNumber(email?.balance_units) ?? 0,
    },
    credits: {
      purchased: credit('topup_units'),
      allocated: credit('allocation_recurring_units'),
      promo: credit('promo_grant_units'),
      consumed: credit('consumed_units'),
      reversed: credit('reversal_units'),
      remaining: (asNumber(sms?.balance_units) ?? 0) + (asNumber(email?.balance_units) ?? 0),
    },
    free_usage: {
      free_sms_segments: asNumber(asRecord(smsClass?.free)?.units) ?? 0,
      sponsored_sms_segments: asNumber(asRecord(smsClass?.sponsored)?.units) ?? 0,
      free_email_credits: asNumber(asRecord(emailClass?.free)?.units) ?? 0,
      sponsored_email_credits: asNumber(asRecord(emailClass?.sponsored)?.units) ?? 0,
      platform_funded_expense_ghs: sumMoney([
        asRecord(smsClass?.free)?.provider_cost_ghs,
        asRecord(smsClass?.sponsored)?.provider_cost_ghs,
        asRecord(emailClass?.free)?.provider_cost_ghs,
        asRecord(emailClass?.sponsored)?.provider_cost_ghs,
      ]),
    },
    provider_cost: {
      sms_ghs: asString(smsUsage?.provider_cost_ghs) ?? '0.00',
      email_ghs: asString(emailUsage?.provider_cost_ghs) ?? '0.00',
      email_is_estimated: Boolean(emailUsage?.provider_cost_is_estimated),
    },
    revenue: {
      topup_cash_ghs: asString(cash?.topup_cash_ghs) ?? '0.00',
      addon_cash_ghs: asString(cash?.addon_cash_ghs) ?? '0.00',
      usage_valued_ghs: sumMoney([
        smsUsage?.usage_valued_revenue_ghs,
        emailUsage?.usage_valued_revenue_ghs,
      ]),
    },
    delivery_stats: {
      sms: deliveryStats(sms?.delivery_statuses),
      email: deliveryStats(email?.delivery_statuses),
    },
    ledger: Array.isArray(data.ledger) ? (data.ledger as SchoolMessagingReport['ledger']) : [],
    topups: Array.isArray(data.topup_history)
      ? data.topup_history.map((row) => {
          const topup = asRecord(row) ?? {}
          return {
            id: String(topup.id ?? ''),
            channel: (topup.channel === 'email' ? 'email' : 'sms') as 'sms' | 'email',
            package_name: asString(topup.package) ?? 'Custom',
            credits: asNumber(topup.credits) ?? 0,
            amount_ghs: asString(topup.amount_ghs) ?? '0.00',
            status: asString(topup.status) ?? '',
            purchased_at: asString(topup.created_at ?? topup.purchased_at) ?? '',
          }
        })
      : (data.topups as SchoolMessagingReport['topups']),
    trend: Array.isArray(data.trend)
      ? data.trend.map((row) => {
          const point = asRecord(row) ?? {}
          return {
            date: asString(point.date) ?? '',
            sms_segments: asNumber(point.sms_segments) ?? 0,
            email_credits: asNumber(point.email_credits ?? point.emails) ?? 0,
          }
        })
      : [],
  }
}

/* ------------------------------------------------------------------ */
/* Free usage & transactions                                           */
/* ------------------------------------------------------------------ */

type ClassMetrics = { messages?: number; units?: number; segments?: number; provider_cost_ghs?: string }

export function adaptFreeUsage(payload: unknown): FreeUsageStats {
  const data = asRecord(payload)
  if (!data) return {}
  if ('free_sms_segments' in data) return payload as FreeUsageStats
  const sms = asRecord(data.sms)
  const email = asRecord(data.email)
  const smsFree = asRecord(sms?.free) as ClassMetrics | undefined
  const smsSponsored = asRecord(sms?.sponsored) as ClassMetrics | undefined
  const emailFree = asRecord(email?.free) as ClassMetrics | undefined
  const emailSponsored = asRecord(email?.sponsored) as ClassMetrics | undefined
  return {
    free_sms_messages: smsFree?.messages ?? 0,
    free_sms_segments: smsFree?.units ?? smsFree?.segments ?? 0,
    sponsored_sms_messages: smsSponsored?.messages ?? 0,
    sponsored_sms_segments: smsSponsored?.units ?? smsSponsored?.segments ?? 0,
    free_email_credits: emailFree?.units ?? emailFree?.messages ?? 0,
    sponsored_email_credits: emailSponsored?.units ?? emailSponsored?.messages ?? 0,
    platform_funded_expense_ghs: sumMoney([
      smsFree?.provider_cost_ghs,
      smsSponsored?.provider_cost_ghs,
      emailFree?.provider_cost_ghs,
      emailSponsored?.provider_cost_ghs,
    ]),
    budget_ghs: asString(data.budget_ghs),
    budget_used_pct: asNumber(data.budget_used_pct),
    by_school: adaptFreeUsageSchools(data.by_school),
  }
}

function adaptFreeUsageSchools(value: unknown): FreeUsageStats['by_school'] {
  if (!Array.isArray(value)) return undefined
  return value.map((row) => {
    const record = asRecord(row) ?? {}
    return {
      school: asString(record.school) ?? '',
      school_name: asString(record.school_name) ?? '',
      free_sms_segments: asNumber(record.free_sms_segments) ?? 0,
      sponsored_sms_segments: asNumber(record.sponsored_sms_segments) ?? 0,
      free_email_credits: asNumber(record.free_email_credits) ?? 0,
      sponsored_email_credits: asNumber(record.sponsored_email_credits) ?? 0,
      expense_ghs: asString(record.expense_ghs) ?? '0.00',
    }
  })
}

const TYPE_TO_API: Record<string, string> = {
  provider_purchase: 'provider_purchase',
  provider_expense: 'provider_expense',
  school_topup: 'school_topup_payment',
  addon_allocation: 'credit_allocation',
  sms_deduction: 'credit_usage_debit',
  email_deduction: 'credit_usage_debit',
  free_message: 'free_send',
  sponsored_message: 'sponsored_send',
  reversal: 'credit_reversal',
  promo_grant: 'credit_promo_grant',
  manual_adjust: 'credit_manual_adjust',
  pricing_change: 'pricing_change',
  reconciliation: 'reconciliation_resolution',
}

const TYPE_FROM_API: Record<string, TransactionType> = {
  provider_purchase: 'provider_purchase',
  provider_expense: 'provider_expense',
  school_topup_payment: 'school_topup',
  credit_allocation: 'addon_allocation',
  credit_topup: 'school_topup',
  credit_reversal: 'reversal',
  credit_promo_grant: 'promo_grant',
  credit_manual_adjust: 'manual_adjust',
  free_send: 'free_message',
  sponsored_send: 'sponsored_message',
  sms_pricing_change: 'pricing_change',
  email_pricing_change: 'pricing_change',
  pricing_change: 'pricing_change',
  reconciliation_resolution: 'reconciliation',
}

export function transactionQueryType(type: string | undefined) {
  if (!type) return undefined
  return TYPE_TO_API[type] ?? type
}

export function adaptTransactions(payload: Paginated<Dict> | null | undefined): Paginated<MessagingTransaction> {
  const results = (payload?.results ?? []).map((row, index) => {
    const kind = String(row.type ?? row.transaction_type ?? '')
    const rawChannel = asString(row.channel)
    const channel: Channel | null = rawChannel === 'sms' || rawChannel === 'email' ? rawChannel : null
    let transactionType: TransactionType | string = TYPE_FROM_API[kind] ?? kind
    if (kind === 'credit_usage_debit') {
      transactionType = channel === 'email' ? 'email_deduction' : 'sms_deduction'
    }
    const reference = asString(row.reference) ?? ''
    return {
      id: String(row.id ?? [row.occurred_at, kind, reference, row.school_id, index].join(':')),
      occurred_at: String(row.occurred_at ?? ''),
      transaction_type: transactionType,
      description: asString(row.description) ?? undefined,
      amount_ghs: asString(row.amount_ghs),
      units: asNumber(row.credits ?? row.units),
      channel,
      reference,
      school: asString(row.school_id ?? row.school),
      school_name: asString(row.school_name),
      provider: (asString(row.provider) as MessagingTransaction['provider']) ?? null,
      actor_name: asString(row.administrator ?? row.actor_name),
    }
  })
  return {
    count: payload?.count ?? results.length,
    next: payload?.next ?? null,
    previous: payload?.previous ?? null,
    results,
  }
}
