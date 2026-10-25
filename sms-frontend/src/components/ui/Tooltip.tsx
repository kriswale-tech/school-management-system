import { type ReactNode, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { mergeClasses } from '@/utils'

type TooltipSide = 'top' | 'bottom'

export type TooltipProps = {
  content: string
  children: ReactNode
  side?: TooltipSide
  className?: string
  /** Allow wrapping for longer help text (default single line). */
  multiline?: boolean
}

const Tooltip = ({
  content,
  children,
  side = 'top',
  className,
  multiline = false,
}: TooltipProps) => {
  const triggerRef = useRef<HTMLSpanElement>(null)
  const [visible, setVisible] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })

  const place = () => {
    const trigger = triggerRef.current
    if (!trigger || !content.trim()) return false

    const rect = trigger.getBoundingClientRect()
    setPosition({
      top: side === 'top' ? rect.top - 8 : rect.bottom + 8,
      left: rect.left + rect.width / 2,
    })
    return true
  }

  const show = () => {
    if (!place()) return
    setVisible(true)
  }

  const hide = () => setVisible(false)

  const toggle = () => {
    if (visible) {
      hide()
      return
    }
    show()
  }

  return (
    <>
      <span
        ref={triggerRef}
        className={mergeClasses('inline-flex', className)}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocusCapture={show}
        onBlurCapture={hide}
        onClick={toggle}
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
              className={mergeClasses(
                'pointer-events-none z-[9999] rounded-md bg-slate-900/95 px-2.5 py-1.5 text-xs font-medium text-white shadow-md',
                multiline
                  ? 'max-w-xs whitespace-normal text-left leading-snug'
                  : 'max-w-xs whitespace-nowrap',
              )}
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
