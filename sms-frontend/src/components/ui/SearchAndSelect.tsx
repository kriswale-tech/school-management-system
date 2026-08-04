import {
  forwardRef,
  useEffect,
  useId,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils'

export type SearchAndSelectOption = {
  value: string
  label: string
  description?: string
  disabled?: boolean
}

type SearchAndSelectBaseProps = {
  options: SearchAndSelectOption[]
  searchValue: string
  onSearchChange: (value: string) => void
  placeholder?: string
  searchPlaceholder?: string
  loading?: boolean
  error?: string
  disabled?: boolean
  emptyMessage?: string
  onBlur?: () => void
  className?: string
  wrapperClassName?: string
  id?: string
}

type SearchAndSelectSingleProps = SearchAndSelectBaseProps & {
  multiple?: false
  value: string
  onChange: (value: string) => void
}

type SearchAndSelectMultiProps = SearchAndSelectBaseProps & {
  multiple: true
  value: string[]
  onChange: (value: string[]) => void
}

export type SearchAndSelectProps = SearchAndSelectSingleProps | SearchAndSelectMultiProps

const isSelected = (props: SearchAndSelectProps, optionValue: string) => {
  if (props.multiple) return props.value.includes(optionValue)
  return props.value === optionValue
}

const getSelectedOptions = (props: SearchAndSelectProps) => {
  const selectedValues = props.multiple ? props.value : props.value ? [props.value] : []
  return selectedValues.map((selectedValue) => {
    const match = props.options.find((option) => option.value === selectedValue)
    return match ?? { value: selectedValue, label: selectedValue }
  })
}

const SearchAndSelect = forwardRef<HTMLButtonElement, SearchAndSelectProps>(
  function SearchAndSelect(props, ref) {
    const {
      options,
      searchValue,
      onSearchChange,
      placeholder = 'Select an option',
      searchPlaceholder = 'Search…',
      loading = false,
      error,
      disabled,
      emptyMessage = 'No results found',
      onBlur,
      className,
      wrapperClassName,
      id: idProp,
    } = props

    const generatedId = useId()
    const id = idProp ?? generatedId
    const listboxId = `${id}-listbox`
    const errorId = `${id}-error`
    const searchId = `${id}-search`
    const containerRef = useRef<HTMLDivElement>(null)
    const searchInputRef = useRef<HTMLInputElement>(null)
    const [isOpen, setIsOpen] = useState(false)

    const selectedOptions = getSelectedOptions(props)
    const hasSelection = selectedOptions.length > 0

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

    useEffect(() => {
      if (!isOpen) return
      searchInputRef.current?.focus()
    }, [isOpen])

    const toggleOpen = () => {
      if (disabled) return
      setIsOpen((open) => !open)
    }

    const handleSelect = (option: SearchAndSelectOption) => {
      if (option.disabled) return

      if (props.multiple) {
        const next = props.value.includes(option.value)
          ? props.value.filter((item) => item !== option.value)
          : [...props.value, option.value]
        props.onChange(next)
        return
      }

      props.onChange(option.value)
      setIsOpen(false)
      onBlur?.()
    }

    const clearSelection = (event: ReactMouseEvent) => {
      event.stopPropagation()
      if (props.multiple) {
        props.onChange([])
      } else {
        props.onChange('')
      }
    }

    const removeChip = (event: ReactMouseEvent, optionValue: string) => {
      event.stopPropagation()
      if (!props.multiple) return
      props.onChange(props.value.filter((item) => item !== optionValue))
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
            if (!isOpen) onBlur?.()
          }}
          className={mergeClasses(
            'flex w-full items-center justify-between gap-3 rounded-lg border border-slate-300 bg-slate-100 px-3 p-4 text-left text-base outline-none transition',
            hasSelection ? 'text-slate-900' : 'text-slate-400',
            'focus:border-slate-400 focus:ring-1 focus:ring-slate-400',
            'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
            error &&
              'border-red-500 focus:border-red-500 focus:ring-red-200/80 aria-invalid:border-red-500',
            className,
          )}
        >
          <span className="min-w-0 flex-1">
            {!hasSelection ? (
              <span className="truncate">{placeholder}</span>
            ) : props.multiple ? (
              <span className="flex flex-wrap gap-1.5">
                {selectedOptions.map((option) => (
                  <span
                    key={option.value}
                    className="inline-flex max-w-full items-center gap-1 rounded-md bg-slate-200 px-2 py-0.5 text-sm text-slate-800"
                  >
                    <span className="truncate">{option.label}</span>
                    <span
                      role="button"
                      tabIndex={-1}
                      aria-label={`Remove ${option.label}`}
                      className="shrink-0 rounded text-slate-500 hover:text-slate-800"
                      onClick={(event) => removeChip(event, option.value)}
                    >
                      <Icon icon="mdi:close" className="size-3.5" aria-hidden />
                    </span>
                  </span>
                ))}
              </span>
            ) : (
              <span className="truncate">{selectedOptions[0]?.label}</span>
            )}
          </span>

          <span className="flex shrink-0 items-center gap-1">
            {hasSelection && !disabled ? (
              <span
                role="button"
                tabIndex={-1}
                aria-label="Clear selection"
                className="rounded p-0.5 text-slate-400 hover:text-slate-700"
                onClick={clearSelection}
              >
                <Icon icon="mdi:close-circle" className="size-4" aria-hidden />
              </span>
            ) : null}
            <Icon
              icon="mdi:chevron-down"
              className={mergeClasses(
                'size-5 text-slate-500 transition-transform',
                isOpen && 'rotate-180',
              )}
              aria-hidden
            />
          </span>
        </button>

        {isOpen ? (
          <div className="absolute top-[calc(100%+0.375rem)] z-50 w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
            <div className="border-b border-slate-100 p-2">
              <label
                htmlFor={searchId}
                className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-2"
              >
                <Icon
                  icon="hugeicons:search-01"
                  className="size-4 shrink-0 text-slate-400"
                  aria-hidden
                />
                <input
                  ref={searchInputRef}
                  id={searchId}
                  type="search"
                  value={searchValue}
                  onChange={(event) => onSearchChange(event.target.value)}
                  placeholder={searchPlaceholder}
                  className="w-full bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                />
                {searchValue ? (
                  <button
                    type="button"
                    aria-label="Clear search"
                    className="shrink-0 text-slate-400 hover:text-slate-700"
                    onClick={() => onSearchChange('')}
                  >
                    <Icon icon="mdi:close" className="size-4" aria-hidden />
                  </button>
                ) : null}
              </label>
            </div>

            <ul
              id={listboxId}
              role="listbox"
              aria-labelledby={id}
              aria-multiselectable={props.multiple || undefined}
              className="max-h-60 overflow-y-auto py-1"
            >
              {loading ? (
                <li className="px-3 py-2.5 text-sm text-slate-500">Loading…</li>
              ) : options.length === 0 ? (
                <li className="px-3 py-2.5 text-sm text-slate-500">{emptyMessage}</li>
              ) : (
                options.map((option) => {
                  const selected = isSelected(props, option.value)

                  return (
                    <li key={option.value} role="presentation">
                      <button
                        type="button"
                        role="option"
                        aria-selected={selected}
                        disabled={option.disabled}
                        onClick={() => handleSelect(option)}
                        className={mergeClasses(
                          'flex w-full items-start justify-between gap-3 px-3 py-2.5 text-left transition',
                          'hover:bg-slate-50 focus-visible:bg-slate-50 focus-visible:outline-none',
                          selected && 'bg-slate-100',
                          option.disabled && 'cursor-not-allowed text-slate-400 hover:bg-white',
                        )}
                      >
                        <span className="min-w-0">
                          <span
                            className={mergeClasses(
                              'block truncate text-base text-slate-700',
                              selected && 'font-medium text-slate-900',
                            )}
                          >
                            {option.label}
                          </span>
                          {option.description ? (
                            <span className="mt-0.5 block truncate text-sm text-slate-500">
                              {option.description}
                            </span>
                          ) : null}
                        </span>
                        {selected ? (
                          <Icon
                            icon="mdi:check"
                            className="mt-0.5 size-4 shrink-0 text-slate-700"
                            aria-hidden
                          />
                        ) : null}
                      </button>
                    </li>
                  )
                })
              )}
            </ul>
          </div>
        ) : null}

        {error ? (
          <p id={errorId} role="alert" className="text-sm text-red-600">
            {error}
          </p>
        ) : null}
      </div>
    )
  },
)

SearchAndSelect.displayName = 'SearchAndSelect'

export default SearchAndSelect
