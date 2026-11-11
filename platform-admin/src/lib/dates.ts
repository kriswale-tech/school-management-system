import dayjs from '@/lib/dayjs'

export function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY') : '—'
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return '—'
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY · h:mm A') : '—'
}
