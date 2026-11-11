import api from '@/app/api/api'
import type {
  AddonSku,
  CreditBalances,
  PaginatedInvoices,
  PaginatedPayments,
  PaymentStats,
  Plan,
  SaasPayment,
  Subscription,
  TopUpPackage,
  UpcomingBill,
} from './types'

export async function getBillingSubscription() {
  const { data } = await api.get<Subscription>('/billing/subscription/')
  return data
}

export async function getBillingPlans() {
  const { data } = await api.get<Plan[]>('/billing/plans/')
  return data
}

export const BILLING_PAGE_SIZE = 10

export async function getBillingInvoices(page = 1) {
  const { data } = await api.get<PaginatedInvoices>('/billing/invoices/', {
    params: { page, page_size: BILLING_PAGE_SIZE },
  })
  return data
}

export async function getUpcomingBill() {
  const { data } = await api.get<UpcomingBill>('/billing/upcoming/')
  return data
}

export async function getBillingPayments(page = 1) {
  const { data } = await api.get<PaginatedPayments>('/billing/payments/', {
    params: { page, page_size: BILLING_PAGE_SIZE },
  })
  return data
}

export async function getBillingPaymentStats() {
  const { data } = await api.get<PaymentStats>('/billing/payments/stats/')
  return data
}

export async function getCommunicationCredits() {
  const { data } = await api.get<CreditBalances>('/communications/credits/')
  return data
}

export async function getCommunicationSkus(interval?: string) {
  const { data } = await api.get<AddonSku[]>('/communications/skus/', {
    params: interval ? { interval } : undefined,
  })
  return data
}

export async function scheduleAddonChange(payload: {
  channel: 'sms' | 'email'
  enabled: boolean
  sku_code?: string
}) {
  const { data } = await api.post<Subscription>(
    '/communications/addons/schedule/',
    payload,
  )
  return data
}

export async function schedulePlanChange(payload: {
  plan_code?: string
  interval?: 'monthly' | 'annual'
}) {
  const { data } = await api.post<Subscription>(
    '/billing/subscription/schedule-change/',
    payload,
  )
  return data
}

export async function requestCapacityUpgrade(payload?: {
  plan_code?: string
  mark_paid?: boolean
}) {
  const { data } = await api.post<{ subscription: Subscription; invoice: InvoiceLike }>(
    '/billing/subscription/capacity-upgrade/',
    payload ?? {},
  )
  return data
}

type InvoiceLike = {
  id: string
  status: string
  total_ghs: string
}

export async function getTopUpPackages(channel?: 'sms' | 'email') {
  const { data } = await api.get<TopUpPackage[]>('/billing/topups/', {
    params: channel ? { channel } : undefined,
  })
  return data
}

export async function payInvoice(invoiceId: string) {
  const { data } = await api.post<SaasPayment>(`/billing/invoices/${invoiceId}/pay/`)
  return data
}

export async function purchaseTopUp(packageCode: string) {
  const { data } = await api.post<SaasPayment>('/billing/topups/purchase/', {
    package_code: packageCode,
  })
  return data
}

export async function verifySaasPayment(reference: string) {
  const { data } = await api.post<{ payment: SaasPayment; invoice?: unknown }>(
    '/billing/payments/verify/',
    { reference },
  )
  return data
}
