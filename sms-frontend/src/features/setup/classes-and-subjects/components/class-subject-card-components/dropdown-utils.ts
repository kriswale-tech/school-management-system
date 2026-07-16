import { useEffect, useRef, useState, type CSSProperties, type RefObject } from 'react'

export type DropdownAlign = 'left' | 'right'

const DROPDOWN_WIDTH = 224 // w-56
const VIEWPORT_PADDING = 8

/** Button near the right → hang left (`right`). Button near the left → hang right (`left`). */
export const getDropdownAlign = (element: HTMLElement | null): DropdownAlign => {
  if (!element) return 'right'
  const rect = element.getBoundingClientRect()
  const spaceLeft = rect.left
  const spaceRight = window.innerWidth - rect.right
  return spaceLeft >= spaceRight ? 'right' : 'left'
}

export const getDropdownPanelStyle = (
  trigger: HTMLElement | null,
  align: DropdownAlign,
): CSSProperties => {
  if (!trigger) return {}

  const rect = trigger.getBoundingClientRect()
  const top = rect.bottom + 4
  const maxLeft = window.innerWidth - DROPDOWN_WIDTH - VIEWPORT_PADDING

  if (align === 'right') {
    const left = Math.min(Math.max(VIEWPORT_PADDING, rect.right - DROPDOWN_WIDTH), maxLeft)
    return {
      position: 'fixed',
      top,
      left,
      width: DROPDOWN_WIDTH,
      zIndex: 40,
    }
  }

  const left = Math.min(Math.max(VIEWPORT_PADDING, rect.left), maxLeft)
  return {
    position: 'fixed',
    top,
    left,
    width: DROPDOWN_WIDTH,
    zIndex: 40,
  }
}

export const useClickOutside = (
  containerRef: RefObject<HTMLDivElement | null>,
  isOpen: boolean,
  onClose: () => void,
) => {
  useEffect(() => {
    if (!isOpen) return

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (!target) return
      if (containerRef.current && !containerRef.current.contains(target)) {
        onClose()
      }
    }

    window.addEventListener('pointerdown', onPointerDown)
    return () => window.removeEventListener('pointerdown', onPointerDown)
  }, [containerRef, isOpen, onClose])
}

export const useAnchoredDropdown = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [align, setAlign] = useState<DropdownAlign>('right')
  const [panelStyle, setPanelStyle] = useState<CSSProperties>({})
  const containerRef = useRef<HTMLDivElement | null>(null)

  useClickOutside(containerRef, isOpen, () => setIsOpen(false))

  const toggleOpen = () => {
    if (!isOpen && containerRef.current) {
      const nextAlign = getDropdownAlign(containerRef.current)
      setAlign(nextAlign)
      setPanelStyle(getDropdownPanelStyle(containerRef.current, nextAlign))
    }
    setIsOpen((open) => !open)
  }

  const close = () => setIsOpen(false)

  return {
    isOpen,
    align,
    panelStyle,
    containerRef,
    toggleOpen,
    close,
    setIsOpen,
  }
}
