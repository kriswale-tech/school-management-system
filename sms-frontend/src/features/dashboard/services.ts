import api from '@/app/api/api'
import type { AdminDashboard } from './types'

export const getAdminDashboard = async (): Promise<AdminDashboard> => {
  const response = await api.get<AdminDashboard>('/dashboard/admin/')
  return response.data
}
