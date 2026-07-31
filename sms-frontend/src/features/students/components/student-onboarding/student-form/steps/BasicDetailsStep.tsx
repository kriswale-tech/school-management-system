import { Controller, type Control, type FieldErrors, type UseFormRegister } from 'react-hook-form'
import { FormLabel, InputField, SelectField } from '@/components/ui'
import { GENDER_OPTIONS } from '../constants'
import type { StudentFormValues } from '../types'

type BasicDetailsStepProps = {
  register: UseFormRegister<StudentFormValues>
  control: Control<StudentFormValues>
  errors: FieldErrors<StudentFormValues>
}

const BasicDetailsStep = ({ register, control, errors }: BasicDetailsStepProps) => {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <FormLabel label="First Name" required />
          <InputField
            placeholder="Enter first name"
            error={errors.first_name?.message}
            {...register('first_name')}
          />
        </div>
        <div className="space-y-2">
          <FormLabel label="Last Name" required />
          <InputField
            placeholder="Enter last name"
            error={errors.last_name?.message}
            {...register('last_name')}
          />
        </div>
      </div>

      <div className="space-y-2">
        <FormLabel label="Other Names" />
        <InputField
          placeholder="Enter other names"
          error={errors.other_names?.message}
          {...register('other_names')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Gender" />
        <Controller
          name="gender"
          control={control}
          render={({ field }) => (
            <SelectField
              options={[...GENDER_OPTIONS]}
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              placeholder="Select gender"
              error={errors.gender?.message}
            />
          )}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <FormLabel label="Date of Birth" required />
          <InputField
            type="date"
            error={errors.date_of_birth?.message}
            {...register('date_of_birth')}
          />
        </div>
        <div className="space-y-2">
          <FormLabel label="Admission Date" required />
          <InputField
            type="date"
            error={errors.admission_date?.message}
            {...register('admission_date')}
          />
        </div>
      </div>
    </div>
  )
}

export default BasicDetailsStep
