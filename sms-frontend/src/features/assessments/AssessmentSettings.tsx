import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import ActionBar from '@/components/shared/ActionBar'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import AssessmentSetupForm from '@/features/setup/assessment/components/AssessmentSetupForm'
import { getAssessmentSettings } from '@/features/setup/assessment/services'
import { getApiErrorMessage } from '@/utils'

const AssessmentSettings = () => {
  const [termSelection, setTermSelection] = useState<FilterSelection | undefined>(undefined)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['assessmentSettings', termSelection ?? 'default'],
    queryFn: () =>
      getAssessmentSettings(
        termSelection === undefined || termSelection === '' ? undefined : String(termSelection),
      ),
  })

  const terms = data?.terms ?? []
  const defaultTermId = data?.active_term_id ?? terms[0]?.id ?? ''
  const term: FilterSelection = termSelection !== undefined ? termSelection : defaultTermId
  const termId = term === '' ? undefined : String(term)
  const selected = terms.find((item) => item.id === termId)
  const readOnly = Boolean(data && !data.is_editable)
  const queryKey = ['assessmentSettings', termSelection ?? 'default'] as const

  const termOptions = useMemo(
    () =>
      terms.map((item) => ({
        value: item.id,
        label: item.is_ended ? `${item.label} (past)` : item.label,
      })),
    [terms],
  )

  return (
    <div className="space-y-6">
      <ActionBar back title="Assessment Settings">
        <FilterComponent
          filterName="Academic year and term"
          filterKey="term"
          options={termOptions}
          value={term}
          placeholder={isLoading ? 'Loading…' : 'Academic year & term'}
          onChange={setTermSelection}
        />
      </ActionBar>

      <div className="bg-white p-4 custom-shadow-md">
        <div className="mb-6">
          <h2 className="text-lg text-slate-900">Assessment Structure</h2>
          <div className="flex justify-between gap-2 items-center">
            <p className="text-sm text-slate-500 mt-1">
              Define how student results are calculated for each department in this term.
            </p>

            <p className="flex items-center gap-1 text-blue-500 text-sm">
              <Icon icon="hugeicons:information-circle" className="size-4" />
              <span>Ensure that Continuous Assessment and Exams together equal 100%.</span>
            </p>
          </div>
        </div>

        {readOnly ? (
          <p className="mb-4 flex items-start gap-2 text-sm text-slate-600">
            <Icon icon="hugeicons:information-circle" className="size-4 shrink-0 mt-0.5" />
            <span>
              {selected?.is_ended ? 'This term has ended. ' : ''}
              Assessment structure for this term is read-only. Changing a later term does not
              rewrite these results.
            </span>
          </p>
        ) : data?.has_recorded_marks ? (
          <p className="mb-4 flex items-start gap-2 text-sm text-amber-800">
            <Icon icon="hugeicons:information-circle" className="size-4 shrink-0 mt-0.5" />
            <span>
              Marks already exist for this term. Saving new weights or grade bands will
              recalculate this term’s totals and grades. Earlier terms stay unchanged.
            </span>
          </p>
        ) : null}

        {isError ? (
          <p className="text-sm text-red-600 py-6" role="alert">
            {getApiErrorMessage(error, 'Unable to load assessment settings.')}
          </p>
        ) : isLoading || !data ? (
          <LoadingSpinner className="mx-auto" />
        ) : (
          <AssessmentSetupForm
            config={data}
            termId={termId}
            readOnly={readOnly}
            queryKey={queryKey}
          />
        )}
      </div>
    </div>
  )
}

export default AssessmentSettings
