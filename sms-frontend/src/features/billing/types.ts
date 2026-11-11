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

export type AddonSku = {
  id: string
  code: string
  name: string
  channel: 'sms' | 'email'
  interval: 'monthly' | 'annual'
  credits_per_period: number
  price_ghs: string
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
  grace_period_ends_at: string | null
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
  pending_sms_sku: AddonSku | null
  pending_email_sku: AddonSku | null
  pending_change_effective_at: string | null
  app_price_snapshot_ghs: string | null
  capacity: Capacity
}

export type CreditBalances = {
  sms: number
  email: number
  billing_active: boolean
}

export type InvoiceLine = {
  id: string
  kind: string
  description: string
  quantity: string
  unit_price_ghs: string
  amount_ghs: string
  metadata: Record<string, unknown>
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
  due_at: string | null
  paid_at: string | null
  notes: string
  lines: InvoiceLine[]
  created_at: string
}

export type PaginatedInvoices = {
  count: number
  next: string | null
  previous: string | null
  results: Invoice[]
}

export type TopUpPackage = {
  id: string
  code: string
  name: string
  channel: 'sms' | 'email'
  credits: number
  price_ghs: string
  sort_order: number
  is_active: boolean
}

export type SaasPayment = {
  id: string
  school: string
  invoice: string | null
  purpose: 'invoice' | 'topup'
  purpose_label?: string
  label?: string
  tag?: string
  topup_channel?: 'sms' | 'email' | null
  topup_credits?: number | null
  package_name?: string | null
  invoice_notes?: string
  provider: string
  status: string
  amount_ghs: string
  currency: string
  reference: string
  authorization_url: string
  access_code?: string
  paid_at: string | null
  created_at: string
}

export type UpcomingBillLine = {
  kind: string
  description: string
  amount_ghs: string
  metadata?: Record<string, unknown>
}

export type UpcomingBill = {
  kind: string
  due_at: string
  period_start: string
  period_end: string
  plan_code: string
  plan_name: string
  interval: 'monthly' | 'annual'
  currency: string
  subtotal_ghs: string
  discount_ghs: string
  total_ghs: string
  discount_label: string | null
  lines: UpcomingBillLine[]
  includes_pending_changes: boolean
  open_invoice_id: string | null
  open_invoice_total_ghs: string | null
  open_invoice_notes: string
}

export type PaymentStats = {
  total_paid_ghs: string
  open_balance_ghs: string
  successful_payments: number
  open_invoices: number
  paid_invoices: number
  by_purpose: Record<string, string>
}

export type PaginatedPayments = {
  count: number
  next: string | null
  previous: string | null
  results: SaasPayment[]
}
