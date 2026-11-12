import { useState } from 'react'
import { Link } from 'react-router-dom'

type CurriculumNotice = {
  name: string
  version: string
  from_version: string | null
  href: string
  summary: string
}

const dismissKey = (notice: CurriculumNotice) =>
  `curriculum-notice:${notice.version}`

const CurriculumUpdateNotice = ({ notice }: { notice: CurriculumNotice }) => {
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem(dismissKey(notice)) === '1')

  if (dismissed) return null

  return (
    <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-amber-950">
            {notice.name} {notice.version} is available
          </h2>
          <p className="mt-1 text-sm text-amber-950">
            You are on {notice.from_version || 'an older copy'}. {notice.summary}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            sessionStorage.setItem(dismissKey(notice), '1')
            setDismissed(true)
          }}
          className="rounded-xl border border-amber-300 bg-white px-3 py-2 text-sm font-medium text-amber-950"
        >
          Dismiss
        </button>
      </div>
      <Link
        to={notice.href}
        className="mt-3 inline-flex rounded-xl bg-amber-900 px-3 py-2 text-sm font-semibold text-white"
      >
        Review changes
      </Link>
    </section>
  )
}

export default CurriculumUpdateNotice
