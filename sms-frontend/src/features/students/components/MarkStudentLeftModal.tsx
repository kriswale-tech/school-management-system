import { useEffect } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { z } from 'zod'
import { Button, FormLabel, Modal, SelectField } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { markStudentLeft } from '../services'
import type { StudentDetail, StudentLeaveReason } from '../types'
import { STUDENT_DETAIL_QUERY_KEY } from '../utils'

const LEAVE_REASON_OPTIONS = [
  { value: 'dropout', label: 'Dropped out' },
  { value: 'transfer', label: 'Transferred' },
  { value: 'other', label: 'Other' },
] as const

const schema = z.object({
  reason: z.enum(['dropout', 'transfer', 'other'], { message: 'Select a reason' }),
  notes: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

type MarkStudentLeftModalProps = {
  open: boolean
  student: StudentDetail
  onClose: () => void
}

const MarkStudentLeftModal = ({ open, student, onClose }: MarkStudentLeftModalProps) => {
  const queryClient = useQueryClient()
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { reason: undefined, notes: '' },
  })

  useEffect(() => {
    if (open) reset({ reason: undefined, notes: '' })
  }, [open, reset])

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) =>
      markStudentLeft(student.id, {
        reason: values.reason as StudentLeaveReason,
        notes: values.notes?.trim() || undefined,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData([STUDENT_DETAIL_QUERY_KEY, student.id], updated)
      toast.success('Student marked as left')
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to mark student as left'))
    },
  })

  return (
    <Modal open={open} title="Mark as left" onClose={onClose} className="max-w-lg">
      <form
        className="space-y-4"
        onSubmit={handleSubmit((values) => mutate(values))}
      >
        <p className="text-sm text-slate-600">
          Mark <span className="font-medium text-slate-800">{student.full_name}</span> as having
          left the school. They will no longer appear as an active student and cannot be enrolled
          until an admin reactivates them.
        </p>

        <div>
          <FormLabel label="Reason" required />
          <Controller
            name="reason"
            control={control}
            render={({ field }) => (
              <SelectField
                id="leave-reason"
                options={[...LEAVE_REASON_OPTIONS]}
                value={field.value ?? ''}
                onChange={field.onChange}
                onBlur={field.onBlur}
                placeholder="Select reason"
                error={errors.reason?.message}
              />
            )}
          />
        </div>

        <div>
          <FormLabel label="Notes" helperText="optional" />
          <textarea
            id="leave-notes"
            rows={3}
            className="mt-1 w-full rounded-sm border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-1 focus:ring-sky-500"
            placeholder="e.g. Moving to another region"
            {...register('notes')}
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" className="w-fit" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" className="w-fit" loading={isPending} color="red">
            Mark as left
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default MarkStudentLeftModal
