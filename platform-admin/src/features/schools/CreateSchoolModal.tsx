import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listAddonSkus, listPlans } from '@/features/billing/services'
import { formatGhs } from '@/features/messages/lib'
import type { AddonSku, Plan } from '@/features/billing/types'

export type CreateSchoolPayload = {
  name: string
  phone_number: string
  email: string
  region: string
  category: string
  plan_code: string
  interval: 'monthly' | 'annual'
  sms_sku_code?: string
  email_sku_code?: string
}

type Props = {
  open: boolean
  pending: boolean
  onClose: () => void
  onCreate: (payload: CreateSchoolPayload) => void
}

type CreateForm = {
  name: string
  phone_number: string
  email: string
  region: string
  category: string
  plan_code: string
  interval: 'monthly' | 'annual'
  sms_sku_code: string
  email_sku_code: string
}

const EMPTY: CreateForm = {
  name: '',
  phone_number: '',
  email: '',
  region: '',
  category: 'primary',
  plan_code: '',
  interval: 'annual',
  sms_sku_code: '',
  email_sku_code: '',
}

function planPrice(plan: Plan, interval: 'monthly' | 'annual') {
  return interval === 'annual' ? plan.price_annual_ghs : plan.price_monthly_ghs
}

function skuFits(sku: AddonSku, plan: Plan, interval: 'monthly' | 'annual') {
  if (!sku.is_active || sku.interval !== interval) return false
  return (sku.available_plans ?? []).some((item) => item.id === plan.id)
}

export default function CreateSchoolModal({ open, pending, onClose, onCreate }: Props) {
  const [form, setForm] = useState(EMPTY)

  const plansQuery = useQuery({
    queryKey: ['platform-billing-plans'],
    queryFn: listPlans,
    enabled: open,
  })
  const addonsQuery = useQuery({
    queryKey: ['platform-comms-skus'],
    queryFn: listAddonSkus,
    enabled: open,
  })

  useEffect(() => {
    if (!open) setForm(EMPTY)
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape' && !pending) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, pending, onClose])

  const plans = useMemo(
    () => (plansQuery.data ?? []).filter((plan) => plan.is_active),
    [plansQuery.data],
  )
  const selectedPlan = plans.find((plan) => plan.code === form.plan_code) ?? null
  const smsOptions = selectedPlan
    ? (addonsQuery.data ?? []).filter(
        (sku) => sku.channel === 'sms' && skuFits(sku, selectedPlan, form.interval),
      )
    : []
  const emailOptions = selectedPlan
    ? (addonsQuery.data ?? []).filter(
        (sku) => sku.channel === 'email' && skuFits(sku, selectedPlan, form.interval),
      )
    : []

  const openingTotal = useMemo(() => {
    if (!selectedPlan) return null
    let total = Number(planPrice(selectedPlan, form.interval))
    const sms = smsOptions.find((sku) => sku.code === form.sms_sku_code)
    const email = emailOptions.find((sku) => sku.code === form.email_sku_code)
    if (sms) total += Number(sms.price_ghs)
    if (email) total += Number(email.price_ghs)
    return Number.isFinite(total) ? total : null
  }, [emailOptions, form.email_sku_code, form.interval, form.sms_sku_code, selectedPlan, smsOptions])

  if (!open) return null

  function setInterval(interval: 'monthly' | 'annual') {
    setForm((prev) => ({
      ...prev,
      interval,
      sms_sku_code: '',
      email_sku_code: '',
    }))
  }

  function setPlan(planCode: string) {
    setForm((prev) => ({
      ...prev,
      plan_code: planCode,
      sms_sku_code: '',
      email_sku_code: '',
    }))
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    onCreate({
      name: form.name.trim(),
      phone_number: form.phone_number.trim(),
      email: form.email.trim(),
      region: form.region.trim(),
      category: form.category,
      plan_code: form.plan_code,
      interval: form.interval,
      sms_sku_code: form.sms_sku_code || undefined,
      email_sku_code: form.email_sku_code || undefined,
    })
  }

  return (
    <div className="fixed inset-0 z-30 flex items-start justify-center overflow-y-auto bg-black/30 px-4 py-10">
      <button
        type="button"
        aria-label="Close create school"
        className="absolute inset-0 cursor-default"
        onClick={() => {
          if (!pending) onClose()
        }}
      />
      <form
        onSubmit={onSubmit}
        className="relative z-10 w-full max-w-2xl rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg"
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold">
              Create school
            </h2>
            <p className="mt-1 text-sm text-[var(--color-ink)]/70">
              The school starts pending. The opening invoice uses the plan and add-ons you choose.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={pending}
            className="rounded-lg px-2 py-1 text-sm text-[var(--color-ink)]/60"
          >
            Close
          </button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {(
            [
              ['name', 'School name', true],
              ['phone_number', 'Phone', true],
              ['email', 'Email', false],
              ['region', 'Region', false],
            ] as const
          ).map(([key, label, required]) => (
            <label key={key} className="block text-sm">
              <span className="mb-1 block font-medium">{label}</span>
              <input
                required={required}
                value={form[key]}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, [key]: event.target.value }))
                }
                className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
              />
            </label>
          ))}
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Category</span>
            <select
              value={form.category}
              onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value }))}
              className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
            >
              <option value="primary">Primary</option>
              <option value="jhs">JHS</option>
              <option value="kindergarten">Kindergarten</option>
              <option value="nursery">Nursery</option>
              <option value="creche">Creche</option>
              <option value="mixed">Mixed</option>
              <option value="other">Other</option>
            </select>
          </label>
          <fieldset className="block text-sm">
            <legend className="mb-1 font-medium">Billing interval</legend>
            <div className="flex gap-2">
              {(['monthly', 'annual'] as const).map((interval) => (
                <label
                  key={interval}
                  className={`flex-1 rounded-xl border px-3 py-2 capitalize ${
                    form.interval === interval
                      ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10'
                      : 'border-[var(--color-line)]'
                  }`}
                >
                  <input
                    type="radio"
                    name="interval"
                    className="mr-2"
                    checked={form.interval === interval}
                    onChange={() => setInterval(interval)}
                  />
                  {interval}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="block text-sm md:col-span-2">
            <span className="mb-1 block font-medium">Plan</span>
            <select
              required
              value={form.plan_code}
              onChange={(event) => setPlan(event.target.value)}
              className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
            >
              <option value="">Select a plan</option>
              {plans.map((plan) => (
                <option key={plan.id} value={plan.code}>
                  {plan.name} · {formatGhs(planPrice(plan, form.interval))} / {form.interval}
                </option>
              ))}
            </select>
            {plansQuery.isLoading && (
              <p className="mt-1 text-xs text-[var(--color-ink)]/60">Loading plans…</p>
            )}
            {plansQuery.isError && (
              <p className="mt-1 text-xs text-red-700">Could not load plans.</p>
            )}
            {!plansQuery.isLoading && plans.length === 0 && (
              <p className="mt-1 text-xs text-red-700">No active plans are available.</p>
            )}
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">SMS add-on</span>
            <select
              value={form.sms_sku_code}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, sms_sku_code: event.target.value }))
              }
              className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
            >
              <option value="">None</option>
              {smsOptions.map((sku) => (
                <option key={sku.id} value={sku.code}>
                  {sku.name} · {formatGhs(sku.price_ghs)} · {sku.credits_per_period} credits
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Email add-on</span>
            <select
              value={form.email_sku_code}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, email_sku_code: event.target.value }))
              }
              className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
            >
              <option value="">None</option>
              {emailOptions.map((sku) => (
                <option key={sku.id} value={sku.code}>
                  {sku.name} · {formatGhs(sku.price_ghs)} · {sku.credits_per_period} credits
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-[var(--color-ink)]/70">
            Opening invoice {openingTotal == null ? '—' : formatGhs(openingTotal)}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={pending}
              className="rounded-xl border border-[var(--color-line)] px-3 py-2 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={pending || !form.plan_code}
              className="rounded-xl bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {pending ? 'Creating…' : 'Create pending school'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
