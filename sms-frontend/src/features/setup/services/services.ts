import api from '@/app/api/api'
import type { Setup, SetupProgressResponse } from '../types/types'

// get setup endpoint
export const getSetup = async () => {
  const response = await api.get<Setup>('/schools/setup/')
  return response.data
}

// complete setup endpoint
export const completeSetup = async () => {
  const response = await api.post<SetupProgressResponse>('/schools/setup/complete/')
  return response.data
}