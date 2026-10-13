import { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import SchoolLogoUpload from '@/features/setup/school-profile/components/SchoolLogoUpload'
import SchoolProfileForm from '@/features/setup/school-profile/components/SchoolProfileForm'
import type { SchoolProfileFormData } from '@/features/setup/school-profile/types'
import { getApiErrorMessage } from '@/utils'
import { SCHOOL_PROFILE_QUERY_KEY, getSchoolProfile, updateSchoolProfile } from '../services'
import SettingsSection from './SettingsSection'

const ProfileSection = () => {
  const queryClient = useQueryClient()
  const [logoFile, setLogoFile] = useState<File | null>(null)

  const { data: schoolProfile, isLoading } = useQuery({
    queryKey: [SCHOOL_PROFILE_QUERY_KEY],
    queryFn: getSchoolProfile,
  })

  const { mutate: saveProfile, isPending } = useMutation({
    mutationFn: (data: SchoolProfileFormData) => updateSchoolProfile(data, logoFile),
    onSuccess: () => {
      toast.success('School profile saved')
      setLogoFile(null)
      void queryClient.invalidateQueries({ queryKey: [SCHOOL_PROFILE_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: ['me'] })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to save school profile'))
    },
  })

  return (
    <SettingsSection
      title="School profile"
      description="Name, contact details, logo, and the prefix used on new student IDs. Existing student IDs stay as they are."
    >
      {isLoading ? (
        <LoadingSpinner className="mx-auto" />
      ) : (
        <>
          <SchoolLogoUpload onLogoChange={setLogoFile} logo={schoolProfile?.logo} />
          <SchoolProfileForm
            schoolProfile={schoolProfile}
            showStudentIdPrefix
            submitLabel={isPending ? 'Saving...' : 'Save profile'}
            onSubmit={saveProfile}
          />
        </>
      )}
    </SettingsSection>
  )
}

export default ProfileSection
