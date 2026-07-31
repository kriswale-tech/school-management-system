import { Icon } from '@iconify/react'
import { useState } from 'react'
import { mergeClasses } from '@/utils'
import type { LevelOption } from '../types'

type LevelClassPickerProps = {
  levels: LevelOption[]
  value: string
  onChange: (streamId: string) => void
  error?: string
}

const LevelClassPicker = ({ levels, value, onChange, error }: LevelClassPickerProps) => {
  const [openLevelId, setOpenLevelId] = useState<string | null>(null)

  const resolvedOpenLevelId =
    openLevelId && levels.some((level) => level.id === openLevelId)
      ? openLevelId
      : (levels[0]?.id ?? null)

  if (!levels.length) {
    return (
      <p className="rounded-xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
        No classes available for the active term.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {levels.map((level) => {
        const isOpen = resolvedOpenLevelId === level.id
        const hasSelectedClass = level.classes.some((item) => item.id === value)

        return (
          <div
            key={level.id}
            className={mergeClasses(
              'overflow-hidden rounded-xl border border-slate-200 bg-white',
              hasSelectedClass && 'border-slate-400',
            )}
          >
            <button
              type="button"
              onClick={() => setOpenLevelId(isOpen ? null : level.id)}
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
              aria-expanded={isOpen}
            >
              <div>
                <p className="font-medium text-slate-900">{level.name}</p>
                <p className="text-xs text-slate-500">
                  {level.classes.length} class{level.classes.length === 1 ? '' : 'es'}
                </p>
              </div>
              <Icon
                icon="mdi:chevron-down"
                className={mergeClasses(
                  'size-5 shrink-0 text-slate-500 transition-transform',
                  isOpen && 'rotate-180',
                )}
              />
            </button>

            {isOpen ? (
              <div className="space-y-2 border-t border-slate-100 px-3 py-3">
                {level.classes.map((classOption) => {
                  const selected = value === classOption.id

                  return (
                    <button
                      key={classOption.id}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => onChange(classOption.id)}
                      className={mergeClasses(
                        'flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-3 text-left transition',
                        selected
                          ? 'border-slate-900 bg-slate-900 text-white'
                          : 'border-slate-200 bg-slate-50 text-slate-800 hover:border-slate-300',
                      )}
                    >
                      <span className="text-sm font-medium">{classOption.display_name}</span>
                      <span
                        className={mergeClasses(
                          'shrink-0 text-xs',
                          selected ? 'text-slate-200' : 'text-slate-500',
                        )}
                      >
                        {classOption.student_count} student
                        {classOption.student_count === 1 ? '' : 's'}
                      </span>
                    </button>
                  )
                })}
              </div>
            ) : null}
          </div>
        )
      })}

      {error ? (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  )
}

export default LevelClassPicker
