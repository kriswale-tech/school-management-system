import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Icon } from '@iconify/react'
import { Link, useNavigate } from 'react-router-dom'
import { Button, Modal } from '@/components/ui'
import { useAuthStore } from '@/features/auth/store'
import { completeSetup } from '@/features/setup/services/services'
import type { Setup } from '@/features/setup/types/types'
import { handleSetupProgressResponse } from '@/features/setup/utils/handle-setup-progress-response'
import { getApiErrorMessage, mergeClasses } from '@/utils'

type CompleteSetupModalProps = {
  open: boolean
  onClose: () => void
  setup: Setup
}

const CompleteSetupModal = ({ open, onClose, setup }: CompleteSetupModalProps) => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const user = useAuthStore((state) => state.user)

  const { mutate: confirmCompletion, isPending } = useMutation({
    mutationFn: completeSetup,
    onSuccess: (response) => {
      toast.success('School setup completed')
      void queryClient.invalidateQueries({ queryKey: ['setup'] })
      onClose()
      handleSetupProgressResponse(response, { navigate, user, setUser })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to complete setup. Please review your steps.'))
    },
  })

  const incompleteRequiredSteps = setup.steps.filter(
    (step) => step.required && !step.completed,
  )

  const isStepAttentionNeeded = (step: Setup['steps'][number]) =>
    !step.completed && step.required

  return (
    <Modal
      open={open}
      title="Complete school setup"
      onClose={onClose}
      scrollable
      className="max-w-2xl"
    >
      <div className="space-y-6">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex gap-3">
            <Icon icon="hugeicons:information-circle" className="mt-0.5 size-5 shrink-0 text-blue-500" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-slate-900">Review before you finish</p>
              <p className="text-sm text-slate-600">
                Please verify that all school information is correct and free of errors. You can
                revisit any step below before confirming completion.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-900">Setup steps</p>
          <ul className="space-y-2">
            {setup.steps.map((step) => (
              <li key={step.step}>
                <Link
                  to={`/setup/${step.step}`}
                  onClick={onClose}
                  className={mergeClasses(
                    'flex items-center justify-between gap-3 rounded-lg border px-4 py-3 transition-colors',
                    step.completed
                      ? 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
                      : isStepAttentionNeeded(step)
                        ? 'border-amber-200 bg-amber-50 hover:border-amber-300'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50',
                  )}
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <Icon
                      icon={
                        step.completed
                          ? 'hugeicons:checkmark-circle-02'
                          : isStepAttentionNeeded(step)
                            ? 'hugeicons:alert-circle'
                            : 'hugeicons:circle'
                      }
                      className={mergeClasses(
                        'size-5 shrink-0',
                        step.completed
                          ? 'text-emerald-600'
                          : isStepAttentionNeeded(step)
                            ? 'text-amber-600'
                            : 'text-slate-400',
                      )}
                    />
                    <span className="text-sm font-medium text-slate-900">{step.name}</span>
                  </div>
                  <span className="shrink-0 text-xs font-medium text-slate-500">Review</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {incompleteRequiredSteps.length > 0 ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {incompleteRequiredSteps.length} required step
            {incompleteRequiredSteps.length === 1 ? '' : 's'} still marked incomplete. You can still
            attempt completion, but validation may fail if required data is missing.
          </div>
        ) : null}

        <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
          <div className="flex gap-3">
            <Icon icon="hugeicons:time-quarter-pass" className="mt-0.5 size-5 shrink-0 text-blue-600" />
            <p className="text-sm text-blue-900">
              Saving and validating your setup may take a little while. Please stay on this page
              until the process finishes.
            </p>
          </div>
        </div>

        <div className="space-y-3 pt-2">
          <Button
            type="button"
            variant="solid"
            className="py-4 text-base font-semibold"
            onClick={() => confirmCompletion()}
            loading={isPending}
            loadingText="Validating setup..."
          >
            Confirm Completion
          </Button>
          <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Go back and review
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default CompleteSetupModal
