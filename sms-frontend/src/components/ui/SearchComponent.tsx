import { Icon } from '@iconify/react'
import { useEffect, useState, type InputHTMLAttributes } from 'react'
import { mergeClasses } from '@/utils/tailwind-merge'

type SearchComponentProps = {
  value?: string
  onChange?: (value: string) => void
  debounceMs?: number
  className?: string
  inputClassName?: string
  placeholder?: string
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'>

const SearchComponent = ({
  value = '',
  onChange,
  debounceMs = 800,
  className,
  inputClassName,
  placeholder = 'Search...',
  ...inputProps
}: SearchComponentProps) => {
  const [localValue, setLocalValue] = useState(value)

  useEffect(() => {
    setLocalValue(value)
  }, [value])

  useEffect(() => {
    if (localValue === value) return

    const timer = window.setTimeout(() => {
      onChange?.(localValue)
    }, debounceMs)

    return () => window.clearTimeout(timer)
  }, [localValue, value, debounceMs, onChange])

  const hasValue = localValue.length > 0

  return (
    <label
      className={mergeClasses(
        'input w-full max-w-sm border border-slate-200 rounded-sm flex items-center gap-2 px-4 py-2',
        className,
      )}
    >
      <Icon icon="hugeicons:search-01" className="size-5 shrink-0 opacity-50" aria-hidden />
      <input
        type="search"
        name="search"
        id="search"
        value={localValue}
        onChange={(event) => setLocalValue(event.target.value)}
        placeholder={placeholder}
        className={mergeClasses(
          'grow text-sm outline-none focus:outline-none focus:ring-0 focus:ring-transparent',
          inputClassName,
        )}
        {...inputProps}
      />
      {hasValue && (
        <button
          type="button"
          className="btn btn-ghost btn-xs btn-square shrink-0"
          onClick={() => {
            setLocalValue('')
            onChange?.('')
          }}
          aria-label="Clear search"
        >
          <Icon icon="hugeicons:cancel-01" className="size-4 opacity-60" />
        </button>
      )}
    </label>
  )
}

export default SearchComponent
