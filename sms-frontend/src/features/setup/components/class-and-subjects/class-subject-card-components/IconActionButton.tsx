import { Icon } from '@iconify/react'

const IconActionButton = ({
  icon,
  label,
  variant = 'default',
  onClick,
}: {
  icon: string
  label: string
  variant?: 'default' | 'danger'
  onClick?: () => void
}) => {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={
        variant === 'danger'
          ? 'rounded p-1 text-red-600 hover:bg-red-50 hover:text-red-700'
          : 'rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900'
      }
    >
      <Icon icon={icon} className="size-3.5" />
    </button>
  )
}

export default IconActionButton
