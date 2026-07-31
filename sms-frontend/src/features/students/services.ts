import api from '@/app/api/api'
import type { PaginatedResponse } from '@/types/generalTypes'
import { getQueryUrl } from '@/utils/get-query-url'
import type {
  Parent,
  ParentQueryParams,
  Student,
  StudentOnboardPayload,
  StudentQueryParams,
  StudentStats,
} from './types'

export const getStudents = async (
  params: StudentQueryParams,
): Promise<PaginatedResponse<Student>> => {
  const url = getQueryUrl<StudentQueryParams>('/students/', params)
  const response = await api.get<PaginatedResponse<Student>>(url)
  return response.data
}

export const getParents = async (
  params: ParentQueryParams = {},
): Promise<PaginatedResponse<Parent>> => {
  const url = getQueryUrl<ParentQueryParams>('/students/parents/', params)
  const response = await api.get<PaginatedResponse<Parent>>(url)
  return response.data
}

export const getStudentStats = async (): Promise<StudentStats> => {
  const response = await api.get<StudentStats>('/students/stats/')
  return response.data
}

export const onboardStudent = async (payload: StudentOnboardPayload): Promise<Student> => {
  const response = await api.post<Student>('/students/onboard/', payload)
  return response.data
}
