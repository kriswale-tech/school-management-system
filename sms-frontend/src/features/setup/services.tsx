import api from '@/app/api/api'
import type { Setup, SchoolProfile, SetupProgressResponse } from './types'

// get setup endpoint
export const getSetup = async () => {
  const response = await api.get<Setup>('/schools/setup/')
  return response.data
}

// get school profile endpoint
export const getSchoolProfile = async () => {
  const response = await api.get<SchoolProfile>('/schools/school/')
  return response.data
}

// update school profile endpoint
export const setupSchoolProfile = async (payload: FormData) => {
  const response = await api.post<SetupProgressResponse>('/schools/setup/school-profile/', payload)
  return response.data
}
