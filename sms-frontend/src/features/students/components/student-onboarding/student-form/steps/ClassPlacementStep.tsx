import { useQuery } from '@tanstack/react-query'
import { Controller, type Control, type FieldErrors } from 'react-hook-form'
import ChoicePillGroup from '@/components/shared/ChoicePillGroup'
import { FormLabel } from '@/components/ui'
import { getAllClasses } from '@/features/classes/services'
import LevelClassPicker from '../components/LevelClassPicker'
import { STUDENT_STATUS_OPTIONS } from '../constants'
import type { StudentFormValues } from '../types'

type ClassPlacementStepProps = {
  control: Control<StudentFormValues>
  errors: FieldErrors<StudentFormValues>
}

const ClassPlacementStep = ({ control, errors }: ClassPlacementStepProps) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['classes', 'all-classes'],
    queryFn: () => getAllClasses(),
  })

  const levels = data?.levels ?? []

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <FormLabel label="Select Class" required />
        <p className="text-sm text-slate-500">
          Expand a level and choose the class or stream for this student.
        </p>
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading classes…</p>
        ) : isError ? (
          <p role="alert" className="text-sm text-red-600">
            Unable to load classes. Try again.
          </p>
        ) : (
          <Controller
            name="stream_id"
            control={control}
            render={({ field }) => (
              <LevelClassPicker
                levels={levels}
                value={field.value}
                onChange={field.onChange}
                error={errors.stream_id?.message}
              />
            )}
          />
        )}
      </div>

      <div className="space-y-3">
        <FormLabel label="Student Status" required />
        <Controller
          name="is_new_student"
          control={control}
          render={({ field }) => (
            <div className="space-y-2">
              <ChoicePillGroup
                name="is-new-student"
                items={STUDENT_STATUS_OPTIONS}
                value={field.value}
                onChange={field.onChange}
              />
              {errors.is_new_student?.message ? (
                <p role="alert" className="text-sm text-red-600">
                  {errors.is_new_student.message}
                </p>
              ) : null}
            </div>
          )}
        />
      </div>
    </div>
  )
}

export default ClassPlacementStep
