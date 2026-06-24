import { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import SchoolLogoUpload from '@/features/setup/components/school-profile/SchoolLogoUpload'
import SchoolProfileForm from '@/features/setup/components/school-profile/SchoolProfileForm'
import type {
  SchoolProfileFormData,
  SchoolProfile as SchoolProfileType,
} from '@/features/setup/types'
import { getSchoolProfile, setupSchoolProfile } from '@/features/setup/services'
import { buildSchoolProfilePayload } from '@/features/setup/utils/build-school-profile-payload'
import { handleSetupProgressResponse } from '@/features/setup/utils/handle-setup-progress-response'
import { useAuthStore } from '@/features/auth/store'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'

const SchoolProfile = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const user = useAuthStore((state) => state.user)
  const [logoFile, setLogoFile] = useState<File | null>(null)

  const { data: schoolProfile, isLoading } = useQuery<SchoolProfileType>({
    queryKey: ['schoolProfile'],
    queryFn: getSchoolProfile,
  })

  const { mutate: saveSchoolProfile } = useMutation({
    mutationFn: setupSchoolProfile,
    onSuccess: (response) => {
      toast.success('School profile saved')
      void queryClient.invalidateQueries({ queryKey: ['setup'] })
      void queryClient.invalidateQueries({ queryKey: ['schoolProfile'] })

      handleSetupProgressResponse(response, { navigate, user, setUser })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to save school profile'))
    },
  })

  const handleProfileSubmit = (data: SchoolProfileFormData) => {
    saveSchoolProfile(buildSchoolProfilePayload(data, logoFile))
  }

  if (isLoading) return <LoadingSpinner className="mx-auto" />

  return (
    <div className="space-y-6">
      <SchoolLogoUpload onLogoChange={setLogoFile} logo={schoolProfile?.logo} />
      <SchoolProfileForm onSubmit={handleProfileSubmit} schoolProfile={schoolProfile} />
    </div>
  )
}

export default SchoolProfile
