import { forwardRef, useEffect, useId, useRef, useState } from 'react'
import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils'

export type SelectOption = {
  value: string
  label: string
  disabled?: boolean
}

export type SelectFieldProps = {
  options: SelectOption[]
  value?: string
  onChange?: (_value: string) => void
  onBlur?: () => void
  name?: string
  placeholder?: string
  /** Shown under the field; set from RHF e.g. `errors.term?.message` */
  error?: string
  disabled?: boolean
  className?: string
  /** Classes for the outer wrapper (stack of control + error) */
  wrapperClassName?: string
  id?: string
}

const SelectField = forwardRef<HTMLButtonElement, SelectFieldProps>(function SelectField(
  {
    options,
    value = '',
    onChange,
    onBlur,
    placeholder = 'Select an option',
    error,
    disabled,
    className,
    wrapperClassName,
    id: idProp,
  },
  ref,
) {
  const generatedId = useId()
  const id = idProp ?? generatedId
  const listboxId = `${id}-listbox`
  const errorId = `${id}-error`
  const containerRef = useRef<HTMLDivElement>(null)
  const [isOpen, setIsOpen] = useState(false)

  const selectedOption = options.find((option) => option.value === value)

  useEffect(() => {
    if (!isOpen) return

    const handlePointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
        onBlur?.()
      }
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
        onBlur?.()
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, onBlur])

  const handleSelect = (option: SelectOption) => {
    if (option.disabled) return

    onChange?.(option.value)
    setIsOpen(false)
    onBlur?.()
  }

  const toggleOpen = () => {
    if (disabled) return
    setIsOpen((open) => !open)
  }

  return (
    <div
      ref={containerRef}
      className={mergeClasses('relative flex flex-col gap-1.5', wrapperClassName)}
    >
      <button
        ref={ref}
        id={id}
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        onClick={toggleOpen}
        onBlur={() => {
          if (!isOpen) {
            onBlur?.()
          }
        }}
        className={mergeClasses(
          'flex w-full items-center justify-between gap-3 rounded-lg border border-slate-300 bg-slate-100 px-3 p-4 text-left text-base outline-none transition',
          selectedOption ? 'text-slate-900' : 'text-slate-400',
          'focus:border-slate-400 focus:ring-1 focus:ring-slate-400',
          'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
          error &&
            'border-red-500 focus:border-red-500 focus:ring-red-200/80 aria-invalid:border-red-500',
          className,
        )}
      >
        <span className="truncate">{selectedOption?.label ?? placeholder}</span>
        <Icon
          icon="mdi:chevron-down"
          className={mergeClasses(
            'size-5 shrink-0 text-slate-500 transition-transform',
            isOpen && 'rotate-180',
          )}
          aria-hidden
        />
      </button>

      {isOpen ? (
        <ul
          id={listboxId}
          role="listbox"
          aria-labelledby={id}
          className="absolute top-[calc(100%+0.375rem)] z-50 max-h-60 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
        >
          {options.length === 0 ? (
            <li className="px-3 py-2.5 text-sm text-slate-500">No options available</li>
          ) : (
            options.map((option) => {
              const isSelected = option.value === value

              return (
                <li key={option.value} role="presentation">
                  <button
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    disabled={option.disabled}
                    onClick={() => handleSelect(option)}
                    className={mergeClasses(
                      'flex w-full items-center justify-between px-3 py-2.5 text-left text-base text-slate-700 transition',
                      'hover:bg-slate-50 focus-visible:bg-slate-50 focus-visible:outline-none',
                      isSelected && 'bg-slate-100 font-medium text-slate-900',
                      option.disabled && 'cursor-not-allowed text-slate-400 hover:bg-white',
                    )}
                  >
                    <span className="truncate">{option.label}</span>
                    {isSelected ? (
                      <Icon icon="mdi:check" className="size-4 shrink-0 text-slate-700" aria-hidden />
                    ) : null}
                  </button>
                </li>
              )
            })
          )}
        </ul>
      ) : null}

      {error ? (
        <p id={errorId} role="alert" className="text-sm text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  )
})

SelectField.displayName = 'SelectField'

export default SelectField
