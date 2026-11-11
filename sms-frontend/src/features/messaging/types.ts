import type { PaginatedResponse } from '@/types/generalTypes'

export type MessagingUsageEvent = {
  channel: 'sms' | 'email'
  event_type: string
  sent: number
  failed: number
  skipped: number
  credits_used: number
}

export type MessagingUsage = {
  sms_sent: number
  sms_failed: number
  sms_skipped: number
  email_sent: number
  email_failed: number
  email_skipped: number
  sms_credits_used: number
  email_credits_used: number
  by_event?: MessagingUsageEvent[]
}

export type MessagingOverview = {
  period?: '7d' | '30d' | 'custom'
  period_start?: string
  period_end?: string
  credits: {
    sms: number
    email: number
    billing_active: boolean
  }
  usage?: MessagingUsage
  usage_7d: MessagingUsage
  open_failures: number
}

export type ChannelCreditCoverage = {
  balance: number
  per_message: number
  needed: number
  shortfall_messages: number
  sufficient: boolean
}

export type CreditCoverage = {
  sms: ChannelCreditCoverage
  email: ChannelCreditCoverage
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

export type EligibleDeliveryItem = {
  id: string
  channel: 'sms' | 'email'
  segments: number
}

export type EligibleResendSelection = {
  total: number
  limit: number
  capped: boolean
  ids: string[]
  items: EligibleDeliveryItem[]
  sms_credits: number
  email_credits: number
}

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
