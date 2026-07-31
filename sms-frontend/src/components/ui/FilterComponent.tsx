import { Icon } from '@iconify/react'
import type { SelectHTMLAttributes } from 'react'
import { mergeClasses } from '@/utils/tailwind-merge'

export type FilterOptionValue = string | number | boolean

export type FilterOption = {
  key?: string
  value: FilterOptionValue
  label: string
}

export type FilterSelection = FilterOptionValue | ''

type FilterComponentProps = {
  filterName: string
  filterKey?: string
  options: FilterOption[]
  value?: FilterSelection
  onChange?: (value: FilterSelection) => void
  className?: string
  selectClassName?: string
  placeholder?: string
} & Omit<SelectHTMLAttributes<HTMLSelectElement>, 'value' | 'onChange'>

const serializeFilterValue = (value: FilterOptionValue) => String(value)

const parseFilterValue = (serialized: string, options: FilterOption[]): FilterSelection => {
  if (serialized === '') {
    return ''
  }

  const option = options.find((item) => serializeFilterValue(item.value) === serialized)

  return option?.value ?? serialized
}

const FilterComponent = ({
  filterName,
  filterKey,
  options,
  value = '',
  onChange,
  className,
  selectClassName,
  placeholder = 'All',
  ...selectProps
}: FilterComponentProps) => {
  const selectId = selectProps.id ?? filterKey ?? filterName
  const serializedValue = value === '' ? '' : serializeFilterValue(value)

  return (
    <div
      className={mergeClasses(
        'flex min-w-28 overflow-hidden border-slate-200 rounded-sm border text-slate-700 text-sm',
        className,
      )}
    >
      <div className="relative min-w-28 flex-1">
        <select
          id={selectId}
          value={serializedValue}
          onChange={(event) => onChange?.(parseFilterValue(event.target.value, options))}
          className={mergeClasses(
            'select h-full w-full p-2 appearance-none rounded-none border-0 bg-transparent pr-9 pl-3 shadow-none focus:outline-none',
            selectClassName,
          )}
          style={{ backgroundImage: 'none' }}
          aria-label={filterName}
          {...selectProps}
        >
          <option value="">{placeholder}</option>
          {options.map((option) => (
            <option
              key={`${option.key ?? filterKey ?? filterName}-${serializeFilterValue(option.value)}`}
              value={serializeFilterValue(option.value)}
            >
              {option.label}
            </option>
          ))}
        </select>

        <Icon
          icon="hugeicons:arrow-down-01"
          className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-base-content/50"
          aria-hidden
        />
      </div>
    </div>
  )
}

export default FilterComponent
