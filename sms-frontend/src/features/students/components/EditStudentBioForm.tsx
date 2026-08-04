import { useEffect } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { z } from 'zod'
import { Button, FormLabel, InputField, Modal, SelectField } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { updateStudent } from '../services'
import type { StudentBioUpdatePayload, StudentDetail } from '../types'
import { GENDER_OPTIONS } from './student-onboarding/student-form/constants'
import {
  hasDirtyChanges,
  pickDirtyFields,
  STUDENT_DETAIL_QUERY_KEY,
} from '../utils'

const schema = z.object({
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().min(1, 'Last name is required'),
  other_names: z.string().optional(),
  gender: z.enum(['male', 'female', 'other'], { message: 'Gender is required' }),
  date_of_birth: z.string().min(1, 'Date of birth is required'),
  admission_date: z.string().min(1, 'Admission date is required'),
  address: z.string().optional(),
})

type EditStudentBioFormValues = z.infer<typeof schema>

type EditStudentBioFormProps = {
  open: boolean
  student: StudentDetail
  onClose: () => void
}

const mapStudentToFormValues = (student: StudentDetail): EditStudentBioFormValues => ({
  first_name: student.first_name,
  last_name: student.last_name,
  other_names: student.other_names ?? '',
  gender: student.gender,
  date_of_birth: student.date_of_birth,
  admission_date: student.admission_date,
  address: student.address ?? '',
})

const EditStudentBioForm = ({ open, student, onClose }: EditStudentBioFormProps) => {
  const queryClient = useQueryClient()

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, dirtyFields },
  } = useForm<EditStudentBioFormValues>({
    resolver: zodResolver(schema),
    defaultValues: mapStudentToFormValues(student),
  })

  useEffect(() => {
    if (open) reset(mapStudentToFormValues(student))
  }, [open, student, reset])

  const { mutate: saveBio, isPending } = useMutation({
    mutationFn: (payload: StudentBioUpdatePayload) => updateStudent(student.id, payload),
    onSuccess: () => {
      toast.success('Student bio updated')
      void queryClient.invalidateQueries({ queryKey: [STUDENT_DETAIL_QUERY_KEY, student.id] })
      onClose()
    },
    onError: (mutationError) => {
      toast.error(getApiErrorMessage(mutationError, 'Unable to update student bio'))
    },
  })

  const onSubmit = (values: EditStudentBioFormValues) => {
    if (!hasDirtyChanges(dirtyFields)) {
      toast.error('No changes to save')
      return
    }

    const payload = pickDirtyFields(values, dirtyFields) as StudentBioUpdatePayload
    saveBio(payload)
  }

  return (
    <Modal open={open} title="Edit Student Bio" onClose={onClose} scrollable className="max-w-2xl">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
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
          <FormLabel label="Gender" required />
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

        <div className="space-y-2">
          <FormLabel label="Address" />
          <InputField
            placeholder="Enter address"
            error={errors.address?.message}
            {...register('address')}
          />
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

export default EditStudentBioForm
