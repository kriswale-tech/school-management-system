import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import { mergeClasses } from '@/utils'

export type EmptyStateProps = {
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  icon?: string
  className?: string
  image?: string
  /** When true, skips form-field-wrapper (for use inside TableWrapper). */
  unstyled?: boolean
}

const EmptyState = ({
  title,
  description,
  actionLabel,
  onAction,
  icon = 'hugeicons:inbox',
  image,
  className,
  unstyled = false,
}: EmptyStateProps) => {
  const showAction = Boolean(actionLabel && onAction)

  return (
    <div
      className={mergeClasses(
        'flex flex-col items-center justify-center py-12 text-center',
        !unstyled && 'form-field-wrapper',
        className,
      )}
    >
      <div className="mb-4 ">
        {image ? (
          <img src={image} alt={title} className="" />
        ) : (
          <Icon icon={icon} className="size-16" />
        )}
      </div>

      <h3 className="text-lg font-medium text-slate-900">{title}</h3>

      {description ? <p className="mt-2 max-w-sm text-base text-slate-500">{description}</p> : null}

      {showAction ? (
        <Button type="button" className="mt-6 w-fit px-6" onClick={onAction}>
          <Icon
            icon="hugeicons:plus-sign"
            className="size-4 bg-white text-black rounded-full p-0.5"
          />{' '}
          <span>{actionLabel}</span>
        </Button>
      ) : null}
    </div>
  )
}

export default EmptyState
