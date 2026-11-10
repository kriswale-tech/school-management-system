import { Fragment, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { FilterBar, rangeLabel, useMessagesFilters } from './components/filters'
import {
  Badge,
  GhostButton,
  Pagination,
  PageHeader,
  Stat,
  TableState,
  TableWrap,
  Td,
  Th,
  Thead,
} from './components/ui'
import { errorMessage, formatGhs, formatUnits } from './lib'
import { downloadExport, listSchoolUsage } from './services'
import { useMessagesAccess } from './permissions'

export default function SchoolUsagePage() {
  const { filters, setFilter, params } = useMessagesFilters()
  const { can } = useMessagesAccess()
  const canExport = can('exports')
  const canSeeMoney = can('profitability.money')
  const [expanded, setExpanded] = useState<string | null>(null)

  const usageQuery = useQuery({
    queryKey: ['platform-messages-school-usage', params, filters.q, filters.page],
    queryFn: () => listSchoolUsage({ ...params, q: filters.q || undefined, page: filters.page }),
    retry: false,
  })

  const rows = usageQuery.data?.results ?? []
  const columnCount = 8

  async function onExport() {
    try {
      await downloadExport({ ...params, type: 'school_usage', format: 'csv' })
      toast.success('Export started')
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  return (
    <div>
      <PageHeader
        title="School usage & analytics"
        description={`Per-school consumption for ${rangeLabel(
          filters,
        )}. SMS is always counted in billable segments — a 2-segment message to 3 guardians is 6 units.`}
        actions={canExport && <GhostButton onClick={onExport}>Export CSV</GhostButton>}
      />

      <FilterBar
        filters={filters}
        setFilter={setFilter}
        show={{ channel: true, classification: true, search: true }}
      />

      <TableWrap>
        <Thead>
          <tr>
            <Th>School</Th>
            <Th align="right" title="Segments debited from the school wallet">
              Paid SMS
            </Th>
            <Th align="right" title="Segments covered by an allowance or campaign — no debit">
              Free SMS
            </Th>
            <Th align="right" title="Current wallet balance in SMS credits">
              SMS balance
            </Th>
            <Th align="right">Paid email</Th>
            <Th align="right">Free email</Th>
            <Th align="right" title="Current wallet balance in email credits">
              Email balance
            </Th>
            <Th>Report</Th>
          </tr>
        </Thead>
        <tbody>
          <TableState
            colSpan={columnCount}
            isLoading={usageQuery.isLoading}
            isError={usageQuery.isError}
            error={usageQuery.error}
            isEmpty={rows.length === 0}
            emptyMessage="No school messaging activity in this range."
          />
          {rows.map((row) => (
            <Fragment key={row.school}>
              <tr className="border-b border-[var(--color-line)]">
                <Td>
                  <button
                    type="button"
                    onClick={() => setExpanded(expanded === row.school ? null : row.school)}
                    className="text-left font-medium hover:underline"
                  >
                    {row.school_name}
                  </button>
                  <span className="block text-xs text-[var(--color-ink)]/50">
                    {expanded === row.school ? 'Hide detail' : 'Show detail'}
                  </span>
                </Td>
                <Td align="right">{formatUnits(row.paid_sms_segments)}</Td>
                <Td align="right">
                  {formatUnits(row.free_sms_segments)}
                  {row.sponsored_sms_segments > 0 && (
                    <span className="block text-xs text-[var(--color-ink)]/50">
                      +{formatUnits(row.sponsored_sms_segments)} sponsored
                    </span>
                  )}
                </Td>
                <Td align="right">{formatUnits(row.sms_balance)}</Td>
                <Td align="right">{formatUnits(row.paid_email_credits)}</Td>
                <Td align="right">
                  {formatUnits(row.free_email_credits)}
                  {row.sponsored_email_credits > 0 && (
                    <span className="block text-xs text-[var(--color-ink)]/50">
                      +{formatUnits(row.sponsored_email_credits)} sponsored
                    </span>
                  )}
                </Td>
                <Td align="right">{formatUnits(row.email_balance)}</Td>
                <Td>
                  <Link
                    to={`/messages/schools/${row.school}`}
                    className="text-sm font-medium text-[var(--color-accent)] hover:underline"
                  >
                    Open
                  </Link>
                </Td>
              </tr>
              {expanded === row.school && (
                <tr className="border-b border-[var(--color-line)]">
                  <td colSpan={columnCount} className="bg-[var(--color-panel)] px-4 py-4">
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                      <Stat
                        label="Total SMS segments"
                        value={formatUnits(
                          row.paid_sms_segments +
                            row.free_sms_segments +
                            row.sponsored_sms_segments,
                        )}
                      />
                      <Stat
                        label="Total email credits"
                        value={formatUnits(
                          row.paid_email_credits +
                            row.free_email_credits +
                            row.sponsored_email_credits,
                        )}
                      />
                      {canSeeMoney && (
                        <>
                          <Stat
                            label="Provider cost (usage)"
                            value={formatGhs(row.provider_cost_ghs)}
                          />
                          <Stat label="Revenue (usage)" value={formatGhs(row.revenue_ghs)} />
                          <Stat
                            label="Gross profit contribution"
                            value={formatGhs(row.gross_profit_ghs)}
                          />
                        </>
                      )}
                      <div className="flex items-end gap-2">
                        <Badge tone={row.sms_addon_enabled ? 'accent' : 'neutral'}>
                          SMS add-on {row.sms_addon_enabled ? 'on' : 'off'}
                        </Badge>
                        <Badge tone={row.email_addon_enabled ? 'accent' : 'neutral'}>
                          Email add-on {row.email_addon_enabled ? 'on' : 'off'}
                        </Badge>
                      </div>
                    </div>
                    <p className="mt-3 text-xs text-[var(--color-ink)]/55">
                      Balances are school credit units; cost and revenue are usage economics.
                      They belong to different layers and are not comparable.
                    </p>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </TableWrap>

      <Pagination
        count={usageQuery.data?.count ?? 0}
        page={filters.page}
        onPage={(page) => setFilter({ page })}
      />
    </div>
  )
}
