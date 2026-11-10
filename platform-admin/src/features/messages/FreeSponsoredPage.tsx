import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { listSchools } from '@/features/schools/services'
import { FilterBar, rangeLabel, useMessagesFilters } from './components/filters'
import {
  Badge,
  Field,
  GhostButton,
  LayerTile,
  PageHeader,
  Panel,
  PrimaryButton,
  QueryNotice,
  SelectInput,
  SummaryStrip,
  TableState,
  TableWrap,
  Td,
  Th,
  Thead,
  TextInput,
} from './components/ui'
import { errorMessage, formatDate, formatGhs, formatPct, formatUnits } from './lib'
import { createAllowance, getFreeUsage, listAllowances, patchAllowance } from './services'
import { useMessagesAccess } from './permissions'
import type { AllowancePolicy, AllowancePolicyInput, Channel } from './types'

const EVENT_TYPES = [
  'ward_enrolled',
  'payment_receipt',
  'debt_reminder',
  'report_ready',
  'next_term_fees',
] as const

const EMPTY_FORM: AllowancePolicyInput = {
  scope: 'school',
  school: '',
  channel: 'sms',
  monthly_free_units: 0,
  daily_limit_units: null,
  applies_to_events: [],
  budget_ghs: null,
  alert_thresholds: [0.8, 0.95],
  starts_at: null,
  ends_at: null,
  is_active: true,
}

function toFormValues(policy: AllowancePolicy): AllowancePolicyInput {
  return {
    scope: policy.scope,
    school: policy.school ?? '',
    channel: policy.channel,
    monthly_free_units: policy.monthly_free_units,
    daily_limit_units: policy.daily_limit_units,
    applies_to_events: policy.applies_to_events ?? [],
    budget_ghs: policy.budget_ghs,
    alert_thresholds: policy.alert_thresholds ?? [],
    starts_at: policy.starts_at,
    ends_at: policy.ends_at,
    is_active: policy.is_active,
  }
}

export default function FreeSponsoredPage() {
  const queryClient = useQueryClient()
  const { filters, setFilter, params } = useMessagesFilters()
  const { can } = useMessagesAccess()
  const canWrite = can('allowances.write')
  const canSeeMoney = can('profitability.money')

  const [editingId, setEditingId] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<AllowancePolicyInput>(EMPTY_FORM)

  const allowancesQuery = useQuery({
    queryKey: ['platform-messages-allowances'],
    queryFn: () => listAllowances(),
    retry: false,
  })

  const freeUsageQuery = useQuery({
    queryKey: ['platform-messages-free-usage', params],
    queryFn: () => getFreeUsage(params),
    retry: false,
  })

  const schoolsQuery = useQuery({
    queryKey: ['platform-schools', 'filter-options'],
    queryFn: () => listSchools({ status: 'active' }),
    staleTime: 1000 * 60 * 10,
  })

  const saveMutation = useMutation({
    mutationFn: (payload: AllowancePolicyInput) =>
      editingId ? patchAllowance(editingId, payload) : createAllowance(payload),
    onSuccess: () => {
      toast.success(editingId ? 'Allowance updated' : 'Allowance created')
      setShowForm(false)
      setEditingId(null)
      setForm(EMPTY_FORM)
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-allowances'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-free-usage'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const toggleMutation = useMutation({
    mutationFn: (policy: AllowancePolicy) =>
      patchAllowance(policy.id, { is_active: !policy.is_active }),
    onSuccess: () => {
      toast.success('Allowance updated')
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-allowances'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const allowances = allowancesQuery.data ?? []
  const usage = freeUsageQuery.data

  function startEdit(policy: AllowancePolicy) {
    setEditingId(policy.id)
    setForm(toFormValues(policy))
    setShowForm(true)
  }

  function startCreate() {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  function toggleEvent(event: string) {
    setForm((prev) => {
      const current = prev.applies_to_events ?? []
      return {
        ...prev,
        applies_to_events: current.includes(event)
          ? current.filter((value) => value !== event)
          : [...current, event],
      }
    })
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    saveMutation.mutate({
      ...form,
      school: form.scope === 'school' ? form.school || null : null,
    })
  }

  return (
    <div>
      <PageHeader
        title="Free & sponsored messaging"
        description={`Allowances and sponsored budgets for ${rangeLabel(
          filters,
        )}. Free and sponsored sends never debit a school wallet — the platform absorbs the provider cost.`}
        actions={canWrite && <PrimaryButton onClick={startCreate}>New allowance</PrimaryButton>}
      />

      <FilterBar filters={filters} setFilter={setFilter} show={{ channel: true, school: true }} />

      <div className="mb-6">
        <QueryNotice
          isLoading={freeUsageQuery.isLoading}
          isError={freeUsageQuery.isError}
          error={freeUsageQuery.error}
        />
      </div>

      <SummaryStrip caption="Free & sponsored consumption">
        <LayerTile
          layer="credits"
          label="Free SMS segments"
          value={formatUnits(usage?.free_sms_segments)}
          hint={`${formatUnits(usage?.free_sms_messages)} messages`}
        />
        <LayerTile
          layer="credits"
          label="Sponsored SMS segments"
          value={formatUnits(usage?.sponsored_sms_segments)}
          hint={`${formatUnits(usage?.sponsored_sms_messages)} messages`}
        />
        <LayerTile
          layer="credits"
          label="Free email credits"
          value={formatUnits(usage?.free_email_credits)}
        />
        <LayerTile
          layer="credits"
          label="Sponsored email credits"
          value={formatUnits(usage?.sponsored_email_credits)}
        />
      </SummaryStrip>

      {canSeeMoney && (
        <SummaryStrip caption="Platform-funded expense">
          <LayerTile
            layer="usage"
            label="Provider cost absorbed"
            value={formatGhs(usage?.platform_funded_expense_ghs)}
            hint="Cost of free and sponsored traffic"
          />
          <LayerTile
            layer="cash"
            label="Budget cap"
            value={formatGhs(usage?.budget_ghs)}
            hint="Across active platform-scope allowances"
          />
          <LayerTile
            layer="usage"
            label="Budget used"
            value={formatPct(usage?.budget_used_pct)}
            hint="Alert thresholds fire against this"
          />
        </SummaryStrip>
      )}

      {showForm && canWrite && (
        <form onSubmit={onSubmit} className="mb-4">
          <Panel
            title={editingId ? 'Edit allowance policy' : 'New allowance policy'}
            description="Absent any policy, guardian traffic stays paid. Nothing here changes behaviour until a policy is active."
          >
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Scope">
                <SelectInput
                  value={form.scope}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      scope: e.target.value as AllowancePolicyInput['scope'],
                    }))
                  }
                >
                  <option value="school">Single school</option>
                  <option value="platform">Platform-wide</option>
                </SelectInput>
              </Field>
              {form.scope === 'school' && (
                <Field label="School">
                  <SelectInput
                    required
                    value={form.school ?? ''}
                    onChange={(e) => setForm((prev) => ({ ...prev, school: e.target.value }))}
                  >
                    <option value="">Select a school</option>
                    {(schoolsQuery.data?.results ?? []).map((school) => (
                      <option key={school.id} value={school.id}>
                        {school.name}
                      </option>
                    ))}
                  </SelectInput>
                </Field>
              )}
              <Field label="Channel">
                <SelectInput
                  value={form.channel}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, channel: e.target.value as Channel }))
                  }
                >
                  <option value="sms">SMS</option>
                  <option value="email">Email</option>
                </SelectInput>
              </Field>
              <Field
                label="Monthly free units"
                hint="SMS segments or email credits covered each month."
              >
                <TextInput
                  required
                  type="number"
                  min={0}
                  value={form.monthly_free_units}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      monthly_free_units: Number(e.target.value),
                    }))
                  }
                />
              </Field>
              <Field label="Daily limit" hint="Optional cap per day.">
                <TextInput
                  type="number"
                  min={0}
                  value={form.daily_limit_units ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      daily_limit_units: e.target.value === '' ? null : Number(e.target.value),
                    }))
                  }
                />
              </Field>
              <Field label="Budget cap (GHS)" hint="Optional platform spend cap.">
                <TextInput
                  inputMode="decimal"
                  value={form.budget_ghs ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      budget_ghs: e.target.value === '' ? null : e.target.value,
                    }))
                  }
                />
              </Field>
              <Field label="Starts at">
                <TextInput
                  type="date"
                  value={form.starts_at ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, starts_at: e.target.value || null }))
                  }
                />
              </Field>
              <Field label="Ends at">
                <TextInput
                  type="date"
                  value={form.ends_at ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, ends_at: e.target.value || null }))
                  }
                />
              </Field>
              <Field label="Alert thresholds" hint="Comma-separated fractions, e.g. 0.8, 0.95.">
                <TextInput
                  value={(form.alert_thresholds ?? []).join(', ')}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      alert_thresholds: e.target.value
                        .split(',')
                        .map((value) => Number(value.trim()))
                        .filter((value) => Number.isFinite(value) && value > 0),
                    }))
                  }
                />
              </Field>
            </div>

            <fieldset className="mt-4">
              <legend className="mb-2 text-sm font-medium">
                Applies to events
                <span className="ml-2 text-xs font-normal text-[var(--color-ink)]/55">
                  Leave all unchecked to cover every guardian event.
                </span>
              </legend>
              <div className="flex flex-wrap gap-3">
                {EVENT_TYPES.map((event) => (
                  <label key={event} className="flex items-center gap-2 text-sm capitalize">
                    <input
                      type="checkbox"
                      checked={(form.applies_to_events ?? []).includes(event)}
                      onChange={() => toggleEvent(event)}
                    />
                    {event.replace(/_/g, ' ')}
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="mt-4 flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active ?? true}
                onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
              />
              Active
            </label>

            <div className="mt-4 flex gap-2">
              <PrimaryButton type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? 'Saving…' : editingId ? 'Save changes' : 'Create'}
              </PrimaryButton>
              <GhostButton
                onClick={() => {
                  setShowForm(false)
                  setEditingId(null)
                }}
              >
                Discard
              </GhostButton>
            </div>
          </Panel>
        </form>
      )}

      <h3 className="mb-3 font-[family-name:var(--font-display)] text-lg font-semibold">
        Allowance policies
      </h3>
      <TableWrap>
        <Thead>
          <tr>
            <Th>Scope</Th>
            <Th>Channel</Th>
            <Th align="right">Monthly free</Th>
            <Th align="right">Daily limit</Th>
            <Th>Events</Th>
            <Th align="right">Budget</Th>
            <Th>Window</Th>
            <Th>Status</Th>
            {canWrite && <Th>Actions</Th>}
          </tr>
        </Thead>
        <tbody>
          <TableState
            colSpan={canWrite ? 9 : 8}
            isLoading={allowancesQuery.isLoading}
            isError={allowancesQuery.isError}
            error={allowancesQuery.error}
            isEmpty={allowances.length === 0}
            emptyMessage="No allowance policies. Guardian traffic classifies as paid by default."
          />
          {allowances.map((policy) => (
            <tr key={policy.id} className="border-b border-[var(--color-line)] last:border-0">
              <Td>
                <span className="font-medium capitalize">{policy.scope}</span>
                <span className="block text-xs text-[var(--color-ink)]/55">
                  {policy.school_name || (policy.scope === 'platform' ? 'All schools' : '—')}
                </span>
              </Td>
              <Td className="uppercase">{policy.channel}</Td>
              <Td align="right">{formatUnits(policy.monthly_free_units)}</Td>
              <Td align="right">{formatUnits(policy.daily_limit_units)}</Td>
              <Td>
                <span className="text-xs text-[var(--color-ink)]/70">
                  {policy.applies_to_events?.length
                    ? policy.applies_to_events.map((e) => e.replace(/_/g, ' ')).join(', ')
                    : 'All events'}
                </span>
              </Td>
              <Td align="right">{formatGhs(policy.budget_ghs)}</Td>
              <Td>
                <span className="text-xs">
                  {formatDate(policy.starts_at)} → {policy.ends_at ? formatDate(policy.ends_at) : 'open'}
                </span>
              </Td>
              <Td>
                {policy.is_active ? <Badge tone="accent">Active</Badge> : <Badge>Inactive</Badge>}
              </Td>
              {canWrite && (
                <Td>
                  <div className="flex gap-2">
                    <GhostButton onClick={() => startEdit(policy)}>Edit</GhostButton>
                    <GhostButton
                      disabled={toggleMutation.isPending}
                      onClick={() => toggleMutation.mutate(policy)}
                    >
                      {policy.is_active ? 'Deactivate' : 'Activate'}
                    </GhostButton>
                  </div>
                </Td>
              )}
            </tr>
          ))}
        </tbody>
      </TableWrap>

      <div className="mt-6">
        <h3 className="mb-3 font-[family-name:var(--font-display)] text-lg font-semibold">
          Free & sponsored by school
        </h3>
        <TableWrap>
          <Thead>
            <tr>
              <Th>School</Th>
              <Th align="right">Free SMS segments</Th>
              <Th align="right">Sponsored SMS segments</Th>
              <Th align="right">Free email credits</Th>
              <Th align="right">Sponsored email credits</Th>
              {canSeeMoney && <Th align="right">Platform expense</Th>}
            </tr>
          </Thead>
          <tbody>
            <TableState
              colSpan={canSeeMoney ? 6 : 5}
              isLoading={freeUsageQuery.isLoading}
              isError={freeUsageQuery.isError}
              error={freeUsageQuery.error}
              isEmpty={(usage?.by_school?.length ?? 0) === 0}
              emptyMessage="No free or sponsored traffic in this range."
            />
            {(usage?.by_school ?? []).map((row) => (
              <tr key={row.school} className="border-b border-[var(--color-line)] last:border-0">
                <Td>{row.school_name}</Td>
                <Td align="right">{formatUnits(row.free_sms_segments)}</Td>
                <Td align="right">{formatUnits(row.sponsored_sms_segments)}</Td>
                <Td align="right">{formatUnits(row.free_email_credits)}</Td>
                <Td align="right">{formatUnits(row.sponsored_email_credits)}</Td>
                {canSeeMoney && <Td align="right">{formatGhs(row.expense_ghs)}</Td>}
              </tr>
            ))}
          </tbody>
        </TableWrap>
      </div>

      <p className="mt-6 max-w-3xl text-xs text-[var(--color-ink)]/55">
        A promotional grant lands credits in the school wallet and is spent as ordinary paid
        traffic. A sponsored send moves no credits at all — the platform absorbs the provider
        cost. Mixing the two corrupts both the wallet story and the P&amp;L.
      </p>
    </div>
  )
}
