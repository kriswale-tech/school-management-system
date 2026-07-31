import api from '@/app/api/api'
import { getQueryUrl } from '@/utils/get-query-url'
import type { AllClassesQueryParams, AllClassesResponse } from './types'

export const getClasses = async () => {
  const response = await api.get<{ name: string; id: string }[]>('/academics/class-levels/')
  return response.data
}

export const getLevels = async () => {
  const response = await api.get<{ name: string; id: string }[]>('/academics/levels/')
  return response.data
}

export const getAllClasses = async (
  params: AllClassesQueryParams = {},
): Promise<AllClassesResponse> => {
  const url = getQueryUrl<AllClassesQueryParams>('/academics/levels/all-classes/', params)
  const response = await api.get<AllClassesResponse>(url)
  return response.data
}
