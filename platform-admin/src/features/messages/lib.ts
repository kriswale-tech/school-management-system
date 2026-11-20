import { isAxiosError } from 'axios'

function firstErrorText(value: unknown): string {
  if (typeof value === 'string' && value.trim()) return value
  if (Array.isArray(value)) {
    for (const item of value) {
      const text = firstErrorText(item)
      if (text) return text
    }
  }
  if (value && typeof value === 'object') {
    for (const item of Object.values(value as Record<string, unknown>)) {
      const text = firstErrorText(item)
      if (text) return text
    }
  }
  return ''
}

export function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    return firstErrorText(error.response?.data) || 'Request failed'
  }
  return 'Request failed'
}

/**
 * The `/platform/messages/*` module ships in milestones (§2.20), so a missing
 * endpoint is an expected state rather than a failure worth alarming about.
 */
export function isEndpointMissing(error: unknown) {
  return isAxiosError(error) && (error.response?.status === 404 || error.response?.status === 501)
}

export function num(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

export function formatUnits(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return '—'
  return value.toLocaleString('en-GH')
}

export function formatGhs(value: string | number | null | undefined) {
  if (value == null || value === '') return '—'
  const parsed = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(parsed)) return '—'
  return `GH₵ ${parsed.toLocaleString('en-GH', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

/** Unit prices run to fractions of a pesewa, so they need more precision. */
export function formatUnitPrice(value: string | number | null | undefined) {
  if (value == null || value === '') return '—'
  const parsed = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(parsed)) return '—'
  return `GH₵ ${parsed.toLocaleString('en-GH', {
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  })}`
}

export function formatPct(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${value.toFixed(1)}%`
}

export { formatDate, formatDateTime } from '@/lib/dates'

export function titleCase(value: string | null | undefined) {
  if (!value) return '—'
  return value.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10)
}
