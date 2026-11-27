import api from '@/lib/api'
import type { Paginated } from '@/features/schools/types'

export type PlatformAuditEntry = {
  id: string
  action: string
  actor_name: string
  actor_email: string
  target_type: string
  target_id: string
  target_label: string
  detail: Record<string, unknown>
  ip_address: string | null
  created_at: string
}

export async function listAudit(params: {
  q?: string
  action?: string
  target_type?: string
  start?: string
  end?: string
  page?: number
}) {
  const { data } = await api.get<Paginated<PlatformAuditEntry>>('/platform/audit/', { params })
  return data
}
