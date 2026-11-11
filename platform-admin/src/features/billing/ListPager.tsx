import { BILLING_PAGE_SIZE } from './services'

export function ListPager({
  count,
  page,
  onPage,
}: {
  count: number
  page: number
  onPage: (page: number) => void
}) {
  if (count <= BILLING_PAGE_SIZE) return null
  const pages = Math.max(1, Math.ceil(count / BILLING_PAGE_SIZE))
  const from = (page - 1) * BILLING_PAGE_SIZE + 1
  const to = Math.min(count, page * BILLING_PAGE_SIZE)
  return (
    <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-[var(--color-ink)]/60">
        {from}–{to} of {count}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className="rounded-lg border border-[var(--color-line)] bg-white px-3 py-1.5 text-xs font-medium disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-xs text-[var(--color-ink)]/60">
          Page {page} of {pages}
        </span>
        <button
          type="button"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          className="rounded-lg border border-[var(--color-line)] bg-white px-3 py-1.5 text-xs font-medium disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
