import { statusLabel } from '../labels'

const TONES: Record<string, string> = {
  ready: 'bg-emerald-50 text-emerald-800',
  committed: 'bg-emerald-50 text-emerald-800',
  exact: 'bg-emerald-50 text-emerald-800',
  current: 'bg-sky-100 text-sky-800',
  create: 'bg-sky-100 text-sky-800',
  blocked: 'bg-rose-100 text-rose-800',
  failed: 'bg-rose-100 text-rose-800',
  rejected: 'bg-rose-100 text-rose-800',
  ambiguous: 'bg-rose-100 text-rose-800',
  probable: 'bg-amber-100 text-amber-800',
  partially_committed: 'bg-amber-100 text-amber-800',
  needs_year: 'bg-amber-100 text-amber-800',
  needs_operational_class: 'bg-amber-100 text-amber-800',
  snapshot: 'bg-violet-100 text-violet-800',
}

export function StatusPill({ value }: { value?: string }) {
  const key = value || 'pending'
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${TONES[key] || 'bg-slate-100 text-slate-700'}`}>
      {statusLabel(key)}
    </span>
  )
}
