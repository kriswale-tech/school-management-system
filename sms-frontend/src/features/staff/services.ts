import api from "@/app/api/api"
import type { PaginatedResponse } from "@/types/generalTypes"
import type { Staff, StaffQueryParams, UpdateStaffResponse } from "./types"
import { getQueryUrl } from "@/utils/get-query-url"



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