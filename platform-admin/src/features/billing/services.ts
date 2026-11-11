import api from '@/lib/api'
import type {
  AddonSku,
  AddonSkuInput,
  PaginatedInvoices,
  PaginatedPayments,
  Plan,
  PlanInput,
  SaasPayment,
  Subscription,
  TopUpPackage,
  TopUpPackageInput,
  DiscountInput,
  DiscountRedemption,
  PlatformDiscount,
} from './types'

export async function listPlans() {
  const { data } = await api.get<Plan[]>('/platform/billing/plans/')
  return data
}

export async function createPlan(payload: PlanInput) {
  const { data } = await api.post<Plan>('/platform/billing/plans/', payload)
  return data
}

export async function patchPlan(id: string, payload: Partial<PlanInput>) {
  const { data } = await api.patch<Plan>(`/platform/billing/plans/${id}/`, payload)
  return data
}

export async function deletePlan(id: string) {
  await api.delete(`/platform/billing/plans/${id}/`)
}

export async function seedPlans() {
  const { data } = await api.post<Plan[]>('/platform/billing/plans/seed/')
  return data
}

export async function listAddonSkus() {
  const { data } = await api.get<AddonSku[]>('/platform/communications/skus/')
  return data
}

export async function createAddonSku(payload: AddonSkuInput) {
  const { data } = await api.post<AddonSku>('/platform/communications/skus/', payload)
  return data
}

export async function patchAddonSku(id: string, payload: Partial<AddonSkuInput>) {
  const { data } = await api.patch<AddonSku>(`/platform/communications/skus/${id}/`, payload)
  return data
}

export async function deleteAddonSku(id: string) {
  await api.delete(`/platform/communications/skus/${id}/`)
}

export async function getSchoolSubscription(schoolId: string) {
  const { data } = await api.get<Subscription>(
    `/platform/billing/schools/${schoolId}/subscription/`,
  )
  return data
}

export async function startSchoolSubscription(
  schoolId: string,
  payload: {
    plan_code?: string
    interval?: 'monthly' | 'annual'
    apply_first_year_free?: boolean
  } = {},
) {
  const { data } = await api.post<Subscription>(
    `/platform/billing/schools/${schoolId}/subscription/`,
    payload,
  )
  return data
}

export async function scheduleSchoolPlanChange(
  schoolId: string,
  payload: { plan_code?: string; interval?: 'monthly' | 'annual' },
) {
  const { data } = await api.post<Subscription>(
    `/platform/billing/schools/${schoolId}/subscription/schedule-change/`,
    payload,
  )
  return data
}

export type UpgradeQuote = {
  plan_code: string
  plan_name: string
  amount_ghs: string
  discount_ghs: string
  remaining_days: number
  total_days: number
}

export async function quoteSchoolUpgrade(schoolId: string, planCode: string) {
  const { data } = await api.get<UpgradeQuote>(
    `/platform/billing/schools/${schoolId}/subscription/upgrade-quote/`,
    { params: { plan_code: planCode } },
  )
  return data
}

export async function recordSchoolTopUp(schoolId: string, packageCode: string) {
  const { data } = await api.post<{
    package_code: string
    package_name: string
    channel: string
    credits: number
    amount_ghs: string
    status: string
  }>(`/platform/billing/schools/${schoolId}/topups/`, { package_code: packageCode })
  return data
}

export async function capacityUpgradeSchool(
  schoolId: string,
  payload: { plan_code?: string; mark_paid?: boolean } = {},
) {
  const { data } = await api.post<{ subscription: Subscription; invoice: InvoiceLike }>(
    `/platform/billing/schools/${schoolId}/subscription/capacity-upgrade/`,
    payload,
  )
  return data
}

type InvoiceLike = { id: string }

export const BILLING_PAGE_SIZE = 10

export async function listSchoolInvoices(schoolId: string, page = 1) {
  const { data } = await api.get<PaginatedInvoices>(
    `/platform/billing/schools/${schoolId}/invoices/`,
    { params: { page, page_size: BILLING_PAGE_SIZE } },
  )
  return data
}

export type SchoolFinance = {
  total_paid_ghs: string
  outstanding_ghs: string
  billed_ghs: string
  discount_ghs: string
  successful_payments: number
  open_invoices: number
  paid_invoices: number
  invoice_count: number
  payment_overdue: boolean
  by_purpose: Record<string, string>
}

export async function getSchoolFinance(schoolId: string) {
  const { data } = await api.get<SchoolFinance>(
    `/platform/billing/schools/${schoolId}/finance/`,
  )
  return data
}

export async function extendSchoolGrace(schoolId: string, until: string) {
  const { data } = await api.post<Subscription>(
    `/platform/billing/schools/${schoolId}/subscription/extend-grace/`,
    { until },
  )
  return data
}

export async function assignSchoolDiscount(schoolId: string, campaignId: string) {
  const { data } = await api.post<Subscription>(
    `/platform/billing/schools/${schoolId}/discounts/`,
    { campaign_id: campaignId },
  )
  return data
}

export async function markInvoicePaid(invoiceId: string) {
  const { data } = await api.post(`/platform/billing/invoices/${invoiceId}/mark-paid/`)
  return data
}

export type CreditChannelUsage = {
  balance: number
  used: number
  allowance: number
  exhaustion_ratio: number | null
}

export type CreditBalances = {
  sms: number
  email: number
  billing_active: boolean
  usage?: {
    sms: CreditChannelUsage
    email: CreditChannelUsage
  }
}

export async function getSchoolCredits(schoolId: string) {
  const { data } = await api.get<CreditBalances>(
    `/platform/communications/schools/${schoolId}/credits/`,
  )
  return data
}

export async function scheduleSchoolAddon(
  schoolId: string,
  payload: { channel: 'sms' | 'email'; enabled: boolean; sku_code?: string },
) {
  const { data } = await api.post<Subscription>(
    `/platform/communications/schools/${schoolId}/addons/schedule/`,
    payload,
  )
  return data
}

export async function adjustSchoolCredits(
  schoolId: string,
  payload: { channel: 'sms' | 'email'; delta: number; reason?: string },
) {
  const { data } = await api.post(
    `/platform/communications/schools/${schoolId}/credits/adjust/`,
    payload,
  )
  return data
}

export async function seedCommunicationSkus() {
  const { data } = await api.post<AddonSku[]>('/platform/communications/skus/seed/')
  return data
}

export async function listTopUpPackages() {
  const { data } = await api.get<TopUpPackage[]>('/platform/billing/topups/')
  return data
}

export async function createTopUpPackage(payload: TopUpPackageInput) {
  const { data } = await api.post<TopUpPackage>('/platform/billing/topups/', payload)
  return data
}

export async function seedTopUpPackages() {
  const { data } = await api.post<TopUpPackage[]>('/platform/billing/topups/seed/')
  return data
}

export async function patchTopUpPackage(id: string, payload: Partial<TopUpPackageInput>) {
  const { data } = await api.patch<TopUpPackage>(`/platform/billing/topups/${id}/`, payload)
  return data
}

export async function deleteTopUpPackage(id: string) {
  await api.delete(`/platform/billing/topups/${id}/`)
}

export async function listPayments(params?: {
  status?: string
  school?: string
  purpose?: string
  page?: number
}) {
  const { data } = await api.get<PaginatedPayments>('/platform/billing/payments/', {
    params: { page_size: BILLING_PAGE_SIZE, ...params },
  })
  return data
}

export async function verifyPayment(paymentId: string) {
  const { data } = await api.post<SaasPayment>(
    `/platform/billing/payments/${paymentId}/verify/`,
  )
  return data
}

export async function listSchoolPayments(schoolId: string, page = 1) {
  const { data } = await api.get<PaginatedPayments>(
    `/platform/billing/schools/${schoolId}/payments/`,
    { params: { page, page_size: BILLING_PAGE_SIZE } },
  )
  return data
}

export async function listDiscounts() {
  const { data } = await api.get<PlatformDiscount[]>('/platform/billing/discounts/')
  return data
}

export async function getDiscount(id: string) {
  const { data } = await api.get<PlatformDiscount>(`/platform/billing/discounts/${id}/`)
  return data
}

export async function createDiscount(payload: DiscountInput) {
  const { data } = await api.post<PlatformDiscount>('/platform/billing/discounts/', payload)
  return data
}

export async function patchDiscount(id: string, payload: Partial<DiscountInput>) {
  const { data } = await api.patch<PlatformDiscount>(`/platform/billing/discounts/${id}/`, payload)
  return data
}

export async function deleteDiscount(id: string) {
  await api.delete(`/platform/billing/discounts/${id}/`)
}

export async function revokeDiscount(discountId: string, redemptionId: string) {
  const { data } = await api.post<DiscountRedemption>(
    `/platform/billing/discounts/${discountId}/redemptions/${redemptionId}/revoke/`,
  )
  return data
}

export async function restoreDiscount(discountId: string, redemptionId: string) {
  const { data } = await api.post<DiscountRedemption>(
    `/platform/billing/discounts/${discountId}/redemptions/${redemptionId}/restore/`,
  )
  return data
}

