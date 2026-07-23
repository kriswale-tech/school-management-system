import { Icon } from '@iconify/react'
import type { PaginatedResponse } from '@/types/generalTypes'
import { mergeClasses } from '@/utils'

export type PaginationMeta = Pick<
  PaginatedResponse<unknown>,
  'page' | 'total_pages' | 'has_next' | 'has_previous' | 'start_index' | 'end_index' | 'count'
>

export type PaginationProps = {
  pagination: PaginationMeta
  onPageChange: (page: number) => void
  isLoading?: boolean
  className?: string
}

const Pagination = ({ pagination, onPageChange, isLoading = false, className }: PaginationProps) => {
  const { page, total_pages, has_next, has_previous, start_index, end_index, count } = pagination

  if (count === 0) return null

  return (
    <div
      className={mergeClasses(
        'flex flex-col gap-3 border-t border-slate-200 px-4 py-3 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between',
        className,
      )}
    >
      <p>
        Showing {start_index}–{end_index} of {count}
      </p>

      <div className="flex items-center gap-3">
        <span className="text-slate-500">
          Page {page} of {total_pages}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Previous page"
            disabled={!has_previous || isLoading}
            onClick={() => onPageChange(page - 1)}
            className="flex size-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Icon icon="mdi:chevron-left" className="text-xl" />
          </button>
          <button
            type="button"
            aria-label="Next page"
            disabled={!has_next || isLoading}
            onClick={() => onPageChange(page + 1)}
            className="flex size-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Icon icon="mdi:chevron-right" className="text-xl" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default Pagination
