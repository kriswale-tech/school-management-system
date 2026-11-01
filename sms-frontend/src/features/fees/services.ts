import api from '@/app/api/api'
import { getQueryUrl } from '@/utils/get-query-url'
import type {
  DebtReminderPreview,
  DebtReminderRequest,
  DebtReminderSendResult,
  FeeDeskFilterOptions,
  FeeDeskListResponse,
  FeeDeskQueryParams,
  FeeDeskSelectionIds,
  FeeDeskStats,
  FeeStructureDetail,
  FeeStructureItem,
  FeeStructureItemPayload,
  NextTermFeePrep,
  RecordPaymentPayload,
  RecordPaymentResponse,
  StudentPaymentTarget,
} from './types'

const baseUrl = '/fees/'

export const getFeeDeskList = async (
  params: FeeDeskQueryParams = {},
): Promise<FeeDeskListResponse> => {
  const url = getQueryUrl(baseUrl, params)
  const response = await api.get<FeeDeskListResponse>(url)
  return response.data
}

export const getFeeDeskStats = async (
  params: FeeDeskQueryParams = {},
): Promise<FeeDeskStats> => {
  const url = getQueryUrl(`${baseUrl}stats/`, params)
  const response = await api.get<FeeDeskStats>(url)
  return response.data
}

export const getFeeDeskSelectionIds = async (
  params: FeeDeskQueryParams = {},
): Promise<FeeDeskSelectionIds> => {
  const url = getQueryUrl(`${baseUrl}selection-ids/`, params)
  const response = await api.get<FeeDeskSelectionIds>(url)
  return response.data
}

export const getFeeDeskFilterOptions = async (): Promise<FeeDeskFilterOptions> => {
  const response = await api.get<FeeDeskFilterOptions>(`${baseUrl}filter-options/`)
  return response.data
}

export const getStudentPaymentTarget = async (
  studentId: string,
): Promise<StudentPaymentTarget> => {
  const response = await api.get<StudentPaymentTarget>(
    `${baseUrl}students/${studentId}/payment-target/`,
  )
  return response.data
}

export const recordPayment = async (
  payload: RecordPaymentPayload,
): Promise<RecordPaymentResponse> => {
  const response = await api.post<RecordPaymentResponse>(`${baseUrl}payments/`, payload)
  return response.data
}

export const previewDebtReminders = async (
  payload: DebtReminderRequest,
): Promise<DebtReminderPreview> => {
  const response = await api.post<DebtReminderPreview>(`${baseUrl}debt-reminders/preview/`, payload)
  return response.data
}

export const sendDebtReminders = async (
  payload: DebtReminderRequest,
): Promise<DebtReminderSendResult> => {
  const response = await api.post<DebtReminderSendResult>(`${baseUrl}debt-reminders/send/`, payload)
  return response.data
}

export const getFeeStructure = async (term?: string): Promise<FeeStructureDetail> => {
  const url = getQueryUrl(`${baseUrl}structures/`, { term })
  const response = await api.get<FeeStructureDetail>(url)
  return response.data
}

export const createFeeStructureItem = async (
  payload: FeeStructureItemPayload,
): Promise<FeeStructureItem> => {
  const response = await api.post<FeeStructureItem>(`${baseUrl}structures/items/`, payload)
  return response.data
}

export const updateFeeStructureItem = async (
  id: string,
  payload: Partial<FeeStructureItemPayload>,
): Promise<FeeStructureItem> => {
  const response = await api.patch<FeeStructureItem>(`${baseUrl}structures/items/${id}/`, payload)
  return response.data
}

export const deleteFeeStructureItem = async (id: string) => {
  await api.delete(`${baseUrl}structures/items/${id}/`)
}

export const publishFeeStructure = async (structureId: string): Promise<FeeStructureDetail> => {
  const response = await api.post<FeeStructureDetail>(
    `${baseUrl}structures/${structureId}/publish/`,
  )
  return response.data
}

export const applyFeeStructure = async (structureId: string): Promise<FeeStructureDetail> => {
  const response = await api.post<FeeStructureDetail>(
    `${baseUrl}structures/${structureId}/apply/`,
  )
  return response.data
}

export const copyFeeStructureFromPrevious = async (
  termId: string,
): Promise<FeeStructureDetail> => {
  const response = await api.post<FeeStructureDetail>(
    `${baseUrl}structures/copy-from-previous/`,
    { term: termId },
  )
  return response.data
}

export const getNextTermFeePrep = async (): Promise<NextTermFeePrep> => {
  const response = await api.get<NextTermFeePrep>(`${baseUrl}next-term-prep/`)
  return response.data
}
