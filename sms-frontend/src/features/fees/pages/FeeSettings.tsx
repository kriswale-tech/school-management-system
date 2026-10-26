import toast from 'react-hot-toast'
import { Icon } from '@iconify/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { ConfirmDialog } from '@/components/shared'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { Button } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import { useAuthStore } from '@/features/auth/store'
import FeesSetupForm from '@/features/setup/fees/components/FeesSetupForm'
import FeesSetupTable from '@/features/setup/fees/components/FeesSetupTable'
import {
  applyFeeStructure,
  copyFeeStructureFromPrevious,
  createFeeStructureItem,
  deleteFeeStructureItem,
  getFeeDeskFilterOptions,
  getFeeStructure,
  publishFeeStructure,
  updateFeeStructureItem,
} from '../services'
import {
  FEE_DESK_FILTERS_QUERY_KEY,
  FEE_DESK_QUERY_KEY,
  FEE_DESK_STATS_QUERY_KEY,
  FEE_NEXT_TERM_PREP_QUERY_KEY,
  FEE_STRUCTURE_QUERY_KEY,
} from '../utils'
import { getApiErrorMessage } from '@/utils'

const statusClassName = (status: string) => {
  if (status === 'applied') return 'text-emerald-700 bg-emerald-50 border-emerald-200'
  if (status === 'published') return 'text-blue-700 bg-blue-50 border-blue-200'
  return 'text-slate-700 bg-slate-100 border-slate-200'
}

type FeeSettingsProps = {
  embedded?: boolean
}

const FeeSettings = ({ embedded = false }: FeeSettingsProps) => {
  const queryClient = useQueryClient()
  const isAdmin = useAuthStore((state) => state.user?.role === 'admin')
  const [searchParams] = useSearchParams()
  const [termSelection, setTermSelection] = useState<FilterSelection | undefined>(undefined)
  const [applyOpen, setApplyOpen] = useState(false)
  const [publishOpen, setPublishOpen] = useState(false)

  const { data: filterOptions, isLoading: filtersLoading } = useQuery({
    queryKey: [FEE_DESK_FILTERS_QUERY_KEY],
    queryFn: getFeeDeskFilterOptions,
  })

  const settingsTerms = useMemo(
    () =>
      (filterOptions?.terms ?? []).filter(
        (item) => !item.is_ended || item.has_fee_structure,
      ),
    [filterOptions?.terms],
  )

  const requestedTermId = searchParams.get('term')
  const defaultTermId =
    requestedTermId && settingsTerms.some((item) => item.id === requestedTermId)
      ? requestedTermId
      : filterOptions?.active_term_id &&
          settingsTerms.some((item) => item.id === filterOptions.active_term_id)
        ? filterOptions.active_term_id
        : (settingsTerms[0]?.id ?? '')

  const term: FilterSelection = termSelection !== undefined ? termSelection : defaultTermId
  const termId = term === '' ? undefined : String(term)
  const structureQueryKey = [FEE_STRUCTURE_QUERY_KEY, termId]

  const selectedTermMeta = settingsTerms.find((item) => item.id === termId)

  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: structureQueryKey,
    queryFn: () => getFeeStructure(termId),
    enabled: Boolean(filterOptions) && Boolean(termId),
  })

  const invalidateStructureQueries = () => {
    void queryClient.invalidateQueries({ queryKey: structureQueryKey })
    void queryClient.invalidateQueries({ queryKey: [FEE_DESK_QUERY_KEY] })
    void queryClient.invalidateQueries({ queryKey: [FEE_DESK_STATS_QUERY_KEY] })
    void queryClient.invalidateQueries({ queryKey: [FEE_DESK_FILTERS_QUERY_KEY] })
    void queryClient.invalidateQueries({ queryKey: [FEE_NEXT_TERM_PREP_QUERY_KEY] })
  }

  const { mutate: publish, isPending: isPublishing } = useMutation({
    mutationFn: publishFeeStructure,
    onSuccess: () => {
      toast.success('Fee catalog published')
      invalidateStructureQueries()
      setPublishOpen(false)
    },
    onError: (err) => {
      toast.error(getApiErrorMessage(err, 'Unable to publish fees'))
    },
  })

  const { mutate: apply, isPending: isApplying } = useMutation({
    mutationFn: applyFeeStructure,
    onSuccess: () => {
      toast.success('Fees applied to enrolled students')
      invalidateStructureQueries()
      setApplyOpen(false)
    },
    onError: (err) => {
      toast.error(getApiErrorMessage(err, 'Unable to apply fees'))
    },
  })

  const { mutate: copyFromPrevious, isPending: isCopying } = useMutation({
    mutationFn: copyFeeStructureFromPrevious,
    onSuccess: () => {
      toast.success('Fee items copied from the previous term')
      invalidateStructureQueries()
    },
    onError: (err) => {
      toast.error(getApiErrorMessage(err, 'Unable to copy fee items'))
    },
  })

  const termOptions = settingsTerms.map((item) => ({
    value: item.id,
    label: item.is_ended ? `${item.label} (past)` : item.label,
  }))

  const structure = data?.fee_structure
  const editable = Boolean(structure?.is_editable)
  const locked = Boolean(structure?.is_locked)
  const termEnded = Boolean(structure?.term_ended || selectedTermMeta?.is_ended)
  const canPublish = Boolean(structure?.can_publish)
  const canCopy = Boolean(structure?.can_copy_from_previous)
  const canApply = Boolean(isAdmin && structure?.can_apply)
  const emptyCatalog = Boolean(structure && structure.item_count === 0 && editable)

  const termControls = (
    <>
      <FilterComponent
        filterName="Term"
        filterKey="term"
        options={termOptions}
        value={term}
        placeholder={filtersLoading ? 'Loading…' : 'Academic Year & Term'}
        onChange={setTermSelection}
      />
      {canPublish ? (
        <Button
          type="button"
          className="py-2 text-sm max-w-fit"
          onClick={() => setPublishOpen(true)}
        >
          Publish
        </Button>
      ) : null}
      {canApply ? (
        <Button
          type="button"
          variant="outline"
          className="py-2 text-sm max-w-fit"
          onClick={() => setApplyOpen(true)}
        >
          Apply to enrolled students
        </Button>
      ) : null}
    </>
  )

  return (
    <div className="space-y-6">
      {embedded ? (
        <div className="flex flex-wrap items-center justify-end gap-3">{termControls}</div>
      ) : (
        <ActionBar back title="Fees Settings">
          {termControls}
        </ActionBar>
      )}

      {!filterOptions || (Boolean(termId) && isLoading) ? (
        <LoadingSpinner className="mx-auto" />
      ) : isError ? (
        <p className="text-sm text-red-600" role="alert">
          {getApiErrorMessage(error, 'Unable to load fee settings for this term.')}
        </p>
      ) : !data || !structure ? (
        <p className="text-sm text-slate-500">Select a term to manage fee items.</p>
      ) : (
        <div className={embedded ? 'space-y-6' : 'bg-white p-4 custom-shadow-md space-y-6'}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg text-slate-900">{structure.name}</h2>
              <p className="text-sm text-slate-500 mt-1">
                {structure.academic_year} · {structure.term_name}
              </p>
            </div>
            <span
              className={`text-xs font-medium px-2 py-1 border ${statusClassName(structure.status)}`}
            >
              {structure.status_display}
            </span>
          </div>

          {termEnded ? (
            <p className="flex items-start gap-2 text-sm text-slate-600">
              <Icon icon="hugeicons:information-circle" className="size-4 shrink-0 mt-0.5" />
              <span>
                This term has ended. The catalog is read-only — amounts cannot be changed or
                re-applied.
              </span>
            </p>
          ) : locked ? (
            <p className="flex items-start gap-2 text-sm text-slate-600">
              <Icon icon="hugeicons:information-circle" className="size-4 shrink-0 mt-0.5" />
              <span>
                This term is locked — amounts cannot change. Students who join later still receive
                these fee items automatically.
              </span>
            </p>
          ) : structure.status === 'published' ? (
            <p className="flex items-start gap-2 text-sm text-slate-600">
              <Icon icon="hugeicons:information-circle" className="size-4 shrink-0 mt-0.5" />
              <span>
                This catalog is published. An admin will apply it when opening the next term (or
                via Apply). You can still edit amounts until it is applied.
              </span>
            </p>
          ) : (
            <p className="flex items-start gap-2 text-sm text-slate-600">
              <Icon icon="hugeicons:information-circle" className="size-4 shrink-0 mt-0.5" />
              <span>
                Add or edit items for this term, then publish when the catalog is ready. Applying
                bills enrolled students and locks amounts.
              </span>
            </p>
          )}

          {emptyCatalog ? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center space-y-3">
              <p className="text-sm font-medium text-slate-900">No fees for this term yet</p>
              <p className="text-sm text-slate-600 max-w-md mx-auto">
                Copy items from the previous term and adjust amounts, or start blank and add items
                below.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-3">
                {canCopy ? (
                  <Button
                    type="button"
                    loading={isCopying}
                    loadingText="Copying"
                    onClick={() => {
                      if (termId) copyFromPrevious(termId)
                    }}
                  >
                    Copy from previous term
                  </Button>
                ) : (
                  <p className="text-xs text-slate-500">
                    No previous term with fee items to copy from.
                  </p>
                )}
              </div>
            </div>
          ) : null}

          {editable ? (
            <FeesSetupForm
              queryKey={structureQueryKey}
              onCreate={(payload) =>
                createFeeStructureItem({
                  ...payload,
                  term: structure.term_id,
                })
              }
            />
          ) : null}

          <FeesSetupTable
            feeItems={data.fee_items}
            queryKey={structureQueryKey}
            readOnly={!editable}
            showTerm
            onUpdate={updateFeeStructureItem}
            onDelete={deleteFeeStructureItem}
          />
        </div>
      )}

      <ConfirmDialog
        open={publishOpen}
        title="Publish fees"
        message="This marks the catalog as ready. Amounts can still be edited until an admin applies the catalog (usually when opening the next term)."
        confirmLabel="Publish"
        onClose={() => setPublishOpen(false)}
        onConfirm={() => {
          if (structure) publish(structure.id)
        }}
        isLoading={isPublishing}
      />

      <ConfirmDialog
        open={applyOpen}
        title="Apply fees"
        message="This bills currently enrolled students for this term and locks the catalog. You will not be able to change amounts afterwards. Students who join later will still receive these items."
        confirmLabel="Apply fees"
        onClose={() => setApplyOpen(false)}
        onConfirm={() => {
          if (structure) apply(structure.id)
        }}
        isLoading={isApplying}
      />
    </div>
  )
}

export default FeeSettings
