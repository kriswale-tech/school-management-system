import api from '@/lib/api'
import type {
  AllowancePolicy,
  AllowancePolicyInput,
  EmailPricingConfig,
  EmailPricingConfigInput,
  FreeUsageStats,
  MessagesOverview,
  MessagingTransaction,
  Paginated,
  Profitability,
  ProfitabilityView,
  Provider,
  ProviderAccount,
  ProviderBalanceSnapshot,
  ProviderExpense,
  ProviderExpenseInput,
  ProviderPurchase,
  ProviderPurchaseInput,
  RangeParams,
  ReconciliationItem,
  ReconciliationRun,
  SesUsageSnapshot,
  SchoolMessagingReport,
  SchoolUsageRow,
  SmsCalculatorResult,
  SmsEncodingConfig,
  SmsEncodingConfigInput,
  TransactionType,
} from './types'

const BASE = '/platform/messages'

/* Overview --------------------------------------------------------- */

export async function getOverview(params: RangeParams) {
  const { data } = await api.get<MessagesOverview>(`${BASE}/overview/`, { params })
  return data
}

/* SMS pricing ------------------------------------------------------- */

export async function listSmsEncodings() {
  const { data } = await api.get<SmsEncodingConfig[]>(`${BASE}/sms-encodings/`)
  return data
}

export async function listSmsEncodingHistory(params?: { encoding?: string }) {
  const { data } = await api.get<SmsEncodingConfig[]>(`${BASE}/sms-encodings/history/`, {
    params,
  })
  return data
}

/** Creates a new version; the previously active row is deactivated server-side. */
export async function createSmsEncoding(payload: SmsEncodingConfigInput) {
  const { data } = await api.post<SmsEncodingConfig>(`${BASE}/sms-encodings/`, payload)
  return data
}

/** PATCH also versions rather than mutating history (§2.6.2). */
export async function patchSmsEncoding(id: string, payload: Partial<SmsEncodingConfigInput>) {
  const { data } = await api.patch<SmsEncodingConfig>(`${BASE}/sms-encodings/${id}/`, payload)
  return data
}

export async function calculateSms(payload: { body: string }) {
  const { data } = await api.post<SmsCalculatorResult>(`${BASE}/calculator/sms/`, payload)
  return data
}

/* Email pricing ----------------------------------------------------- */

export async function getEmailPricing() {
  const { data } = await api.get<EmailPricingConfig>(`${BASE}/email-pricing/`)
  return data
}

export async function createEmailPricing(payload: EmailPricingConfigInput) {
  const { data } = await api.post<EmailPricingConfig>(`${BASE}/email-pricing/`, payload)
  return data
}

export async function listEmailPricingHistory() {
  const { data } = await api.get<EmailPricingConfig[]>(`${BASE}/email-pricing/history/`)
  return data
}

/* Providers --------------------------------------------------------- */

export async function listProviders() {
  const { data } = await api.get<ProviderAccount[]>(`${BASE}/providers/`)
  return data
}

export async function syncArkeselBalance() {
  const { data } = await api.post<ProviderBalanceSnapshot>(
    `${BASE}/providers/arkesel/sync-balance/`,
  )
  return data
}

export async function listArkeselSnapshots(params?: { page?: number }) {
  const { data } = await api.get<Paginated<ProviderBalanceSnapshot>>(
    `${BASE}/providers/arkesel/snapshots/`,
    { params },
  )
  return data
}

export async function syncSesUsage() {
  const { data } = await api.post<SesUsageSnapshot>(`${BASE}/providers/ses/sync-usage/`)
  return data
}

export async function listSesUsage(params?: { page?: number }) {
  const { data } = await api.get<Paginated<SesUsageSnapshot>>(
    `${BASE}/providers/ses/usage/`,
    { params },
  )
  return data
}

/** @deprecated Prefer syncSesUsage */
export async function syncResendUsage() {
  return syncSesUsage()
}

/** @deprecated Prefer listSesUsage */
export async function listResendUsage(params?: { page?: number }) {
  return listSesUsage(params)
}

/* Purchases & expenses ---------------------------------------------- */

export async function listPurchases(params?: { provider?: Provider; page?: number }) {
  const { data } = await api.get<Paginated<ProviderPurchase>>(`${BASE}/purchases/`, { params })
  return data
}

export async function createPurchase(payload: ProviderPurchaseInput) {
  const { data } = await api.post<ProviderPurchase>(`${BASE}/purchases/`, payload)
  return data
}

export async function listExpenses(params?: { provider?: Provider; page?: number }) {
  const { data } = await api.get<Paginated<ProviderExpense>>(`${BASE}/expenses/`, { params })
  return data
}

export async function createExpense(payload: ProviderExpenseInput) {
  const { data } = await api.post<ProviderExpense>(`${BASE}/expenses/`, payload)
  return data
}

/* School usage ------------------------------------------------------ */

export async function listSchoolUsage(params: RangeParams & { q?: string; page?: number }) {
  const { data } = await api.get<Paginated<SchoolUsageRow>>(`${BASE}/schools/usage/`, { params })
  return data
}

export async function getSchoolReport(schoolId: string, params: RangeParams) {
  const { data } = await api.get<SchoolMessagingReport>(
    `${BASE}/schools/${schoolId}/report/`,
    { params },
  )
  return data
}

/* Free & sponsored --------------------------------------------------- */

export async function listAllowances(params?: { school?: string; channel?: string }) {
  const { data } = await api.get<AllowancePolicy[]>(`${BASE}/allowances/`, { params })
  return data
}

export async function createAllowance(payload: AllowancePolicyInput) {
  const { data } = await api.post<AllowancePolicy>(`${BASE}/allowances/`, payload)
  return data
}

export async function patchAllowance(id: string, payload: Partial<AllowancePolicyInput>) {
  const { data } = await api.patch<AllowancePolicy>(`${BASE}/allowances/${id}/`, payload)
  return data
}

export async function getFreeUsage(params: RangeParams) {
  const { data } = await api.get<FreeUsageStats>(`${BASE}/free-usage/`, { params })
  return data
}

/* Profitability ------------------------------------------------------ */

export async function getProfitability(params: RangeParams & { view: ProfitabilityView }) {
  const { data } = await api.get<Profitability>(`${BASE}/profitability/`, { params })
  return data
}

/* Transactions ------------------------------------------------------- */

export async function listTransactions(
  params: RangeParams & { type?: TransactionType | ''; provider?: Provider | ''; page?: number },
) {
  const { data } = await api.get<Paginated<MessagingTransaction>>(`${BASE}/transactions/`, {
    params,
  })
  return data
}

/* Exports ------------------------------------------------------------ */

export type ExportType =
  | 'school_usage'
  | 'provider_purchases'
  | 'provider_expenses'
  | 'sms_pricing_history'
  | 'email_pricing_history'
  | 'profitability'
  | 'free_sponsored'
  | 'credit_ledger'
  | 'monthly_summary'
  | 'reconciliation'

/** Streams the CSV/XLSX to the browser; audited server-side as an export event. */
export async function downloadExport(
  params: RangeParams & { type: ExportType; format: 'csv' | 'xlsx'; view?: ProfitabilityView },
) {
  const response = await api.get(`${BASE}/export/`, { params, responseType: 'blob' })
  const url = URL.createObjectURL(response.data as Blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${params.type}-${new Date().toISOString().slice(0, 10)}.${params.format}`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

/* Reconciliation ------------------------------------------------------ */

export async function reconcileProvider(
  provider: Provider,
  payload?: { window_start?: string; window_end?: string },
) {
  const { data } = await api.post<ReconciliationRun>(`${BASE}/reconcile/${provider}/`, payload)
  return data
}

export async function listReconciliationRuns(params?: { provider?: Provider; page?: number }) {
  const { data } = await api.get<Paginated<ReconciliationRun>>(`${BASE}/runs/`, { params })
  return data
}

export async function listReconciliationItems(
  runId: string,
  params?: { resolution?: string; page?: number },
) {
  const { data } = await api.get<Paginated<ReconciliationItem>>(`${BASE}/runs/${runId}/items/`, {
    params,
  })
  return data
}

export async function resolveReconciliationItem(
  runId: string,
  itemId: string,
  payload: { resolution: 'accepted' | 'adjusted' | 'ignored'; resolution_note: string },
) {
  const { data } = await api.post<ReconciliationItem>(
    `${BASE}/runs/${runId}/items/${itemId}/resolve/`,
    payload,
  )
  return data
}
