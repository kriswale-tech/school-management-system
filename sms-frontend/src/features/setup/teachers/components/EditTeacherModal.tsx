import { useRef } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImageUpload } from '@/components/shared'
import { Modal } from '@/components/ui'
import { updateStaff } from '@/features/staff/services'
import { buildStaffFormData } from '@/features/staff/utils'
import { getApiErrorMessage } from '@/utils'
import type { Teacher, TeacherFormData } from '../types'
import AddTeacherForm from './AddTeacherForm'

type EditTeacherModalProps = {
  open: boolean
  teacher: Teacher | null
  onClose: () => void
}

const EditTeacherModal = ({ open, teacher, onClose }: EditTeacherModalProps) => {
  const queryClient = useQueryClient()
  const photoFileRef = useRef<File | null>(null)

  const { mutate: saveTeacher, isPending } = useMutation({
    mutationFn: (payload: FormData) => updateStaff(teacher!.id, payload),
    onSuccess: () => {
      toast.success('Teacher updated')
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to update teacher'))
    },
  })

  const handleSubmit = (data: TeacherFormData) => {
    saveTeacher(
      buildStaffFormData(data, {
        role: 'teacher',
        profilePicture: photoFileRef.current,
      }),
    )
  }

  if (!open || !teacher) return null

  return (
    <Modal
      open={open}
      title="Edit Teacher"
      onClose={onClose}
      scrollable
      className="max-w-4xl"
    >
      <div key={teacher.id} className="space-y-6">
        <ImageUpload
          label="Profile Photo"
          imageUrl={teacher.profile.profile_picture ?? undefined}
          onImageChange={(file) => {
            photoFileRef.current = file
          }}
          previewAlt="Teacher profile photo preview"
        />
        <AddTeacherForm
          teacher={teacher}
          onSubmit={handleSubmit}
          onCancel={onClose}
          isSubmitting={isPending}
          submitLabel="Save Changes"
        />
      </div>
    </Modal>
  )
}

export default EditTeacherModal
