import api from '@/app/api/api'
import type {
  AppNotification,
  NotificationListResponse,
  UnreadCountResponse,
} from './types'

export const NOTIFICATIONS_QUERY_KEY = 'notifications'
export const NOTIFICATIONS_UNREAD_QUERY_KEY = 'notificationsUnread'

export const getNotifications = async (unreadOnly = false) => {
  const response = await api.get<NotificationListResponse>('/notifications/', {
    params: {
      page_size: 20,
      ...(unreadOnly ? { unread: true } : {}),
    },
  })
  return response.data
}

export const getNotificationsUnreadCount = async () => {
  const response = await api.get<UnreadCountResponse>('/notifications/unread-count/')
  return response.data.count
}

export const markNotificationRead = async (notificationId: string) => {
  const response = await api.post<AppNotification>(
    `/notifications/${notificationId}/read/`,
  )
  return response.data
}

export const markAllNotificationsRead = async () => {
  const response = await api.post<{ updated: number }>('/notifications/read-all/')
  return response.data
}
