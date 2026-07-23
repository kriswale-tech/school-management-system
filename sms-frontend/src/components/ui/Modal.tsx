import { useEffect, useId, type ReactNode } from 'react'
import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils'

interface ModalProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  className?: string
  scrollable?: boolean
}

const Modal = ({ open, title, onClose, children, className, scrollable = false }: ModalProps) => {
  const titleId = useId()

  useEffect(() => {
    if (!open) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Close modal"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={mergeClasses(
          'relative w-full max-w-md rounded-lg bg-white p-6 shadow-xl',
          scrollable && 'flex max-h-[95vh] flex-col overflow-hidden',
          className,
        )}
      >
        <div className="mb-4 flex shrink-0 items-start justify-between gap-4">
          <h2 id={titleId} className="text-lg font-medium text-slate-900">
            {title}
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
          >
            <Icon icon="hugeicons:cancel-01" className="size-5" />
          </button>
        </div>

        {scrollable ? (
          <div className="min-h-0 flex-1 overflow-y-auto pr-1">{children}</div>
        ) : (
          children
        )}
      </div>
    </div>
  )
}

export default Modal
