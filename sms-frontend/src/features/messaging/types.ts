import type { PaginatedResponse } from '@/types/generalTypes'

export type MessagingOverview = {
  credits: {
    sms: number
    email: number
    billing_active: boolean
  }
  usage_7d: {
    sms_sent: number
    sms_failed: number
    sms_skipped: number
    email_sent: number
    email_failed: number
    email_skipped: number
    sms_credits_used: number
    email_credits_used: number
  }
  open_failures: number
}

export type DeliveryStatus =
  | 'queued'
  | 'processing'
  | 'submitted'
  | 'delivered'
  | 'failed'
  | 'unknown'
  | 'skipped'
  | 'sent'

export type GuardianDelivery = {
  id: string
  event_type: string
  channel: 'sms' | 'email'
  status: DeliveryStatus
  status_label?: string
  status_description?: string
  recipient_address: string
  body_preview: string
  provider_message_id: string
  provider_status?: string
  skip_reason: string
  error_message: string
  user_error_message?: string
  display_error?: string
  segments?: number
  credits_charged?: number
  can_resend?: boolean
  source_delivery?: string | null
  parent: string
  parent_name: string
  student: string | null
  student_name: string | null
  status_updated_at?: string | null
  created_at: string
}

export type PaginatedDeliveries = PaginatedResponse<GuardianDelivery>

export type MessageTemplatePlaceholder = {
  key: string
  label: string
}

export type MessageTemplate = {
  event_type: string
  label: string
  placeholders: MessageTemplatePlaceholder[]
  sms_prefix_example: string
  sms_body: string
  sms_body_is_custom: boolean
  sms_body_default: string
  sms_body_all_time: string
  sms_body_all_time_is_custom: boolean
  sms_body_all_time_default: string
  email_subject: string
  email_subject_is_custom: boolean
  email_subject_default: string
  email_text: string
  email_text_is_custom: boolean
  email_text_default: string
  email_html: string
  email_html_is_custom: boolean
  updated_at: string | null
}

export type MessageTemplatePreview = {
  event_type: string
  channel: 'sms' | 'email'
  prefix?: string
  rendered_body?: string
  rendered: string
  rendered_subject?: string
  characters?: number
  sms?: {
    characters: number
    encoding: string
    segments: number
    credits_per_recipient: number
  }
}

export type MessageTemplateUpdatePayload = {
  event_type: string
  sms_body?: string
  sms_body_all_time?: string
  email_subject?: string
  email_text?: string
  email_html?: string
  restore?: Array<
    'sms_body' | 'sms_body_all_time' | 'email_subject' | 'email_text' | 'email_html'
  >
}
