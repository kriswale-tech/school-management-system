import { Modal } from '@/components/ui'
import { mergeClasses } from '@/utils'
import type { CorrectionInboxItem } from '@/features/classes/assessment/types'

type CorrectionsInboxProps = {
  open: boolean
  onClose: () => void
  items: CorrectionInboxItem[]
  title?: string
  emptyLabel?: string
  onOpenItem: (_item: CorrectionInboxItem) => void
}

const kindLabel = (item: CorrectionInboxItem) => {
  if (item.kind === 'reopen_request' && item.status === 'open') return 'Reopen requested'
  if (item.kind === 'reopen') return 'Reopened'
  if (item.status === 'applied') return 'Needs correction'
  if (item.kind === 'reject') return 'Sent back'
  return item.kind
}

const CorrectionsInbox = ({
  open,
  onClose,
  items,
  title = 'Corrections',
  emptyLabel = 'No open corrections right now.',
  onOpenItem,
}: CorrectionsInboxProps) => {
  const count = items.length

  return (
    <Modal
      open={open}
      title={`${title} (${count})`}
      onClose={onClose}
      scrollable
      className="max-w-lg"
    >
      {count === 0 ? (
        <p className="text-sm text-slate-500">{emptyLabel}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => {
                  onOpenItem(item)
                  onClose()
                }}
                className={mergeClasses(
                  'w-full rounded-md border border-orange-200 bg-orange-50/40 px-3 py-2 text-left',
                  'hover:border-orange-300 hover:bg-orange-50 cursor-pointer',
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">
                      {item.student_name}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {item.class_name}
                      {item.student_code ? ` · ${item.student_code}` : ''}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-md bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-800">
                    {kindLabel(item)}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-xs text-slate-600">{item.reason}</p>
                <p className="mt-1 truncate text-[11px] text-slate-500">
                  {item.subjects.map((subject) => subject.subject_label).join(', ')}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  )
}

export default CorrectionsInbox
