import { useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImageUpload } from '@/components/shared'
import { Modal } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { updateStaff } from '../services'
import type { EditableStaffUser } from '../types'
import {
  buildStaffUpdateFormData,
  formatStaffRole,
  hasStaffUpdateChanges,
} from '../utils'
import StaffUserForm from './StaffUserForm'

type EditStaffUserModalProps = {
  open: boolean
  user: EditableStaffUser | null
  onClose: () => void
  title?: string
  successMessage?: string
  invalidateQueryKey: string
  previewAlt?: string
}

type EditStaffUserModalContentProps = {
  user: EditableStaffUser
  title?: string
  successMessage?: string
  invalidateQueryKey: string
  previewAlt: string
  onClose: () => void
}

const EditStaffUserModalContent = ({
  user,
  title,
  successMessage,
  invalidateQueryKey,
  previewAlt,
  onClose,
}: EditStaffUserModalContentProps) => {
  const queryClient = useQueryClient()
  const photoFileRef = useRef<File | null>(null)
  const [photoChanged, setPhotoChanged] = useState(false)

  const modalTitle = title ?? `Edit ${formatStaffRole(user.role)}`
  const savedMessage = successMessage ?? `${formatStaffRole(user.role)} updated`

  const { mutate: saveUser, isPending } = useMutation({
    mutationFn: (payload: FormData) => updateStaff(user.id, payload),
    onSuccess: (response) => {
      toast.success(
        response.linked_existing_user
          ? 'Phone number matched an existing person; they were linked to this school.'
          : savedMessage,
      )
      void queryClient.invalidateQueries({ queryKey: [invalidateQueryKey] })
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, `Unable to update ${modalTitle.toLowerCase()}`))
    },
  })

  const handleSubmit = ({
    data,
    dirtyFields,
  }: {
    data: Parameters<typeof buildStaffUpdateFormData>[0]
    dirtyFields: Partial<Record<keyof typeof data, boolean>>
  }) => {
    const includeProfilePicture = photoChanged && Boolean(photoFileRef.current)

    if (!hasStaffUpdateChanges(dirtyFields, includeProfilePicture)) {
      toast.error('No changes to save')
      return
    }

    saveUser(
      buildStaffUpdateFormData(data, {
        dirtyFields,
        profilePicture: photoFileRef.current,
        includeProfilePicture,
      }),
    )
  }

  const handleClose = () => {
    photoFileRef.current = null
    setPhotoChanged(false)
    onClose()
  }

  return (
    <Modal open title={modalTitle} onClose={handleClose} scrollable className="max-w-4xl">
      <div className="space-y-6">
        <ImageUpload
          label="Profile Photo"
          imageUrl={user.profile.profile_picture ?? undefined}
          onImageChange={(file) => {
            photoFileRef.current = file
            setPhotoChanged(true)
          }}
          previewAlt={previewAlt}
        />
        <StaffUserForm
          user={user}
          onSubmit={handleSubmit}
          onCancel={handleClose}
          isSubmitting={isPending}
          submitLabel="Save Changes"
        />
      </div>
    </Modal>
  )
}

const EditStaffUserModal = ({
  open,
  user,
  onClose,
  title,
  successMessage,
  invalidateQueryKey,
  previewAlt = 'Profile photo preview',
}: EditStaffUserModalProps) => {
  if (!open || !user) return null

  return (
    <EditStaffUserModalContent
      key={user.id}
      user={user}
      title={title}
      successMessage={successMessage}
      invalidateQueryKey={invalidateQueryKey}
      previewAlt={previewAlt}
      onClose={onClose}
    />
  )
}

export default EditStaffUserModal
