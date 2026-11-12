import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { FilterBar, rangeLabel, useMessagesFilters } from './components/filters'
import {
  activityTone,
  Badge,
  GhostButton,
  Pagination,
  PageHeader,
  Panel,
  SelectInput,
  Stat,
  TableState,
  TableWrap,
  Td,
  Th,
  Thead,
} from './components/ui'
import { errorMessage, formatDateTime, formatGhs, formatUnits, titleCase } from './lib'
import { downloadExport, listTransactions } from './services'
import { useMessagesAccess } from './permissions'
import type { MessagingTransaction, Provider, TransactionType } from './types'

const TYPE_OPTIONS: Array<{ value: TransactionType | ''; label: string }> = [
  { value: '', label: 'All transaction types' },
  { value: 'provider_purchase', label: 'Provider purchase' },
  { value: 'provider_expense', label: 'Provider expense' },
  { value: 'school_topup', label: 'School top-up' },
  { value: 'addon_allocation', label: 'Add-on allocation' },
  { value: 'sms_deduction', label: 'SMS deduction' },
  { value: 'email_deduction', label: 'Email deduction' },
  { value: 'free_message', label: 'Free message' },
  { value: 'sponsored_message', label: 'Sponsored message' },
  { value: 'reversal', label: 'Reversal / refund' },
  { value: 'promo_grant', label: 'Promotional allocation' },
  { value: 'manual_adjust', label: 'Manual adjustment' },
  { value: 'pricing_change', label: 'Pricing change' },
  { value: 'reconciliation', label: 'Reconciliation' },
]

/** Credit movements are units; provider and top-up rows are cash. Never mixed. */
function amountCell(row: MessagingTransaction) {
  if (row.amount_ghs != null && row.amount_ghs !== '') {
    return (
      <>
        <span>{formatGhs(row.amount_ghs)}</span>
        <span className="block text-xs text-[var(--color-ink)]/50">cash</span>
      </>
    )
  }
  if (row.units != null) {
    return (
      <>
        <span className={row.units < 0 ? 'text-red-700' : ''}>
          {row.units > 0 ? '+' : ''}
          {formatUnits(row.units)}
        </span>
        <span className="block text-xs text-[var(--color-ink)]/50">units</span>
      </>
    )
  }
  return '—'
}

export default function TransactionsPage() {
  const { filters, setFilter, params } = useMessagesFilters()
  const { can } = useMessagesAccess()
  const canExport = can('exports')

  const [type, setType] = useState<TransactionType | ''>('')
  const [provider, setProvider] = useState<Provider | ''>('')
  const [selected, setSelected] = useState<MessagingTransaction | null>(null)

  const transactionsQuery = useQuery({
    queryKey: ['platform-messages-transactions', params, type, provider, filters.page],
    queryFn: () =>
      listTransactions({ ...params, type: type || undefined, provider: provider || undefined, page: filters.page }),
    retry: false,
  })

  const rows = transactionsQuery.data?.results ?? []

  async function onExport() {
    try {
      await downloadExport({ ...params, type: 'credit_ledger', format: 'csv' })
      toast.success('Export started')
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  return (
    <div>
      <PageHeader
        title="Transactions & purchase history"
        description={`Unified feed for ${rangeLabel(
          filters,
        )} covering provider purchases and expenses, school top-ups, deductions, free and sponsored sends, reversals, adjustments, and pricing changes.`}
        actions={canExport && <GhostButton onClick={onExport}>Export CSV</GhostButton>}
      />

      <FilterBar
        filters={filters}
        setFilter={setFilter}
        show={{ channel: true, classification: true, school: true }}
      />

      <div className="mb-5 flex flex-wrap gap-2">
        <SelectInput
          value={type}
          onChange={(e) => {
            setType(e.target.value as TransactionType | '')
            setFilter({ page: 1 })
          }}
          className="w-auto bg-white"
          aria-label="Transaction type"
        >
          {TYPE_OPTIONS.map((option) => (
            <option key={option.value || 'all'} value={option.value}>
              {option.label}
            </option>
          ))}
        </SelectInput>
        <SelectInput
          value={provider}
          onChange={(e) => {
            setProvider(e.target.value as Provider | '')
            setFilter({ page: 1 })
          }}
          className="w-auto bg-white"
          aria-label="Provider"
        >
          <option value="">All providers</option>
          <option value="arkesel">Arkesel</option>
          <option value="ses">Amazon SES</option>
          <option value="resend">Resend (legacy)</option>
        </SelectInput>
      </div>

      <TableWrap>
        <Thead>
          <tr>
            <Th>Date</Th>
            <Th>Type</Th>
            <Th align="right">Amount / quantity</Th>
            <Th>School</Th>
            <Th>Provider</Th>
            <Th>Reference</Th>
            <Th>Administrator</Th>
            <Th>Detail</Th>
          </tr>
        </Thead>
        <tbody>
          <TableState
            colSpan={8}
            isLoading={transactionsQuery.isLoading}
            isError={transactionsQuery.isError}
            error={transactionsQuery.error}
            isEmpty={rows.length === 0}
            emptyMessage="No transactions match these filters."
          />
          {rows.map((row) => (
            <tr key={row.id} className="border-b border-[var(--color-line)] last:border-0">
              <Td>{formatDateTime(row.occurred_at)}</Td>
              <Td>
                <Badge tone={activityTone(row.transaction_type)}>
                  {titleCase(row.transaction_type)}
                </Badge>
                {row.channel && (
                  <span className="mt-1 block text-xs text-[var(--color-ink)]/50 uppercase">
                    {row.channel}
                  </span>
                )}
              </Td>
              <Td align="right">{amountCell(row)}</Td>
              <Td>
                {row.school && row.school_name ? (
                  <Link
                    to={`/messages/schools/${row.school}`}
                    className="text-[var(--color-accent)] hover:underline"
                  >
                    {row.school_name}
                  </Link>
                ) : (
                  <span className="text-[var(--color-ink)]/50">Platform</span>
                )}
              </Td>
              <Td className="capitalize">{row.provider || '—'}</Td>
              <Td>
                <span className="font-mono text-xs">{row.reference || '—'}</span>
              </Td>
              <Td>{row.actor_name || '—'}</Td>
              <Td>
                <GhostButton onClick={() => setSelected(row)}>View</GhostButton>
              </Td>
            </tr>
          ))}
        </tbody>
      </TableWrap>

      <Pagination
        count={transactionsQuery.data?.count ?? 0}
        page={filters.page}
        onPage={(page) => setFilter({ page })}
      />

      {selected && (
        <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/30 p-4">
          <div className="max-h-full w-full max-w-md overflow-y-auto">
            <Panel
              title="Transaction detail"
              actions={<GhostButton onClick={() => setSelected(null)}>Close</GhostButton>}
            >
              <div className="grid grid-cols-2 gap-4">
                <Stat label="Date" value={formatDateTime(selected.occurred_at)} />
                <Stat
                  label="Type"
                  value={
                    <Badge tone={activityTone(selected.transaction_type)}>
                      {titleCase(selected.transaction_type)}
                    </Badge>
                  }
                />
                <Stat
                  label="Amount"
                  value={selected.amount_ghs ? formatGhs(selected.amount_ghs) : '—'}
                  hint="Cash layer"
                />
                <Stat
                  label="Quantity"
                  value={selected.units != null ? formatUnits(selected.units) : '—'}
                  hint="Credit units layer"
                />
                <Stat label="Channel" value={selected.channel?.toUpperCase() || '—'} />
                <Stat label="Provider" value={titleCase(selected.provider)} />
                <Stat label="School" value={selected.school_name || 'Platform'} />
                <Stat label="Administrator" value={selected.actor_name || '—'} />
              </div>
              <div className="mt-4 border-t border-[var(--color-line)] pt-3">
                <Stat label="Reference" value={selected.reference || '—'} />
                {selected.description && (
                  <p className="mt-2 text-sm text-[var(--color-ink)]/70">
                    {selected.description}
                  </p>
                )}
              </div>
            </Panel>
          </div>
        </div>
      )}
    </div>
  )
}
