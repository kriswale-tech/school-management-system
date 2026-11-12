import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Badge,
  EstimatedTag,
  Field,
  GhostButton,
  PageHeader,
  Panel,
  PrimaryButton,
  QueryNotice,
  Stat,
  TableState,
  TableWrap,
  Td,
  Th,
  Thead,
  TextInput,
} from './components/ui'
import { errorMessage, formatDate, formatDateTime, formatUnitPrice } from './lib'
import { createEmailPricing, getEmailPricing, listEmailPricingHistory } from './services'
import { useMessagesAccess } from './permissions'
import type { EmailPricingConfigInput } from './types'

const EMPTY_FORM: EmailPricingConfigInput = {
  school_price_per_credit_ghs: '',
  estimated_provider_cost_per_email_ghs: '',
}

export default function EmailPricingPage() {
  const queryClient = useQueryClient()
  const { can } = useMessagesAccess()
  const canWrite = can('pricing.write')

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<EmailPricingConfigInput>(EMPTY_FORM)

  const activeQuery = useQuery({
    queryKey: ['platform-messages-email-pricing'],
    queryFn: getEmailPricing,
    retry: false,
  })

  const historyQuery = useQuery({
    queryKey: ['platform-messages-email-pricing-history'],
    queryFn: listEmailPricingHistory,
    retry: false,
  })

  const createMutation = useMutation({
    mutationFn: createEmailPricing,
    onSuccess: () => {
      toast.success('New email pricing version created')
      setShowForm(false)
      setForm(EMPTY_FORM)
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-email-pricing'] })
      void queryClient.invalidateQueries({
        queryKey: ['platform-messages-email-pricing-history'],
      })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const active = activeQuery.data
  const history = historyQuery.data ?? []

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    createMutation.mutate(form)
  }

  return (
    <div>
      <PageHeader
        title="Email pricing & configuration"
        description="Email unit economics are versioned the same way as SMS. SES is pay-per-send; per-email provider cost may still be estimated until AWS Cost Explorer is wired."
        actions={
          canWrite && (
            <PrimaryButton onClick={() => setShowForm((v) => !v)}>
              {showForm ? 'Cancel' : 'New version'}
            </PrimaryButton>
          )
        }
      />

      <Panel
        title="Active configuration"
        footnote="Billing unit locked by v4: 1 email credit = 1 provider-accepted recipient delivery attempt. Acceptance by SES is the billable event, not delivery confirmation."
      >
        <QueryNotice
          isLoading={activeQuery.isLoading}
          isError={activeQuery.isError}
          error={activeQuery.error}
        />
        {active && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Reference sell / credit"
              value={formatUnitPrice(active.school_price_per_credit_ghs)}
              hint="P&L reference only — never charged at send time"
            />
            <Stat
              label="Provider cost / email"
              value={
                <>
                  {formatUnitPrice(active.estimated_provider_cost_per_email_ghs)}
                  <EstimatedTag />
                </>
              }
              hint="Estimated SES send cost (plus optional monitoring)"
            />
            <Stat
              label="Billing unit"
              value={active.billing_unit || '1 accepted recipient = 1 credit'}
            />
            <Stat
              label="Effective from"
              value={formatDate(active.effective_from)}
              hint={active.changed_by_name ? `Set by ${active.changed_by_name}` : undefined}
            />
          </div>
        )}
      </Panel>

      {showForm && canWrite && (
        <form onSubmit={onSubmit} className="mt-4">
          <Panel
            title="Create new version"
            description="The current active configuration is closed out and a new one begins. Historical sends keep their own snapshots."
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Field
                label="Reference sell price per credit (GHS)"
                hint="Used to value consumed email credits in reports."
              >
                <TextInput
                  required
                  inputMode="decimal"
                  value={form.school_price_per_credit_ghs}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, school_price_per_credit_ghs: e.target.value }))
                  }
                />
              </Field>
              <Field
                label="Estimated provider cost per email (GHS)"
                hint="Always surfaced as estimated until live SES cost data is connected."
              >
                <TextInput
                  required
                  inputMode="decimal"
                  value={form.estimated_provider_cost_per_email_ghs}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      estimated_provider_cost_per_email_ghs: e.target.value,
                    }))
                  }
                />
              </Field>
              <Field label="Effective from" hint="Leave blank to activate immediately.">
                <TextInput
                  type="date"
                  value={form.effective_from ?? ''}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, effective_from: e.target.value }))
                  }
                />
              </Field>
            </div>
            <div className="mt-4 flex gap-2">
              <PrimaryButton type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Saving…' : 'Create version'}
              </PrimaryButton>
              <GhostButton onClick={() => setShowForm(false)}>Discard</GhostButton>
            </div>
          </Panel>
        </form>
      )}

      <div className="mt-4">
        <h3 className="mb-3 font-[family-name:var(--font-display)] text-lg font-semibold">
          Pricing history
        </h3>
        <TableWrap>
          <Thead>
            <tr>
              <Th align="right">Reference sell / credit</Th>
              <Th align="right">Estimated cost / email</Th>
              <Th>Billing unit</Th>
              <Th>Effective</Th>
              <Th>Changed by</Th>
              <Th>Status</Th>
            </tr>
          </Thead>
          <tbody>
            <TableState
              colSpan={6}
              isLoading={historyQuery.isLoading}
              isError={historyQuery.isError}
              error={historyQuery.error}
              isEmpty={history.length === 0}
              emptyMessage="No email pricing versions recorded yet."
            />
            {history.map((row) => (
              <tr key={row.id} className="border-b border-[var(--color-line)] last:border-0">
                <Td align="right">{formatUnitPrice(row.school_price_per_credit_ghs)}</Td>
                <Td align="right">
                  {formatUnitPrice(row.estimated_provider_cost_per_email_ghs)}
                </Td>
                <Td>{row.billing_unit || '1 accepted recipient'}</Td>
                <Td>
                  {formatDate(row.effective_from)}
                  {' → '}
                  {row.effective_to ? formatDate(row.effective_to) : 'now'}
                </Td>
                <Td>
                  <span className="text-[var(--color-ink)]/70">{row.changed_by_name || '—'}</span>
                  <span className="block text-xs text-[var(--color-ink)]/50">
                    {formatDateTime(row.created_at)}
                  </span>
                </Td>
                <Td>
                  {row.is_active ? <Badge tone="success">Active</Badge> : <Badge>Superseded</Badge>}
                </Td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
      </div>
    </div>
  )
}
