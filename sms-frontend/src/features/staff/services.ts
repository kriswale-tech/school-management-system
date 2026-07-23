import api from "@/app/api/api"
import type { PaginatedResponse } from "@/types/generalTypes"
import type { Staff } from "./types"



export const getStaff = async (page = 1): Promise<PaginatedResponse<Staff>> => {
  const response = await api.get<PaginatedResponse<Staff>>('/accounts/users/', {
    params: { page },
  })
  return response.data
}

export const createStaff = async (data: FormData): Promise<Staff> => {
  const response = await api.post<Staff>('/accounts/users/', data)
  return response.data
}

export const updateStaff = async (id: string, data: FormData): Promise<Staff> => {
  const response = await api.patch<Staff>(`/accounts/users/${id}/`, data)
  return response.data
}

export const deleteStaff = async (id: string): Promise<void> => {
  await api.delete(`/accounts/users/${id}/`)
}