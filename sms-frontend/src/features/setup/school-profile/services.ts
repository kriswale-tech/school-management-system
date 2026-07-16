import api from '@/app/api/api'
import type { SetupProgressResponse } from '../types/types'
import type { SchoolProfile } from './types'

export const getSchoolProfile = async () => {
  const response = await api.get<SchoolProfile>('/schools/school/')
  return response.data
}

export const setupSchoolProfile = async (payload: FormData) => {
  const response = await api.post<SetupProgressResponse>('/schools/setup/school-profile/', payload)
  return response.data
}
