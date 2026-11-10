import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { FormWrapper } from '@/features/auth/components'
import AppLogo from '@/components/shared/AppLogo'
import { Button } from '@/components/ui'
import { acceptSchoolAdminInvite, getSchoolAdminInvite } from '../services'
import { useAuthStore } from '../store'
import { getApiErrorMessage } from '@/utils'

const InviteAcceptPage = () => {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const setVerificationPhone = useAuthStore((state) => state.setVerificationPhone)

  const inviteQuery = useQuery({
    queryKey: ['school-admin-invite', token],
    queryFn: () => getSchoolAdminInvite(token),
    enabled: Boolean(token),
  })

  const acceptMutation = useMutation({
    mutationFn: () => acceptSchoolAdminInvite(token),
    onSuccess: (data) => {
      setVerificationPhone(data.phone_number)
      toast.success(data.message)
      navigate('/auth/login', { replace: true })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to accept invitation.'))
    },
  })

  const invite = inviteQuery.data
  const canAccept = invite?.status === 'pending'

  return (
    <FormWrapper>
      <div className="mb-6 flex flex-col items-center gap-6 text-center">
        <AppLogo />
        <div>
          <h2 className="mb-3 text-2xl font-semibold">School admin invitation</h2>
          <p className="text-lg text-slate-400">
            Accept your invite, then sign in with your phone number.
          </p>
        </div>
      </div>

      {inviteQuery.isLoading ? (
        <p className="text-center text-slate-500">Loading invitation…</p>
      ) : inviteQuery.isError ? (
        <div className="space-y-4 text-center">
          <p className="text-red-600">This invitation is invalid or no longer available.</p>
          <Link to="/auth/login" className="text-blue-500 hover:text-blue-600">
            Go to login
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          <dl className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">School</dt>
              <dd className="font-medium">{invite?.school_name}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Name</dt>
              <dd className="font-medium">
                {invite?.first_name} {invite?.last_name}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Phone</dt>
              <dd className="font-medium">{invite?.phone_number}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Status</dt>
              <dd className="font-medium capitalize">{invite?.status}</dd>
            </div>
          </dl>

          {canAccept ? (
            <Button
              type="button"
              disabled={acceptMutation.isPending}
              onClick={() => acceptMutation.mutate()}
            >
              {acceptMutation.isPending ? 'Accepting…' : 'Accept invitation'}
            </Button>
          ) : (
            <p className="text-center text-slate-500">
              This invitation cannot be accepted. Please contact SCHOOLASST support.
            </p>
          )}

          <p className="text-center text-sm text-slate-500">
            Already accepted?{' '}
            <Link to="/auth/login" className="text-blue-500 hover:text-blue-600">
              Log in
            </Link>
          </p>
        </div>
      )}
    </FormWrapper>
  )
}

export default InviteAcceptPage
