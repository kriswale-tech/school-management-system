import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils'

const DEFAULT_SIZE = 28

export type LoadingSpinnerProps = {
  size?: number
  className?: string
}

const LoadingSpinner = ({ size = DEFAULT_SIZE, className }: LoadingSpinnerProps) => {
  return (
    <Icon
      icon="si:spinner-fill"
      width={size}
      height={size}
      role="status"
      aria-label="Loading"
      className={mergeClasses('animate-spin text-slate-600', className)}
    />
  )
}

export default LoadingSpinner
