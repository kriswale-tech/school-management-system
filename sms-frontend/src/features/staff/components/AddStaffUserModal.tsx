import { useRef } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImageUpload } from '@/components/shared'
import { Modal } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { createStaff } from '../services'
import type { StaffFormData } from '../types'
import { buildStaffFormData } from '../utils'
import StaffUserForm from './StaffUserForm'

type AddStaffUserModalProps = {
  open: boolean
  onClose: () => void
  sessionKey: number
  role: string
  title: string
  submitLabel: string
  successMessage: string
  invalidateQueryKey: string
  previewAlt?: string
}

const AddStaffUserModal = ({
  open,
  onClose,
  sessionKey,
  role,
  title,
  submitLabel,
  successMessage,
  invalidateQueryKey,
  previewAlt = 'Profile photo preview',
}: AddStaffUserModalProps) => {
  const queryClient = useQueryClient()
  const photoFileRef = useRef<File | null>(null)

  const { mutate: createUser, isPending } = useMutation({
    mutationFn: createStaff,
    onSuccess: () => {
      toast.success(successMessage)
      void queryClient.invalidateQueries({ queryKey: [invalidateQueryKey] })
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, `Unable to add ${title.toLowerCase()}`))
    },
  })

  const handleSubmit = ({ data }: { data: StaffFormData }) => {
    createUser(
      buildStaffFormData(data, {
        role,
        profilePicture: photoFileRef.current,
      }),
    )
  }

  return (
    <Modal open={open} title={title} onClose={onClose} scrollable className="max-w-4xl">
      {open ? (
        <div key={sessionKey} className="space-y-6">
          <ImageUpload
            label="Profile Photo"
            onImageChange={(file) => {
              photoFileRef.current = file
            }}
            previewAlt={previewAlt}
          />
          <StaffUserForm
            onSubmit={handleSubmit}
            onCancel={onClose}
            isSubmitting={isPending}
            submitLabel={submitLabel}
          />
        </div>
      ) : null}
    </Modal>
  )
}

export default AddStaffUserModal
