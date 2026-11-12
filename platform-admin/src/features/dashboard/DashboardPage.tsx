import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/features/auth/store'
import { getCurriculum } from '@/features/curriculum/services'
import { formatDateTime, formatGhs, formatPct, formatUnits, num } from '@/features/messages/lib'
import { useMessagesAccess } from '@/features/messages/permissions'
import { getOverview } from '@/features/messages/services'
import { fetchSchoolSummary, listSchools } from '@/features/schools/services'

type AttentionItem = {
  id: string
  href: string
  label: string
}

function people(count: number, singular: string, plural: string) {
  return `${count.toLocaleString()} ${count === 1 ? singular : plural}`
}

function count(value: number | undefined, loading: boolean) {
  if (loading) return '…'
  return (value ?? 0).toLocaleString()
}

function Figure({
  label,
  value,
  hint,
  tone = 'default',
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'default' | 'danger'
}) {
  return (
    <div>
      <p className="text-xs font-medium tracking-wide text-[var(--color-ink)]/55 uppercase">{label}</p>
      <p
        className={`mt-1 font-[family-name:var(--font-display)] text-2xl font-semibold ${
          tone === 'danger' ? 'text-red-700' : ''
        }`}
      >
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-[var(--color-ink)]/55">{hint}</p> : null}
    </div>
  )
}

function Block({
  title,
  href,
  linkLabel,
  children,
}: {
  title: string
  href: string
  linkLabel: string
  children: ReactNode
}) {
  return (
    <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-6">
      <div className="mb-5 flex items-baseline justify-between gap-3">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">{title}</h2>
        <Link to={href} className="text-sm font-medium text-[var(--color-accent)]">
          {linkLabel}
        </Link>
      </div>
      {children}
    </section>
  )
}

function providerNote(name: string, status: string | null | undefined) {
  if (status === 'error') return `${name} last sync failed.`
  if (status === 'not_configured') return `${name} is not configured.`
  return null
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const { can } = useMessagesAccess()
  const showMessages = can('messages.view')
  const showMoney = can('profitability.money')
  const showCurriculum = user?.role === 'super_admin' || user?.role === 'curriculum'

  const schoolsQuery = useQuery({
    queryKey: ['platform-school-directory-summary'],
    queryFn: fetchSchoolSummary,
  })
  const pendingQuery = useQuery({
    queryKey: ['platform-schools', 'pending-count'],
    queryFn: () => listSchools({ status: 'pending', page: 1, page_size: 1 }),
  })
  const curriculumQuery = useQuery({
    queryKey: ['platform-curriculum'],
    queryFn: getCurriculum,
    enabled: showCurriculum,
    retry: false,
  })
  const messagesQuery = useQuery({
    queryKey: ['platform-messages-overview', { range: 'last_30' }],
    queryFn: () => getOverview({ range: 'last_30' }),
    enabled: showMessages,
    retry: false,
  })

  const schools = schoolsQuery.data
  const curriculum = curriculumQuery.data
  const live = curriculum?.active
  const messages = messagesQuery.data
  const usage = messages?.usage_layer
  const cash = messages?.cash_layer
  const sms = messages?.sms
  const email = messages?.email
  const provider = messages?.provider_layer
  const failed = num(sms?.failed) + num(email?.failed)
  const sesUsed = provider?.ses_monthly_used ?? provider?.resend_monthly_used
  const sesLimit = provider?.ses_monthly_limit ?? provider?.resend_monthly_limit
  const showEmailPlan = sesUsed != null || sesLimit != null
  const providerNotes = [
    providerNote('Arkesel', provider?.arkesel_api_status),
    providerNote('Email', provider?.ses_api_status ?? provider?.resend_api_status),
  ].filter((note): note is string => Boolean(note))

  const attention: AttentionItem[] = []
  if (!schoolsQuery.isLoading && !schoolsQuery.isError && (schools?.overdue_school_count ?? 0) > 0) {
    attention.push({
      id: 'overdue',
      href: '/payments',
      label: `${people(schools?.overdue_school_count ?? 0, 'school is', 'schools are')} past due`,
    })
  }
  if (!pendingQuery.isLoading && !pendingQuery.isError && (pendingQuery.data?.count ?? 0) > 0) {
    attention.push({
      id: 'pending',
      href: '/schools?status=pending',
      label: `${people(pendingQuery.data?.count ?? 0, 'school is', 'schools are')} still pending`,
    })
  }
  if (showCurriculum && curriculum && (curriculum.schools_behind.length ?? 0) > 0) {
    attention.push({
      id: 'curriculum-behind',
      href: '/curriculum',
      label: `${people(curriculum.schools_behind.length, 'school is', 'schools are')} still on an older curriculum`,
    })
  }
  if (showCurriculum && curriculum?.draft) {
    attention.push({
      id: 'curriculum-draft',
      href: '/curriculum',
      label: `Curriculum draft ${curriculum.draft.version} is waiting to publish`,
    })
  }
  if (showMessages && messages && failed > 0) {
    attention.push({
      id: 'failed-sends',
      href: '/messages',
      label: `${people(failed, 'send failed', 'sends failed')} in the last 30 days`,
    })
  }
  if (showMessages && messages) {
    providerNotes.forEach((note, index) => {
      attention.push({
        id: `provider-${index}`,
        href: '/messages/providers',
        label: note.replace(/\.$/, ''),
      })
    })
  }
  if (showMessages && showMoney && messages && num(usage?.unpriced_units) > 0) {
    attention.push({
      id: 'unpriced',
      href: '/messages',
      label: `${people(num(usage?.unpriced_units), 'send has', 'sends have')} no price on record`,
    })
  }

  return (
    <div>
      <header className="mb-8">
        <p className="font-[family-name:var(--font-display)] text-sm font-semibold tracking-[0.18em] text-[var(--color-accent)] uppercase">
          Overview
        </p>
        <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight">
          Platform overview
        </h1>
        <p className="mt-2 text-[var(--color-ink)]/70">
          Signed in as {user?.full_name || user?.email}.
        </p>
      </header>

      <div className="flex flex-col gap-4">
        {attention.length > 0 ? (
          <section className="rounded-2xl border border-amber-200 bg-amber-50/80 p-6">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">Needs attention</h2>
            <ul className="mt-2 divide-y divide-amber-200/80">
              {attention.map((item) => (
                <li key={item.id}>
                  <Link
                    to={item.href}
                    className="flex items-center justify-between gap-4 py-3 text-sm font-medium text-[var(--color-ink)] hover:text-[var(--color-accent)]"
                  >
                    <span>{item.label}</span>
                    <span className="shrink-0 text-[var(--color-accent)]">Open</span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <Block title="Schools" href="/schools" linkLabel="Open directory">
          {schoolsQuery.isError ? (
            <p className="text-sm text-red-700">Could not load schools.</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
                <Figure label="Schools" value={count(schools?.school_count, schoolsQuery.isLoading)} />
                <Figure label="Active" value={count(schools?.active_school_count, schoolsQuery.isLoading)} />
                <Figure label="Students" value={count(schools?.student_count, schoolsQuery.isLoading)} />
                <Figure label="Staff" value={count(schools?.staff_count, schoolsQuery.isLoading)} />
              </div>
            </>
          )}
        </Block>

        {showMessages ? (
          <Block title="Messaging" href="/messages" linkLabel="Open messages">
            {messagesQuery.isLoading ? (
              <p className="text-sm text-[var(--color-ink)]/60">Loading…</p>
            ) : messagesQuery.isError ? (
              <p className="text-sm text-red-700">Could not load messaging.</p>
            ) : (
              <>
                <p className="mb-4 text-xs font-semibold tracking-[0.12em] text-[var(--color-ink)]/45 uppercase">
                  Last 30 days
                </p>
                {showMoney ? (
                  <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
                    <Figure label="Revenue" value={formatGhs(usage?.usage_valued_revenue_ghs)} hint="Value of sends" />
                    <Figure
                      label="Profit"
                      value={formatGhs(usage?.gross_profit_ghs)}
                      hint={`Margin ${formatPct(usage?.gross_margin_pct)}`}
                    />
                    <Figure
                      label="Cost"
                      value={
                        <>
                          {formatGhs(usage?.provider_cost_ghs)}
                          {usage?.email_cost_is_estimated ? (
                            <span className="ml-2 align-middle text-xs font-medium tracking-wide text-amber-800 uppercase">
                              Estimated
                            </span>
                          ) : null}
                        </>
                      }
                      hint={`Free and sponsored ${formatGhs(usage?.free_sponsored_expense_ghs)}`}
                    />
                    <Figure
                      label="Cash collected"
                      value={formatGhs(cash?.received_from_schools_ghs)}
                      hint="Paid in by schools"
                    />
                  </div>
                ) : null}

                <div
                  className={`grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-3 ${
                    showMoney ? 'mt-6 border-t border-[var(--color-line)] pt-6' : ''
                  }`}
                >
                  <Figure label="SMS used" value={formatUnits(sms?.segments_total)} hint="Billable segments" />
                  <Figure label="Email used" value={formatUnits(email?.credits_total)} hint="Credits" />
                  <Figure
                    label="Failed"
                    value={formatUnits(failed)}
                    tone={failed > 0 ? 'danger' : 'default'}
                    hint={`SMS ${formatUnits(sms?.failed)} · email ${formatUnits(email?.failed)}`}
                  />
                </div>

                <p className="mt-6 mb-4 text-xs font-semibold tracking-[0.12em] text-[var(--color-ink)]/45 uppercase">
                  Right now
                </p>
                <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
                  <Figure
                    label="SMS wallet"
                    value={formatUnits(provider?.arkesel_sms_balance)}
                    hint={
                      provider?.arkesel_captured_at
                        ? `Synced ${formatDateTime(provider.arkesel_captured_at)}`
                        : 'Not synced yet'
                    }
                  />
                  {showEmailPlan ? (
                    <Figure
                      label="Email plan"
                      value={`${formatUnits(sesUsed)} / ${sesLimit == null ? '∞' : formatUnits(sesLimit)}`}
                      hint="Used this month"
                    />
                  ) : null}
                </div>

              </>
            )}
          </Block>
        ) : null}

        {showCurriculum ? (
          <Block title="Curriculum" href="/curriculum" linkLabel="Open curriculum">
            {curriculumQuery.isLoading ? (
              <p className="text-sm text-[var(--color-ink)]/60">Loading…</p>
            ) : curriculumQuery.isError ? (
              <p className="text-sm text-red-700">Could not load curriculum.</p>
            ) : live ? (
              <div className="grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
                <Figure label="Live version" value={live.version} hint={live.name} />
                <Figure
                  label="Schools behind"
                  value={(curriculum?.schools_behind.length ?? 0).toLocaleString()}
                  tone={(curriculum?.schools_behind.length ?? 0) > 0 ? 'danger' : 'default'}
                  hint={
                    (curriculum?.schools_behind.length ?? 0) > 0
                      ? 'Still on an older version'
                      : 'None waiting on an older version'
                  }
                />
              </div>
            ) : (
              <p className="text-sm text-[var(--color-ink)]/70">No live curriculum yet.</p>
            )}
          </Block>
        ) : null}
      </div>
    </div>
  )
}
