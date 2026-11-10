import { forwardRef, type ReactNode, useId } from 'react'
import { mergeClasses } from '@/utils'

export type ToggleFieldProps = Omit<React.ComponentProps<'input'>, 'type'> & {
  children?: ReactNode
  error?: string
  className?: string
  wrapperClassName?: string
  labelClassName?: string
}

const ToggleField = forwardRef<HTMLInputElement, ToggleFieldProps>(function ToggleField(
  { children, error, className, wrapperClassName, labelClassName, id: idProp, disabled, ...props },
  ref,
) {
  const generatedId = useId()
  const id = idProp ?? generatedId
  const errorId = `${id}-error`

  return (
    <div className={mergeClasses('flex flex-col gap-1.5', wrapperClassName)}>
      <label
        htmlFor={id}
        className={mergeClasses(
          'inline-flex w-full items-center justify-between gap-3 text-slate-700',
          disabled && 'cursor-not-allowed text-slate-400',
          labelClassName,
        )}
      >
        {children ? <span className="min-w-0 flex-1 leading-5">{children}</span> : null}
        <span className="relative inline-flex h-6 w-11 shrink-0 items-center">
          <input
            ref={ref}
            id={id}
            type="checkbox"
            role="switch"
            disabled={disabled}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
            className={mergeClasses(
              'peer absolute inset-0 z-10 size-full cursor-pointer appearance-none opacity-0',
              'disabled:cursor-not-allowed',
              className,
            )}
            {...props}
          />
          <span
            aria-hidden
            className={mergeClasses(
              'pointer-events-none absolute inset-0 rounded-full border transition',
              'border-slate-300 bg-slate-200',
              'peer-checked:border-slate-900 peer-checked:bg-slate-900',
              'peer-focus-visible:ring-2 peer-focus-visible:ring-slate-400/40',
              'peer-disabled:border-slate-200 peer-disabled:bg-slate-100',
              error && 'border-red-500',
            )}
          />
          <span
            aria-hidden
            className={mergeClasses(
              'pointer-events-none absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow-sm transition-transform',
              'peer-checked:translate-x-5',
              'peer-disabled:bg-slate-50',
            )}
          />
        </span>
      </label>

      {error ? (
        <p id={errorId} role="alert" className="text-sm text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  )
})

ToggleField.displayName = 'ToggleField'

export default ToggleField
