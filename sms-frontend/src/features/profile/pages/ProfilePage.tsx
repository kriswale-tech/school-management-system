import { useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import ActionBar from '@/components/shared/ActionBar'
import { ImageUpload } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'
import { useAuthStore } from '@/features/auth/store'
import { getApiErrorMessage } from '@/utils'
import ProfileForm from '../components/ProfileForm'
import ProfileSummaryCard from '../components/ProfileSummaryCard'
import { updateMyProfile } from '../services'
import type { ProfileFormData } from '../types'
import { buildProfileUpdateFormData, hasProfileUpdateChanges } from '../utils'

const ProfilePage = () => {
  const { user } = useAuth({ requireAuth: true })
  const setUser = useAuthStore((state) => state.setUser)
  const queryClient = useQueryClient()
  const photoFileRef = useRef<File | null>(null)
  const [photoChanged, setPhotoChanged] = useState(false)

  const { mutate: saveProfile, isPending } = useMutation({
    mutationFn: updateMyProfile,
    onSuccess: (updated) => {
      setUser(updated)
      void queryClient.invalidateQueries({ queryKey: ['me', 'session'] })
      photoFileRef.current = null
      setPhotoChanged(false)
      toast.success('Profile saved')
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to save profile'))
    },
  })

  if (!user) {
    return null
  }

  const handleSubmit = ({
    data,
    dirtyFields,
  }: {
    data: ProfileFormData
    dirtyFields: Partial<Record<keyof ProfileFormData, boolean>>
  }) => {
    const includeProfilePicture = photoChanged && Boolean(photoFileRef.current)

    if (!hasProfileUpdateChanges(dirtyFields, includeProfilePicture)) {
      toast.error('No changes to save')
      return
    }

    saveProfile(
      buildProfileUpdateFormData(data, {
        dirtyFields,
        profilePicture: photoFileRef.current,
        includeProfilePicture,
      }),
    )
  }

  return (
    <div className="space-y-6">
      <ActionBar title="Profile" />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,520px)_minmax(0,1fr)]">
        <div className="bg-white p-4 custom-shadow-md lg:p-6">
          <ProfileSummaryCard user={user} />
        </div>

        <div className="bg-white p-4 custom-shadow-md lg:p-6">
          <div className="space-y-6">
            <ImageUpload
              label="Profile photo"
              imageUrl={user.profile?.profile_picture ?? undefined}
              previewAlt={`${user.full_name} profile photo`}
              onImageChange={(file) => {
                photoFileRef.current = file
                setPhotoChanged(Boolean(file))
              }}
            />
            <ProfileForm
              key={`${user.id}-${user.profile?.profile_picture ?? ''}-${user.first_name}`}
              user={user}
              isSubmitting={isPending}
              photoDirty={photoChanged}
              onSubmit={handleSubmit}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProfilePage
