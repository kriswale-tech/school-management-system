export interface AppNotification {
  id: string
  event_type: string
  title: string
  body: string
  href: string
  target_kind: string
  target_id: string | null
  read_at: string | null
  created_at: string
  actor_name: string
}

export interface NotificationListResponse {
  count: number
  results: AppNotification[]
}

export interface UnreadCountResponse {
  count: number
}
