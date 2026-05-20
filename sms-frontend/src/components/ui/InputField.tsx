import { forwardRef, useId } from 'react'
import { mergeClasses } from '@/utils'
export type InputFieldProps = React.ComponentProps<'input'> & {
  /** Shown under the field; set from RHF e.g. `errors.email?.message` */
  error?: string
  className?: string
  /** Classes for the outer wrapper (stack of label + input + error) */
  wrapperClassName?: string
}

const InputField = forwardRef<HTMLInputElement, InputFieldProps>(function InputField(
  { error, className, wrapperClassName, id: idProp, disabled, ...props },
  ref,
) {
  const generatedId = useId()
  const id = idProp ?? generatedId
  const errorId = `${id}-error`

  return (
    <div className={mergeClasses('flex flex-col gap-1.5', wrapperClassName)}>
      <input
        ref={ref}
        id={id}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className={mergeClasses(
          'w-full rounded-lg border border-slate-300 bg-slate-100 px-3 p-4 text-base text-slate-900 outline-none transition',
          'placeholder:text-slate-400',
          'focus:border-slate-400 focus:ring-1 focus:ring-slate-400',
          'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
          error &&
            'border-red-500 focus:border-red-500 focus:ring-red-200/80 aria-invalid:border-red-500',
          className,
        )}
        {...props}
      />
      {error ? (
        <p id={errorId} role="alert" className="text-sm text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  )
})

InputField.displayName = 'InputField'

export default InputField
