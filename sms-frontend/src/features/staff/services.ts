import api from '@/app/api/api'
import type { PaginatedResponse } from '@/types/generalTypes'
import type {
  Staff,
  StaffDeskDetail,
  StaffDeskQueryParams,
  StaffDeskRow,
  StaffDeskStats,
  StaffQueryParams,
  UpdateStaffResponse,
} from './types'
import { getQueryUrl } from '@/utils/get-query-url'

/** Setup / user-management list (existing `/accounts/users/` endpoint). */
export const getStaff = async (params: StaffQueryParams): Promise<PaginatedResponse<Staff>> => {
  const url = getQueryUrl<StaffQueryParams>('/accounts/users/', params)
  const response = await api.get<PaginatedResponse<Staff>>(url)
  return response.data
}

export const createStaff = async (data: FormData): Promise<Staff> => {
  const response = await api.post<Staff>('/accounts/users/', data)
  return response.data
}

export const updateStaff = async (id: string, data: FormData): Promise<UpdateStaffResponse> => {
  const response = await api.patch<UpdateStaffResponse>(`/accounts/users/${id}/`, data)
  return response.data
}

export const deleteStaff = async (id: string): Promise<void> => {
  await api.delete(`/accounts/users/${id}/`)
}

/** Staff directory list — GET /accounts/staff/ */
export const getStaffDeskList = async (
  params: StaffDeskQueryParams,
): Promise<PaginatedResponse<StaffDeskRow>> => {
  const url = getQueryUrl<StaffDeskQueryParams>('/accounts/staff/', params)
  const response = await api.get<PaginatedResponse<StaffDeskRow>>(url)
  return response.data
}

/** Filter-aware stats — GET /accounts/staff/stats/ */
export const getStaffDeskStats = async (
  params: Omit<StaffDeskQueryParams, 'page' | 'page_size'>,
): Promise<StaffDeskStats> => {
  const url = getQueryUrl('/accounts/staff/stats/', params)
  const response = await api.get<StaffDeskStats>(url)
  return response.data
}

/** Staff directory detail — GET /accounts/staff/:id/ */
export const getStaffDeskDetail = async (id: string): Promise<StaffDeskDetail> => {
  const response = await api.get<StaffDeskDetail>(`/accounts/staff/${id}/`)
  return response.data
}
