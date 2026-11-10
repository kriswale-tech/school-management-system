import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Badge,
  Field,
  GhostButton,
  PageHeader,
  Panel,
  PrimaryButton,
  QueryNotice,
  SelectInput,
  Stat,
  TableState,
  TableWrap,
  Td,
  Th,
  Thead,
  TextArea,
  TextInput,
} from './components/ui'
import { errorMessage, formatDate, formatDateTime, formatUnitPrice, formatUnits } from './lib'
import { calculateSms, createSmsEncoding, listSmsEncodingHistory, listSmsEncodings } from './services'
import { useMessagesAccess } from './permissions'
import type { SmsEncoding, SmsEncodingConfig, SmsEncodingConfigInput } from './types'

const ENCODING_LABEL: Record<SmsEncoding, string> = {
  gsm7: 'GSM-7',
  ucs2: 'UCS-2 (Unicode)',
}

const EMPTY_FORM: SmsEncodingConfigInput = {
  encoding: 'gsm7',
  provider_cost_per_segment_ghs: '',
  school_price_per_segment_ghs: '',
  single_segment_limit: 160,
  multipart_segment_limit: 153,
}

function ActiveConfigCard({
  encoding,
  config,
}: {
  encoding: SmsEncoding
  config?: SmsEncodingConfig
}) {
  return (
    <div className="rounded-xl border border-[var(--color-line)] bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <h4 className="font-[family-name:var(--font-display)] text-base font-semibold">
          {ENCODING_LABEL[encoding]}
        </h4>
        {config ? <Badge tone="accent">Active</Badge> : <Badge tone="warn">Not configured</Badge>}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Stat
          label="Provider cost / segment"
          value={formatUnitPrice(config?.provider_cost_per_segment_ghs)}
        />
        <Stat
          label="Reference sell / segment"
          value={formatUnitPrice(config?.school_price_per_segment_ghs)}
          hint="Economics only — never charged at send time"
        />
        <Stat label="Single-segment limit" value={formatUnits(config?.single_segment_limit)} />
        <Stat label="Multipart limit" value={formatUnits(config?.multipart_segment_limit)} />
        <Stat label="Effective from" value={formatDate(config?.effective_from)} />
        <Stat label="Changed by" value={config?.changed_by_name || '—'} />
      </div>
    </div>
  )
}

export default function SmsPricingPage() {
  const queryClient = useQueryClient()
  const { can } = useMessagesAccess()
  const canWrite = can('pricing.write')

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<SmsEncodingConfigInput>(EMPTY_FORM)
  const [body, setBody] = useState('')
  const [debouncedBody, setDebouncedBody] = useState('')

  const activeQuery = useQuery({
    queryKey: ['platform-messages-sms-encodings'],
    queryFn: listSmsEncodings,
    retry: false,
  })

  const historyQuery = useQuery({
    queryKey: ['platform-messages-sms-encodings-history'],
    queryFn: () => listSmsEncodingHistory(),
    retry: false,
  })

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedBody(body), 350)
    return () => window.clearTimeout(timer)
  }, [body])

  const calculatorQuery = useQuery({
    queryKey: ['platform-messages-sms-calculator', debouncedBody],
    queryFn: () => calculateSms({ body: debouncedBody }),
    enabled: debouncedBody.length > 0,
    retry: false,
  })

  const createMutation = useMutation({
    mutationFn: createSmsEncoding,
    onSuccess: () => {
      toast.success('New pricing version created')
      setShowForm(false)
      setForm(EMPTY_FORM)
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-sms-encodings'] })
      void queryClient.invalidateQueries({
        queryKey: ['platform-messages-sms-encodings-history'],
      })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const configs = activeQuery.data ?? []
  const activeGsm7 = configs.find((c) => c.encoding === 'gsm7' && c.is_active)
  const activeUcs2 = configs.find((c) => c.encoding === 'ucs2' && c.is_active)
  const history = historyQuery.data ?? []
  const calc = calculatorQuery.data

  function onEncodingChange(encoding: SmsEncoding) {
    setForm((prev) => ({
      ...prev,
      encoding,
      single_segment_limit: encoding === 'gsm7' ? 160 : 70,
      multipart_segment_limit: encoding === 'gsm7' ? 153 : 67,
    }))
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    createMutation.mutate(form)
  }

  return (
    <div>
      <PageHeader
        title="SMS pricing & configuration"
        description="Segment limits and unit economics are versioned. Editing never rewrites history — it creates a new active version and closes the previous one."
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
        description="One active row per encoding. Historical sends keep the limits and costs they were metered with."
        footnote="Reference sell price values consumed units for P&L. Schools are billed in credits via add-on SKUs and top-up packages, never in GHS at send time."
      >
        <QueryNotice
          isLoading={activeQuery.isLoading}
          isError={activeQuery.isError}
          error={activeQuery.error}
        />
        {!activeQuery.isLoading && !activeQuery.isError && (
          <div className="grid gap-3 md:grid-cols-2">
            <ActiveConfigCard encoding="gsm7" config={activeGsm7} />
            <ActiveConfigCard encoding="ucs2" config={activeUcs2} />
          </div>
        )}
      </Panel>

      {showForm && canWrite && (
        <form onSubmit={onSubmit} className="mt-4">
          <Panel
            title="Create new version"
            description="Submitting deactivates the current active row for this encoding and starts a new one."
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Encoding">
                <SelectInput
                  value={form.encoding}
                  onChange={(e) => onEncodingChange(e.target.value as SmsEncoding)}
                >
                  <option value="gsm7">GSM-7</option>
                  <option value="ucs2">UCS-2 (Unicode)</option>
                </SelectInput>
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
              <Field label="Provider cost per segment (GHS)" hint="What Arkesel charges us.">
                <TextInput
                  required
                  inputMode="decimal"
                  value={form.provider_cost_per_segment_ghs}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      provider_cost_per_segment_ghs: e.target.value,
                    }))
                  }
                />
              </Field>
              <Field
                label="Reference sell price per segment (GHS)"
                hint="P&L reference only — not charged at send time."
              >
                <TextInput
                  required
                  inputMode="decimal"
                  value={form.school_price_per_segment_ghs}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      school_price_per_segment_ghs: e.target.value,
                    }))
                  }
                />
              </Field>
              <Field label="Single-segment limit" hint="Default 160 GSM-7 / 70 UCS-2.">
                <TextInput
                  required
                  type="number"
                  min={1}
                  value={form.single_segment_limit}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      single_segment_limit: Number(e.target.value),
                    }))
                  }
                />
              </Field>
              <Field label="Multipart segment limit" hint="Default 153 GSM-7 / 67 UCS-2.">
                <TextInput
                  required
                  type="number"
                  min={1}
                  value={form.multipart_segment_limit}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      multipart_segment_limit: Number(e.target.value),
                    }))
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
        <Panel
          title="Live segment calculator"
          description="Runs the production metering path, so the result is exactly what a send of this body would debit per recipient."
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Message body"
              hint="Paste a rendered body — templates must be substituted first."
            >
              <TextArea
                rows={7}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Fees due — GH₵500 for Kofi Mensah."
              />
            </Field>
            <div className="rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] p-4">
              {debouncedBody.length === 0 ? (
                <p className="text-sm text-[var(--color-ink)]/60">
                  Type a message to see encoding, length, segments, and credits.
                </p>
              ) : (
                <>
                  <QueryNotice
                    isLoading={calculatorQuery.isLoading}
                    isError={calculatorQuery.isError}
                    error={calculatorQuery.error}
                  />
                  {calc && (
                    <div className="grid grid-cols-2 gap-4">
                      <Stat label="Encoding" value={calc.encoding} />
                      <Stat
                        label={calc.encoding === 'gsm7' ? 'Septets' : 'Characters'}
                        value={formatUnits(calc.characters)}
                      />
                      <Stat label="Segments" value={formatUnits(calc.segments)} />
                      <Stat
                        label="Credits per recipient"
                        value={formatUnits(calc.credits_per_recipient)}
                      />
                      <Stat
                        label="Single-segment limit used"
                        value={formatUnits(calc.limits_used?.single_segment_limit)}
                      />
                      <Stat
                        label="Multipart limit used"
                        value={formatUnits(calc.limits_used?.multipart_segment_limit)}
                      />
                    </div>
                  )}
                  {calc?.limits_used?.effective_from && (
                    <p className="mt-3 border-t border-[var(--color-line)] pt-3 text-xs text-[var(--color-ink)]/55">
                      Limits from the config effective{' '}
                      {formatDate(calc.limits_used.effective_from)}.
                    </p>
                  )}
                </>
              )}
            </div>
          </div>
        </Panel>
      </div>

      <div className="mt-4">
        <h3 className="mb-3 font-[family-name:var(--font-display)] text-lg font-semibold">
          Pricing history
        </h3>
        <TableWrap>
          <Thead>
            <tr>
              <Th>Encoding</Th>
              <Th align="right">Provider cost</Th>
              <Th align="right">Reference sell</Th>
              <Th align="right">Single</Th>
              <Th align="right">Multipart</Th>
              <Th>Effective</Th>
              <Th>Changed by</Th>
              <Th>Status</Th>
            </tr>
          </Thead>
          <tbody>
            <TableState
              colSpan={8}
              isLoading={historyQuery.isLoading}
              isError={historyQuery.isError}
              error={historyQuery.error}
              isEmpty={history.length === 0}
              emptyMessage="No pricing versions recorded yet."
            />
            {history.map((row) => (
              <tr key={row.id} className="border-b border-[var(--color-line)] last:border-0">
                <Td>{ENCODING_LABEL[row.encoding] ?? row.encoding}</Td>
                <Td align="right">{formatUnitPrice(row.provider_cost_per_segment_ghs)}</Td>
                <Td align="right">{formatUnitPrice(row.school_price_per_segment_ghs)}</Td>
                <Td align="right">{formatUnits(row.single_segment_limit)}</Td>
                <Td align="right">{formatUnits(row.multipart_segment_limit)}</Td>
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
                  {row.is_active ? (
                    <Badge tone="accent">Active</Badge>
                  ) : (
                    <Badge>Superseded</Badge>
                  )}
                </Td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
      </div>
    </div>
  )
}
