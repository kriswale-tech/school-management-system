import api from '@/lib/api'
import type {
  AddonSku,
  AddonSkuInput,
  PaginatedInvoices,
  PaginatedPayments,
  Plan,
  PlanInput,
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

export async function listSchoolInvoices(schoolId: string) {
  const { data } = await api.get<PaginatedInvoices>(
    `/platform/billing/schools/${schoolId}/invoices/`,
  )
  return data
}

export async function markInvoicePaid(invoiceId: string) {
  const { data } = await api.post(`/platform/billing/invoices/${invoiceId}/mark-paid/`)
  return data
}

export type CreditBalances = {
  sms: number
  email: number
  billing_active: boolean
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
}) {
  const { data } = await api.get<PaginatedPayments>('/platform/billing/payments/', { params })
  return data
}

export async function listSchoolPayments(schoolId: string) {
  const { data } = await api.get<PaginatedPayments>(
    `/platform/billing/schools/${schoolId}/payments/`,
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

