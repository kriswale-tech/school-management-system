export const ADMIN_DASHBOARD_QUERY_KEY = 'admin-dashboard' as const

/** Compact GHS display for overview cards (e.g. GHS 25K). */
export const formatCompactFeeAmount = (amount: string | number) => {
  const parsed = typeof amount === 'number' ? amount : Number(amount)
  if (Number.isNaN(parsed)) return String(amount)

  const abs = Math.abs(parsed)
  if (abs >= 1_000_000) {
    const value = parsed / 1_000_000
    const formatted = value % 1 === 0 ? value.toFixed(0) : value.toFixed(1)
    return `GHS ${formatted}M`
  }
  if (abs >= 1_000) {
    const value = parsed / 1_000
    const formatted = value % 1 === 0 ? value.toFixed(0) : value.toFixed(1)
    return `GHS ${formatted}K`
  }

  return new Intl.NumberFormat('en-GH', {
    style: 'currency',
    currency: 'GHS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(parsed)
}

export const formatDashboardCount = (value: number | null | undefined) =>
  new Intl.NumberFormat('en-GH').format(Number(value) || 0)

/** Zero-padded display matching the design mock for small counts. */
export const padDashboardCount = (value: number | null | undefined) => {
  const count = Number(value) || 0
  if (count === 0) return '000'
  if (count < 10) return `00${count}`
  if (count < 100) return `0${count}`
  return formatDashboardCount(count)
}
