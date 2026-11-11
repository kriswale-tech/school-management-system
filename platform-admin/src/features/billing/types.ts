export type Plan = {
  id: string
  code: string
  name: string
  student_min: number
  student_max: number | null
  staff_min: number
  staff_max: number | null
  price_monthly_ghs: string
  price_annual_ghs: string
  warning_thresholds: number[]
  sort_order: number
  is_active: boolean
}

export type PlanInput = {
  code: string
  name: string
  student_min: number
  student_max: number | null
  staff_min: number
  staff_max: number | null
  price_monthly_ghs: string
  price_annual_ghs: string
  sort_order?: number
  is_active?: boolean
  warning_thresholds?: number[]
}

export type Capacity = {
  active_students: number
  capacity_max: number | null
  active_staff: number
  staff_capacity_max: number | null
  plan_code: string | null
  plan_name: string | null
  warnings: number[]
  triggered_warnings: number[]
  at_or_over_capacity: boolean
  at_or_over_student_capacity: boolean
  at_or_over_staff_capacity: boolean
  usage_ratio: number | null
  staff_usage_ratio: number | null
}

export type AddonPlanBrief = {
  id: string
  code: string
  name: string
  is_active: boolean
}

export type AddonSku = {
  id: string
  code: string
  name: string
  channel: 'sms' | 'email'
  interval: 'monthly' | 'annual'
  credits_per_period: number
  price_ghs: string
  /** Messages sell unit price (informational). */
  unit_price_ghs?: string
  /** credits × Messages sell price (informational — not billed). */
  reference_price_ghs?: string
  /** Messages provider unit cost (informational). */
  provider_unit_cost_ghs?: string
  /** credits × provider unit cost (informational). */
  cost_price_ghs?: string
  available_plans?: AddonPlanBrief[]
  available_plan_ids?: string[]
  sort_order: number
  is_active: boolean
}

export type AddonSkuInput = {
  code: string
  name: string
  channel: 'sms' | 'email'
  interval: 'monthly' | 'annual'
  credits_per_period: number
  price_ghs: string
  available_plan_ids?: string[]
  sort_order?: number
  is_active?: boolean
}

export type Subscription = {
  id: string
  school: string
  plan: Plan
  interval: 'monthly' | 'annual'
  status: string
  is_current: boolean
  current_period_start: string
  current_period_end: string
  grace_period_ends_at?: string | null
  dunning_notice_sent_at?: string | null
  billing_suspended_school?: boolean
  sms_addon_enabled: boolean
  email_addon_enabled: boolean
  sms_sku: AddonSku | null
  email_sku: AddonSku | null
  pending_plan: Plan | null
  pending_interval: string
  pending_sms_enabled: boolean | null
  pending_email_enabled: boolean | null
  pending_sms_sku?: AddonSku | null
  pending_email_sku?: AddonSku | null
  pending_change_effective_at: string | null
  app_price_snapshot_ghs: string | null
  capacity: Capacity
  discounts?: SchoolDiscount[]
}

export type SchoolDiscount = {
  id: string
  campaign_id: string
  code: string
  name: string
  discount_percent: string
  schedule: 'introductory' | 'recurring' | 'date_range'
  applies_to: 'application' | 'communication' | 'all'
  starts_at: string | null
  ends_at: string | null
}

export type DiscountSchool = {
  id: string
  name: string
}

export type DiscountRedemption = {
  id: string
  school: string
  school_name: string
  starts_at: string
  ends_at: string | null
  discount_percent: string
  applies_to: string
  schedule: string
  billing_interval: string
  revoked_at: string | null
  created_at: string
}

export type PlatformDiscount = {
  id: string
  code: string
  name: string
  discount_percent: string
  applies_to: 'application' | 'communication' | 'all'
  schedule: 'introductory' | 'recurring' | 'date_range'
  audience: 'all' | 'new' | 'selected'
  billing_interval: '' | 'monthly' | 'annual'
  duration_months: number
  starts_at: string | null
  ends_at: string | null
  is_active: boolean
  schools: DiscountSchool[]
  redemption_count: number
  redemptions?: DiscountRedemption[]
  created_at: string
  updated_at: string
}

export type DiscountInput = {
  code: string
  name: string
  discount_percent: string
  applies_to: PlatformDiscount['applies_to']
  schedule: PlatformDiscount['schedule']
  audience: PlatformDiscount['audience']
  billing_interval: PlatformDiscount['billing_interval']
  duration_months: number
  starts_at: string | null
  ends_at: string | null
  is_active: boolean
  school_ids: string[]
}

export type TopUpPackage = {
  id: string
  code: string
  name: string
  channel: 'sms' | 'email'
  credits: number
  discount_percent: string
  unit_price_ghs?: string
  list_price_ghs?: string
  provider_unit_cost_ghs?: string
  cost_price_ghs?: string
  price_ghs: string
  sort_order: number
  is_active: boolean
}

export type TopUpPackageInput = {
  code: string
  name: string
  channel: 'sms' | 'email'
  credits: number
  discount_percent: string
  sort_order?: number
  is_active?: boolean
}

export type SaasPayment = {
  id: string
  school: string
  school_name?: string
  invoice: string | null
  purpose: string
  purpose_label?: string
  label?: string
  tag?: string
  topup_channel?: string | null
  topup_credits?: number | null
  package_name?: string | null
  invoice_notes?: string
  provider: string
  status: string
  amount_ghs: string
  currency: string
  reference: string
  provider_transaction_id?: string
  authorization_url: string
  paid_at: string | null
  created_at: string
}

export type PaginatedPayments = {
  count: number
  next: string | null
  previous: string | null
  results: SaasPayment[]
}

export type Invoice = {
  id: string
  currency: string
  status: string
  period_start: string
  period_end: string
  subtotal_ghs: string
  discount_ghs: string
  total_ghs: string
  amount_paid_ghs: string
  paid_at: string | null
  notes?: string
  created_at: string
}

export type PaginatedInvoices = {
  count: number
  next: string | null
  previous: string | null
  results: Invoice[]
}
