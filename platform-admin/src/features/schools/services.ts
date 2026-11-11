import api from '@/lib/api'
import type {
  Paginated,
  PlatformSchoolAuditEntry,
  PlatformSchoolDetail,
  PlatformSchoolListItem,
  PlatformSchoolSummary,
  SchoolAdminInvite,
  SchoolStatus,
} from './types'

export async function fetchSchoolSummary() {
  const { data } = await api.get<PlatformSchoolSummary>('/platform/schools/summary/')
  return data
}

export async function listSchools(params?: {
  status?: string
  search?: string
  page?: number
  page_size?: number
}) {
  const { data } = await api.get<Paginated<PlatformSchoolListItem>>('/platform/schools/', {
    params,
  })
  return data
}

export async function createSchool(payload: {
  name: string
  phone_number: string
  phone_number_alt?: string
  email?: string
  address?: string
  region?: string
  category?: string
  plan_code?: string
  interval?: 'monthly' | 'annual'
  sms_sku_code?: string
  email_sku_code?: string
}) {
  const { data } = await api.post<PlatformSchoolDetail>('/platform/schools/', payload)
  return data
}

export async function getSchool(id: string) {
  const { data } = await api.get<PlatformSchoolDetail>(`/platform/schools/${id}/`)
  return data
}

export async function updateSchoolStatus(id: string, status: SchoolStatus, reason: string) {
  const { data } = await api.post<PlatformSchoolDetail>(`/platform/schools/${id}/status/`, {
    status,
    reason,
  })
  return data
}

export async function listSchoolAudit(id: string, page = 1) {
  const { data } = await api.get<Paginated<PlatformSchoolAuditEntry>>(
    `/platform/schools/${id}/audit/`,
    { params: { page, page_size: 20 } },
  )
  return data
}

export async function inviteSchoolAdmin(
  schoolId: string,
  payload: {
    phone_number: string
    email: string
    first_name: string
    last_name?: string
  },
) {
  const { data } = await api.post<SchoolAdminInvite>(
    `/platform/schools/${schoolId}/invites/`,
    payload,
  )
  return data
}

export async function resendSchoolAdminInvite(schoolId: string, inviteId: string) {
  const { data } = await api.post<SchoolAdminInvite>(
    `/platform/schools/${schoolId}/invites/${inviteId}/resend/`,
  )
  return data
}
