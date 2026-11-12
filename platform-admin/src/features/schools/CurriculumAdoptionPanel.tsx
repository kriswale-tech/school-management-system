import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import { adoptSchoolCurriculum, getSchoolAdoption } from '@/features/curriculum/services'
import { useAuthStore } from '@/features/auth/store'

function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string } | undefined
    return data?.detail || 'Request failed'
  }
  return 'Request failed'
}

export default function CurriculumAdoptionPanel({ schoolId }: { schoolId: string }) {
  const role = useAuthStore((state) => state.user?.role)
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const canAdopt = role === 'super_admin' || role === 'curriculum'

  const planQuery = useQuery({
    queryKey: ['platform-school-curriculum', schoolId],
    queryFn: () => getSchoolAdoption(schoolId),
    enabled: canAdopt && Boolean(schoolId),
  })

  const adoptMutation = useMutation({
    mutationFn: () => adoptSchoolCurriculum(schoolId),
    onSuccess: (result) => {
      toast.success(
        result.scheduled
          ? `Version ${result.to_version} will take effect when the next term starts`
          : `Version ${result.to_version} is now in use`,
      )
      setOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['platform-school-curriculum', schoolId] })
      void queryClient.invalidateQueries({ queryKey: ['platform-curriculum'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  if (!canAdopt || !planQuery.data || planQuery.data.up_to_date) return null

  const plan = planQuery.data

  return (
    <section className="mb-8 rounded-2xl border border-amber-200 bg-amber-50 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
            Curriculum {plan.to_version} is available
          </h2>
          <p className="mt-1 text-sm text-amber-950">
            This school is on {plan.from_version || 'an older copy'}.{' '}
            {plan.summary
              || 'This term stays as it is. The new classes and subjects take effect when the next term starts.'}{' '}
            Records that already have marks keep their current name.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="rounded-xl bg-[var(--color-accent)] px-3 py-2 text-xs font-semibold text-white"
        >
          {open ? 'Hide changes' : 'Review and adopt'}
        </button>
      </div>
      {open && (
        <div className="mt-4">
          <ul className="space-y-1 text-sm">
            {plan.changes.length === 0 ? (
              <li>
                The standard matches this school.{' '}
                {plan.applies_on === 'now'
                  ? 'Applying updates the version now.'
                  : 'Adopting keeps this term as it is and records the version for the next term.'}
              </li>
            ) : (
              plan.changes.map((change) => (
                <li key={`${change.action}-${change.summary}`}>{change.summary}</li>
              ))
            )}
          </ul>
          <button
            type="button"
            disabled={adoptMutation.isPending}
            onClick={() => adoptMutation.mutate()}
            className="mt-4 rounded-xl bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white"
          >
            {plan.applies_on === 'now'
              ? `Apply version ${plan.to_version} now`
              : `Adopt version ${plan.to_version} for the next term`}
          </button>
        </div>
      )}
    </section>
  )
}
