import { Button, FormLabel, InputField, SelectField } from '@/components/ui'
import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'
import { GENDER_OPTIONS, type Teacher, type TeacherFormData } from '../types'
import { mapTeacherToFormData } from '../utils'

const ghanaPhoneSchema = z.string().regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana phone number')

const schema = z.object({
  first_name: z.string().min(1, { message: 'First name is required' }),
  last_name: z.string().min(1, { message: 'Last name is required' }),
  gender: z.enum(['male', 'female']).optional(),
  phone_number: z.string().min(1, { message: 'Primary phone number is required' }).pipe(ghanaPhoneSchema),
  phone_number_alt: z
    .string()
    .optional()
    .refine((value) => !value || ghanaPhoneSchema.safeParse(value).success, {
      message: 'Invalid Ghana phone number',
    }),
  email: z
    .string()
    .optional()
    .refine((value) => !value || z.string().email().safeParse(value).success, {
      message: 'Invalid email address',
    }),
  date_of_birth: z.string().optional(),
  address: z.string().optional(),
})

type AddTeacherFormProps = {
  onSubmit: (_data: TeacherFormData) => void
  onCancel: () => void
  isSubmitting?: boolean
  teacher?: Teacher | null
  submitLabel?: string
}

const defaultValues: TeacherFormData = {
  first_name: '',
  last_name: '',
  gender: undefined,
  phone_number: '',
  phone_number_alt: '',
  email: '',
  date_of_birth: '',
  address: '',
}

const AddTeacherForm = ({
  onSubmit,
  onCancel,
  isSubmitting = false,
  teacher,
  submitLabel = 'Add Teacher',
}: AddTeacherFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<TeacherFormData>({
    resolver: zodResolver(schema),
    defaultValues: teacher ? mapTeacherToFormData(teacher) : defaultValues,
  })

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="flex gap-4 items-start justify-between">
        <div className="w-1/2 space-y-2">
          <FormLabel label="First Name" className="font-normal text-base" required />
          <InputField
            placeholder="Enter first name"
            error={errors.first_name?.message}
            {...register('first_name')}
          />
        </div>
        <div className="w-1/2 space-y-2">
          <FormLabel label="Last Name" className="font-normal text-base" required />
          <InputField
            placeholder="Enter last name"
            error={errors.last_name?.message}
            {...register('last_name')}
          />
        </div>
      </div>

      <div className="space-y-2">
        <FormLabel label="Primary Phone Number" className="font-normal text-base" required />
        <InputField
          placeholder="e.g +233240000000 or 0240000000"
          type="tel"
          error={errors.phone_number?.message}
          {...register('phone_number')}
        />
        <p className="text-sm text-slate-500">This is the number user will login with</p>
      </div>

      <div className="space-y-2">
        <FormLabel label="Gender" className="font-normal text-base" />
        <Controller
          name="gender"
          control={control}
          render={({ field }) => (
            <SelectField
              options={[...GENDER_OPTIONS]}
              value={field.value ?? ''}
              onChange={field.onChange}
              onBlur={field.onBlur}
              placeholder="Select gender"
              error={errors.gender?.message}
            />
          )}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Date of Birth" className="font-normal text-base" />
        <InputField type="date" error={errors.date_of_birth?.message} {...register('date_of_birth')} />
      </div>

      <div className="space-y-2">
        <FormLabel label="Alternate Phone Number" className="font-normal text-base" />
        <InputField
          placeholder="e.g +233240000000 or 0240000000"
          type="tel"
          error={errors.phone_number_alt?.message}
          {...register('phone_number_alt')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Email Address" className="font-normal text-base" />
        <InputField
          placeholder="e.g. teacher@school.com"
          type="email"
          error={errors.email?.message}
          {...register('email')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="House Address" className="font-normal text-base" />
        <InputField
          placeholder="Enter house address"
          error={errors.address?.message}
          {...register('address')}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" loading={isSubmitting} loadingText="Saving...">
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}

export default AddTeacherForm
