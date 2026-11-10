import api from '@/app/api/api'
import type {
  MessageTemplate,
  MessageTemplatePreview,
  MessageTemplateUpdatePayload,
  MessagingOverview,
  PaginatedDeliveries,
} from './types'

export async function getMessagingOverview() {
  const { data } = await api.get<MessagingOverview>('/messaging/overview/')
  return data
}

export async function getMessagingDeliveries(params?: {
  channel?: string
  status?: string
  event_type?: string
  search?: string
  page?: number
}) {
  const { data } = await api.get<PaginatedDeliveries>('/messaging/deliveries/', { params })
  return data
}

export async function retryMessagingDelivery(id: string) {
  const { data } = await api.post(`/messaging/deliveries/${id}/retry/`)
  return data as {
    queued: number
    channel: string
    idempotency_key: string
    source_delivery_id: string
  }
}

export async function verifyMessagingDelivery(id: string) {
  const { data } = await api.post(`/messaging/deliveries/${id}/verify/`)
  return data as {
    id: string
    status: string
    can_resend: boolean
    provider_status: string
    verified: boolean
  }
}

export async function getMessageTemplates() {
  const { data } = await api.get<MessageTemplate[]>('/messaging/templates/')
  return data
}

export async function updateMessageTemplate(payload: MessageTemplateUpdatePayload) {
  const { data } = await api.put<MessageTemplate[]>('/messaging/templates/update/', payload)
  return data
}

export async function previewMessageTemplate(payload: {
  event_type: string
  channel: 'sms' | 'email'
  sms_body?: string
  sms_body_all_time?: string
  email_subject?: string
  email_text?: string
  all_time?: boolean
}) {
  const { data } = await api.post<MessageTemplatePreview>(
    '/messaging/templates/preview/',
    payload,
  )
  return data
}
