import { useQuery } from '@tanstack/react-query'
import { FilterBar, rangeLabel, useMessagesFilters } from './components/filters'
import {
  LayerTile,
  PageHeader,
  Panel,
  QueryNotice,
  Stat,
  SummaryStrip,
  TrendChart,
} from './components/ui'
import { formatDateTime, formatGhs, formatPct, formatUnits, num } from './lib'
import { getOverview } from './services'
import { useMessagesAccess } from './permissions'

export default function OverviewPage() {
  const { filters, setFilter, params } = useMessagesFilters()
  const { can } = useMessagesAccess()
  const showMoney = can('profitability.money') || can('profitability.view')

  const overviewQuery = useQuery({
    queryKey: ['platform-messages-overview', params],
    queryFn: () => getOverview(params),
    retry: false,
  })

  const data = overviewQuery.data
  const sms = data?.sms
  const email = data?.email
  const provider = data?.provider_layer
  const credits = data?.school_credit_layer
  const cash = data?.cash_layer
  const usage = data?.usage_layer

  const trend = (data?.trend ?? []).map((point) => ({
    label: point.date,
    a: num(point.sms_segments),
    b: num(point.email_credits),
  }))

  return (
    <div>
      <PageHeader
        title="Overview"
        description={`Platform-wide messaging activity for ${rangeLabel(filters)}.`}
      />

      <FilterBar
        filters={filters}
        setFilter={setFilter}
        show={{ channel: true, classification: true, school: true }}
      />

      <div className="mb-6">
        <QueryNotice
          isLoading={overviewQuery.isLoading}
          isError={overviewQuery.isError}
          error={overviewQuery.error}
        />
      </div>

      <SummaryStrip caption="Layer 1 — provider wallet & plan">
        <LayerTile
          layer="provider"
          label="Arkesel SMS balance"
          value={formatUnits(provider?.arkesel_sms_balance)}
          hint={`Captured ${formatDateTime(provider?.arkesel_captured_at)}`}
        />
        <LayerTile
          layer="provider"
          label="SES monthly volume used"
          value={
            (provider?.ses_monthly_used ?? provider?.resend_monthly_used) == null
              ? '—'
              : `${formatUnits(provider?.ses_monthly_used ?? provider?.resend_monthly_used)} / ${
                  (provider?.ses_monthly_limit ?? provider?.resend_monthly_limit) == null
                    ? '∞'
                    : formatUnits(provider?.ses_monthly_limit ?? provider?.resend_monthly_limit)
                }`
          }
          hint="Pay-per-send — SES has no prepaid wallet"
        />
        <LayerTile
          layer="provider"
          label="Arkesel API status"
          value={provider?.arkesel_api_status ?? '—'}
          hint="From the last sync attempt"
        />
        <LayerTile
          layer="provider"
          label="SES API status"
          value={provider?.ses_api_status ?? provider?.resend_api_status ?? '—'}
          hint={`Synced ${formatDateTime(provider?.ses_captured_at ?? provider?.resend_captured_at)}`}
        />
      </SummaryStrip>

      <SummaryStrip caption="Layer 2 — school credit wallets (units, not money)">
        <LayerTile
          layer="credits"
          label="SMS credits outstanding"
          value={formatUnits(credits?.sms_outstanding_units)}
          hint="Unused credits are a delivery liability, not revenue"
        />
        <LayerTile
          layer="credits"
          label="Email credits outstanding"
          value={formatUnits(credits?.email_outstanding_units)}
          hint="Unused credits are a delivery liability, not revenue"
        />
        <LayerTile
          layer="credits"
          label="Credits allocated in range"
          value={formatUnits(credits?.allocated_units)}
          hint="Recurring allocation + top-up + promo + adjustments"
        />
        <LayerTile
          layer="credits"
          label="Credits consumed in range"
          value={formatUnits(credits?.consumed_units)}
          hint="Usage debits net of reversals"
        />
      </SummaryStrip>

      {showMoney && (
        <>
          <SummaryStrip caption="Layers 3 & 4 — cash movements">
            <LayerTile
              layer="cash"
              label="Cash received from schools"
              value={formatGhs(cash?.received_from_schools_ghs)}
              hint={`Top-ups ${formatGhs(cash?.topup_cash_ghs)} · add-ons ${formatGhs(
                cash?.addon_cash_ghs,
              )}`}
            />
            <LayerTile
              layer="cash"
              label="Cash paid to providers"
              value={formatGhs(cash?.paid_to_providers_ghs)}
              hint={`Purchases ${formatGhs(cash?.provider_purchases_ghs)} · expenses ${formatGhs(
                cash?.provider_expenses_ghs,
              )}`}
            />
            <LayerTile
              layer="cash"
              label="Wallet purchases (Arkesel)"
              value={formatGhs(cash?.provider_purchases_ghs)}
              hint="Cash out — not the cost of messages already sent"
            />
            <LayerTile
              layer="cash"
              label="Provider expenses (SES)"
              value={formatGhs(cash?.provider_expenses_ghs)}
              hint="Usage and monitoring charges"
            />
          </SummaryStrip>

          <SummaryStrip caption="Layer 5 — usage economics, valued at send-time snapshots">
            <LayerTile
              layer="usage"
              label="Usage-valued revenue"
              value={formatGhs(usage?.usage_valued_revenue_ghs)}
              hint="Paid units × reference unit price at send time"
            />
            <LayerTile
              layer="usage"
              label="Provider cost of usage"
              value={formatGhs(usage?.provider_cost_ghs)}
              estimated={usage?.email_cost_is_estimated}
              hint="Email cost is an allocation, not an invoice"
            />
            <LayerTile
              layer="usage"
              label="Gross profit"
              value={formatGhs(usage?.gross_profit_ghs)}
              hint={`Margin ${formatPct(usage?.gross_margin_pct)}`}
            />
            <LayerTile
              layer="usage"
              label="Free & sponsored expense"
              value={formatGhs(usage?.free_sponsored_expense_ghs)}
              hint="Platform-funded provider cost"
            />
          </SummaryStrip>
        </>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel
          title="SMS"
          description="Always reported in billable segments, never message counts."
          footnote="A 2-segment message to 3 guardians is 6 billable units."
        >
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Stat label="Segments total" value={formatUnits(sms?.segments_total)} />
            <Stat label="Paid segments" value={formatUnits(sms?.segments_paid)} />
            <Stat label="Free segments" value={formatUnits(sms?.segments_free)} />
            <Stat label="Sponsored segments" value={formatUnits(sms?.segments_sponsored)} />
            <Stat label="Messages" value={formatUnits(sms?.messages_total)} />
            <Stat label="Recipients" value={formatUnits(sms?.recipients_total)} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 border-t border-[var(--color-line)] pt-4 sm:grid-cols-5">
            <Stat label="Submitted" value={formatUnits(sms?.submitted)} />
            <Stat label="Delivered" value={formatUnits(sms?.delivered)} />
            <Stat label="Failed" value={formatUnits(sms?.failed)} />
            <Stat label="Skipped" value={formatUnits(sms?.skipped)} />
            <Stat label="Unknown" value={formatUnits(sms?.unknown)} />
          </div>
        </Panel>

        <Panel
          title="Email"
          description="1 credit = 1 provider-accepted recipient delivery attempt."
          footnote="Delivery states beyond submitted depend on SES SNS webhooks."
        >
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Stat label="Credits total" value={formatUnits(email?.credits_total)} />
            <Stat label="Paid credits" value={formatUnits(email?.credits_paid)} />
            <Stat label="Free credits" value={formatUnits(email?.credits_free)} />
            <Stat label="Sponsored credits" value={formatUnits(email?.credits_sponsored)} />
            <Stat label="Accepted" value={formatUnits(email?.accepted)} />
            <Stat label="Submitted" value={formatUnits(email?.submitted)} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 border-t border-[var(--color-line)] pt-4 sm:grid-cols-5">
            <Stat label="Delivered" value={formatUnits(email?.delivered)} />
            <Stat label="Failed" value={formatUnits(email?.failed)} />
            <Stat label="Skipped" value={formatUnits(email?.skipped)} />
            <Stat label="Unknown" value={formatUnits(email?.unknown)} />
          </div>
        </Panel>
      </div>

      <div className="mt-4">
        <Panel title="Volume trend" description="Consumed units per day across the range.">
          <TrendChart data={trend} seriesA="SMS segments" seriesB="Email credits" />
        </Panel>
      </div>

      {usage != null && num(usage.unpriced_units) > 0 && (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {formatUnits(usage.unpriced_units)} consumed units in this range predate pricing
          snapshots and are excluded from every valued figure above.
        </p>
      )}
    </div>
  )
}
