import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ButtonTabComponent } from '@/components/shared'
import { Button } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import { getFeeDeskFilterOptions } from '@/features/fees/services'
import { FEE_DESK_FILTERS_QUERY_KEY } from '@/features/fees/utils'
import { getApiErrorMessage } from '@/utils'
import { getStudentCurrentYearFees, getStudentPayments } from '../../services'
import {
  formatFeeAmount,
  getFeePaymentStatusClass,
  STUDENT_FEES_QUERY_KEY,
  STUDENT_PAYMENTS_QUERY_KEY,
} from '../../utils'
import DownloadPaymentHistoryModal from '../DownloadPaymentHistoryModal'
import FeeYearBreakdown from '../FeeYearBreakdown'
import PaymentHistoryTable from '../PaymentHistoryTable'

const TAB_BREAKDOWN = 'Fees Breakdown'
const TAB_HISTORY = 'Payment History'

const TAB_FROM_QUERY: Record<string, string> = {
  breakdown: TAB_BREAKDOWN,
  history: TAB_HISTORY,
}

const QUERY_FROM_TAB: Record<string, string> = {
  [TAB_BREAKDOWN]: 'breakdown',
  [TAB_HISTORY]: 'history',
}

type FeesProps = {
  studentId: string
}

const Fees = ({ studentId }: FeesProps) => {
  const [searchParams, setSearchParams] = useSearchParams()
  const feesTabParam = searchParams.get('feesTab')
  const activeTab =
    (feesTabParam && TAB_FROM_QUERY[feesTabParam.toLowerCase()]) || TAB_BREAKDOWN
  const [termSelection, setTermSelection] = useState<FilterSelection | undefined>(undefined)
  const [downloadOpen, setDownloadOpen] = useState(false)

  const selectFeesTab = (label: string) => {
    const key = QUERY_FROM_TAB[label]
    if (!key) return
    const next = new URLSearchParams(searchParams)
    next.set('tab', 'fees')
    if (key === 'breakdown') next.delete('feesTab')
    else next.set('feesTab', key)
    setSearchParams(next, { replace: true })
  }

  const { data: filterOptions, isLoading: filtersLoading } = useQuery({
    queryKey: [FEE_DESK_FILTERS_QUERY_KEY],
    queryFn: getFeeDeskFilterOptions,
  })

  const term: FilterSelection =
    termSelection !== undefined ? termSelection : (filterOptions?.active_term_id ?? '')

  const filtersReady = Boolean(filterOptions)
  const feeParams = useMemo(
    () => ({
      term: term === '' ? undefined : String(term),
    }),
    [term],
  )

  const {
    data,
    isLoading: feesLoading,
    isError: feesError,
    error: feesErrorValue,
  } = useQuery({
    queryKey: [STUDENT_FEES_QUERY_KEY, studentId, feeParams],
    queryFn: () => getStudentCurrentYearFees(studentId, feeParams),
    enabled: Boolean(studentId) && filtersReady && activeTab === TAB_BREAKDOWN,
  })

  const {
    data: payments = [],
    isLoading: paymentsLoading,
    isError: paymentsError,
    error: paymentsErrorValue,
  } = useQuery({
    queryKey: [STUDENT_PAYMENTS_QUERY_KEY, studentId, feeParams],
    queryFn: () => getStudentPayments(studentId, feeParams),
    enabled: Boolean(studentId) && filtersReady && activeTab === TAB_HISTORY,
  })

  const termOptions = (filterOptions?.terms ?? []).map((item) => ({
    value: item.id,
    label: item.label,
  }))

  const academicYearOptions = (filterOptions?.academic_years ?? []).map((item) => ({
    value: item.id,
    label: item.academic_year,
  }))

  const paidClass = data ? getFeePaymentStatusClass(data.payment_status) : ''

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ButtonTabComponent
          activeTab={activeTab}
          tabs={[
            {
              label: TAB_BREAKDOWN,
              onClick: () => selectFeesTab(TAB_BREAKDOWN),
            },
            {
              label: TAB_HISTORY,
              onClick: () => selectFeesTab(TAB_HISTORY),
            },
          ]}
        />
        <FilterComponent
          filterName="Term"
          filterKey="student_fees_term"
          options={termOptions}
          value={term}
          placeholder={filtersLoading ? 'Loading…' : 'Academic Year & Term'}
          onChange={setTermSelection}
        />
      </div>

      {activeTab === TAB_BREAKDOWN ? (
        <div className="space-y-6 bg-gray-100 p-4">
          {!filtersReady || feesLoading ? (
            <p className="text-sm text-slate-500 py-6">Loading fees…</p>
          ) : feesError || !data ? (
            <p className="text-sm text-red-600 py-6" role="alert">
              {getApiErrorMessage(feesErrorValue, 'Unable to load student fees.')}
            </p>
          ) : (
            <>
              <div className="space-y-1 border-b border-slate-300 pb-4">
                <h3 className="text-lg font-medium text-slate-900">
                  {data.academic_year} Academic Year Fees Breakdown
                </h3>
                <p className={`text-sm font-medium ${paidClass}`}>
                  Fees Paid · {formatFeeAmount(data.total_paid)} /{' '}
                  {formatFeeAmount(data.total_billed)}
                </p>
              </div>
              <FeeYearBreakdown yearFees={data} />
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4  bg-gray-100 p-4">
          <div className="flex justify-end">
            <Button
              type="button"
              className="w-fit py-2 text-sm"
              onClick={() => setDownloadOpen(true)}
            >
              <Icon icon="hugeicons:download-04" className="size-4" />
              Download
            </Button>
          </div>

          {!filtersReady || paymentsLoading ? (
            <p className="text-sm text-slate-500 py-6">Loading payments…</p>
          ) : paymentsError ? (
            <p className="text-sm text-red-600 py-6" role="alert">
              {getApiErrorMessage(paymentsErrorValue, 'Unable to load payment history.')}
            </p>
          ) : (
            <PaymentHistoryTable payments={payments} />
          )}
        </div>
      )}

      <DownloadPaymentHistoryModal
        open={downloadOpen}
        onClose={() => setDownloadOpen(false)}
        academicYearOptions={academicYearOptions}
        termOptions={termOptions}
      />
    </div>
  )
}

export default Fees
