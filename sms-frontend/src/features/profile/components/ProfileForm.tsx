import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm } from 'react-hook-form'
import { z } from 'zod'
import { Button, FormLabel, InputField, SelectField } from '@/components/ui'
import type { User } from '@/features/auth/types'
import type { ProfileFormData } from '../types'
import { GENDER_OPTIONS, mapUserToFormData } from '../utils'

const ghanaPhoneSchema = z.string().regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana phone number')

const schema = z.object({
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().min(1, 'Last name is required'),
  email: z
    .string()
    .refine((value) => !value || z.string().email().safeParse(value).success, {
      message: 'Invalid email address',
    }),
  gender: z.enum(['male', 'female', 'other']).optional(),
  phone_number_alt: z
    .string()
    .refine((value) => !value || ghanaPhoneSchema.safeParse(value).success, {
      message: 'Invalid Ghana phone number',
    }),
  date_of_birth: z.string(),
  address: z.string(),
  bio: z.string().max(500, 'Bio must be 500 characters or fewer'),
})

type ProfileFormSubmitPayload = {
  data: ProfileFormData
  dirtyFields: Partial<Record<keyof ProfileFormData, boolean>>
}

type ProfileFormProps = {
  user: User
  isSubmitting?: boolean
  photoDirty?: boolean
  onSubmit: (payload: ProfileFormSubmitPayload) => void
}

const ProfileForm = ({ user, isSubmitting = false, photoDirty = false, onSubmit }: ProfileFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, dirtyFields, isDirty },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(schema),
    defaultValues: mapUserToFormData(user),
  })

  return (
    <form
      onSubmit={handleSubmit((data) => onSubmit({ data, dirtyFields }))}
      className="space-y-8"
    >
      <section className="space-y-4">
        <div>
          <h3 className="text-base text-slate-900">Account</h3>
          <p className="mt-1 text-sm text-slate-500">How you appear across the schools you belong to.</p>
        </div>
        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="w-full space-y-2 sm:w-1/2">
            <FormLabel label="First name" className="font-normal text-base" required />
            <InputField
              placeholder="Enter first name"
              error={errors.first_name?.message}
              {...register('first_name')}
            />
          </div>
          <div className="w-full space-y-2 sm:w-1/2">
            <FormLabel label="Last name" className="font-normal text-base" required />
            <InputField
              placeholder="Enter last name"
              error={errors.last_name?.message}
              {...register('last_name')}
            />
          </div>
        </div>
        <div className="space-y-2">
          <FormLabel label="Email" className="font-normal text-base" />
          <InputField
            placeholder="e.g. you@school.com"
            type="email"
            error={errors.email?.message}
            {...register('email')}
          />
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h3 className="text-base text-slate-900">Personal details</h3>
          <p className="mt-1 text-sm text-slate-500">Optional information for your school directory.</p>
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
          <FormLabel label="Alternate phone" className="font-normal text-base" />
          <InputField
            placeholder="e.g +233240000000 or 0240000000"
            type="tel"
            error={errors.phone_number_alt?.message}
            {...register('phone_number_alt')}
          />
        </div>
        <div className="space-y-2">
          <FormLabel label="Date of birth" className="font-normal text-base" />
          <InputField type="date" error={errors.date_of_birth?.message} {...register('date_of_birth')} />
        </div>
        <div className="space-y-2">
          <FormLabel label="Address" className="font-normal text-base" />
          <InputField placeholder="Enter address" error={errors.address?.message} {...register('address')} />
        </div>
        <div className="space-y-2">
          <FormLabel label="Bio" className="font-normal text-base" />
          <textarea
            rows={3}
            placeholder="A short note about you (optional)"
            className="w-full rounded-lg border border-slate-300 bg-white p-2 text-sm text-slate-700 outline-none transition focus:border-slate-400 focus:ring-1 focus:ring-slate-400"
            {...register('bio')}
          />
          {errors.bio?.message ? <p className="text-sm text-red-600">{errors.bio.message}</p> : null}
        </div>
      </section>

      <Button
        type="submit"
        variant="outline"
        loading={isSubmitting}
        disabled={(!isDirty && !photoDirty) || isSubmitting}
      >
        Save profile
      </Button>
    </form>
  )
}

export default ProfileForm
