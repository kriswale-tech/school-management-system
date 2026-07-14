import { useEffect } from 'react'
import { Button, FormLabel, InputField } from '@/components/ui'
import type { SchoolProfile, SchoolProfileFormData } from '@/features/setup/types/types'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

const ghanaPhoneSchema = z.string().regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana phone number')

const schema = z.object({
  school_name: z.string().min(1, { message: 'School name is required' }),
  motto: z.string().min(1, { message: 'School motto is required' }),
  address: z.string().min(1, { message: 'School address is required' }),
  gps_address: z.string().min(1, { message: 'GPS address is required' }),
  po_box: z.string().optional(),
  phone_number: z.string().min(1, { message: 'Phone number is required' }).pipe(ghanaPhoneSchema),
  phone_number_alt: z
    .string()
    .optional()
    .refine((value) => !value || ghanaPhoneSchema.safeParse(value).success, {
      message: 'Invalid Ghana phone number',
    }),
  email: z
    .string()
    .min(1, { message: 'Email is required' })
    .email({ message: 'Invalid email address' }),
})

interface SchoolProfileFormProps {
  onSubmit: (_data: SchoolProfileFormData) => void
  schoolProfile?: SchoolProfile
}

function toFormData(profile?: SchoolProfile): SchoolProfileFormData {
  return {
    school_name: profile?.name ?? '',
    motto: profile?.motto ?? '',
    address: profile?.address ?? '',
    gps_address: profile?.gps_address ?? '',
    po_box: profile?.box_address ?? '',
    phone_number: profile?.phone_number ?? '',
    phone_number_alt: profile?.phone_number_alt ?? '',
    email: profile?.email ?? '',
  }
}

const SchoolProfileForm = ({ onSubmit, schoolProfile }: SchoolProfileFormProps) => {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<SchoolProfileFormData>({
    resolver: zodResolver(schema),
    defaultValues: toFormData(schoolProfile),
  })

  useEffect(() => {
    reset(toFormData(schoolProfile))
  }, [schoolProfile, reset])

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <FormLabel label="School Name" className="font-normal text-base" required />
        <InputField
          placeholder="Enter the name of your school"
          error={errors.school_name?.message}
          {...register('school_name')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="School Motto / Slogan" className="font-normal text-base" required />
        <InputField
          placeholder="Enter the motto/slogan of your school"
          error={errors.motto?.message}
          {...register('motto')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="School Address" className="font-normal text-base" required />
        <InputField
          placeholder="e.g. Adepa Loop, Tabora, Accra"
          error={errors.address?.message}
          {...register('address')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="School GPS Address" className="font-normal text-base" required />
        <InputField
          placeholder="e.g. GA-000-0000"
          error={errors.gps_address?.message}
          {...register('gps_address')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="P.O. Box" className="font-normal text-base" helperText="If available" />
        <InputField
          placeholder="Enter the P.O. box of your school"
          error={errors.po_box?.message}
          {...register('po_box')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="School Phone Number" className="font-normal text-base" required />
        <InputField
          placeholder="e.g +233240000000 or 0240000000"
          type="tel"
          error={errors.phone_number?.message}
          {...register('phone_number')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel
          label="School Phone Number"
          className="font-normal text-base"
          helperText="Alternate"
        />
        <InputField
          placeholder="e.g +233240000000 or 0240000000"
          type="tel"
          error={errors.phone_number_alt?.message}
          {...register('phone_number_alt')}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="School Email" className="font-normal text-base" required />
        <InputField
          placeholder="e.g. info@school.com"
          type="email"
          error={errors.email?.message}
          {...register('email')}
        />
      </div>

      <Button
        type="submit"
        variant="outline"
        loading={isSubmitting}
        loadingText="Saving..."
        disabled={!isDirty}
      >
        Proceed to Next Step
      </Button>
    </form>
  )
}

export default SchoolProfileForm
