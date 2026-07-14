import type { UseFormRegister } from 'react-hook-form'
import { FormLabel } from '@/components/ui'
import type { AcademicYearAndTermFormData } from '@/features/setup/types/types'
import { mergeClasses } from '@/utils'

type TermScheduleProps = {
  label: string
  startDateRegister: ReturnType<UseFormRegister<AcademicYearAndTermFormData>>
  endDateRegister: ReturnType<UseFormRegister<AcademicYearAndTermFormData>>
  startDateError?: string
  endDateError?: string
}

const dateInputClassName =
  'w-full rounded-lg border border-slate-300 bg-white p-2 text-sm text-slate-700 outline-none transition focus:border-slate-400 focus:ring-1 focus:ring-slate-400'

const TermSchedule = ({
  label,
  startDateRegister,
  endDateRegister,
  startDateError,
  endDateError,
}: TermScheduleProps) => {
  return (
    <div className="form-field-wrapper">
      <FormLabel label={label} className="font-normal text-base" />

      <div className="mt-4 flex gap-4">
        <div className="w-1/2 space-y-2">
          <FormLabel label="Start Date" className="font-normal text-sm" />
          <input
            type="date"
            aria-invalid={startDateError ? true : undefined}
            className={mergeClasses(
              dateInputClassName,
              startDateError && 'border-red-500 focus:border-red-500 focus:ring-red-200/80',
            )}
            {...startDateRegister}
          />
          {startDateError ? <p className="text-sm text-red-600">{startDateError}</p> : null}
        </div>
        <div className="w-1/2 space-y-2">
          <FormLabel label="End Date" className="font-normal text-sm" />
          <input
            type="date"
            aria-invalid={endDateError ? true : undefined}
            className={mergeClasses(
              dateInputClassName,
              endDateError && 'border-red-500 focus:border-red-500 focus:ring-red-200/80',
            )}
            {...endDateRegister}
          />
          {endDateError ? <p className="text-sm text-red-600">{endDateError}</p> : null}
        </div>
      </div>
    </div>
  )
}

export default TermSchedule
