import api from '@/app/api/api'
import type { Setup } from '../types/types'

// get setup endpoint
export const getSetup = async () => {
  const response = await api.get<Setup>('/schools/setup/')
  return response.data
}
