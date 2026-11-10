import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import {
  createAddonSku,
  createPlan,
  createTopUpPackage,
  deleteAddonSku,
  deletePlan,
  deleteTopUpPackage,
  listAddonSkus,
  listPlans,
  listTopUpPackages,
  patchAddonSku,
  patchPlan,
  patchTopUpPackage,
  seedCommunicationSkus,
  seedPlans,
  seedTopUpPackages,
} from './services'
import type {
  AddonSku,
  AddonSkuInput,
  Plan,
  PlanInput,
  TopUpPackage,
  TopUpPackageInput,
} from './types'

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

function formatGhs(value: string | number | null | undefined) {
  if (value == null || value === '') return '—'
  return `GH₵ ${Number(value).toLocaleString('en-GH', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40)
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

const EMPTY_PLAN: PlanInput = {
  code: '',
  name: '',
  student_min: 1,
  student_max: 100,
  staff_min: 1,
  staff_max: 10,
  price_monthly_ghs: '0.00',
  price_annual_ghs: '0.00',
  sort_order: 1,
  is_active: false,
}

const EMPTY_ADDON: AddonSkuInput = {
  code: '',
  name: '',
  channel: 'sms',
  interval: 'monthly',
  credits_per_period: 1000,
  price_ghs: '0.00',
  available_plan_ids: [],
  sort_order: 1,
  is_active: false,
}

const EMPTY_TOPUP: TopUpPackageInput = {
  code: '',
  name: '',
  channel: 'sms',
  credits: 100,
  discount_percent: '0.00',
  sort_order: 1,
  is_active: false,
}

function Field({
  label,
  children,
  hint,
  className = '',
}: {
  label: string
  children: ReactNode
  hint?: string
  className?: string
}) {
  return (
    <label className={`block ${className}`}>
      <span className={labelClass}>{label}</span>
      {children}
      {hint ? <span className="mt-1 block text-xs text-[var(--color-ink)]/50">{hint}</span> : null}
    </label>
  )
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
        className="relative z-10 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-xl"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="font-[family-name:var(--font-display)] text-xl font-semibold">
              {title}
            </h3>
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

export default function PlansPage() {
  const queryClient = useQueryClient()

  const plansQuery = useQuery({ queryKey: ['platform-billing-plans'], queryFn: listPlans })
  const addonsQuery = useQuery({ queryKey: ['platform-comms-skus'], queryFn: listAddonSkus })
  const topupsQuery = useQuery({
    queryKey: ['platform-billing-topups'],
    queryFn: listTopUpPackages,
  })

  const [planForm, setPlanForm] = useState<PlanInput>(EMPTY_PLAN)
  const [editingPlanId, setEditingPlanId] = useState<string | null>(null)
  const [showPlanForm, setShowPlanForm] = useState(false)

  const [addonForm, setAddonForm] = useState<AddonSkuInput>(EMPTY_ADDON)
  const [editingAddonId, setEditingAddonId] = useState<string | null>(null)
  const [showAddonForm, setShowAddonForm] = useState(false)

  const [topupForm, setTopupForm] = useState<TopUpPackageInput>(EMPTY_TOPUP)
  const [editingTopupId, setEditingTopupId] = useState<string | null>(null)
  const [showTopupForm, setShowTopupForm] = useState(false)

  const invalidatePlans = () =>
    void queryClient.invalidateQueries({ queryKey: ['platform-billing-plans'] })
  const invalidateAddons = () =>
    void queryClient.invalidateQueries({ queryKey: ['platform-comms-skus'] })
  const invalidateTopups = () =>
    void queryClient.invalidateQueries({ queryKey: ['platform-billing-topups'] })

  const seedPlansMutation = useMutation({
    mutationFn: seedPlans,
    onSuccess: () => {
      toast.success('Default plans seeded')
      invalidatePlans()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const seedAddonsMutation = useMutation({
    mutationFn: seedCommunicationSkus,
    onSuccess: () => {
      toast.success('Default addon SKUs seeded')
      invalidateAddons()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const seedTopupsMutation = useMutation({
    mutationFn: seedTopUpPackages,
    onSuccess: () => {
      toast.success('Top-up packages seeded from Messages prices')
      invalidateTopups()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const savePlanMutation = useMutation({
    mutationFn: async () => {
      const payload: PlanInput = {
        ...planForm,
        code: planForm.code || slugify(planForm.name),
        student_max:
          planForm.student_max === null || Number.isNaN(Number(planForm.student_max))
            ? null
            : Number(planForm.student_max),
        staff_max:
          planForm.staff_max === null || Number.isNaN(Number(planForm.staff_max))
            ? null
            : Number(planForm.staff_max),
      }
      if (editingPlanId) return patchPlan(editingPlanId, payload)
      return createPlan(payload)
    },
    onSuccess: () => {
      toast.success(editingPlanId ? 'Plan updated' : 'Plan created (inactive until activated)')
      closePlanModal()
      invalidatePlans()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const saveAddonMutation = useMutation({
    mutationFn: async () => {
      const payload: AddonSkuInput = {
        ...addonForm,
        code: addonForm.code || slugify(addonForm.name),
        available_plan_ids: addonForm.available_plan_ids ?? [],
      }
      if (editingAddonId) return patchAddonSku(editingAddonId, payload)
      return createAddonSku(payload)
    },
    onSuccess: () => {
      toast.success(editingAddonId ? 'Addon SKU updated' : 'Addon SKU created (inactive until activated)')
      closeAddonModal()
      invalidateAddons()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const saveTopupMutation = useMutation({
    mutationFn: async () => {
      const payload: TopUpPackageInput = {
        ...topupForm,
        code: topupForm.code || slugify(topupForm.name),
      }
      if (editingTopupId) return patchTopUpPackage(editingTopupId, payload)
      return createTopUpPackage(payload)
    },
    onSuccess: () => {
      toast.success(editingTopupId ? 'Top-up updated' : 'Top-up created (inactive until activated)')
      closeTopupModal()
      invalidateTopups()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const deletePlanMutation = useMutation({
    mutationFn: deletePlan,
    onSuccess: () => {
      toast.success('Plan deleted')
      invalidatePlans()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const deleteAddonMutation = useMutation({
    mutationFn: deleteAddonSku,
    onSuccess: () => {
      toast.success('Addon SKU deleted')
      invalidateAddons()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const deleteTopupMutation = useMutation({
    mutationFn: deleteTopUpPackage,
    onSuccess: () => {
      toast.success('Top-up package deleted')
      invalidateTopups()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  function confirmAction(message: string, action: () => void) {
    if (window.confirm(message)) action()
  }

  function closePlanModal() {
    setShowPlanForm(false)
    setEditingPlanId(null)
    setPlanForm(EMPTY_PLAN)
  }

  function closeAddonModal() {
    setShowAddonForm(false)
    setEditingAddonId(null)
    setAddonForm(EMPTY_ADDON)
  }

  function closeTopupModal() {
    setShowTopupForm(false)
    setEditingTopupId(null)
    setTopupForm(EMPTY_TOPUP)
  }

  function startEditPlan(plan: Plan) {
    setEditingPlanId(plan.id)
    setPlanForm({
      code: plan.code,
      name: plan.name,
      student_min: plan.student_min,
      student_max: plan.student_max,
      staff_min: plan.staff_min,
      staff_max: plan.staff_max,
      price_monthly_ghs: plan.price_monthly_ghs,
      price_annual_ghs: plan.price_annual_ghs,
      sort_order: plan.sort_order,
      is_active: plan.is_active,
      warning_thresholds: plan.warning_thresholds,
    })
    setShowPlanForm(true)
  }

  function startEditAddon(sku: AddonSku) {
    setEditingAddonId(sku.id)
    setAddonForm({
      code: sku.code,
      name: sku.name,
      channel: sku.channel,
      interval: sku.interval,
      credits_per_period: sku.credits_per_period,
      price_ghs: sku.price_ghs,
      available_plan_ids: sku.available_plan_ids ?? sku.available_plans?.map((p) => p.id) ?? [],
      sort_order: sku.sort_order,
      is_active: sku.is_active,
    })
    setShowAddonForm(true)
  }

  function startEditTopup(pkg: TopUpPackage) {
    setEditingTopupId(pkg.id)
    setTopupForm({
      code: pkg.code,
      name: pkg.name,
      channel: pkg.channel,
      credits: pkg.credits,
      discount_percent: pkg.discount_percent ?? '0.00',
      sort_order: pkg.sort_order,
      is_active: pkg.is_active,
    })
    setShowTopupForm(true)
  }

  const addonReferenceHint = useMemo(() => {
    if (!editingAddonId) return null
    return addonsQuery.data?.find((s) => s.id === editingAddonId)?.reference_price_ghs ?? null
  }, [addonsQuery.data, editingAddonId])

  function toggleAddonPlan(planId: string) {
    setAddonForm((prev) => {
      const current = new Set(prev.available_plan_ids ?? [])
      if (current.has(planId)) current.delete(planId)
      else current.add(planId)
      return { ...prev, available_plan_ids: [...current] }
    })
  }

  return (
    <div>
      {/* Plans */}
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold">Plans</h1>
          <p className="mt-2 text-sm text-[var(--color-ink)]/70">
            Application tiers by student/staff capacity. New plans start inactive — activate when
            ready to sell.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={btnPrimary}
            onClick={() => {
              setEditingPlanId(null)
              setPlanForm(EMPTY_PLAN)
              setShowPlanForm(true)
            }}
          >
            Add plan
          </button>
          <button
            type="button"
            className={btnGhost}
            disabled={seedPlansMutation.isPending}
            onClick={() =>
              confirmAction(
                'Seed will create or overwrite default plans (starter, basic, standard, premium, enterprise) by code and mark them active. Custom plan codes are unchanged. Continue?',
                () => seedPlansMutation.mutate(),
              )
            }
          >
            Seed defaults
          </button>
        </div>
      </div>

      {plansQuery.isLoading && <p className="text-sm text-[var(--color-ink)]/60">Loading…</p>}
      {plansQuery.isError && <p className="text-sm text-red-700">Could not load plans.</p>}

      <div className="overflow-hidden rounded-2xl border border-[var(--color-line)] bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-[var(--color-line)] bg-[var(--color-accent-soft)]/40 text-[var(--color-ink)]/70">
            <tr>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium">Students</th>
              <th className="px-4 py-3 font-medium">Staff</th>
              <th className="px-4 py-3 font-medium">Monthly</th>
              <th className="px-4 py-3 font-medium">Annual</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {(plansQuery.data ?? []).map((plan) => (
              <tr key={plan.id} className="border-b border-[var(--color-line)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium">{plan.name}</div>
                  <div className="text-xs text-[var(--color-ink)]/50">{plan.code}</div>
                </td>
                <td className="px-4 py-3">
                  {plan.student_max != null
                    ? `${plan.student_min}–${plan.student_max}`
                    : `${plan.student_min}+`}
                </td>
                <td className="px-4 py-3">
                  {plan.staff_max != null
                    ? `${plan.staff_min}–${plan.staff_max}`
                    : `${plan.staff_min}+`}
                </td>
                <td className="px-4 py-3">{formatGhs(plan.price_monthly_ghs)}</td>
                <td className="px-4 py-3">{formatGhs(plan.price_annual_ghs)}</td>
                <td className="px-4 py-3">{plan.is_active ? 'Active' : 'Inactive'}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button type="button" className={btnGhost} onClick={() => startEditPlan(plan)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className={btnDanger}
                      disabled={deletePlanMutation.isPending}
                      onClick={() =>
                        confirmAction(`Delete plan “${plan.name}”? This cannot be undone.`, () =>
                          deletePlanMutation.mutate(plan.id),
                        )
                      }
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(plansQuery.data?.length ?? 0) === 0 && !plansQuery.isLoading && (
          <p className="px-4 py-6 text-sm text-[var(--color-ink)]/60">
            No plans yet. Seed defaults or add a plan.
          </p>
        )}
      </div>

      {/* Addon SKUs */}
      <div className="mb-4 mt-12 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold">
            Recurring addon SKUs
          </h2>
          <p className="mt-2 text-sm text-[var(--color-ink)]/70">
            Fixed GHS on renewals, gated to selected plans. New SKUs start inactive.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={btnPrimary}
            onClick={() => {
              setEditingAddonId(null)
              setAddonForm(EMPTY_ADDON)
              setShowAddonForm(true)
            }}
          >
            Add addon SKU
          </button>
          <button
            type="button"
            className={btnGhost}
            disabled={seedAddonsMutation.isPending}
            onClick={() =>
              confirmAction(
                'Seed will create or overwrite default addon SKUs by code, mark them active, and attach them to all existing plans. Custom SKU codes are unchanged. Continue?',
                () => seedAddonsMutation.mutate(),
              )
            }
          >
            Seed addons
          </button>
        </div>
      </div>

      {addonsQuery.isError && (
        <p className="mb-3 text-sm text-red-700">Could not load addon SKUs.</p>
      )}

      <div className="overflow-hidden rounded-2xl border border-[var(--color-line)] bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-[var(--color-line)] bg-[var(--color-accent-soft)]/40 text-[var(--color-ink)]/70">
            <tr>
              <th className="px-4 py-3 font-medium">SKU</th>
              <th className="px-4 py-3 font-medium">Channel</th>
              <th className="px-4 py-3 font-medium">Plans</th>
              <th className="px-4 py-3 font-medium">Credits</th>
              <th className="px-4 py-3 font-medium">Cost</th>
              <th className="px-4 py-3 font-medium">Messages ref.</th>
              <th className="px-4 py-3 font-medium">Fixed price</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {(addonsQuery.data ?? []).map((sku) => (
              <tr key={sku.id} className="border-b border-[var(--color-line)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium">{sku.name}</div>
                  <div className="text-xs text-[var(--color-ink)]/50">
                    {sku.code} · {sku.interval}
                  </div>
                </td>
                <td className="px-4 py-3 uppercase">{sku.channel}</td>
                <td className="px-4 py-3">
                  {(sku.available_plans?.length ?? 0) === 0 ? (
                    <span className="text-[var(--color-ink)]/45">None</span>
                  ) : (
                    <span className="text-xs">
                      {sku.available_plans!.map((p) => p.code).join(', ')}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">{sku.credits_per_period.toLocaleString()}</td>
                <td className="px-4 py-3">
                  <div>{formatGhs(sku.cost_price_ghs)}</div>
                  <div className="text-xs text-[var(--color-ink)]/50">
                    @ {formatGhs(sku.provider_unit_cost_ghs)} / unit
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div>{formatGhs(sku.reference_price_ghs)}</div>
                  <div className="text-xs text-[var(--color-ink)]/50">
                    @ {formatGhs(sku.unit_price_ghs)} / unit
                  </div>
                </td>
                <td className="px-4 py-3 font-medium">{formatGhs(sku.price_ghs)}</td>
                <td className="px-4 py-3">{sku.is_active ? 'Active' : 'Inactive'}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button type="button" className={btnGhost} onClick={() => startEditAddon(sku)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className={btnDanger}
                      disabled={deleteAddonMutation.isPending}
                      onClick={() =>
                        confirmAction(`Delete addon “${sku.name}”? This cannot be undone.`, () =>
                          deleteAddonMutation.mutate(sku.id),
                        )
                      }
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(addonsQuery.data?.length ?? 0) === 0 && !addonsQuery.isLoading && (
          <p className="px-4 py-6 text-sm text-[var(--color-ink)]/60">
            No addon SKUs yet. Seed defaults or add one.
          </p>
        )}
      </div>

      {/* Top-ups */}
      <div className="mb-4 mt-12 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold">
            Top-up packages
          </h2>
          <p className="mt-2 text-sm text-[var(--color-ink)]/70">
            Final price = Messages sell × credits − discount. New packages start inactive.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={btnPrimary}
            onClick={() => {
              setEditingTopupId(null)
              setTopupForm(EMPTY_TOPUP)
              setShowTopupForm(true)
            }}
          >
            Add top-up
          </button>
          <button
            type="button"
            className={btnGhost}
            disabled={seedTopupsMutation.isPending}
            onClick={() =>
              confirmAction(
                'Seed will create or overwrite default top-up packages by code, recalculate prices from current Messages sell rates (with default discounts), and mark them active. Custom package codes are unchanged. Continue?',
                () => seedTopupsMutation.mutate(),
              )
            }
          >
            Seed top-ups
          </button>
        </div>
      </div>

      {topupsQuery.isError && (
        <p className="mb-3 text-sm text-red-700">Could not load top-up packages.</p>
      )}

      <div className="overflow-hidden rounded-2xl border border-[var(--color-line)] bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-[var(--color-line)] bg-[var(--color-accent-soft)]/40 text-[var(--color-ink)]/70">
            <tr>
              <th className="px-4 py-3 font-medium">Package</th>
              <th className="px-4 py-3 font-medium">Channel</th>
              <th className="px-4 py-3 font-medium">Credits</th>
              <th className="px-4 py-3 font-medium">Cost</th>
              <th className="px-4 py-3 font-medium">List</th>
              <th className="px-4 py-3 font-medium">Discount</th>
              <th className="px-4 py-3 font-medium">Final</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {(topupsQuery.data ?? []).map((pkg) => (
              <tr key={pkg.id} className="border-b border-[var(--color-line)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium">{pkg.name}</div>
                  <div className="text-xs text-[var(--color-ink)]/50">{pkg.code}</div>
                </td>
                <td className="px-4 py-3 uppercase">{pkg.channel}</td>
                <td className="px-4 py-3">{pkg.credits.toLocaleString()}</td>
                <td className="px-4 py-3">
                  <div>{formatGhs(pkg.cost_price_ghs)}</div>
                  <div className="text-xs text-[var(--color-ink)]/50">
                    @ {formatGhs(pkg.provider_unit_cost_ghs)} / unit
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div>{formatGhs(pkg.list_price_ghs)}</div>
                  <div className="text-xs text-[var(--color-ink)]/50">
                    @ {formatGhs(pkg.unit_price_ghs)} / unit
                  </div>
                </td>
                <td className="px-4 py-3">{Number(pkg.discount_percent || 0)}%</td>
                <td className="px-4 py-3 font-medium">{formatGhs(pkg.price_ghs)}</td>
                <td className="px-4 py-3">{pkg.is_active ? 'Active' : 'Inactive'}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button type="button" className={btnGhost} onClick={() => startEditTopup(pkg)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className={btnDanger}
                      disabled={deleteTopupMutation.isPending}
                      onClick={() =>
                        confirmAction(`Delete top-up “${pkg.name}”? This cannot be undone.`, () =>
                          deleteTopupMutation.mutate(pkg.id),
                        )
                      }
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(topupsQuery.data?.length ?? 0) === 0 && !topupsQuery.isLoading && (
          <p className="px-4 py-6 text-sm text-[var(--color-ink)]/60">
            No top-up packages yet. Seed defaults or add one.
          </p>
        )}
      </div>

      {/* ---------------- Modals ---------------- */}
      <Modal
        open={showPlanForm}
        title={editingPlanId ? 'Edit plan' : 'Add plan'}
        description="New plans are inactive until you turn Active on."
        onClose={closePlanModal}
      >
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            savePlanMutation.mutate()
          }}
          className="grid gap-3 md:grid-cols-2"
        >
          <Field label="Name">
            <input
              required
              className={inputClass}
              value={planForm.name}
              onChange={(e) =>
                setPlanForm((p) => ({
                  ...p,
                  name: e.target.value,
                  code: editingPlanId ? p.code : slugify(e.target.value),
                }))
              }
            />
          </Field>
          <Field label="Code" hint="Stable slug used by subscriptions.">
            <input
              required
              className={inputClass}
              value={planForm.code}
              disabled={Boolean(editingPlanId)}
              onChange={(e) => setPlanForm((p) => ({ ...p, code: slugify(e.target.value) }))}
            />
          </Field>
          <Field label="Student min">
            <input
              type="number"
              min={1}
              required
              className={inputClass}
              value={planForm.student_min}
              onChange={(e) =>
                setPlanForm((p) => ({ ...p, student_min: Number(e.target.value) || 1 }))
              }
            />
          </Field>
          <Field label="Student max" hint="Empty = open-ended.">
            <input
              type="number"
              min={1}
              className={inputClass}
              value={planForm.student_max ?? ''}
              onChange={(e) =>
                setPlanForm((p) => ({
                  ...p,
                  student_max: e.target.value === '' ? null : Number(e.target.value),
                }))
              }
            />
          </Field>
          <Field label="Staff min">
            <input
              type="number"
              min={1}
              required
              className={inputClass}
              value={planForm.staff_min}
              onChange={(e) =>
                setPlanForm((p) => ({ ...p, staff_min: Number(e.target.value) || 1 }))
              }
            />
          </Field>
          <Field label="Staff max" hint="Empty = open-ended.">
            <input
              type="number"
              min={1}
              className={inputClass}
              value={planForm.staff_max ?? ''}
              onChange={(e) =>
                setPlanForm((p) => ({
                  ...p,
                  staff_max: e.target.value === '' ? null : Number(e.target.value),
                }))
              }
            />
          </Field>
          <Field label="Monthly price (GHS)">
            <input
              required
              inputMode="decimal"
              className={inputClass}
              value={planForm.price_monthly_ghs}
              onChange={(e) => setPlanForm((p) => ({ ...p, price_monthly_ghs: e.target.value }))}
            />
          </Field>
          <Field label="Annual price (GHS)">
            <input
              required
              inputMode="decimal"
              className={inputClass}
              value={planForm.price_annual_ghs}
              onChange={(e) => setPlanForm((p) => ({ ...p, price_annual_ghs: e.target.value }))}
            />
          </Field>
          <Field label="Sort order">
            <input
              type="number"
              min={1}
              className={inputClass}
              value={planForm.sort_order ?? 1}
              onChange={(e) =>
                setPlanForm((p) => ({ ...p, sort_order: Number(e.target.value) || 1 }))
              }
            />
          </Field>
          <Field label="Status" hint="Inactive plans are hidden from school catalog.">
            <select
              className={inputClass}
              value={planForm.is_active ? '1' : '0'}
              onChange={(e) => setPlanForm((p) => ({ ...p, is_active: e.target.value === '1' }))}
            >
              <option value="0">Inactive</option>
              <option value="1">Active</option>
            </select>
          </Field>
          <div className="md:col-span-2 flex gap-2 pt-2">
            <button type="submit" disabled={savePlanMutation.isPending} className={btnPrimary}>
              {savePlanMutation.isPending ? 'Saving…' : editingPlanId ? 'Save plan' : 'Create plan'}
            </button>
            <button type="button" className={btnGhost} onClick={closePlanModal}>
              Cancel
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={showAddonForm}
        title={editingAddonId ? 'Edit addon SKU' : 'Add addon SKU'}
        description="Assign plans that may buy this SKU. Empty plan list = available nowhere."
        onClose={closeAddonModal}
      >
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            saveAddonMutation.mutate()
          }}
          className="grid gap-3 md:grid-cols-2"
        >
          <Field label="Name">
            <input
              required
              className={inputClass}
              value={addonForm.name}
              onChange={(e) =>
                setAddonForm((p) => ({
                  ...p,
                  name: e.target.value,
                  code: editingAddonId ? p.code : slugify(e.target.value),
                }))
              }
            />
          </Field>
          <Field label="Code">
            <input
              required
              className={inputClass}
              value={addonForm.code}
              disabled={Boolean(editingAddonId)}
              onChange={(e) => setAddonForm((p) => ({ ...p, code: slugify(e.target.value) }))}
            />
          </Field>
          <Field label="Channel">
            <select
              className={inputClass}
              value={addonForm.channel}
              onChange={(e) =>
                setAddonForm((p) => ({
                  ...p,
                  channel: e.target.value as AddonSkuInput['channel'],
                }))
              }
            >
              <option value="sms">SMS</option>
              <option value="email">Email</option>
            </select>
          </Field>
          <Field label="Interval">
            <select
              className={inputClass}
              value={addonForm.interval}
              onChange={(e) =>
                setAddonForm((p) => ({
                  ...p,
                  interval: e.target.value as AddonSkuInput['interval'],
                }))
              }
            >
              <option value="monthly">Monthly</option>
              <option value="annual">Annual</option>
            </select>
          </Field>
          <Field label="Credits per period">
            <input
              type="number"
              min={1}
              required
              className={inputClass}
              value={addonForm.credits_per_period}
              onChange={(e) =>
                setAddonForm((p) => ({
                  ...p,
                  credits_per_period: Number(e.target.value) || 1,
                }))
              }
            />
          </Field>
          <Field
            label="Fixed price (GHS)"
            hint={
              addonReferenceHint
                ? `Messages reference: ${formatGhs(addonReferenceHint)}`
                : 'Billed on renewal — independent of Messages sell price.'
            }
          >
            <input
              required
              inputMode="decimal"
              className={inputClass}
              value={addonForm.price_ghs}
              onChange={(e) => setAddonForm((p) => ({ ...p, price_ghs: e.target.value }))}
            />
          </Field>
          <Field label="Sort order">
            <input
              type="number"
              min={1}
              className={inputClass}
              value={addonForm.sort_order ?? 1}
              onChange={(e) =>
                setAddonForm((p) => ({ ...p, sort_order: Number(e.target.value) || 1 }))
              }
            />
          </Field>
          <Field label="Status">
            <select
              className={inputClass}
              value={addonForm.is_active ? '1' : '0'}
              onChange={(e) => setAddonForm((p) => ({ ...p, is_active: e.target.value === '1' }))}
            >
              <option value="0">Inactive</option>
              <option value="1">Active</option>
            </select>
          </Field>
          <Field
            label="Available on plans"
            className="md:col-span-2"
            hint="Only schools on a selected plan can opt into this SKU. Empty = available nowhere."
          >
            <div className="max-h-40 space-y-2 overflow-y-auto rounded-lg border border-[var(--color-line)] p-3">
              {(plansQuery.data ?? []).length === 0 ? (
                <p className="text-sm text-[var(--color-ink)]/55">No plans in catalog.</p>
              ) : (
                (plansQuery.data ?? []).map((plan) => {
                  const checked = (addonForm.available_plan_ids ?? []).includes(plan.id)
                  return (
                    <label key={plan.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleAddonPlan(plan.id)}
                      />
                      <span>
                        {plan.name}{' '}
                        <span className="text-[var(--color-ink)]/50">
                          ({plan.code}
                          {plan.is_active ? '' : ' · inactive'})
                        </span>
                      </span>
                    </label>
                  )
                })
              )}
            </div>
          </Field>
          <div className="md:col-span-2 flex gap-2 pt-2">
            <button type="submit" disabled={saveAddonMutation.isPending} className={btnPrimary}>
              {saveAddonMutation.isPending
                ? 'Saving…'
                : editingAddonId
                  ? 'Save addon'
                  : 'Create addon'}
            </button>
            <button type="button" className={btnGhost} onClick={closeAddonModal}>
              Cancel
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        open={showTopupForm}
        title={editingTopupId ? 'Edit top-up' : 'Add top-up'}
        description="Final price is calculated from Messages sell price × credits − discount."
        onClose={closeTopupModal}
      >
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            saveTopupMutation.mutate()
          }}
          className="grid gap-3 md:grid-cols-2"
        >
          <Field label="Name">
            <input
              required
              className={inputClass}
              value={topupForm.name}
              onChange={(e) =>
                setTopupForm((p) => ({
                  ...p,
                  name: e.target.value,
                  code: editingTopupId ? p.code : slugify(e.target.value),
                }))
              }
            />
          </Field>
          <Field label="Code">
            <input
              required
              className={inputClass}
              value={topupForm.code}
              disabled={Boolean(editingTopupId)}
              onChange={(e) => setTopupForm((p) => ({ ...p, code: slugify(e.target.value) }))}
            />
          </Field>
          <Field label="Channel">
            <select
              className={inputClass}
              value={topupForm.channel}
              onChange={(e) =>
                setTopupForm((p) => ({
                  ...p,
                  channel: e.target.value as TopUpPackageInput['channel'],
                }))
              }
            >
              <option value="sms">SMS</option>
              <option value="email">Email</option>
            </select>
          </Field>
          <Field label="Credits">
            <input
              type="number"
              min={1}
              required
              className={inputClass}
              value={topupForm.credits}
              onChange={(e) =>
                setTopupForm((p) => ({ ...p, credits: Number(e.target.value) || 1 }))
              }
            />
          </Field>
          <Field label="Discount %" hint="Applied to list price (credits × Messages sell).">
            <input
              required
              inputMode="decimal"
              className={inputClass}
              value={topupForm.discount_percent}
              onChange={(e) => setTopupForm((p) => ({ ...p, discount_percent: e.target.value }))}
            />
          </Field>
          <Field label="Sort order">
            <input
              type="number"
              min={1}
              className={inputClass}
              value={topupForm.sort_order ?? 1}
              onChange={(e) =>
                setTopupForm((p) => ({ ...p, sort_order: Number(e.target.value) || 1 }))
              }
            />
          </Field>
          <Field label="Status" hint="Inactive packages are hidden from schools.">
            <select
              className={inputClass}
              value={topupForm.is_active ? '1' : '0'}
              onChange={(e) => setTopupForm((p) => ({ ...p, is_active: e.target.value === '1' }))}
            >
              <option value="0">Inactive</option>
              <option value="1">Active</option>
            </select>
          </Field>
          <div className="md:col-span-2 flex gap-2 pt-2">
            <button type="submit" disabled={saveTopupMutation.isPending} className={btnPrimary}>
              {saveTopupMutation.isPending
                ? 'Saving…'
                : editingTopupId
                  ? 'Save top-up'
                  : 'Create top-up'}
            </button>
            <button type="button" className={btnGhost} onClick={closeTopupModal}>
              Cancel
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
