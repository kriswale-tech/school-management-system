import api from '@/app/api/api'
import type { PaginatedResponse } from '@/types/generalTypes'
import type { ActivityItem, AdminDashboard, TeacherDashboard } from './types'

export const getAdminDashboard = async (): Promise<AdminDashboard> => {
  const response = await api.get<AdminDashboard>('/dashboard/admin/')
  return response.data
}

export const getTeacherDashboard = async (): Promise<TeacherDashboard> => {
  const response = await api.get<TeacherDashboard>('/dashboard/teacher/')
  return response.data
}

export const getRecentActivities = async (): Promise<ActivityItem[]> => {
  const response = await api.get<PaginatedResponse<ActivityItem>>('/activities/', {
    params: { page_size: 10 },
  })
  return response.data.results
}
