import type { ReactNode } from 'react'
import { isEndpointMissing } from '../lib'

/* ------------------------------------------------------------------ */
/* Layout                                                              */
/* ------------------------------------------------------------------ */

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold">{title}</h2>
        {description && (
          <p className="mt-1 max-w-2xl text-sm text-[var(--color-ink)]/70">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

export function Panel({
  title,
  description,
  actions,
  footnote,
  children,
}: {
  title?: string
  description?: ReactNode
  actions?: ReactNode
  footnote?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && (
              <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold">
                {title}
              </h3>
            )}
            {description && (
              <p className="mt-1 max-w-2xl text-sm text-[var(--color-ink)]/70">{description}</p>
            )}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
      {footnote && (
        <p className="mt-4 border-t border-[var(--color-line)] pt-3 text-xs text-[var(--color-ink)]/55">
          {footnote}
        </p>
      )}
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Money/credit layer labelling (§2.5, §2.18)                          */
/* ------------------------------------------------------------------ */

export type MoneyLayer = 'provider' | 'credits' | 'cash' | 'usage'

const LAYER_META: Record<MoneyLayer, { label: string; className: string }> = {
  provider: {
    label: 'Provider layer',
    className: 'border-amber-200 bg-amber-50 text-amber-800',
  },
  credits: {
    label: 'School credits · units',
    className:
      'border-[var(--color-accent)]/25 bg-[var(--color-accent-soft)] text-[var(--color-accent)]',
  },
  cash: {
    label: 'Cash · GHS',
    className: 'border-[var(--color-line)] bg-[var(--color-panel)] text-[var(--color-ink)]/70',
  },
  usage: {
    label: 'Usage economics · GHS',
    className: 'border-sky-200 bg-sky-50 text-sky-900',
  },
}

export function LayerBadge({ layer }: { layer: MoneyLayer }) {
  const meta = LAYER_META[layer]
  return (
    <span
      className={`inline-flex rounded-md border px-1.5 py-0.5 text-[10px] font-semibold tracking-[0.08em] uppercase ${meta.className}`}
    >
      {meta.label}
    </span>
  )
}

export function LayerTile({
  layer,
  label,
  value,
  hint,
  estimated,
}: {
  layer: MoneyLayer
  label: string
  value: ReactNode
  hint?: ReactNode
  estimated?: boolean
}) {
  return (
    <div className="rounded-xl border border-[var(--color-line)] bg-white p-4">
      <LayerBadge layer={layer} />
      <p className="mt-2 text-xs font-medium text-[var(--color-ink)]/60">{label}</p>
      <p className="mt-1 font-[family-name:var(--font-display)] text-xl font-semibold">
        {value}
        {estimated && <EstimatedTag />}
      </p>
      {hint && <p className="mt-1 text-xs text-[var(--color-ink)]/55">{hint}</p>}
    </div>
  )
}

export function SummaryStrip({
  caption,
  children,
}: {
  caption?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="mb-6">
      {caption && (
        <p className="mb-2 text-xs font-semibold tracking-[0.12em] text-[var(--color-ink)]/50 uppercase">
          {caption}
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{children}</div>
    </div>
  )
}

export function EstimatedTag() {
  return (
    <span
      title="Estimated SES provider cost — not a per-message invoice line."
      className="ml-2 align-middle rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold tracking-[0.08em] text-amber-800 uppercase"
    >
      Estimated
    </span>
  )
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
}) {
  return (
    <div>
      <p className="text-xs font-medium text-[var(--color-ink)]/55">{label}</p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
      {hint && <p className="text-xs text-[var(--color-ink)]/55">{hint}</p>}
    </div>
  )
}

export function Badge({
  tone = 'neutral',
  children,
}: {
  tone?: 'neutral' | 'accent' | 'warn' | 'danger'
  children: ReactNode
}) {
  const tones = {
    neutral: 'border-[var(--color-line)] bg-[var(--color-panel)] text-[var(--color-ink)]/70',
    accent:
      'border-[var(--color-accent)]/25 bg-[var(--color-accent-soft)] text-[var(--color-accent)]',
    warn: 'border-amber-200 bg-amber-50 text-amber-800',
    danger: 'border-red-200 bg-red-50 text-red-700',
  }
  return (
    <span
      className={`inline-flex rounded-md border px-2 py-0.5 text-xs font-medium capitalize ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

/* ------------------------------------------------------------------ */
/* Tables and query states                                             */
/* ------------------------------------------------------------------ */

export function TableWrap({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-[var(--color-line)] bg-white">
      <table className="min-w-full text-left text-sm">{children}</table>
    </div>
  )
}

export function Thead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-[var(--color-line)] bg-[var(--color-accent-soft)]/40 text-[var(--color-ink)]/70">
      {children}
    </thead>
  )
}

export function Th({
  children,
  align = 'left',
  title,
}: {
  children: ReactNode
  align?: 'left' | 'right'
  title?: string
}) {
  return (
    <th
      title={title}
      className={`px-4 py-3 font-medium whitespace-nowrap ${align === 'right' ? 'text-right' : ''}`}
    >
      {children}
    </th>
  )
}

export function Td({
  children,
  align = 'left',
  className = '',
}: {
  children: ReactNode
  align?: 'left' | 'right'
  className?: string
}) {
  return (
    <td className={`px-4 py-3 ${align === 'right' ? 'text-right tabular-nums' : ''} ${className}`}>
      {children}
    </td>
  )
}

/**
 * Renders the loading / error / empty row for a table body. Returns `null`
 * once there is data so the caller can render rows normally.
 */
export function TableState({
  colSpan,
  isLoading,
  isError,
  error,
  isEmpty,
  emptyMessage = 'Nothing to show for this filter.',
}: {
  colSpan: number
  isLoading: boolean
  isError: boolean
  error?: unknown
  isEmpty: boolean
  emptyMessage?: string
}) {
  if (isLoading) {
    return (
      <tr>
        <td colSpan={colSpan} className="px-4 py-8 text-sm text-[var(--color-ink)]/60">
          Loading…
        </td>
      </tr>
    )
  }
  if (isError) {
    return (
      <tr>
        <td colSpan={colSpan} className="px-4 py-8 text-sm">
          {isEndpointMissing(error) ? (
            <span className="text-[var(--color-ink)]/60">{PENDING_COPY}</span>
          ) : (
            <span className="text-red-700">Could not load this data.</span>
          )}
        </td>
      </tr>
    )
  }
  if (isEmpty) {
    return (
      <tr>
        <td colSpan={colSpan} className="px-4 py-8 text-sm text-[var(--color-ink)]/60">
          {emptyMessage}
        </td>
      </tr>
    )
  }
  return null
}

const PENDING_COPY = 'Not available yet — this endpoint ships with the Messages backend module.'

/** Non-table equivalent of `TableState`, for panels and summary strips. */
export function QueryNotice({
  isLoading,
  isError,
  error,
}: {
  isLoading: boolean
  isError: boolean
  error?: unknown
}) {
  if (isLoading) {
    return <p className="text-sm text-[var(--color-ink)]/60">Loading…</p>
  }
  if (isError) {
    return isEndpointMissing(error) ? (
      <p className="rounded-xl border border-dashed border-[var(--color-line)] bg-[var(--color-panel)] px-4 py-3 text-sm text-[var(--color-ink)]/60">
        {PENDING_COPY}
      </p>
    ) : (
      <p className="text-sm text-red-700">Could not load this data.</p>
    )
  }
  return null
}

export function Pagination({
  count,
  page,
  pageSize = 25,
  onPage,
}: {
  count: number
  page: number
  pageSize?: number
  onPage: (page: number) => void
}) {
  const pages = Math.max(1, Math.ceil(count / pageSize))
  if (count === 0) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(count, page * pageSize)
  return (
    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-[var(--color-ink)]/60">
        {from}–{to} of {count.toLocaleString('en-GH')}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className="rounded-lg border border-[var(--color-line)] bg-white px-3 py-1.5 text-xs font-medium disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-xs text-[var(--color-ink)]/60">
          Page {page} of {pages}
        </span>
        <button
          type="button"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          className="rounded-lg border border-[var(--color-line)] bg-white px-3 py-1.5 text-xs font-medium disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Form controls                                                       */
/* ------------------------------------------------------------------ */

const controlClass =
  'w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2 text-sm'

export function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: ReactNode
  children: ReactNode
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-[var(--color-ink)]/55">{hint}</span>}
    </label>
  )
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const { className = '', ...rest } = props
  return <input {...rest} className={`${controlClass} ${className}`} />
}

export function SelectInput(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  const { className = '', children, ...rest } = props
  return (
    <select {...rest} className={`${controlClass} ${className}`}>
      {children}
    </select>
  )
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const { className = '', ...rest } = props
  return <textarea {...rest} className={`${controlClass} ${className}`} />
}

export function PrimaryButton(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { className = '', ...rest } = props
  return (
    <button
      type="button"
      {...rest}
      className={`rounded-xl bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60 ${className}`}
    />
  )
}

export function GhostButton(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { className = '', ...rest } = props
  return (
    <button
      type="button"
      {...rest}
      className={`rounded-xl border border-[var(--color-line)] bg-white px-3 py-2 text-xs font-medium disabled:opacity-50 ${className}`}
    />
  )
}

/* ------------------------------------------------------------------ */
/* Charts                                                              */
/* ------------------------------------------------------------------ */

export type SeriesPoint = { label: string; a: number; b?: number }

/**
 * Dependency-free grouped bar chart. Two series max, which covers the volume
 * (SMS/email) and margin (revenue/cost) trends the spec asks for.
 */
export function TrendChart({
  data,
  seriesA,
  seriesB,
  formatValue = (v) => v.toLocaleString('en-GH'),
}: {
  data: SeriesPoint[]
  seriesA: string
  seriesB?: string
  formatValue?: (value: number) => string
}) {
  if (data.length === 0) {
    return (
      <p className="py-6 text-sm text-[var(--color-ink)]/60">No activity in this range yet.</p>
    )
  }
  const max = Math.max(1, ...data.flatMap((d) => [d.a, d.b ?? 0]))
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-[var(--color-ink)]/70">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-[var(--color-accent)]" />
          {seriesA}
        </span>
        {seriesB && (
          <span className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-[var(--color-accent)]/35" />
            {seriesB}
          </span>
        )}
        <span className="ml-auto">Peak {formatValue(max)}</span>
      </div>
      <div className="flex h-40 items-end gap-1 overflow-x-auto">
        {data.map((point) => (
          <div
            key={point.label}
            className="group flex h-full min-w-[14px] flex-1 flex-col justify-end"
            title={`${point.label} · ${seriesA} ${formatValue(point.a)}${
              seriesB ? ` · ${seriesB} ${formatValue(point.b ?? 0)}` : ''
            }`}
          >
            <div className="flex h-full items-end gap-[2px]">
              <div
                className="flex-1 rounded-t-sm bg-[var(--color-accent)] transition group-hover:opacity-80"
                style={{ height: `${Math.max(2, (point.a / max) * 100)}%` }}
              />
              {seriesB && (
                <div
                  className="flex-1 rounded-t-sm bg-[var(--color-accent)]/35 transition group-hover:opacity-80"
                  style={{ height: `${Math.max(2, ((point.b ?? 0) / max) * 100)}%` }}
                />
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex justify-between text-xs text-[var(--color-ink)]/50">
        <span>{data[0]?.label}</span>
        <span>{data[data.length - 1]?.label}</span>
      </div>
    </div>
  )
}
