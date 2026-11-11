import type { MessagingOverview, MessagingUsageEvent } from '../types'

const EVENT_LABELS: Record<string, string> = {
  ward_enrolled: 'Ward enrolled',
  payment_receipt: 'Payment receipt',
  debt_reminder: 'Debt reminder',
  report_ready: 'Report ready',
  next_term_fees: 'Next term fees',
}

const PERIODS = [
  { key: '7d', label: '7 days' },
  { key: '30d', label: '30 days' },
  { key: 'custom', label: 'Custom' },
] as const

type UsagePeriod = (typeof PERIODS)[number]['key']

type MessagingUsageProps = {
  overview: MessagingOverview
  period: UsagePeriod
  start: string
  end: string
  onPeriodChange: (period: UsagePeriod) => void
  onStartChange: (value: string) => void
  onEndChange: (value: string) => void
}

function eventLabel(value: string) {
  return EVENT_LABELS[value] ?? value.replaceAll('_', ' ')
}

function OutcomeBar({
  sent,
  failed,
  skipped,
}: {
  sent: number
  failed: number
  skipped: number
}) {
  const total = sent + failed + skipped
  if (total === 0) {
    return <div className="h-2.5 rounded-full bg-slate-100" />
  }
  return (
    <div className="flex h-2.5 overflow-hidden rounded-full bg-slate-100">
      {sent > 0 ? (
        <div className="bg-emerald-500" style={{ width: `${(sent / total) * 100}%` }} />
      ) : null}
      {failed > 0 ? (
        <div className="bg-red-500" style={{ width: `${(failed / total) * 100}%` }} />
      ) : null}
      {skipped > 0 ? (
        <div className="bg-amber-400" style={{ width: `${(skipped / total) * 100}%` }} />
      ) : null}
    </div>
  )
}

function ChannelCard({
  title,
  tone,
  balance,
  sent,
  failed,
  skipped,
  creditsUsed,
  events,
}: {
  title: string
  tone: 'sms' | 'email'
  balance: number
  sent: number
  failed: number
  skipped: number
  creditsUsed: number
  events: MessagingUsageEvent[]
}) {
  const empty = balance <= 0
  const low = !empty && creditsUsed > 0 && balance < creditsUsed
  const shell =
    tone === 'sms' ? 'border-sky-200 bg-sky-50/40' : 'border-indigo-200 bg-indigo-50/40'
  const balanceClass = empty ? 'text-red-700' : low ? 'text-amber-800' : 'text-slate-900'

  return (
    <section className={`rounded-2xl border p-5 ${shell}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          <p className={`mt-1 text-2xl font-semibold ${balanceClass}`}>
            {balance.toLocaleString()}
            <span className="ml-2 text-sm font-medium text-slate-500">credits left</span>
          </p>
        </div>
        <p className="text-right text-sm text-slate-600">
          <span className="block font-medium text-slate-900">{creditsUsed.toLocaleString()}</span>
          used
        </p>
      </div>
      {empty ? (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">
          No credits left. New {title} messages will be skipped until you top up.
        </p>
      ) : low ? (
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Credits left are less than this period’s usage. A large send may be partly skipped.
        </p>
      ) : null}
      <div className="mt-4">
        <OutcomeBar sent={sent} failed={failed} skipped={skipped} />
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-emerald-500" />
            {sent} sent
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-red-500" />
            {failed} failed
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-amber-400" />
            {skipped} skipped
          </span>
        </div>
      </div>
      {events.length > 0 ? (
        <table className="mt-4 w-full text-left text-sm">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-1 font-medium">Message</th>
              <th className="py-1 text-right font-medium">Sent</th>
              <th className="py-1 text-right font-medium">Failed</th>
              <th className="py-1 text-right font-medium">Skipped</th>
              <th className="py-1 text-right font-medium">Credits</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.event_type} className="border-t border-slate-200/80">
                <td className="py-1.5 text-slate-800">{eventLabel(event.event_type)}</td>
                <td className="py-1.5 text-right">{event.sent}</td>
                <td className="py-1.5 text-right">{event.failed}</td>
                <td className="py-1.5 text-right">{event.skipped}</td>
                <td className="py-1.5 text-right">{event.credits_used}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="mt-4 text-sm text-slate-500">No {title} messages in this period.</p>
      )}
    </section>
  )
}

const MessagingUsagePanel = ({
  overview,
  period,
  start,
  end,
  onPeriodChange,
  onStartChange,
  onEndChange,
}: MessagingUsageProps) => {
  const usage = overview.usage ?? overview.usage_7d
  const events = usage.by_event ?? []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          {overview.open_failures} open failure{overview.open_failures === 1 ? '' : 's'} still need
          attention.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border border-slate-200 p-0.5 text-sm">
            {PERIODS.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`cursor-pointer rounded-md px-3 py-1.5 ${
                  period === item.key
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
                onClick={() => onPeriodChange(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>
          {period === 'custom' ? (
            <div className="flex items-center gap-2 text-sm">
              <input
                type="date"
                value={start}
                max={end || undefined}
                aria-label="From"
                className="rounded-lg border border-slate-200 px-2 py-1.5"
                onChange={(event) => onStartChange(event.target.value)}
              />
              <span className="text-slate-400">to</span>
              <input
                type="date"
                value={end}
                min={start || undefined}
                aria-label="To"
                className="rounded-lg border border-slate-200 px-2 py-1.5"
                onChange={(event) => onEndChange(event.target.value)}
              />
            </div>
          ) : null}
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChannelCard
          title="SMS"
          tone="sms"
          balance={overview.credits.sms}
          sent={usage.sms_sent}
          failed={usage.sms_failed}
          skipped={usage.sms_skipped}
          creditsUsed={usage.sms_credits_used}
          events={events.filter((event) => event.channel === 'sms')}
        />
        <ChannelCard
          title="Email"
          tone="email"
          balance={overview.credits.email}
          sent={usage.email_sent}
          failed={usage.email_failed}
          skipped={usage.email_skipped}
          creditsUsed={usage.email_credits_used}
          events={events.filter((event) => event.channel === 'email')}
        />
      </div>
    </div>
  )
}

export default MessagingUsagePanel
