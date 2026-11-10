import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FilterBar, rangeLabel, useMessagesFilters } from './components/filters'
import {
  Badge,
  LayerTile,
  PageHeader,
  Panel,
  QueryNotice,
  Stat,
  SummaryStrip,
  TableState,
  TableWrap,
  Td,
  Th,
  Thead,
  TrendChart,
} from './components/ui'
import { formatDateTime, formatGhs, formatPct, formatUnits, num, titleCase } from './lib'
import { getSchoolReport } from './services'
import { useMessagesAccess } from './permissions'
import type { DeliveryStats } from './types'

function DeliveryStatsRow({ label, stats }: { label: string; stats?: DeliveryStats }) {
  return (
    <div className="grid grid-cols-3 gap-4 border-t border-[var(--color-line)] py-3 first:border-t-0 sm:grid-cols-6">
      <Stat label={label} value={formatPct(stats?.success_rate_pct)} hint="Success rate" />
      <Stat label="Submitted" value={formatUnits(stats?.submitted)} />
      <Stat label="Delivered" value={formatUnits(stats?.delivered)} />
      <Stat label="Failed" value={formatUnits(stats?.failed)} />
      <Stat label="Skipped" value={formatUnits(stats?.skipped)} />
      <Stat label="Unknown" value={formatUnits(stats?.unknown)} />
    </div>
  )
}

export default function SchoolReportPage() {
  const { id = '' } = useParams()
  const { filters, setFilter, params } = useMessagesFilters()
  const { can } = useMessagesAccess()
  const canSeeMoney = can('profitability.money')

  const reportQuery = useQuery({
    queryKey: ['platform-messages-school-report', id, params],
    queryFn: () => getSchoolReport(id, params),
    enabled: Boolean(id),
    retry: false,
  })

  const report = reportQuery.data
  const trend = (report?.trend ?? []).map((point) => ({
    label: point.date,
    a: num(point.sms_segments),
    b: num(point.email_credits),
  }))

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
        <Link to="/messages/schools" className="text-[var(--color-accent)] hover:underline">
          ← Back to school usage
        </Link>
        {id && (
          <Link
            to={`/schools/${id}`}
            className="text-[var(--color-ink)]/60 hover:underline"
          >
            Open school record
          </Link>
        )}
      </div>

      <PageHeader
        title={report?.school?.name || 'School messaging report'}
        description={`Messaging consumption and economics for ${rangeLabel(filters)}.`}
        actions={
          report?.school?.status && <Badge tone="neutral">{report.school.status}</Badge>
        }
      />

      <FilterBar filters={filters} setFilter={setFilter} show={{ channel: true, classification: true }} />

      <div className="mb-6">
        <QueryNotice
          isLoading={reportQuery.isLoading}
          isError={reportQuery.isError}
          error={reportQuery.error}
        />
      </div>

      <SummaryStrip caption="School credit wallets (units)">
        <LayerTile
          layer="credits"
          label="SMS balance"
          value={formatUnits(report?.balances?.sms)}
          hint="Unused credits are a delivery liability"
        />
        <LayerTile
          layer="credits"
          label="Email balance"
          value={formatUnits(report?.balances?.email)}
          hint="Unused credits are a delivery liability"
        />
        <LayerTile
          layer="credits"
          label="Credits consumed"
          value={formatUnits(report?.credits?.consumed)}
          hint={`Reversed ${formatUnits(report?.credits?.reversed)}`}
        />
        <LayerTile
          layer="credits"
          label="Credits remaining"
          value={formatUnits(report?.credits?.remaining)}
        />
      </SummaryStrip>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel
          title="Credit movements"
          description="Where this school's units came from, in the selected range."
          footnote="A promo grant lands credits in the wallet and is spent as paid traffic. A sponsored send moves no credits at all."
        >
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Stat label="Purchased (top-ups)" value={formatUnits(report?.credits?.purchased)} />
            <Stat
              label="Subscription allocations"
              value={formatUnits(report?.credits?.allocated)}
            />
            <Stat label="Promotional credits" value={formatUnits(report?.credits?.promo)} />
            <Stat label="Consumed" value={formatUnits(report?.credits?.consumed)} />
            <Stat label="Reversed" value={formatUnits(report?.credits?.reversed)} />
            <Stat label="Remaining" value={formatUnits(report?.credits?.remaining)} />
          </div>
        </Panel>

        <Panel
          title="Free & sponsored consumption"
          description="Traffic the school did not pay for. No wallet debit was made."
        >
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Stat
              label="Free SMS segments"
              value={formatUnits(report?.free_usage?.free_sms_segments)}
            />
            <Stat
              label="Sponsored SMS segments"
              value={formatUnits(report?.free_usage?.sponsored_sms_segments)}
            />
            <Stat
              label="Free email credits"
              value={formatUnits(report?.free_usage?.free_email_credits)}
            />
            <Stat
              label="Sponsored email credits"
              value={formatUnits(report?.free_usage?.sponsored_email_credits)}
            />
            {canSeeMoney && (
              <Stat
                label="Platform-funded expense"
                value={formatGhs(report?.free_usage?.platform_funded_expense_ghs)}
              />
            )}
          </div>
        </Panel>
      </div>

      {canSeeMoney && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Panel title="Provider cost attributable to this school">
            <div className="grid grid-cols-2 gap-4">
              <Stat label="SMS cost" value={formatGhs(report?.provider_cost?.sms_ghs)} />
              <Stat
                label="Email cost"
                value={formatGhs(report?.provider_cost?.email_ghs)}
                hint={
                  report?.provider_cost?.email_is_estimated
                    ? 'Estimated SES send cost allocated to this school'
                    : undefined
                }
              />
            </div>
          </Panel>
          <Panel
            title="Revenue"
            footnote="Cash and usage value are different views of the same sale at different times — never add them."
          >
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Stat label="Top-up cash" value={formatGhs(report?.revenue?.topup_cash_ghs)} />
              <Stat label="Add-on cash" value={formatGhs(report?.revenue?.addon_cash_ghs)} />
              <Stat
                label="Usage-valued revenue"
                value={formatGhs(report?.revenue?.usage_valued_ghs)}
              />
            </div>
          </Panel>
        </div>
      )}

      <div className="mt-4">
        <Panel title="Delivery statistics">
          <DeliveryStatsRow label="SMS" stats={report?.delivery_stats?.sms} />
          <DeliveryStatsRow label="Email" stats={report?.delivery_stats?.email} />
        </Panel>
      </div>

      <div className="mt-4">
        <Panel title="Consumption trend">
          <TrendChart data={trend} seriesA="SMS segments" seriesB="Email credits" />
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 font-[family-name:var(--font-display)] text-lg font-semibold">
            Recent ledger entries
          </h3>
          <TableWrap>
            <Thead>
              <tr>
                <Th>When</Th>
                <Th>Type</Th>
                <Th>Channel</Th>
                <Th align="right">Delta</Th>
                <Th align="right">Balance after</Th>
              </tr>
            </Thead>
            <tbody>
              <TableState
                colSpan={5}
                isLoading={reportQuery.isLoading}
                isError={reportQuery.isError}
                error={reportQuery.error}
                isEmpty={(report?.ledger?.length ?? 0) === 0}
                emptyMessage="No credit movements in this range."
              />
              {(report?.ledger ?? []).map((entry) => (
                <tr key={entry.id} className="border-b border-[var(--color-line)] last:border-0">
                  <Td>{formatDateTime(entry.occurred_at)}</Td>
                  <Td>{titleCase(entry.entry_type)}</Td>
                  <Td className="uppercase">{entry.channel}</Td>
                  <Td align="right" className={entry.delta < 0 ? 'text-red-700' : ''}>
                    {entry.delta > 0 ? '+' : ''}
                    {formatUnits(entry.delta)}
                  </Td>
                  <Td align="right">{formatUnits(entry.balance_after)}</Td>
                </tr>
              ))}
            </tbody>
          </TableWrap>
        </div>

        <div>
          <h3 className="mb-3 font-[family-name:var(--font-display)] text-lg font-semibold">
            Top-up history
          </h3>
          <TableWrap>
            <Thead>
              <tr>
                <Th>Purchased</Th>
                <Th>Package</Th>
                <Th align="right">Credits</Th>
                <Th align="right">Amount</Th>
                <Th>Status</Th>
              </tr>
            </Thead>
            <tbody>
              <TableState
                colSpan={5}
                isLoading={reportQuery.isLoading}
                isError={reportQuery.isError}
                error={reportQuery.error}
                isEmpty={(report?.topups?.length ?? 0) === 0}
                emptyMessage="No top-ups in this range."
              />
              {(report?.topups ?? []).map((topup) => (
                <tr key={topup.id} className="border-b border-[var(--color-line)] last:border-0">
                  <Td>{formatDateTime(topup.purchased_at)}</Td>
                  <Td>
                    {topup.package_name}
                    <span className="block text-xs text-[var(--color-ink)]/50 uppercase">
                      {topup.channel}
                    </span>
                  </Td>
                  <Td align="right">{formatUnits(topup.credits)}</Td>
                  <Td align="right">{formatGhs(topup.amount_ghs)}</Td>
                  <Td>
                    <Badge tone={topup.status === 'success' ? 'accent' : 'neutral'}>
                      {titleCase(topup.status)}
                    </Badge>
                  </Td>
                </tr>
              ))}
            </tbody>
          </TableWrap>
        </div>
      </div>

      <p className="mt-6 text-xs text-[var(--color-ink)]/55">
        Each successful paid submit debits the wallet, so a retry of the same logical message
        debits again — the provider units were genuinely consumed both times.
      </p>
    </div>
  )
}
