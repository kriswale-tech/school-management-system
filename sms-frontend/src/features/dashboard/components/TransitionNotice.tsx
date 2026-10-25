import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui'
import { useAuth } from '@/features/auth/hooks'
import { useTransitionWizard } from '@/features/settings/hooks/useTransitionWizard'
import { getTransitionStatus, TRANSITION_STATUS_QUERY_KEY } from '@/features/settings/services'
import { mergeClasses } from '@/utils'

const formatEndDate = (value: string) => {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

const TransitionNotice = () => {
  const { user } = useAuth()
  const transitionWizard = useTransitionWizard()
  const isAdmin = user?.role === 'admin'
  const [dismissed, setDismissed] = useState(false)

  const { data } = useQuery({
    queryKey: [TRANSITION_STATUS_QUERY_KEY],
    queryFn: getTransitionStatus,
    enabled: Boolean(user?.school_id) && isAdmin,
    staleTime: 60_000,
  })

  const open = Boolean(
    isAdmin
    && data?.visible
    && data.popup_enabled
    && data.unfinished_count > 0
    && data.term_ends_on
    && !dismissed
  )

  const dismiss = () => setDismissed(true)

  if (!open || !data?.term_ends_on) return null

  const urgent = data.urgency === 'red'
  const ended = (data.days_remaining ?? 0) < 0
  const headline = ended
    ? `This term ended on ${formatEndDate(data.term_ends_on)}`
    : data.days_remaining === 0
      ? 'This term ends today'
      : `This term ends on ${formatEndDate(data.term_ends_on)}`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Dismiss transition notice"
        className="absolute inset-0 bg-slate-900/50"
        onClick={dismiss}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="transition-notice-title"
        className="relative w-full max-w-md overflow-hidden rounded-2xl bg-white shadow-2xl"
      >
        <div className={mergeClasses('px-6 py-5 text-white', urgent ? 'bg-red-700' : 'bg-amber-600')}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-white/80">
                Term transition
              </p>
              <h2 id="transition-notice-title" className="mt-1 text-lg font-semibold leading-snug">
                {headline}
              </h2>
            </div>
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/15">
              <Icon icon="hugeicons:calendar-03" className="text-2xl" />
            </span>
          </div>
          {data.term_label ? (
            <p className="mt-3 text-sm text-white/90">Next up: {data.term_label}</p>
          ) : null}
        </div>

        <ul className="space-y-2 px-6 py-5">
          {data.checklist.map((item) => (
            <li key={item.kind} className="flex gap-3 text-sm">
              <span
                className={mergeClasses(
                  'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold',
                  item.done ? 'bg-emerald-100 text-emerald-800' : urgent ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-900',
                )}
                aria-hidden
              >
                {item.done ? '✓' : '!'}
              </span>
              <span>
                <span className="font-medium text-slate-900">{item.title}. </span>
                <span className="text-slate-600">{item.summary}</span>
                {item.href && !item.done ? (
                  <>
                    {' '}
                    <Link to={item.href} className="font-medium text-sky-700 underline" onClick={dismiss}>
                      Open
                    </Link>
                  </>
                ) : null}
              </span>
            </li>
          ))}
        </ul>

        <div className="grid grid-cols-2 gap-3 px-6 pb-6">
          <Button type="button" variant="outline" onClick={dismiss}>
            Not now
          </Button>
          <Button
            type="button"
            onClick={() => {
              dismiss()
              transitionWizard?.openWizard()
            }}
          >
            Continue
          </Button>
        </div>
      </div>
    </div>
  )
}

export default TransitionNotice
