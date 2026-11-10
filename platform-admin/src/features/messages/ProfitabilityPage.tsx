import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { FilterBar, rangeLabel, useMessagesFilters } from './components/filters'
import {
  EstimatedTag,
  GhostButton,
  LayerTile,
  PageHeader,
  Panel,
  QueryNotice,
  Stat,
  SummaryStrip,
  TrendChart,
} from './components/ui'
import { errorMessage, formatGhs, formatPct, formatUnits } from './lib'
import { downloadExport, getProfitability } from './services'
import { useMessagesAccess } from './permissions'
import type { ChannelPnl, ProfitabilityView } from './types'

function ChannelPanel({
  title,
  description,
  pnl,
  showMoney,
  extra,
}: {
  title: string
  description: string
  pnl?: ChannelPnl
  showMoney: boolean
  extra?: Array<{ label: string; value: string }>
}) {
  return (
    <Panel title={title} description={description}>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Stat label="Units consumed" value={formatUnits(pnl?.units_consumed)} />
        {showMoney && (
          <>
            {extra?.map((item) => (
              <Stat key={item.label} label={item.label} value={item.value} />
            ))}
            <Stat
              label="Provider cost"
              value={
                <>
                  {formatGhs(pnl?.provider_cost_ghs)}
                  {pnl?.cost_is_estimated && <EstimatedTag />}
                </>
              }
            />
            <Stat label="Credit revenue" value={formatGhs(pnl?.credit_revenue_ghs)} />
            <Stat label="Add-on revenue" value={formatGhs(pnl?.addon_revenue_ghs)} />
            <Stat label="Gross profit" value={formatGhs(pnl?.gross_profit_ghs)} />
            <Stat label="Gross margin" value={formatPct(pnl?.gross_margin_pct)} />
          </>
        )}
      </div>
    </Panel>
  )
}

export default function ProfitabilityPage() {
  const { filters, setFilter, params } = useMessagesFilters()
  const { can } = useMessagesAccess()
  const [view, setView] = useState<ProfitabilityView>('usage')

  const showMoney = can('profitability.money')
  const canExport = can('exports')

  const profitabilityQuery = useQuery({
    queryKey: ['platform-messages-profitability', params, view],
    queryFn: () => getProfitability({ ...params, view }),
    retry: false,
    enabled: can('profitability.view'),
  })

  if (!can('profitability.view')) {
    return <Navigate to="/messages" replace />
  }

  const data = profitabilityQuery.data
  const trend = (data?.trend ?? []).map((point) => ({
    label: point.date,
    a: Number(point.revenue_ghs) || 0,
    b: Number(point.cost_ghs) || 0,
  }))

  async function onExport(format: 'csv' | 'xlsx') {
    try {
      await downloadExport({ ...params, type: 'profitability', format, view })
      toast.success('Export started')
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  return (
    <div>
      <PageHeader
        title="Revenue & profitability"
        description={`Messaging P&L for ${rangeLabel(
          filters,
        )}. Cash and usage are shown as separate views and are never blended into one profit number.`}
        actions={
          canExport && (
            <>
              <GhostButton onClick={() => onExport('csv')}>Export CSV</GhostButton>
              <GhostButton onClick={() => onExport('xlsx')}>Export Excel</GhostButton>
            </>
          )
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] p-1">
          {(['usage', 'cash'] as ProfitabilityView[]).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setView(option)}
              className={[
                'rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition',
                view === option
                  ? 'bg-[var(--color-accent)] text-white'
                  : 'text-[var(--color-ink)]/70',
              ].join(' ')}
            >
              {option} view
            </button>
          ))}
        </div>
        <p className="text-sm text-[var(--color-ink)]/60">
          {view === 'cash'
            ? 'What actually moved: cash received from schools and cash paid to providers.'
            : 'What was actually consumed, valued at the cost and price snapshots taken at send time.'}
        </p>
      </div>

      <FilterBar filters={filters} setFilter={setFilter} show={{ channel: true, school: true }} />

      <div className="mb-6">
        <QueryNotice
          isLoading={profitabilityQuery.isLoading}
          isError={profitabilityQuery.isError}
          error={profitabilityQuery.error}
        />
      </div>

      {!showMoney && (
        <p className="mb-6 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-4 py-3 text-sm text-[var(--color-ink)]/70">
          Your role sees messaging volumes only. Revenue, cost, and margin figures are restricted
          to Finance and Super Admin.
        </p>
      )}

      {view === 'cash' && showMoney && (
        <SummaryStrip caption="Cash view — layers 3 & 4">
          <LayerTile
            layer="cash"
            label="Received from schools"
            value={formatGhs(data?.cash?.received_from_schools_ghs)}
            hint={`Top-ups ${formatGhs(data?.cash?.topup_cash_ghs)} · add-ons ${formatGhs(
              data?.cash?.addon_cash_ghs,
            )}`}
          />
          <LayerTile
            layer="cash"
            label="Paid to providers"
            value={formatGhs(data?.cash?.paid_to_providers_ghs)}
            hint={`Purchases ${formatGhs(
              data?.cash?.provider_purchases_ghs,
            )} · expenses ${formatGhs(data?.cash?.provider_expenses_ghs)}`}
          />
          <LayerTile
            layer="cash"
            label="Net cash"
            value={formatGhs(data?.cash?.net_cash_ghs)}
            hint="Not profit — credits sold may still be undelivered"
          />
          <LayerTile
            layer="credits"
            label="Unused credits outstanding"
            value={formatUnits(data?.combined?.unused_credits_units)}
            hint="A delivery liability, not revenue"
          />
        </SummaryStrip>
      )}

      {view === 'usage' && showMoney && (
        <SummaryStrip caption="Usage view — layer 5">
          <LayerTile
            layer="usage"
            label="Usage-valued revenue"
            value={formatGhs(data?.combined?.usage_valued_revenue_ghs)}
            hint="Paid units × snapshot sell price"
          />
          <LayerTile
            layer="usage"
            label="Provider cost of usage"
            value={formatGhs(data?.combined?.provider_cost_ghs)}
            estimated={data?.combined?.cost_is_estimated}
          />
          <LayerTile
            layer="usage"
            label="Gross profit"
            value={formatGhs(data?.combined?.gross_profit_ghs)}
            hint={`Margin ${formatPct(data?.combined?.gross_margin_pct)}`}
          />
          <LayerTile
            layer="usage"
            label="Overall contribution"
            value={formatGhs(data?.combined?.overall_contribution_ghs)}
            hint={`After free & sponsored expense ${formatGhs(
              data?.combined?.free_sponsored_expense_ghs,
            )}`}
          />
        </SummaryStrip>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <ChannelPanel
          title="SMS"
          description="Prepaid wallet economics. Purchases are cash out; cost accrues as segments are consumed."
          pnl={data?.sms}
          showMoney={showMoney}
          extra={[
            {
              label: 'Provider purchases',
              value: formatGhs(data?.sms?.provider_purchases_ghs),
            },
          ]}
        />
        <ChannelPanel
          title="Email"
          description="Subscription plus overage. Per-email cost is an allocation, never an invoice line."
          pnl={data?.email}
          showMoney={showMoney}
          extra={[
            {
              label: 'Subscription expense',
              value: formatGhs(data?.email?.subscription_expense_ghs),
            },
            {
              label: 'Overage expense',
              value: formatGhs(data?.email?.overage_expense_ghs),
            },
          ]}
        />
      </div>

      {showMoney && (
        <div className="mt-4">
          <Panel
            title="Combined messaging"
            footnote="Never count unused credits as consumed revenue, and never treat a full wallet purchase as the cost of messages already sent."
          >
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
              <Stat
                label="Total revenue (usage)"
                value={formatGhs(data?.combined?.usage_valued_revenue_ghs)}
              />
              <Stat
                label="Total provider cost"
                value={formatGhs(data?.combined?.provider_cost_ghs)}
              />
              <Stat
                label="Paid gross profit"
                value={formatGhs(data?.combined?.gross_profit_ghs)}
              />
              <Stat
                label="Free & sponsored expense"
                value={formatGhs(data?.combined?.free_sponsored_expense_ghs)}
              />
              <Stat
                label="Overall contribution"
                value={formatGhs(data?.combined?.overall_contribution_ghs)}
              />
              <Stat label="Gross margin" value={formatPct(data?.combined?.gross_margin_pct)} />
            </div>
          </Panel>
        </div>
      )}

      <div className="mt-4">
        <Panel
          title="Margin trend"
          description="Revenue against provider cost, per day in the selected range."
        >
          <TrendChart
            data={trend}
            seriesA="Revenue"
            seriesB="Provider cost"
            formatValue={(value) => formatGhs(value)}
          />
        </Panel>
      </div>
    </div>
  )
}
