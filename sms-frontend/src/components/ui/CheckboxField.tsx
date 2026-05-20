import { forwardRef, type ReactNode, useId } from 'react'
import { mergeClasses } from '@/utils'

export type CheckboxFieldProps = Omit<React.ComponentProps<'input'>, 'type'> & {
  children?: ReactNode
  /** Shown under the field; set from RHF e.g. `errors.terms?.message` */
  error?: string
  className?: string
  /** Classes for the outer wrapper (stack of control + error) */
  wrapperClassName?: string
  labelClassName?: string
}

const CheckboxField = forwardRef<HTMLInputElement, CheckboxFieldProps>(function CheckboxField(
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
          'inline-flex w-fit items-start gap-2 text-slate-700',
          disabled && 'cursor-not-allowed text-slate-400',
          labelClassName,
        )}
      >
        <input
          ref={ref}
          id={id}
          type="checkbox"
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={mergeClasses(
            'size-5 shrink-0 cursor-pointer appearance-none rounded-[6px] border border-slate-400 bg-white transition',
            'grid place-content-center before:h-3 before:w-3 before:origin-center before:scale-0 before:transition before:content-[""]',
            'checked:border-black checked:bg-black checked:before:scale-100',
            'checked:before:[clip-path:polygon(14%_44%,0_65%,50%_100%,100%_16%,80%_0%,43%_62%)] checked:before:bg-white',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/25',
            'disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-100',
            error && 'border-red-500',
            className,
          )}
          {...props}
        />
        {children ? <span className="leading-5">{children}</span> : null}
      </label>

      {error ? (
        <p id={errorId} role="alert" className="text-sm text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  )
})

CheckboxField.displayName = 'CheckboxField'

export default CheckboxField
