import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import { listSchools } from '@/features/schools/services'
import { formatDate } from '@/lib/dates'
import {
  createDiscount,
  deleteDiscount,
  getDiscount,
  listDiscounts,
  patchDiscount,
  restoreDiscount,
  revokeDiscount,
} from './services'
import type { DiscountInput, DiscountSchool, PlatformDiscount } from './types'

function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as
      | { detail?: string; [key: string]: unknown }
      | undefined
    if (data?.detail && typeof data.detail === 'string') return data.detail
    if (data && typeof data === 'object') {
      const first = Object.values(data).flat()[0]
      if (typeof first === 'string') return first
      if (Array.isArray(first) && typeof first[0] === 'string') return first[0]
    }
    return 'Request failed'
  }
  return 'Request failed'
}

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 60)
}

function toStartIso(date: string) {
  return new Date(`${date}T00:00:00`).toISOString()
}

function toExclusiveEndIso(date: string) {
  const value = new Date(`${date}T00:00:00`)
  value.setDate(value.getDate() + 1)
  return value.toISOString()
}

function toDateInput(iso: string | null, exclusive = false) {
  if (!iso) return ''
  const value = new Date(iso)
  if (Number.isNaN(value.getTime())) return ''
  if (exclusive) value.setDate(value.getDate() - 1)
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${value.getFullYear()}-${month}-${day}`
}

const inputClass =
  'w-full rounded-lg border border-[var(--color-line)] bg-white px-3 py-2 text-sm'
const labelClass = 'mb-1 block text-xs font-medium text-[var(--color-ink)]/70'
const btnPrimary =
  'rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-60'
const btnGhost =
  'rounded-lg border border-[var(--color-line)] px-4 py-2 text-sm font-medium disabled:opacity-60'
const btnDanger =
  'rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-60'

type FormState = {
  code: string
  name: string
  discount_percent: string
  applies_to: DiscountInput['applies_to']
  schedule: DiscountInput['schedule']
  audience: DiscountInput['audience']
  billing_interval: DiscountInput['billing_interval']
  duration_months: number
  starts_on: string
  ends_on: string
  is_active: boolean
  schools: DiscountSchool[]
}

const EMPTY_FORM: FormState = {
  code: '',
  name: '',
  discount_percent: '10.00',
  applies_to: 'application',
  schedule: 'introductory',
  audience: 'new',
  billing_interval: '',
  duration_months: 6,
  starts_on: '',
  ends_on: '',
  is_active: false,
  schools: [],
}

function formFromDiscount(discount: PlatformDiscount): FormState {
  return {
    code: discount.code,
    name: discount.name,
    discount_percent: discount.discount_percent,
    applies_to: discount.applies_to,
    schedule: discount.schedule,
    audience: discount.audience,
    billing_interval: discount.billing_interval || '',
    duration_months: discount.duration_months,
    starts_on: toDateInput(discount.starts_at),
    ends_on: toDateInput(discount.ends_at, true),
    is_active: discount.is_active,
    schools: discount.schools,
  }
}

function Modal({
  open,
  title,
  description,
  onClose,
  children,
}: {
  open: boolean
  title: string
  description?: string
  onClose: () => void
  children: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <button
        type="button"
        aria-label="Close dialog backdrop"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative z-10 max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-xl"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="font-[family-name:var(--font-display)] text-xl font-semibold">{title}</h3>
            {description ? (
              <p className="mt-1 text-sm text-[var(--color-ink)]/65">{description}</p>
            ) : null}
          </div>
          <button type="button" className={btnGhost} onClick={onClose}>
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function Field({
  label,
  children,
  hint,
}: {
  label: string
  children: ReactNode
  hint?: string
}) {
  return (
    <label className="block">
      <span className={labelClass}>{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-[var(--color-ink)]/50">{hint}</span> : null}
    </label>
  )
}

const SCHEDULE_LABEL = {
  introductory: 'First months',
  recurring: 'Recurring',
  date_range: 'Date range',
} as const

const AUDIENCE_LABEL = {
  all: 'All schools',
  new: 'New schools',
  selected: 'Selected schools',
} as const

export default function DiscountsPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [codeTouched, setCodeTouched] = useState(false)
  const [schoolSearch, setSchoolSearch] = useState('')
  const [openId, setOpenId] = useState<string | null>(null)

  const discountsQuery = useQuery({
    queryKey: ['platform-billing-discounts'],
    queryFn: listDiscounts,
  })

  const detailQuery = useQuery({
    queryKey: ['platform-billing-discount', openId],
    queryFn: () => getDiscount(openId || ''),
    enabled: Boolean(openId),
  })

  const schoolsQuery = useQuery({
    queryKey: ['platform-schools-picker', schoolSearch],
    queryFn: () => listSchools({ search: schoolSearch, page: 1 }),
    enabled: showForm && form.audience === 'selected',
  })

  const saveMutation = useMutation({
    mutationFn: (payload: DiscountInput) =>
      editingId ? patchDiscount(editingId, payload) : createDiscount(payload),
    onSuccess: () => {
      toast.success(editingId ? 'Discount updated' : 'Discount created')
      setShowForm(false)
      setEditingId(null)
      void queryClient.invalidateQueries({ queryKey: ['platform-billing-discounts'] })
      if (openId) {
        void queryClient.invalidateQueries({ queryKey: ['platform-billing-discount', openId] })
      }
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteDiscount,
    onSuccess: () => {
      toast.success('Discount deleted')
      setOpenId(null)
      void queryClient.invalidateQueries({ queryKey: ['platform-billing-discounts'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const revokeMutation = useMutation({
    mutationFn: ({ discountId, redemptionId }: { discountId: string; redemptionId: string }) =>
      revokeDiscount(discountId, redemptionId),
    onSuccess: () => {
      toast.success('Discount revoked for that school')
      void queryClient.invalidateQueries({ queryKey: ['platform-billing-discount', openId] })
      void queryClient.invalidateQueries({ queryKey: ['platform-billing-discounts'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const restoreMutation = useMutation({
    mutationFn: ({ discountId, redemptionId }: { discountId: string; redemptionId: string }) =>
      restoreDiscount(discountId, redemptionId),
    onSuccess: () => {
      toast.success('Discount restored for that school')
      void queryClient.invalidateQueries({ queryKey: ['platform-billing-discount', openId] })
      void queryClient.invalidateQueries({ queryKey: ['platform-billing-discounts'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  useEffect(() => {
    if (!showForm || codeTouched || editingId) return
    setForm((current) => ({ ...current, code: slugify(current.name) }))
  }, [form.name, showForm, codeTouched, editingId])

  const selectedIds = useMemo(() => new Set(form.schools.map((school) => school.id)), [form.schools])

  function startCreate() {
    setOpenId(null)
    setEditingId(null)
    setCodeTouched(false)
    setForm(EMPTY_FORM)
    setSchoolSearch('')
    setShowForm(true)
  }

  function startEdit(discount: PlatformDiscount) {
    setOpenId(null)
    setEditingId(discount.id)
    setCodeTouched(true)
    setForm(formFromDiscount(discount))
    setSchoolSearch('')
    setShowForm(true)
  }

  function toggleSchool(school: DiscountSchool) {
    setForm((current) => {
      const exists = current.schools.some((item) => item.id === school.id)
      return {
        ...current,
        schools: exists
          ? current.schools.filter((item) => item.id !== school.id)
          : [...current.schools, school],
      }
    })
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (form.schedule === 'date_range' && (!form.starts_on || !form.ends_on)) {
      toast.error('Choose the first and last day of the date range.')
      return
    }
    if (form.audience === 'selected' && form.schools.length === 0) {
      toast.error('Choose at least one school.')
      return
    }
    const payload: DiscountInput = {
      code: form.code,
      name: form.name,
      discount_percent: form.discount_percent,
      applies_to: form.applies_to,
      schedule: form.schedule,
      audience: form.audience,
      billing_interval: form.billing_interval,
      duration_months: Number(form.duration_months) || 1,
      starts_at: form.schedule === 'date_range' ? toStartIso(form.starts_on) : null,
      ends_at: form.schedule === 'date_range' ? toExclusiveEndIso(form.ends_on) : null,
      is_active: form.is_active,
      school_ids: form.audience === 'selected' ? form.schools.map((school) => school.id) : [],
    }
    saveMutation.mutate(payload)
  }

  const discounts = discountsQuery.data ?? []

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold">
            Discounts
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-[var(--color-ink)]/70">
            Percent off subscription invoices. A first-months discount follows the school from
            the day its subscription started, and only those months are reduced on a monthly or
            annual bill. When two discounts match one invoice, the larger saving is applied.
          </p>
        </div>
        <button type="button" className={btnPrimary} onClick={startCreate}>
          Add discount
        </button>
      </div>

      {discountsQuery.isLoading && <p className="text-sm text-[var(--color-ink)]/60">Loading…</p>}
      {discountsQuery.isError && (
        <p className="text-sm text-red-700">Could not load discounts.</p>
      )}

      {!discountsQuery.isLoading && discounts.length === 0 && (
        <p className="text-sm text-[var(--color-ink)]/60">No discounts yet.</p>
      )}

      {discounts.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-[var(--color-line)] bg-white/90">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[var(--color-line)] text-xs text-[var(--color-ink)]/60">
              <tr>
                <th className="px-4 py-3 font-medium">Discount</th>
                <th className="px-4 py-3 font-medium">Off</th>
                <th className="px-4 py-3 font-medium">Who</th>
                <th className="px-4 py-3 font-medium">When</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium" />
              </tr>
            </thead>
            <tbody>
              {discounts.map((discount) => (
                <tr key={discount.id} className="border-b border-[var(--color-line)] last:border-0">
                  <td className="px-4 py-3">
                    <div className="font-medium">{discount.name}</div>
                    <div className="text-xs text-[var(--color-ink)]/50">{discount.code}</div>
                  </td>
                  <td className="px-4 py-3">{Number(discount.discount_percent)}%</td>
                  <td className="px-4 py-3">
                    {AUDIENCE_LABEL[discount.audience]}
                    {discount.billing_interval ? ` · ${discount.billing_interval}` : ' · any interval'}
                  </td>
                  <td className="px-4 py-3">
                    {discount.schedule === 'introductory'
                      ? `First ${discount.duration_months} months`
                      : SCHEDULE_LABEL[discount.schedule]}
                  </td>
                  <td className="px-4 py-3">{discount.is_active ? 'Active' : 'Inactive'}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button type="button" className={btnGhost} onClick={() => startEdit(discount)}>
                        Edit
                      </button>
                      <button
                        type="button"
                        className={btnGhost}
                        onClick={() => {
                          setShowForm(false)
                          setEditingId(null)
                          setOpenId(discount.id)
                        }}
                      >
                        Schools
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal
        open={Boolean(openId)}
        title={`Schools receiving ${detailQuery.data?.name || 'this discount'}`}
        description="Revoke stops this discount on the school's next invoice. Restore puts the same discount back for any months still left in the original window. Invoices already issued stay as they are."
        onClose={() => setOpenId(null)}
      >
        <div className="mb-3 flex justify-end">
          {detailQuery.data && detailQuery.data.redemption_count === 0 && openId && (
            <button
              type="button"
              className={btnDanger}
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(openId)}
            >
              Delete discount
            </button>
          )}
        </div>
        {detailQuery.isLoading && (
          <p className="text-sm text-[var(--color-ink)]/60">Loading schools…</p>
        )}
        {detailQuery.data && (detailQuery.data.redemptions ?? []).length === 0 && (
          <p className="text-sm text-[var(--color-ink)]/60">
            No school has been billed with this discount yet.
          </p>
        )}
        <ul className="space-y-2 text-sm">
          {(detailQuery.data?.redemptions ?? []).map((redemption) => (
            <li key={redemption.id} className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <strong>{redemption.school_name}</strong>
                {' · '}
                {Number(redemption.discount_percent)}%
                {redemption.revoked_at
                  ? ' · revoked'
                  : redemption.ends_at
                    ? ` · until ${formatDate(redemption.ends_at)}`
                    : ' · recurring'}
              </span>
              {openId && redemption.revoked_at ? (
                <button
                  type="button"
                  className={btnGhost}
                  disabled={restoreMutation.isPending}
                  onClick={() =>
                    restoreMutation.mutate({ discountId: openId, redemptionId: redemption.id })
                  }
                >
                  Restore
                </button>
              ) : (
                openId && (
                  <button
                    type="button"
                    className={btnDanger}
                    disabled={revokeMutation.isPending}
                    onClick={() =>
                      revokeMutation.mutate({ discountId: openId, redemptionId: redemption.id })
                    }
                  >
                    Revoke
                  </button>
                )
              )}
            </li>
          ))}
        </ul>
      </Modal>

      <Modal
        open={showForm}
        title={editingId ? 'Edit discount' : 'New discount'}
        description="A school keeps the percent and dates from the first invoice this discount applied to. Later edits affect schools that have not been billed with it yet."
        onClose={() => {
          setShowForm(false)
          setEditingId(null)
        }}
      >
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Name">
              <input
                required
                className={inputClass}
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              />
            </Field>
            <Field label="Code">
              <input
                required
                className={inputClass}
                value={form.code}
                onChange={(event) => {
                  setCodeTouched(true)
                  setForm((current) => ({ ...current, code: slugify(event.target.value) }))
                }}
              />
            </Field>
            <Field label="Percent off">
              <input
                required
                min={0.01}
                max={100}
                step="0.01"
                type="number"
                className={inputClass}
                value={form.discount_percent}
                onChange={(event) =>
                  setForm((current) => ({ ...current, discount_percent: event.target.value }))
                }
              />
            </Field>
            <Field label="Applies to">
              <select
                className={inputClass}
                value={form.applies_to}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    applies_to: event.target.value as FormState['applies_to'],
                  }))
                }
              >
                <option value="application">Application subscription</option>
                <option value="communication">Communication add-ons</option>
                <option value="all">Application and communication</option>
              </select>
            </Field>
            <Field label="Who">
              <select
                className={inputClass}
                value={form.audience}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    audience: event.target.value as FormState['audience'],
                  }))
                }
              >
                <option value="new">New schools</option>
                <option value="all">All schools</option>
                <option value="selected">Selected schools</option>
              </select>
            </Field>
            <Field
              label="Billing interval"
              hint="Leave as any interval so the months apply whether the school pays monthly or annually."
            >
              <select
                className={inputClass}
                value={form.billing_interval}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    billing_interval: event.target.value as FormState['billing_interval'],
                  }))
                }
              >
                <option value="">Any interval</option>
                <option value="monthly">Monthly only</option>
                <option value="annual">Annual only</option>
              </select>
            </Field>
            <Field label="Schedule">
              <select
                className={inputClass}
                value={form.schedule}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    schedule: event.target.value as FormState['schedule'],
                  }))
                }
              >
                <option value="introductory">First months of the school</option>
                <option value="recurring">Every invoice</option>
                <option value="date_range">Date range</option>
              </select>
            </Field>
            {form.schedule === 'introductory' && (
              <Field
                label="Months from subscription start"
                hint="Six months on an annual plan reduces half of that invoice."
              >
                <input
                  required
                  min={1}
                  type="number"
                  className={inputClass}
                  value={form.duration_months}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      duration_months: Number(event.target.value),
                    }))
                  }
                />
              </Field>
            )}
            {form.schedule === 'date_range' && (
              <>
                <Field label="First day">
                  <input
                    required
                    type="date"
                    className={inputClass}
                    value={form.starts_on}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, starts_on: event.target.value }))
                    }
                  />
                </Field>
                <Field
                  label="Last day"
                  hint="A billing month is included when it starts on or between these days."
                >
                  <input
                    required
                    type="date"
                    className={inputClass}
                    value={form.ends_on}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, ends_on: event.target.value }))
                    }
                  />
                </Field>
              </>
            )}
          </div>

          {form.audience === 'selected' && (
            <div>
              <span className={labelClass}>Schools</span>
              {form.schools.length > 0 && (
                <div className="mb-2 flex flex-wrap gap-2">
                  {form.schools.map((school) => (
                    <button
                      key={school.id}
                      type="button"
                      className="rounded-full border border-[var(--color-line)] px-3 py-1 text-xs"
                      onClick={() => toggleSchool(school)}
                    >
                      {school.name} ×
                    </button>
                  ))}
                </div>
              )}
              <input
                className={inputClass}
                placeholder="Search schools"
                value={schoolSearch}
                onChange={(event) => setSchoolSearch(event.target.value)}
              />
              <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-sm">
                {(schoolsQuery.data?.results ?? []).map((school) => (
                  <li key={school.id}>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(school.id)}
                        onChange={() => toggleSchool({ id: school.id, name: school.name })}
                      />
                      <span>{school.name}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) =>
                setForm((current) => ({ ...current, is_active: event.target.checked }))
              }
            />
            Active — applied the next time a matching school is invoiced
          </label>

          <div className="flex gap-2">
            <button type="submit" className={btnPrimary} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Saving…' : 'Save discount'}
            </button>
            <button
              type="button"
              className={btnGhost}
              onClick={() => {
                setShowForm(false)
                setEditingId(null)
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
