import { useRef } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImageUpload } from '@/components/shared'
import { Modal } from '@/components/ui'
import { createStaff } from '@/features/staff/services'
import { buildStaffFormData } from '@/features/staff/utils'
import { getApiErrorMessage } from '@/utils'
import type { TeacherFormData } from '../types'
import AddTeacherForm from './AddTeacherForm'

type AddTeacherModalProps = {
  open: boolean
  onClose: () => void
  sessionKey: number
}

const AddTeacherModal = ({ open, onClose, sessionKey }: AddTeacherModalProps) => {
  const queryClient = useQueryClient()
  const photoFileRef = useRef<File | null>(null)

  const handleClose = () => {
    onClose()
  }

  const { mutate: createTeacher, isPending } = useMutation({
    mutationFn: createStaff,
    onSuccess: () => {
      toast.success('Teacher added')
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      handleClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to add teacher'))
    },
  })

  const handleSubmit = (data: TeacherFormData) => {
    createTeacher(
      buildStaffFormData(data, {
        role: 'teacher',
        profilePicture: photoFileRef.current,
      }),
    )
  }

  return (
    <Modal
      open={open}
      title="Add Teacher"
      onClose={handleClose}
      scrollable
      className="max-w-4xl"
    >
      {open ? (
        <div key={sessionKey} className="space-y-6">
          <ImageUpload
            label="Profile Photo"
            onImageChange={(file) => {
              photoFileRef.current = file
            }}
            previewAlt="Teacher profile photo preview"
          />
          <AddTeacherForm
            onSubmit={handleSubmit}
            onCancel={handleClose}
            isSubmitting={isPending}
          />
        </div>
      ) : null}
    </Modal>
  )
}

export default AddTeacherModal
