import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/app/api/api'
import { useAuth } from '@/features/auth/hooks'
import { SCHOOL_ALERTS_QUERY_KEY } from '@/features/settings/services'
import { ADMIN_DASHBOARD_QUERY_KEY } from '@/features/dashboard/utils'
import { getApiErrorMessage } from '@/utils'

type AdoptionChange = { action: string; kind: string; summary: string }

type AdoptionPlan = {
  up_to_date: boolean
  from_version: string | null
  to_version: string
  changes: AdoptionChange[]
  applies_on?: 'next_term' | 'now'
  scheduled?: boolean
  applied?: boolean
  summary?: string
}

async function getAdoption() {
  const { data } = await api.get<AdoptionPlan>('/schools/curriculum-adoption/')
  return data
}

async function adoptCurriculum() {
  const { data } = await api.post<AdoptionPlan>('/schools/curriculum-adoption/')
  return data
}

export default function CurriculumUpdateBanner() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const isAdmin = user?.role === 'admin'

  const planQuery = useQuery({
    queryKey: ['curriculum-adoption'],
    queryFn: getAdoption,
    enabled: isAdmin,
  })

  const adoptMutation = useMutation({
    mutationFn: adoptCurriculum,
    onSuccess: (result) => {
      toast.success(
        result.scheduled
          ? `Version ${result.to_version} will take effect when the next term starts`
          : `Curriculum ${result.to_version} is now in use`,
      )
      setOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['curriculum-adoption'] })
      void queryClient.invalidateQueries({ queryKey: ['manageClasses', 'curriculum'] })
      void queryClient.invalidateQueries({ queryKey: ['classes'] })
      void queryClient.invalidateQueries({ queryKey: ['classAndSubjects'] })
      void queryClient.invalidateQueries({ queryKey: [SCHOOL_ALERTS_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: [ADMIN_DASHBOARD_QUERY_KEY] })
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not adopt the curriculum')),
  })

  if (!isAdmin || !planQuery.data || planQuery.data.up_to_date) return null

  const plan = planQuery.data

  return (
    <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-amber-950">
            Ghana curriculum {plan.to_version} is available
          </h2>
          <p className="mt-1 text-sm text-amber-950">
            You are on {plan.from_version || 'an older copy'}.{' '}
            {plan.summary
              || 'This term stays as it is. The new classes and subjects take effect when the next term starts.'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="rounded-xl bg-amber-900 px-3 py-2 text-sm font-semibold text-white"
        >
          {open ? 'Hide changes' : 'Review changes'}
        </button>
      </div>
      {open && (
        <div className="mt-4">
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-950">
            {plan.changes.length === 0 ? (
              <li>
                The standard matches your classes.{' '}
                {plan.applies_on === 'now'
                  ? 'Adopting applies this version now.'
                  : 'Adopting keeps this term as it is and records the version for the next term.'}
              </li>
            ) : (
              plan.changes.map((change) => <li key={`${change.action}-${change.summary}`}>{change.summary}</li>)
            )}
          </ul>
          <button
            type="button"
            disabled={adoptMutation.isPending}
            onClick={() => adoptMutation.mutate()}
            className="mt-4 rounded-xl bg-amber-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            Adopt {plan.applies_on === 'now' ? 'now' : 'for the next term'}
          </button>
        </div>
      )}
    </section>
  )
}
