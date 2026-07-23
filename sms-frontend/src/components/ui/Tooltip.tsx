import { type ReactNode, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { mergeClasses } from '@/utils'

type TooltipSide = 'top' | 'bottom'

export type TooltipProps = {
  content: string
  children: ReactNode
  side?: TooltipSide
  className?: string
}

const Tooltip = ({ content, children, side = 'top', className }: TooltipProps) => {
  const triggerRef = useRef<HTMLSpanElement>(null)
  const [visible, setVisible] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })

  const show = () => {
    const trigger = triggerRef.current
    if (!trigger || !content.trim()) return

    const rect = trigger.getBoundingClientRect()
    setPosition({
      top: side === 'top' ? rect.top - 8 : rect.bottom + 8,
      left: rect.left + rect.width / 2,
    })
    setVisible(true)
  }

  const hide = () => setVisible(false)

  return (
    <>
      <span
        ref={triggerRef}
        className={mergeClasses('inline-flex', className)}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocusCapture={show}
        onBlurCapture={hide}
      >
        {children}
      </span>

      {visible
        ? createPortal(
            <span
              role="tooltip"
              style={{
                position: 'fixed',
                top: position.top,
                left: position.left,
                transform: side === 'top' ? 'translate(-50%, -100%)' : 'translate(-50%, 0)',
              }}
              className="pointer-events-none z-[9999] max-w-xs whitespace-nowrap rounded-md bg-slate-900/95 px-2.5 py-1 text-xs font-medium text-white shadow-md"
            >
              {content}
            </span>,
            document.body,
          )
        : null}
    </>
  )
}

export default Tooltip
