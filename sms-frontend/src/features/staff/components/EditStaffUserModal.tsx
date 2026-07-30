import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ImageUpload } from '@/components/shared'
import { Modal } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { updateStaff } from '../services'
import type { Staff } from '../types'
import {
  buildStaffUpdateFormData,
  formatStaffRole,
  hasStaffUpdateChanges,
} from '../utils'
import StaffUserForm from './StaffUserForm'

type EditStaffUserModalProps = {
  open: boolean
  user: Staff | null
  onClose: () => void
  title?: string
  successMessage?: string
  invalidateQueryKey: string
  previewAlt?: string
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
  const queryClient = useQueryClient()
  const photoFileRef = useRef<File | null>(null)
  const [photoChanged, setPhotoChanged] = useState(false)

  const modalTitle = title ?? (user ? `Edit ${formatStaffRole(user.role)}` : 'Edit User')
  const savedMessage = successMessage ?? `${user ? formatStaffRole(user.role) : 'User'} updated`

  useEffect(() => {
    photoFileRef.current = null
    setPhotoChanged(false)
  }, [user?.id])

  const { mutate: saveUser, isPending } = useMutation({
    mutationFn: (payload: FormData) => updateStaff(user!.id, payload),
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
    if (!user) return

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

  if (!open || !user) return null

  return (
    <Modal open={open} title={modalTitle} onClose={handleClose} scrollable className="max-w-4xl">
      <div key={user.id} className="space-y-6">
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

export default EditStaffUserModal
