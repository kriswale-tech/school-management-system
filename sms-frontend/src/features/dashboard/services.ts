import api from '@/app/api/api'
import type { PaginatedResponse } from '@/types/generalTypes'
import type {
  ActivityItem,
  AdminDashboard,
  StaffDashboard,
  TeacherDashboard,
} from './types'

export const getAdminDashboard = async (): Promise<AdminDashboard> => {
  const response = await api.get<AdminDashboard>('/dashboard/admin/')
  return response.data
}

export const getTeacherDashboard = async (): Promise<TeacherDashboard> => {
  const response = await api.get<TeacherDashboard>('/dashboard/teacher/')
  return response.data
}

export const getStaffDashboard = async (): Promise<StaffDashboard> => {
  const response = await api.get<StaffDashboard>('/dashboard/staff/')
  return response.data
}

export type ActivitiesParams = {
  term?: string
  page?: number
  page_size?: number
}

export const getActivities = async (
  params: ActivitiesParams = {},
): Promise<PaginatedResponse<ActivityItem>> => {
  const response = await api.get<PaginatedResponse<ActivityItem>>('/activities/', {
    params: {
      page_size: params.page_size ?? 20,
      ...(params.term ? { term: params.term } : {}),
      ...(params.page ? { page: params.page } : {}),
    },
  })
  return response.data
}

export const getRecentActivities = async (): Promise<ActivityItem[]> => {
  const data = await getActivities({ page_size: 10 })
  return data.results
}
