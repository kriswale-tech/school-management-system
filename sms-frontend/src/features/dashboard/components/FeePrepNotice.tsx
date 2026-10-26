import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks'
import { getNextTermFeePrep } from '@/features/fees/services'
import { FEE_NEXT_TERM_PREP_QUERY_KEY } from '@/features/fees/utils'
import { mergeClasses } from '@/utils'

const formatEndDate = (value: string) => {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

type FeePrepNoticeProps = {
  /** Inline banner on the dashboard / fees desk instead of a modal. */
  variant?: 'banner' | 'modal'
}

const FeePrepNotice = ({ variant = 'banner' }: FeePrepNoticeProps) => {
  const canManageFees = useCan(Capability.FEES_MANAGE_SETTINGS)
  const [dismissed, setDismissed] = useState(false)

  const { data } = useQuery({
    queryKey: [FEE_NEXT_TERM_PREP_QUERY_KEY],
    queryFn: getNextTermFeePrep,
    enabled: canManageFees,
    staleTime: 60_000,
  })

  const open = Boolean(
    canManageFees
    && data?.visible
    && !data.done
    && data.term_ends_on
    && !dismissed,
  )

  if (!open || !data?.term_ends_on) return null

  const urgent = data.urgency === 'red'
  const ended = (data.days_remaining ?? 0) < 0
  const headline = ended
    ? `Term ended on ${formatEndDate(data.term_ends_on)}`
    : data.days_remaining === 0
      ? 'This term ends today'
      : `This term ends on ${formatEndDate(data.term_ends_on)}`

  const body = (
    <>
      <div className={mergeClasses('px-5 py-4 text-white', urgent ? 'bg-red-700' : 'bg-amber-600')}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-white/80">
              Next term fees
            </p>
            <h2 className="mt-1 text-base font-semibold leading-snug">{headline}</h2>
            {data.next_term_label ? (
              <p className="mt-1 text-sm text-white/90">Prepare: {data.next_term_label}</p>
            ) : null}
          </div>
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/15">
            <Icon icon="hugeicons:money-bag-02" className="text-xl" />
          </span>
        </div>
      </div>
      <div className="px-5 py-4 space-y-4">
        <p className="text-sm text-slate-600">{data.summary}</p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={() => setDismissed(true)}>
            Not now
          </Button>
          <Link to={data.href} onClick={() => setDismissed(true)}>
            <Button type="button">Set up fees</Button>
          </Link>
        </div>
      </div>
    </>
  )

  if (variant === 'modal') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <button
          type="button"
          aria-label="Dismiss fee prep notice"
          className="absolute inset-0 bg-slate-900/50"
          onClick={() => setDismissed(true)}
        />
        <div
          role="dialog"
          aria-modal="true"
          className="relative w-full max-w-md overflow-hidden rounded-2xl bg-white shadow-2xl"
        >
          {body}
        </div>
      </div>
    )
  }

  return (
    <div className="mb-4 overflow-hidden rounded-xl border border-slate-200 bg-white custom-shadow-md">
      {body}
    </div>
  )
}

export default FeePrepNotice
