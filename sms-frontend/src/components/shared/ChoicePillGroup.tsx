import { useEffect, useId, useRef, useState } from 'react'
import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils'

export type ChoiceValue = string | boolean

export type ChoiceOption<T extends ChoiceValue = string> = {
  label: string
  value: T
}

export type ChoiceItem<T extends ChoiceValue = string> =
  | { label: string; value: T; options?: never }
  | { label: string; value?: never; options: ChoiceOption<T>[] }

export type ChoicePillGroupProps<T extends ChoiceValue = string> = {
  items: ChoiceItem<T>[]
  value: T | null
  onChange: (value: T) => void
  name?: string
  className?: string
}

const hasOptions = <T extends ChoiceValue>(
  item: ChoiceItem<T>,
): item is Extract<ChoiceItem<T>, { options: ChoiceOption<T>[] }> =>
  Array.isArray(item.options) && item.options.length > 0

const getSelectedNestedOption = <T extends ChoiceValue>(
  item: ChoiceItem<T>,
  value: T | null,
) => {
  if (value === null || !hasOptions(item)) return null
  return item.options.find((option) => option.value === value) ?? null
}

const isItemSelected = <T extends ChoiceValue>(item: ChoiceItem<T>, value: T | null) => {
  if (value === null) return false
  if (hasOptions(item)) return item.options.some((option) => option.value === value)
  return item.value === value
}

const getButtonLabel = <T extends ChoiceValue>(item: ChoiceItem<T>, value: T | null) => {
  const selectedOption = getSelectedNestedOption(item, value)
  if (selectedOption) return `${item.label} - ${selectedOption.label}`
  return item.label
}

function ChoicePillGroup<T extends ChoiceValue = string>({
  items,
  value,
  onChange,
  name,
  className,
}: ChoicePillGroupProps<T>) {
  const groupId = useId()
  const [openIndex, setOpenIndex] = useState<number | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (openIndex === null) return

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (!target) return
      if (containerRef.current && !containerRef.current.contains(target)) {
        setOpenIndex(null)
      }
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpenIndex(null)
    }

    window.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [openIndex])

  return (
    <div
      ref={containerRef}
      role="radiogroup"
      aria-label={name}
      className={mergeClasses('flex flex-wrap gap-4', className)}
    >
      {items.map((item, index) => {
        const selected = isItemSelected(item, value)
        const isOpen = openIndex === index
        const nested = hasOptions(item)

        if (!nested) {
          return (
            <button
              key={String(item.value)}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => {
                setOpenIndex(null)
                onChange(item.value)
              }}
              className={mergeClasses(
                'rounded-full px-6 py-3 transition',
                selected
                  ? 'bg-slate-800 text-white'
                  : 'bg-slate-200 text-slate-900 hover:bg-slate-300',
              )}
            >
              {item.label}
            </button>
          )
        }

        return (
          <div key={`${groupId}-${item.label}`} className="relative">
            <button
              type="button"
              role="radio"
              aria-checked={selected}
              aria-haspopup="listbox"
              aria-expanded={isOpen}
              onClick={() => setOpenIndex(isOpen ? null : index)}
              className={mergeClasses(
                'inline-flex items-center gap-2 rounded-full px-6 py-3 transition',
                selected
                  ? 'bg-slate-800 text-white'
                  : 'bg-slate-200 text-slate-900 hover:bg-slate-300',
              )}
            >
              <span>{getButtonLabel(item, value)}</span>
              <Icon
                icon="mdi:chevron-down"
                className={mergeClasses('text-lg transition-transform', isOpen && 'rotate-180')}
              />
            </button>

            {isOpen ? (
              <div
                role="listbox"
                className="absolute left-0 z-40 mt-2 w-max min-w-56 max-w-80 rounded-xl border border-slate-200 bg-white p-1 shadow-lg"
              >
                {item.options.map((option) => {
                  const optionSelected = value === option.value
                  return (
                    <button
                      key={String(option.value)}
                      type="button"
                      role="option"
                      aria-selected={optionSelected}
                      onClick={() => {
                        onChange(option.value)
                        setOpenIndex(null)
                      }}
                      className={mergeClasses(
                        'flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition',
                        optionSelected
                          ? 'bg-slate-800 text-white'
                          : 'text-slate-700 hover:bg-slate-100',
                      )}
                    >
                      {option.label}
                    </button>
                  )
                })}
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}

export default ChoicePillGroup
