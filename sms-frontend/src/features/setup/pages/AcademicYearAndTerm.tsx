import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import AcademicYearAndTermForm from '@/features/setup/components/academic-year-term/AcademicYearAndTermForm'
import type {
  AcademicYearAndTerm as AcademicYearAndTermType,
  AcademicYearAndTermFormData,
} from '@/features/setup/types/types'
import {
  getAcademicYearAndTerm,
  updateAcademicYearAndTerm,
} from '@/features/setup/services/services'
import { mapFormToApiPayload } from '@/features/setup/utils/academic-year'
import { handleSetupProgressResponse } from '@/features/setup/utils/handle-setup-progress-response'
import { useAuthStore } from '@/features/auth/store'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'

const AcademicYearAndTerm = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const user = useAuthStore((state) => state.user)

  const { data: academicYearAndTerm, isLoading } = useQuery<AcademicYearAndTermType>({
    queryKey: ['academicYearAndTerm'],
    queryFn: getAcademicYearAndTerm,
  })

  const { mutate: saveAcademicYearAndTerm } = useMutation({
    mutationFn: updateAcademicYearAndTerm,
    onSuccess: (response) => {
      toast.success('Academic year and term saved')
      void queryClient.invalidateQueries({ queryKey: ['setup'] })
      void queryClient.invalidateQueries({ queryKey: ['academicYearAndTerm'] })

      handleSetupProgressResponse(response, { navigate, user, setUser })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to save academic year and term'))
    },
  })

  const handleSubmit = (data: AcademicYearAndTermFormData) => {
    saveAcademicYearAndTerm(mapFormToApiPayload(data))
  }

  if (isLoading) return <LoadingSpinner className="mx-auto" />

  return (
    <AcademicYearAndTermForm onSubmit={handleSubmit} academicYearAndTerm={academicYearAndTerm} />
  )
}

export default AcademicYearAndTerm
