import type { ReactNode } from 'react'
import { Icon } from '@iconify/react'
import { EmptyState } from '@/components/shared'
import { Tooltip } from '@/components/ui'

type ChartCardProps = {
  title: string
  description?: string
  /** Explains what this chart measures — shown via the info icon. */
  info?: string
  children: ReactNode
  empty?: boolean
  emptyTitle?: string
  emptyDescription?: string
  /** Local filters / actions for this card only. */
  actions?: ReactNode
  /** Override default chart height wrapper. */
  bodyClassName?: string
}

const ChartCard = ({
  title,
  description,
  info,
  children,
  empty = false,
  emptyTitle = 'No data yet',
  emptyDescription = 'Publish subject results to see insights here.',
  actions,
  bodyClassName = 'h-80 w-full',
}: ChartCardProps) => {
  return (
    <div className="bg-white p-4 custom-shadow-md">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
            {info ? (
              <Tooltip content={info} side="bottom" multiline>
                <button
                  type="button"
                  aria-label={`About ${title}`}
                  className="inline-flex rounded p-0.5 text-slate-400 transition-colors hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
                >
                  <Icon icon="hugeicons:information-circle" className="size-4" />
                </button>
              </Tooltip>
            ) : null}
          </div>
          {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {empty ? (
        <EmptyState title={emptyTitle} description={emptyDescription} unstyled className="py-8" />
      ) : (
        <div className={bodyClassName}>{children}</div>
      )}
    </div>
  )
}

export default ChartCard
