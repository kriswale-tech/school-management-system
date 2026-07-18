import toast from 'react-hot-toast'
import { Icon } from '@iconify/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import Button from '@/components/ui/Button'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { useAuthStore } from '@/features/auth/store'
import { handleSetupProgressResponse } from '@/features/setup/utils/handle-setup-progress-response'
import { getApiErrorMessage } from '@/utils'
import FeesSetupForm from './components/FeesSetupForm'
import FeesSetupTable from './components/FeesSetupTable'
import { completeFeeSetup, getFeeStructures } from './services'

const Fees = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const user = useAuthStore((state) => state.user)

  const { data, isLoading } = useQuery({
    queryKey: ['feeStructures'],
    queryFn: getFeeStructures,
  })

  const { mutate: completeSetup, isPending: isCompleting } = useMutation({
    mutationFn: completeFeeSetup,
    onSuccess: (response) => {
      toast.success('Fees setup saved')
      void queryClient.invalidateQueries({ queryKey: ['setup'] })
      void queryClient.invalidateQueries({ queryKey: ['feeStructures'] })
      handleSetupProgressResponse(response, { navigate, user, setUser })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to complete fees setup'))
    },
  })

  if (isLoading || !data) {
    return <LoadingSpinner className="mx-auto" />
  }

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h2 className="text-lg text-slate-900">Fees Setup (Applies to current term)</h2>
        <div className="flex justify-between gap-2 items-center">
          <p className="text-sm text-slate-500 mt-1">Define the fees structure for your school.</p>

          <p className="flex items-center gap-1 text-blue-500 text-sm">
            <Icon icon="hugeicons:information-circle" className="size-4 " />{' '}
            <span>You can add or edit fees for your school.</span>
          </p>
        </div>
      </div>

      <FeesSetupForm />

      <div>
        <h3 className="text-lg mb-2 text-slate-900">{data.fee_structure.name}</h3>
        <FeesSetupTable feeItems={data.fee_items} />
      </div>

      <Button type="button" variant="outline" onClick={() => completeSetup()} loading={isCompleting}>
        Proceed to Next Step
      </Button>
    </div>
  )
}

export default Fees
