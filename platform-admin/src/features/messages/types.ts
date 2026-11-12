/**
 * View models for `/api/v1/platform/messages/*`.
 *
 * The API nests figures by money layer (`channels`, `providers`, `layer_3_*`).
 * `adapt.ts` flattens that payload into these types. A missing figure stays
 * null so the UI can render "—" instead of crashing.
 */

export type Paginated<T> = {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type Channel = 'sms' | 'email'
export type Classification = 'paid' | 'free' | 'sponsored'
export type Provider = 'arkesel' | 'ses' | 'resend'
export type SmsEncoding = 'gsm7' | 'ucs2'

/** Must match backend ``communications.services.ranges.RANGE_CHOICES``. */
export type RangePreset =
  | 'today'
  | 'last_7'
  | 'last_30'
  | 'this_month'
  | 'last_month'
  | 'custom'

/** Query params shared by every Messages data surface (§2.18). */
export type RangeParams = {
  range?: RangePreset
  /** Custom range start — query key ``from``. */
  from?: string
  /** Custom range end — query key ``to``. */
  to?: string
  channel?: Channel
  classification?: Classification
  school?: string
}

/* ------------------------------------------------------------------ */
/* Overview                                                            */
/* ------------------------------------------------------------------ */

export type SmsVolume = {
  segments_total: number
  segments_paid: number
  segments_free: number
  segments_sponsored: number
  messages_total: number
  recipients_total: number
  submitted: number
  delivered: number
  failed: number
  skipped: number
  unknown: number
}

export type EmailVolume = {
  credits_total: number
  credits_paid: number
  credits_free: number
  credits_sponsored: number
  accepted: number
  submitted: number
  delivered: number
  failed: number
  skipped: number
  unknown: number
}

/** Layer 1 — provider wallet / plan. Never summed with any other layer. */
export type ProviderLayer = {
  arkesel_sms_balance: number | null
  arkesel_captured_at: string | null
  arkesel_api_status: string | null
  ses_monthly_used?: number | null
  ses_monthly_limit?: number | null
  ses_captured_at?: string | null
  ses_api_status?: string | null
  /** @deprecated Prefer ses_* — kept while overview payloads catch up. */
  resend_monthly_used: number | null
  resend_monthly_limit: number | null
  resend_captured_at: string | null
  resend_api_status: string | null
}

/** Layer 2 — school credit wallets (units). */
export type SchoolCreditLayer = {
  sms_outstanding_units: number | null
  email_outstanding_units: number | null
  allocated_units: number
  consumed_units: number
}

/** Layers 3 & 4 — cash in from schools, cash out to providers (GHS). */
export type CashLayer = {
  received_from_schools_ghs: string
  topup_cash_ghs: string
  addon_cash_ghs: string
  paid_to_providers_ghs: string
  provider_purchases_ghs: string
  provider_expenses_ghs: string
}

/** Layer 5 — usage economics valued at send-time snapshots. */
export type UsageLayer = {
  usage_valued_revenue_ghs: string
  provider_cost_ghs: string
  gross_profit_ghs: string
  gross_margin_pct: number | null
  free_sponsored_expense_ghs: string
  unpriced_units: number
  email_cost_is_estimated: boolean
}

export type TrendPoint = {
  date: string
  sms_segments: number
  email_credits: number
}

export type MessagesOverview = {
  range_start?: string
  range_end?: string
  sms?: SmsVolume
  email?: EmailVolume
  provider_layer?: ProviderLayer
  school_credit_layer?: SchoolCreditLayer
  cash_layer?: CashLayer
  usage_layer?: UsageLayer
  trend?: TrendPoint[]
}

/* ------------------------------------------------------------------ */
/* Pricing configuration                                               */
/* ------------------------------------------------------------------ */

export type SmsEncodingConfig = {
  id: string
  encoding: SmsEncoding
  provider_cost_per_segment_ghs: string
  school_price_per_segment_ghs: string
  single_segment_limit: number
  multipart_segment_limit: number
  effective_from: string
  effective_to: string | null
  is_active: boolean
  changed_by_name?: string | null
  created_at: string
}

export type SmsEncodingConfigInput = {
  encoding: SmsEncoding
  provider_cost_per_segment_ghs: string
  school_price_per_segment_ghs: string
  single_segment_limit: number
  multipart_segment_limit: number
  effective_from?: string
}

export type EmailPricingConfig = {
  id: string
  school_price_per_credit_ghs: string
  estimated_provider_cost_per_email_ghs: string
  billing_unit: string
  effective_from: string
  effective_to: string | null
  is_active: boolean
  changed_by_name?: string | null
  created_at: string
}

export type EmailPricingConfigInput = {
  school_price_per_credit_ghs: string
  estimated_provider_cost_per_email_ghs: string
  effective_from?: string
}

export type SmsCalculatorResult = {
  encoding: SmsEncoding | string
  characters: number
  segments: number
  credits_per_recipient: number
  limits_used?: {
    single_segment_limit: number
    multipart_segment_limit: number
    config_id?: string | null
    effective_from?: string | null
  }
}

/* ------------------------------------------------------------------ */
/* Providers                                                           */
/* ------------------------------------------------------------------ */

export type ProviderAccount = {
  id: string
  provider: Provider
  channel: Channel
  display_name: string
  api_status: string
  last_synced_at: string | null
  metadata?: Record<string, unknown>
}

export type ProviderBalanceSnapshot = {
  id: string
  sms_balance: number | null
  main_balance_text: string | null
  captured_at: string
  source: 'api' | 'manual'
}

export type SesUsageSnapshot = {
  id: string
  monthly_used: number | null
  monthly_limit: number | null
  daily_used: number | null
  daily_limit: number | null
  sent_count: number | null
  received_count: number | null
  captured_at: string
  source: 'api' | 'manual'
  placeholder?: boolean
}

/** @deprecated Use SesUsageSnapshot */
export type ResendUsageSnapshot = SesUsageSnapshot

export type ProviderPurchase = {
  id: string
  provider: Provider
  channel: Channel
  amount_ghs: string
  credits_or_units: number
  effective_cost_per_unit: string
  provider_reference: string
  purchased_at: string
  payment_method: string
  notes: string
  recorded_by_name?: string | null
}

export type ProviderPurchaseInput = {
  provider: Provider
  channel: Channel
  amount_ghs: string
  credits_or_units: number
  provider_reference?: string
  purchased_at?: string
  payment_method?: string
  notes?: string
}

export type ExpenseKind = 'subscription' | 'overage' | 'other'

export type ProviderExpense = {
  id: string
  provider: Provider
  expense_kind: ExpenseKind
  period_start: string
  period_end: string
  amount_ghs: string
  units: number | null
  notes: string
  source: 'manual' | 'import'
  recorded_by_name?: string | null
}

export type ProviderExpenseInput = {
  provider: Provider
  expense_kind: ExpenseKind
  period_start: string
  period_end: string
  amount_ghs: string
  units?: number | null
  notes?: string
}

/* ------------------------------------------------------------------ */
/* School usage & reports                                              */
/* ------------------------------------------------------------------ */

export type SchoolUsageRow = {
  school: string
  school_name: string
  paid_sms_segments: number
  free_sms_segments: number
  sponsored_sms_segments: number
  sms_balance: number
  paid_email_credits: number
  free_email_credits: number
  sponsored_email_credits: number
  email_balance: number
  provider_cost_ghs?: string
  revenue_ghs?: string
  gross_profit_ghs?: string
  sms_addon_enabled?: boolean
  email_addon_enabled?: boolean
}

export type DeliveryStats = {
  submitted: number
  delivered: number
  failed: number
  skipped: number
  unknown: number
  success_rate_pct: number | null
}

export type LedgerEntryType =
  | 'allocation_recurring'
  | 'topup'
  | 'promo_grant'
  | 'usage_debit'
  | 'manual_adjust'
  | 'reversal'

export type LedgerEntry = {
  id: string
  channel: Channel
  entry_type: LedgerEntryType
  delta: number
  balance_after: number
  occurred_at: string
  notes?: string
}

export type SchoolTopUp = {
  id: string
  channel: Channel
  package_name: string
  credits: number
  amount_ghs: string
  status: string
  purchased_at: string
}

export type SchoolMessagingReport = {
  school?: { id: string; name: string; status?: string }
  balances?: { sms: number; email: number }
  credits?: {
    purchased: number
    allocated: number
    promo: number
    consumed: number
    reversed: number
    remaining: number
  }
  free_usage?: {
    free_sms_segments: number
    sponsored_sms_segments: number
    free_email_credits: number
    sponsored_email_credits: number
    platform_funded_expense_ghs: string
  }
  provider_cost?: { sms_ghs: string; email_ghs: string; email_is_estimated: boolean }
  revenue?: { topup_cash_ghs: string; addon_cash_ghs: string; usage_valued_ghs: string }
  delivery_stats?: { sms?: DeliveryStats; email?: DeliveryStats }
  ledger?: LedgerEntry[]
  topups?: SchoolTopUp[]
  trend?: TrendPoint[]
}

/* ------------------------------------------------------------------ */
/* Free & sponsored                                                    */
/* ------------------------------------------------------------------ */

export type AllowancePolicy = {
  id: string
  scope: 'school' | 'platform'
  school: string | null
  school_name?: string | null
  channel: Channel
  monthly_free_units: number
  daily_limit_units: number | null
  applies_to_events: string[]
  budget_ghs: string | null
  alert_thresholds: number[]
  starts_at: string | null
  ends_at: string | null
  is_active: boolean
  created_by_name?: string | null
}

export type AllowancePolicyInput = {
  scope: 'school' | 'platform'
  school?: string | null
  channel: Channel
  monthly_free_units: number
  daily_limit_units?: number | null
  applies_to_events?: string[]
  budget_ghs?: string | null
  alert_thresholds?: number[]
  starts_at?: string | null
  ends_at?: string | null
  is_active?: boolean
}

export type FreeUsageStats = {
  free_sms_messages?: number
  free_sms_segments?: number
  free_email_credits?: number
  sponsored_sms_messages?: number
  sponsored_sms_segments?: number
  sponsored_email_credits?: number
  platform_funded_expense_ghs?: string
  budget_ghs?: string | null
  budget_used_pct?: number | null
  by_school?: Array<{
    school: string
    school_name: string
    free_sms_segments: number
    free_email_credits: number
    sponsored_sms_segments: number
    sponsored_email_credits: number
    expense_ghs: string
  }>
}

/* ------------------------------------------------------------------ */
/* Profitability                                                       */
/* ------------------------------------------------------------------ */

export type ProfitabilityView = 'cash' | 'usage'

export type ChannelPnl = {
  provider_purchases_ghs?: string
  provider_expenses_ghs?: string
  subscription_expense_ghs?: string
  overage_expense_ghs?: string
  provider_cost_ghs?: string
  credit_revenue_ghs?: string
  addon_revenue_ghs?: string
  usage_valued_revenue_ghs?: string
  gross_profit_ghs?: string
  gross_margin_pct?: number | null
  units_consumed?: number
  cost_is_estimated?: boolean
}

export type Profitability = {
  view?: ProfitabilityView
  range_start?: string
  range_end?: string
  cash?: {
    received_from_schools_ghs: string
    topup_cash_ghs: string
    addon_cash_ghs: string
    paid_to_providers_ghs: string
    provider_purchases_ghs: string
    provider_expenses_ghs: string
    net_cash_ghs: string
  }
  sms?: ChannelPnl
  email?: ChannelPnl
  combined?: ChannelPnl & {
    free_sponsored_expense_ghs?: string
    overall_contribution_ghs?: string
    unused_credits_units?: number
  }
  trend?: Array<{ date: string; revenue_ghs: string; cost_ghs: string }>
}

/* ------------------------------------------------------------------ */
/* Transactions                                                        */
/* ------------------------------------------------------------------ */

export type TransactionType =
  | 'provider_purchase'
  | 'provider_expense'
  | 'school_topup'
  | 'addon_allocation'
  | 'sms_deduction'
  | 'email_deduction'
  | 'free_message'
  | 'sponsored_message'
  | 'reversal'
  | 'promo_grant'
  | 'manual_adjust'
  | 'pricing_change'
  | 'reconciliation'

export type MessagingTransaction = {
  id: string
  occurred_at: string
  transaction_type: TransactionType | string
  description?: string
  amount_ghs: string | null
  units: number | null
  channel: Channel | null
  reference: string
  school: string | null
  school_name: string | null
  provider: Provider | null
  actor_name: string | null
}

/* ------------------------------------------------------------------ */
/* Reconciliation                                                      */
/* ------------------------------------------------------------------ */

export type ReconciliationRun = {
  id: string
  provider: Provider
  channel: Channel
  window_start: string
  window_end: string
  status: string
  matched_count: number
  unmatched_count: number
  discrepancy_count: number
  started_at: string
  finished_at: string | null
  triggered_by_name?: string | null
  error_detail?: string
}

export type DiscrepancyType =
  | 'missing_internally'
  | 'missing_at_provider'
  | 'status_mismatch'
  | 'unit_count_mismatch'
  | 'unbilled_send'

export type ReconciliationResolution = 'open' | 'accepted' | 'adjusted' | 'ignored'

export type ReconciliationItem = {
  id: string
  internal_delivery_type: string | null
  internal_delivery_id: string | null
  provider_message_id: string | null
  discrepancy_type: DiscrepancyType | string
  resolution: ReconciliationResolution
  resolution_note: string
  resolved_by_name?: string | null
  resolved_at: string | null
  provider_payload?: Record<string, unknown>
}
