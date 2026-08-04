import { useEffect } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { z } from 'zod'
import {
  Button,
  CheckboxField,
  FormLabel,
  InputField,
  Modal,
  SelectField,
} from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { updateStudentGuardian } from '../services'
import type { GuardianUpdatePayload, StudentGuardian } from '../types'
import { RELATIONSHIP_OPTIONS } from './student-onboarding/student-form/constants'
import {
  hasDirtyChanges,
  pickDirtyFields,
  STUDENT_DETAIL_QUERY_KEY,
} from '../utils'

const ghanaPhoneSchema = z
  .string()
  .min(1, { message: 'Primary phone is required' })
  .regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana phone number')

const optionalPhoneSchema = z
  .string()
  .refine((value) => !value || /^(\+233|0)[0-9]{9}$/.test(value), {
    message: 'Invalid Ghana phone number',
  })

const schema = z.object({
  name: z.string().min(1, { message: 'Guardian name is required' }),
  phone_number: ghanaPhoneSchema,
  phone_number_alt: optionalPhoneSchema,
  email: z
    .string()
    .refine((value) => !value || z.string().email().safeParse(value).success, {
      message: 'Invalid email address',
    }),
  address: z.string(),
  relationship: z.enum(
    [
      'father',
      'mother',
      'guardian',
      'other',
      'uncle',
      'aunt',
      'cousin',
      'sibling',
      'grandparent',
    ],
    { message: 'Relationship is required' },
  ),
  is_emergency_contact: z.boolean(),
  is_primary: z.boolean(),
})

type EditGuardianFormValues = z.infer<typeof schema>

type EditGuardianFormProps = {
  open: boolean
  studentId: string
  guardian: StudentGuardian | null
  onClose: () => void
}

const mapGuardianToFormValues = (guardian: StudentGuardian): EditGuardianFormValues => ({
  name: guardian.name,
  phone_number: guardian.phone_number,
  phone_number_alt: guardian.phone_number_alt ?? '',
  email: guardian.email ?? '',
  address: guardian.address ?? '',
  relationship: guardian.relationship,
  is_emergency_contact: guardian.is_emergency_contact,
  is_primary: guardian.is_primary,
})

const EditGuardianForm = ({ open, studentId, guardian, onClose }: EditGuardianFormProps) => {
  const queryClient = useQueryClient()

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, dirtyFields },
  } = useForm<EditGuardianFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      phone_number: '',
      phone_number_alt: '',
      email: '',
      address: '',
      relationship: 'guardian',
      is_emergency_contact: false,
      is_primary: false,
    },
  })

  useEffect(() => {
    if (open && guardian) {
      reset(mapGuardianToFormValues(guardian))
    }
  }, [open, guardian, reset])

  const { mutate: saveGuardian, isPending } = useMutation({
    mutationFn: (payload: GuardianUpdatePayload) =>
      updateStudentGuardian(studentId, guardian!.id, payload),
    onSuccess: () => {
      toast.success('Guardian updated')
      void queryClient.invalidateQueries({ queryKey: [STUDENT_DETAIL_QUERY_KEY, studentId] })
      onClose()
    },
    onError: (mutationError) => {
      toast.error(getApiErrorMessage(mutationError, 'Unable to update guardian'))
    },
  })

  if (!open || !guardian) return null

  const onSubmit = (values: EditGuardianFormValues) => {
    if (!hasDirtyChanges(dirtyFields)) {
      toast.error('No changes to save')
      return
    }

    const payload = pickDirtyFields(values, dirtyFields) as GuardianUpdatePayload

    // API only accepts promoting a guardian to primary (not demoting).
    if (payload.is_primary === false) {
      delete payload.is_primary
    }

    if (Object.keys(payload).length === 0) {
      toast.error('No changes to save')
      return
    }

    saveGuardian(payload)
  }

  return (
    <Modal
      open={open}
      title={guardian.is_primary ? 'Edit Primary Guardian' : 'Edit Guardian'}
      onClose={onClose}
      scrollable
      className="max-w-2xl"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <p className="text-sm text-slate-500">
          Contact details (name, phone, email, address) are shared across the school. Updating them
          here updates this parent for every linked student.
        </p>

        <div className="space-y-2">
          <FormLabel label="Full Name" required />
          <InputField
            placeholder="Enter guardian name"
            error={errors.name?.message}
            {...register('name')}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <FormLabel label="Primary Phone" required />
            <InputField
              type="tel"
              placeholder="e.g +233240000000 or 0240000000"
              error={errors.phone_number?.message}
              {...register('phone_number')}
            />
          </div>
          <div className="space-y-2">
            <FormLabel label="Alternate Phone" />
            <InputField
              type="tel"
              placeholder="Optional"
              error={errors.phone_number_alt?.message}
              {...register('phone_number_alt')}
            />
          </div>
        </div>

        <div className="space-y-2">
          <FormLabel label="Email" />
          <InputField
            type="email"
            placeholder="Enter email (optional)"
            error={errors.email?.message}
            {...register('email')}
          />
        </div>

        <div className="space-y-2">
          <FormLabel label="Address" />
          <InputField
            placeholder="Enter address (optional)"
            error={errors.address?.message}
            {...register('address')}
          />
        </div>

        <div className="space-y-2">
          <FormLabel label="Relationship" required />
          <Controller
            name="relationship"
            control={control}
            render={({ field }) => (
              <SelectField
                options={[...RELATIONSHIP_OPTIONS]}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                placeholder="Select relationship"
                error={errors.relationship?.message}
              />
            )}
          />
        </div>

        <div className="space-y-3">
          <CheckboxField {...register('is_emergency_contact')}>
            Emergency contact
          </CheckboxField>

          {!guardian.is_primary ? (
            <CheckboxField {...register('is_primary')}>Make primary guardian</CheckboxField>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button type="submit" loading={isPending} loadingText="Saving...">
            Save Changes
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default EditGuardianForm
