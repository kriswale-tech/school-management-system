import { isAxiosError } from 'axios'

export function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string } | undefined
    return data?.detail || 'Request failed'
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

export function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('en-GB')
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return `${date.toLocaleDateString('en-GB')} ${date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })}`
}

export function titleCase(value: string | null | undefined) {
  if (!value) return '—'
  return value.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10)
}
