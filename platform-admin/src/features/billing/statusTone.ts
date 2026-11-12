export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'quiet'

const PILL: Record<StatusTone, string> = {
  success: 'bg-emerald-50 text-emerald-800',
  warning: 'bg-amber-50 text-amber-800',
  danger: 'bg-red-50 text-red-800',
  info: 'bg-sky-50 text-sky-800',
  quiet: 'bg-slate-100 text-slate-600',
}

const SURFACE: Record<StatusTone, string> = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  warning: 'border-amber-200 bg-amber-50 text-amber-950',
  danger: 'border-red-200 bg-red-50 text-red-900',
  info: 'border-sky-200 bg-sky-50 text-sky-900',
  quiet: 'border-slate-200 bg-slate-100 text-slate-700',
}

const SUCCESS = new Set([
  'paid',
  'success',
  'active',
  'complete',
  'completed',
  'ok',
  'current',
  'accepted',
  'delivered',
  'matched',
  'on',
])
const WARNING = new Set([
  'pending',
  'open',
  'past_due',
  'processing',
  'incomplete',
  'warning',
  'skipped',
  'not_configured',
  'running',
])
const DANGER = new Set([
  'failed',
  'abandoned',
  'suspended',
  'overdue',
  'uncollectible',
  'error',
  'expired',
])
const INFO = new Set(['scheduled', 'info', 'recorded', 'submitted', 'adjusted'])

const LABELS: Record<string, string> = {
  paid: 'Paid',
  success: 'Success',
  active: 'Active',
  complete: 'Complete',
  completed: 'Completed',
  ok: 'OK',
  current: 'Current',
  accepted: 'Accepted',
  pending: 'Pending',
  open: 'Pending',
  past_due: 'Past due',
  processing: 'Processing',
  incomplete: 'Incomplete',
  warning: 'Warning',
  failed: 'Failed',
  abandoned: 'Abandoned',
  suspended: 'Suspended',
  overdue: 'Overdue',
  uncollectible: 'Uncollectible',
  error: 'Error',
  expired: 'Expired',
  scheduled: 'Scheduled',
  info: 'Info',
  recorded: 'Recorded',
  void: 'Void',
  draft: 'Draft',
  archived: 'Archived',
  cancelled: 'Cancelled',
  canceled: 'Cancelled',
}

function statusKey(status: string) {
  return status.trim().toLowerCase()
}

export function statusToneName(status: string): StatusTone {
  const key = statusKey(status)
  if (SUCCESS.has(key)) return 'success'
  if (WARNING.has(key)) return 'warning'
  if (DANGER.has(key)) return 'danger'
  if (INFO.has(key)) return 'info'
  return 'quiet'
}

export function statusLabel(status: string) {
  const key = statusKey(status)
  return LABELS[key] ?? key.replaceAll('_', ' ')
}

export function statusPillClass(status: string) {
  return PILL[statusToneName(status)]
}

export function statusSurfaceClass(status: string) {
  return SURFACE[statusToneName(status)]
}
