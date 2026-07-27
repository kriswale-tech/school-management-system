import { useEffect, useId, useRef, type ReactNode } from 'react'
import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils'

interface SideSliderProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  className?: string
}

const SideSlider = ({ open, title, onClose, children, className }: SideSliderProps) => {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const panel = panelRef.current
    if (!open || !panel) return

    panel.classList.add('translate-x-full')
    panel.classList.remove('translate-x-0')

    const frame = requestAnimationFrame(() => {
      panel.classList.remove('translate-x-full')
      panel.classList.add('translate-x-0')
    })

    return () => cancelAnimationFrame(frame)
  }, [open])

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
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        aria-label="Close panel"
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={mergeClasses(
          'absolute inset-y-0 right-0 flex w-[40vw] min-w-80 max-w-xl translate-x-full flex-col bg-white shadow-xl',
          'transition-transform duration-300 ease-out',
          className,
        )}
      >
        <div className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 px-6 py-4">
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

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">{children}</div>
      </div>
    </div>
  )
}

export default SideSlider
