import { mergeClasses } from '@/utils/tailwind-merge'
import { Icon } from '@iconify/react'
import Tooltip from './Tooltip'

interface ActionButtonProps {
  icon: string
  label: string
  onClick?: () => void
  className?: string
  tooltipSide?: 'top' | 'bottom'
}

const actionButtonClassName =
  'flex size-8 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm cursor-pointer'

const ActionButton = ({
  icon,
  label,
  onClick,
  className,
  tooltipSide = 'top',
}: ActionButtonProps) => {
  return (
    <Tooltip content={label} side={tooltipSide}>
      <button
        type="button"
        className={mergeClasses(actionButtonClassName, className)}
        onClick={onClick}
        aria-label={label}
      >
        <Icon icon={icon} className="size-4" />
      </button>
    </Tooltip>
  )
}

export default ActionButton
