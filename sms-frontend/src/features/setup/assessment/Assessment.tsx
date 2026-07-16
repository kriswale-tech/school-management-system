import toast from 'react-hot-toast'
import { Icon } from '@iconify/react/dist/iconify.cjs'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { useAuthStore } from '@/features/auth/store'
import { handleSetupProgressResponse } from '@/features/setup/utils/handle-setup-progress-response'
import { getApiErrorMessage } from '@/utils'
import { completeAssessmentSetup, getAssessmentConfig } from './services'
import AssessmentSetupForm from './components/AssessmentSetupForm'

const Assessment = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const user = useAuthStore((state) => state.user)

  const { data: config, isLoading } = useQuery({
    queryKey: ['assessmentConfig'],
    queryFn: getAssessmentConfig,
  })

  const { mutate: completeSetup, isPending: isCompleting } = useMutation({
    mutationFn: completeAssessmentSetup,
    onSuccess: (response) => {
      toast.success('Assessment setup saved')
      void queryClient.invalidateQueries({ queryKey: ['setup'] })
      void queryClient.invalidateQueries({ queryKey: ['assessmentConfig'] })
      handleSetupProgressResponse(response, { navigate, user, setUser })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to complete assessment setup'))
    },
  })

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg text-slate-900">Assessment Structure</h2>
        <div className="flex justify-between gap-2 items-center">
          <p className="text-sm text-slate-500 mt-1">
            Define how student results are calculated for each department.
          </p>

          <p className="flex items-center gap-1 text-blue-500 text-sm">
            <Icon icon="hugeicons:information-circle" className="size-4 " />{' '}
            <span>Ensure that Continuous Assessment and Exams together equal 100%.</span>
          </p>
        </div>
      </div>

      {isLoading || !config ? (
        <LoadingSpinner className="mx-auto" />
      ) : (
        <AssessmentSetupForm
          config={config}
          onComplete={() => completeSetup()}
          isCompleting={isCompleting}
        />
      )}
    </div>
  )
}

export default Assessment
