import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import ReconciliationPanel from './components/ReconciliationPanel'
import {
  activityTone,
  Badge,
  badgeToneFor,
  Field,
  GhostButton,
  LayerTile,
  Pagination,
  PageHeader,
  Panel,
  PrimaryButton,
  QueryNotice,
  SelectInput,
  Stat,
  SummaryStrip,
  TableState,
  TableWrap,
  Td,
  Th,
  Thead,
  TextInput,
} from './components/ui'
import {
  errorMessage,
  formatDate,
  formatDateTime,
  formatGhs,
  formatUnitPrice,
  formatUnits,
  titleCase,
  todayIso,
} from './lib'
import {
  createExpense,
  createPurchase,
  listArkeselSnapshots,
  listExpenses,
  listProviders,
  listPurchases,
  listSesUsage,
  syncArkeselBalance,
  syncSesUsage,
} from './services'
import { useMessagesAccess } from './permissions'
import type { ExpenseKind, ProviderExpenseInput, ProviderPurchaseInput } from './types'

const EMPTY_PURCHASE: ProviderPurchaseInput = {
  provider: 'arkesel',
  channel: 'sms',
  amount_ghs: '',
  credits_or_units: 0,
  provider_reference: '',
  purchased_at: todayIso(),
  payment_method: '',
  notes: '',
}

const EMPTY_EXPENSE: ProviderExpenseInput = {
  provider: 'ses',
  expense_kind: 'other',
  period_start: todayIso(),
  period_end: todayIso(),
  amount_ghs: '',
  units: null,
  notes: '',
}

export default function ProvidersPage() {
  const queryClient = useQueryClient()
  const { can } = useMessagesAccess()
  const canSync = can('providers.sync')
  const canSeeCash = can('providers.cash.view')
  const canWriteCash = can('providers.cash.write')

  const [purchaseForm, setPurchaseForm] = useState<ProviderPurchaseInput>(EMPTY_PURCHASE)
  const [expenseForm, setExpenseForm] = useState<ProviderExpenseInput>(EMPTY_EXPENSE)
  const [showPurchaseForm, setShowPurchaseForm] = useState(false)
  const [showExpenseForm, setShowExpenseForm] = useState(false)
  const [purchasePage, setPurchasePage] = useState(1)
  const [expensePage, setExpensePage] = useState(1)

  const providersQuery = useQuery({
    queryKey: ['platform-messages-providers'],
    queryFn: listProviders,
    retry: false,
  })

  const snapshotsQuery = useQuery({
    queryKey: ['platform-messages-arkesel-snapshots'],
    queryFn: () => listArkeselSnapshots(),
    retry: false,
  })

  const sesUsageQuery = useQuery({
    queryKey: ['platform-messages-ses-usage'],
    queryFn: () => listSesUsage(),
    retry: false,
  })

  const purchasesQuery = useQuery({
    queryKey: ['platform-messages-purchases', purchasePage],
    queryFn: () => listPurchases({ page: purchasePage }),
    enabled: canSeeCash,
    retry: false,
  })

  const expensesQuery = useQuery({
    queryKey: ['platform-messages-expenses', expensePage],
    queryFn: () => listExpenses({ page: expensePage }),
    enabled: canSeeCash,
    retry: false,
  })

  const syncArkeselMutation = useMutation({
    mutationFn: syncArkeselBalance,
    onSuccess: () => {
      toast.success('Arkesel balance synced')
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-arkesel-snapshots'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-providers'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const syncSesMutation = useMutation({
    mutationFn: syncSesUsage,
    onSuccess: (data) => {
      toast.success(data?.placeholder ? 'SES placeholder usage recorded' : 'SES usage synced')
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-ses-usage'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-providers'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const purchaseMutation = useMutation({
    mutationFn: createPurchase,
    onSuccess: () => {
      toast.success('Purchase recorded')
      setPurchaseForm(EMPTY_PURCHASE)
      setShowPurchaseForm(false)
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-purchases'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const expenseMutation = useMutation({
    mutationFn: createExpense,
    onSuccess: () => {
      toast.success('Expense recorded')
      setExpenseForm(EMPTY_EXPENSE)
      setShowExpenseForm(false)
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-expenses'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const arkeselAccount = providersQuery.data?.find((p) => p.provider === 'arkesel')
  const sesAccount = providersQuery.data?.find((p) => p.provider === 'ses')
  const latestSnapshot = snapshotsQuery.data?.results?.[0]
  const latestUsage = sesUsageQuery.data?.results?.[0]
  const purchases = purchasesQuery.data?.results ?? []
  const expenses = expensesQuery.data?.results ?? []

  const purchasedUnits = purchases.reduce((total, row) => total + (row.credits_or_units || 0), 0)

  function onPurchaseSubmit(event: FormEvent) {
    event.preventDefault()
    purchaseMutation.mutate(purchaseForm)
  }

  function onExpenseSubmit(event: FormEvent) {
    event.preventDefault()
    expenseMutation.mutate(expenseForm)
  }

  return (
    <div>
      <PageHeader
        title="Provider credits & accounts"
        description="Arkesel runs a prepaid wallet. Amazon SES is pay-per-send (no prepaid balance) — usage syncs as a placeholder until AWS credentials are configured."
      />

      <QueryNotice
        isLoading={providersQuery.isLoading}
        isError={providersQuery.isError}
        error={providersQuery.error}
      />

      {/* ---------------------------------------------------------- */}
      {/* Arkesel                                                     */}
      {/* ---------------------------------------------------------- */}
      <Panel
        title="Arkesel — prepaid SMS wallet"
        description={
          arkeselAccount ? (
            <span className="inline-flex flex-wrap items-center gap-2">
              {arkeselAccount.display_name}
              <Badge tone={badgeToneFor(arkeselAccount.api_status || 'unknown')}>
                {(arkeselAccount.api_status || 'unknown').replaceAll('_', ' ')}
              </Badge>
            </span>
          ) : (
            'Prepaid SMS provider.'
          )
        }
        actions={
          canSync && (
            <PrimaryButton
              disabled={syncArkeselMutation.isPending}
              onClick={() => syncArkeselMutation.mutate()}
            >
              {syncArkeselMutation.isPending ? 'Syncing…' : 'Sync balance'}
            </PrimaryButton>
          )
        }
        footnote="Wallet balance and purchase totals are different layers and are never added together. A wallet top-up is cash out, not the cost of messages already sent."
      >
        <SummaryStrip>
          <LayerTile
            layer="provider"
            label="Current SMS balance"
            value={formatUnits(latestSnapshot?.sms_balance)}
            hint={`Captured ${formatDateTime(latestSnapshot?.captured_at)}`}
          />
          <LayerTile
            layer="provider"
            label="Main balance (provider text)"
            value={latestSnapshot?.main_balance_text || '—'}
            hint={`Source: ${latestSnapshot?.source ?? '—'}`}
          />
          <LayerTile
            layer="cash"
            label="Units purchased (listed)"
            value={formatUnits(purchasedUnits)}
            hint="Sum of recorded wallet top-ups on this page"
          />
          <LayerTile
            layer="provider"
            label="Last sync"
            value={formatDateTime(arkeselAccount?.last_synced_at ?? latestSnapshot?.captured_at)}
            hint={
              <Badge tone={badgeToneFor(arkeselAccount?.api_status || 'unknown')}>
                {(arkeselAccount?.api_status || 'unknown').replaceAll('_', ' ')}
              </Badge>
            }
          />
        </SummaryStrip>

        <h4 className="mt-2 mb-2 text-sm font-semibold">Balance snapshots</h4>
        <TableWrap>
          <Thead>
            <tr>
              <Th>Captured</Th>
              <Th align="right">SMS balance</Th>
              <Th>Main balance</Th>
              <Th>Source</Th>
            </tr>
          </Thead>
          <tbody>
            <TableState
              colSpan={4}
              isLoading={snapshotsQuery.isLoading}
              isError={snapshotsQuery.isError}
              error={snapshotsQuery.error}
              isEmpty={(snapshotsQuery.data?.results?.length ?? 0) === 0}
              emptyMessage="No balance snapshots captured yet."
            />
            {(snapshotsQuery.data?.results ?? []).map((snapshot) => (
              <tr key={snapshot.id} className="border-b border-[var(--color-line)] last:border-0">
                <Td>{formatDateTime(snapshot.captured_at)}</Td>
                <Td align="right">{formatUnits(snapshot.sms_balance)}</Td>
                <Td>{snapshot.main_balance_text || '—'}</Td>
                <Td>
                  <Badge tone={activityTone(snapshot.source)}>{snapshot.source}</Badge>
                </Td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
      </Panel>

      {canSeeCash && (
        <div className="mt-4">
          <Panel
            title="Wallet purchases"
            description="Arkesel has no purchase API, so wallet top-ups are recorded manually by Finance."
            actions={
              canWriteCash && (
                <PrimaryButton onClick={() => setShowPurchaseForm((v) => !v)}>
                  {showPurchaseForm ? 'Cancel' : 'Record purchase'}
                </PrimaryButton>
              )
            }
          >
            {showPurchaseForm && canWriteCash && (
              <form
                onSubmit={onPurchaseSubmit}
                className="mb-5 grid gap-3 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] p-4 md:grid-cols-3"
              >
                <Field label="Provider">
                  <SelectInput
                    value={purchaseForm.provider}
                    onChange={(e) =>
                      setPurchaseForm((prev) => ({
                        ...prev,
                        provider: e.target.value as ProviderPurchaseInput['provider'],
                      }))
                    }
                  >
                    <option value="arkesel">Arkesel</option>
                  </SelectInput>
                </Field>
                <Field label="Channel">
                  <SelectInput
                    value={purchaseForm.channel}
                    onChange={(e) =>
                      setPurchaseForm((prev) => ({
                        ...prev,
                        channel: e.target.value as ProviderPurchaseInput['channel'],
                      }))
                    }
                  >
                    <option value="sms">SMS</option>
                    <option value="email">Email</option>
                  </SelectInput>
                </Field>
                <Field label="Purchased on">
                  <TextInput
                    type="date"
                    required
                    value={purchaseForm.purchased_at ?? ''}
                    onChange={(e) =>
                      setPurchaseForm((prev) => ({ ...prev, purchased_at: e.target.value }))
                    }
                  />
                </Field>
                <Field label="Amount paid (GHS)">
                  <TextInput
                    required
                    inputMode="decimal"
                    value={purchaseForm.amount_ghs}
                    onChange={(e) =>
                      setPurchaseForm((prev) => ({ ...prev, amount_ghs: e.target.value }))
                    }
                  />
                </Field>
                <Field label="Units purchased" hint="Effective cost per unit is derived and stored.">
                  <TextInput
                    required
                    type="number"
                    min={1}
                    value={purchaseForm.credits_or_units || ''}
                    onChange={(e) =>
                      setPurchaseForm((prev) => ({
                        ...prev,
                        credits_or_units: Number(e.target.value),
                      }))
                    }
                  />
                </Field>
                <Field label="Payment method">
                  <TextInput
                    value={purchaseForm.payment_method ?? ''}
                    placeholder="Bank transfer, MoMo…"
                    onChange={(e) =>
                      setPurchaseForm((prev) => ({ ...prev, payment_method: e.target.value }))
                    }
                  />
                </Field>
                <Field label="Provider reference">
                  <TextInput
                    value={purchaseForm.provider_reference ?? ''}
                    onChange={(e) =>
                      setPurchaseForm((prev) => ({
                        ...prev,
                        provider_reference: e.target.value,
                      }))
                    }
                  />
                </Field>
                <Field label="Notes">
                  <TextInput
                    value={purchaseForm.notes ?? ''}
                    onChange={(e) =>
                      setPurchaseForm((prev) => ({ ...prev, notes: e.target.value }))
                    }
                  />
                </Field>
                <div className="flex items-end gap-2">
                  <PrimaryButton type="submit" disabled={purchaseMutation.isPending}>
                    {purchaseMutation.isPending ? 'Saving…' : 'Save purchase'}
                  </PrimaryButton>
                  <GhostButton onClick={() => setShowPurchaseForm(false)}>Discard</GhostButton>
                </div>
              </form>
            )}

            <TableWrap>
              <Thead>
                <tr>
                  <Th>Purchased</Th>
                  <Th>Provider</Th>
                  <Th align="right">Amount</Th>
                  <Th align="right">Units</Th>
                  <Th align="right">Effective cost / unit</Th>
                  <Th>Reference</Th>
                  <Th>Recorded by</Th>
                </tr>
              </Thead>
              <tbody>
                <TableState
                  colSpan={7}
                  isLoading={purchasesQuery.isLoading}
                  isError={purchasesQuery.isError}
                  error={purchasesQuery.error}
                  isEmpty={purchases.length === 0}
                  emptyMessage="No wallet purchases recorded yet."
                />
                {purchases.map((purchase) => (
                  <tr
                    key={purchase.id}
                    className="border-b border-[var(--color-line)] last:border-0"
                  >
                    <Td>{formatDate(purchase.purchased_at)}</Td>
                    <Td>
                      <span className="capitalize">{purchase.provider}</span>
                      <span className="block text-xs text-[var(--color-ink)]/50 uppercase">
                        {purchase.channel}
                      </span>
                    </Td>
                    <Td align="right">{formatGhs(purchase.amount_ghs)}</Td>
                    <Td align="right">{formatUnits(purchase.credits_or_units)}</Td>
                    <Td align="right">{formatUnitPrice(purchase.effective_cost_per_unit)}</Td>
                    <Td>
                      <span className="font-mono text-xs">{purchase.provider_reference || '—'}</span>
                      {purchase.notes && (
                        <span className="block text-xs text-[var(--color-ink)]/55">
                          {purchase.notes}
                        </span>
                      )}
                    </Td>
                    <Td>{purchase.recorded_by_name || '—'}</Td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
            <Pagination
              count={purchasesQuery.data?.count ?? 0}
              page={purchasePage}
              onPage={setPurchasePage}
            />
          </Panel>
        </div>
      )}

      {/* ---------------------------------------------------------- */}
      {/* Amazon SES                                                  */}
      {/* ---------------------------------------------------------- */}
      <div className="mt-4">
        <Panel
          title="Amazon SES — pay-per-send"
          description={
            sesAccount ? (
              <span className="inline-flex flex-wrap items-center gap-2">
                {sesAccount.display_name}
                <Badge tone={badgeToneFor(sesAccount.api_status || 'unknown')}>
                  {(sesAccount.api_status || 'unknown').replaceAll('_', ' ')}
                </Badge>
              </span>
            ) : (
              'Transactional email via Amazon SES.'
            )
          }
          actions={
            canSync && (
              <PrimaryButton
                disabled={syncSesMutation.isPending}
                onClick={() => syncSesMutation.mutate()}
              >
                {syncSesMutation.isPending ? 'Syncing…' : 'Sync usage'}
              </PrimaryButton>
            )
          }
          footnote="SES has no prepaid wallet. Until AWS credentials are set, sync writes a placeholder snapshot so flows can be tested. Record AWS usage/monitoring costs as provider expenses."
        >
          <SummaryStrip>
            <LayerTile
              layer="provider"
              label="Monthly volume used"
              value={
                latestUsage?.monthly_used == null
                  ? '—'
                  : `${formatUnits(latestUsage.monthly_used)} / ${
                      latestUsage.monthly_limit == null
                        ? '∞'
                        : formatUnits(latestUsage.monthly_limit)
                    }`
              }
              hint="Placeholder until CloudWatch/SES metrics are wired"
            />
            <LayerTile
              layer="provider"
              label="Daily volume used"
              value={
                latestUsage?.daily_used == null
                  ? '—'
                  : `${formatUnits(latestUsage.daily_used)} / ${
                      latestUsage.daily_limit == null ? '∞' : formatUnits(latestUsage.daily_limit)
                    }`
              }
            />
            <LayerTile
              layer="provider"
              label="Sent / received"
              value={`${formatUnits(latestUsage?.sent_count)} / ${formatUnits(
                latestUsage?.received_count,
              )}`}
            />
            <LayerTile
              layer="provider"
              label="Last sync"
              value={formatDateTime(sesAccount?.last_synced_at ?? latestUsage?.captured_at)}
              hint={
                <Badge tone={badgeToneFor(sesAccount?.api_status || 'unknown')}>
                  {(sesAccount?.api_status || 'unknown').replaceAll('_', ' ')}
                </Badge>
              }
            />
          </SummaryStrip>

          <h4 className="mt-2 mb-2 text-sm font-semibold">Usage snapshots</h4>
          <TableWrap>
            <Thead>
              <tr>
                <Th>Captured</Th>
                <Th align="right">Monthly used</Th>
                <Th align="right">Monthly limit</Th>
                <Th align="right">Daily used</Th>
                <Th>Source</Th>
              </tr>
            </Thead>
            <tbody>
              <TableState
                colSpan={5}
                isLoading={sesUsageQuery.isLoading}
                isError={sesUsageQuery.isError}
                error={sesUsageQuery.error}
                isEmpty={(sesUsageQuery.data?.results?.length ?? 0) === 0}
                emptyMessage="No usage snapshots captured yet."
              />
              {(sesUsageQuery.data?.results ?? []).map((snapshot) => (
                <tr
                  key={snapshot.id}
                  className="border-b border-[var(--color-line)] last:border-0"
                >
                  <Td>{formatDateTime(snapshot.captured_at)}</Td>
                  <Td align="right">{formatUnits(snapshot.monthly_used)}</Td>
                  <Td align="right">{formatUnits(snapshot.monthly_limit)}</Td>
                  <Td align="right">{formatUnits(snapshot.daily_used)}</Td>
                  <Td>
                    <Badge tone={activityTone(snapshot.source)}>{snapshot.source}</Badge>
                  </Td>
                </tr>
              ))}
            </tbody>
          </TableWrap>
        </Panel>
      </div>

      {canSeeCash && (
        <div className="mt-4">
          <Panel
            title="Provider expenses"
            description="SES usage, AWS monitoring, and other provider charges. Invoice amounts are recorded manually until Cost Explorer is wired."
            actions={
              canWriteCash && (
                <PrimaryButton onClick={() => setShowExpenseForm((v) => !v)}>
                  {showExpenseForm ? 'Cancel' : 'Record expense'}
                </PrimaryButton>
              )
            }
          >
            {showExpenseForm && canWriteCash && (
              <form
                onSubmit={onExpenseSubmit}
                className="mb-5 grid gap-3 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] p-4 md:grid-cols-3"
              >
                <Field label="Provider">
                  <SelectInput
                    value={expenseForm.provider}
                    onChange={(e) =>
                      setExpenseForm((prev) => ({
                        ...prev,
                        provider: e.target.value as ProviderExpenseInput['provider'],
                      }))
                    }
                  >
                    <option value="ses">Amazon SES</option>
                    <option value="arkesel">Arkesel</option>
                    <option value="resend">Resend (legacy)</option>
                  </SelectInput>
                </Field>
                <Field label="Expense kind">
                  <SelectInput
                    value={expenseForm.expense_kind}
                    onChange={(e) =>
                      setExpenseForm((prev) => ({
                        ...prev,
                        expense_kind: e.target.value as ExpenseKind,
                      }))
                    }
                  >
                    <option value="other">Usage / other</option>
                    <option value="subscription">Subscription</option>
                    <option value="overage">Overage</option>
                  </SelectInput>
                </Field>
                <Field label="Amount (GHS)">
                  <TextInput
                    required
                    inputMode="decimal"
                    value={expenseForm.amount_ghs}
                    onChange={(e) =>
                      setExpenseForm((prev) => ({ ...prev, amount_ghs: e.target.value }))
                    }
                  />
                </Field>
                <Field label="Period start">
                  <TextInput
                    required
                    type="date"
                    value={expenseForm.period_start}
                    onChange={(e) =>
                      setExpenseForm((prev) => ({ ...prev, period_start: e.target.value }))
                    }
                  />
                </Field>
                <Field label="Period end">
                  <TextInput
                    required
                    type="date"
                    value={expenseForm.period_end}
                    onChange={(e) =>
                      setExpenseForm((prev) => ({ ...prev, period_end: e.target.value }))
                    }
                  />
                </Field>
                <Field label="Units" hint="Optional — overage volume, if known.">
                  <TextInput
                    type="number"
                    min={0}
                    value={expenseForm.units ?? ''}
                    onChange={(e) =>
                      setExpenseForm((prev) => ({
                        ...prev,
                        units: e.target.value === '' ? null : Number(e.target.value),
                      }))
                    }
                  />
                </Field>
                <Field label="Notes">
                  <TextInput
                    value={expenseForm.notes ?? ''}
                    onChange={(e) =>
                      setExpenseForm((prev) => ({ ...prev, notes: e.target.value }))
                    }
                  />
                </Field>
                <div className="flex items-end gap-2">
                  <PrimaryButton type="submit" disabled={expenseMutation.isPending}>
                    {expenseMutation.isPending ? 'Saving…' : 'Save expense'}
                  </PrimaryButton>
                  <GhostButton onClick={() => setShowExpenseForm(false)}>Discard</GhostButton>
                </div>
              </form>
            )}

            <TableWrap>
              <Thead>
                <tr>
                  <Th>Period</Th>
                  <Th>Provider</Th>
                  <Th>Kind</Th>
                  <Th align="right">Amount</Th>
                  <Th align="right">Units</Th>
                  <Th>Recorded by</Th>
                </tr>
              </Thead>
              <tbody>
                <TableState
                  colSpan={6}
                  isLoading={expensesQuery.isLoading}
                  isError={expensesQuery.isError}
                  error={expensesQuery.error}
                  isEmpty={expenses.length === 0}
                  emptyMessage="No provider expenses recorded yet."
                />
                {expenses.map((expense) => (
                  <tr
                    key={expense.id}
                    className="border-b border-[var(--color-line)] last:border-0"
                  >
                    <Td>
                      {formatDate(expense.period_start)} → {formatDate(expense.period_end)}
                    </Td>
                    <Td className="capitalize">{expense.provider}</Td>
                    <Td>
                      <Badge tone={activityTone(expense.expense_kind)}>
                        {titleCase(expense.expense_kind)}
                      </Badge>
                    </Td>
                    <Td align="right">{formatGhs(expense.amount_ghs)}</Td>
                    <Td align="right">{formatUnits(expense.units)}</Td>
                    <Td>
                      <span>{expense.recorded_by_name || '—'}</span>
                      <span className="mt-1 block">
                        <Badge tone={activityTone(expense.source)}>{titleCase(expense.source)}</Badge>
                      </span>
                      {expense.notes && (
                        <span className="block text-xs text-[var(--color-ink)]/55">
                          {expense.notes}
                        </span>
                      )}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
            <Pagination
              count={expensesQuery.data?.count ?? 0}
              page={expensePage}
              onPage={setExpensePage}
            />
          </Panel>
        </div>
      )}

      <div className="mt-4">
        <ReconciliationPanel />
      </div>

      {!canSeeCash && (
        <p className="mt-4 text-sm text-[var(--color-ink)]/55">
          Provider purchases and expenses are restricted to Finance, Operations, and Super Admin.
        </p>
      )}

      {providersQuery.data && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {providersQuery.data.map((account) => (
            <div
              key={account.id}
              className="rounded-xl border border-[var(--color-line)] bg-white p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium capitalize">{account.provider}</span>
                <Badge tone={badgeToneFor(account.api_status || 'unknown')}>
                  {(account.api_status || 'unknown').replaceAll('_', ' ')}
                </Badge>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-3">
                <Stat label="Channel" value={account.channel.toUpperCase()} />
                <Stat label="Last synced" value={formatDateTime(account.last_synced_at)} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
