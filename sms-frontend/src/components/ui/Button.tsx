import type { ButtonHTMLAttributes, ReactNode } from 'react'
import LoadingSpinner from './LoadingSpinner'
import { mergeClasses } from '@/utils'

type ButtonVariant = 'outline' | 'solid' | 'solidReverse' | 'ghost'
type ButtonColor = 'slate' | 'red'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode
  variant?: ButtonVariant
  color?: ButtonColor
  loading?: boolean
  loadingText?: string
}

const colorVariantClasses: Record<ButtonColor, Record<ButtonVariant, string>> = {
  slate: {
    outline:
      'border border-slate-900 bg-transparent text-slate-900 enabled:hover:bg-slate-900 enabled:hover:text-white',
    solid:
      'border border-slate-900 bg-slate-900 text-white enabled:hover:bg-slate-800 enabled:hover:border-slate-800',
    solidReverse:
      'border border-slate-900 bg-white text-slate-900 enabled:hover:bg-slate-900 enabled:hover:text-white',
    ghost: 'border border-transparent bg-slate-200 text-slate-900 enabled:hover:bg-slate-300',
  },
  red: {
    outline:
      'border border-red-600 bg-transparent text-red-600 enabled:hover:bg-red-600 enabled:hover:text-white',
    solid:
      'border border-red-600 bg-red-600 text-white enabled:hover:bg-red-700 enabled:hover:border-red-700',
    solidReverse:
      'border border-red-600 bg-white text-red-600 enabled:hover:bg-red-600 enabled:hover:text-white',
    ghost: 'border border-transparent bg-red-100 text-red-700 enabled:hover:bg-red-200',
  },
}

const Button = ({
  children,
  variant = 'solid',
  color = 'slate',
  className,
  type = 'button',
  loading = false,
  loadingText = 'Loading',
  disabled,
  ...props
}: ButtonProps) => {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading}
      className={mergeClasses(
        'w-full rounded-lg bg-transparent px-4 py-3 text-center text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-60',
        'inline-flex items-center justify-center gap-2 cursor-pointer',
        colorVariantClasses[color][variant],
        className,
      )}
      {...props}
    >
      {loading ? (
        <>
          <LoadingSpinner size={16} className="text-current" />
          {loadingText}
        </>
      ) : (
        children
      )}
    </button>
  )
}

export default Button
