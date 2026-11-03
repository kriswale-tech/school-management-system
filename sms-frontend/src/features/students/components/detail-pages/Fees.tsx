import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ButtonTabComponent } from '@/components/shared'
import { Button, SearchComponent } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import ReceiptViewModal from '@/features/fees/components/ReceiptViewModal'
import { getFeeDeskFilterOptions } from '@/features/fees/services'
import {
  FEE_DESK_ALL_TIME_TERM,
  FEE_DESK_FILTERS_QUERY_KEY,
  isFeeDeskAllTimeTerm,
} from '@/features/fees/utils'
import { getApiErrorMessage } from '@/utils'
import {
  getStudentCurrentYearFees,
  getStudentFeeHistory,
  getStudentPayments,
} from '../../services'
import {
  formatFeeAmount,
  getFeePaymentStatusClass,
  STUDENT_FEE_HISTORY_QUERY_KEY,
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
  const [receiptSearch, setReceiptSearch] = useState('')
  const [viewReceiptId, setViewReceiptId] = useState<string | null>(null)

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
    termSelection !== undefined ? termSelection : FEE_DESK_ALL_TIME_TERM
  const isAllTime = isFeeDeskAllTimeTerm(typeof term === 'string' ? term : '')

  const filtersReady = Boolean(filterOptions)
  const feeParams = useMemo(
    () => ({
      term: !isAllTime && term !== '' ? String(term) : undefined,
    }),
    [term, isAllTime],
  )

  const paymentParams = useMemo(
    () => ({
      ...feeParams,
      search: receiptSearch.trim() || undefined,
    }),
    [feeParams, receiptSearch],
  )

  const {
    data,
    isLoading: feesLoading,
    isError: feesError,
    error: feesErrorValue,
  } = useQuery({
    queryKey: [STUDENT_FEES_QUERY_KEY, studentId, feeParams],
    queryFn: () => getStudentCurrentYearFees(studentId, feeParams),
    enabled: Boolean(studentId) && filtersReady && activeTab === TAB_BREAKDOWN && !isAllTime,
  })

  const {
    data: feeHistory,
    isLoading: historyFeesLoading,
    isError: historyFeesError,
    error: historyFeesErrorValue,
  } = useQuery({
    queryKey: [STUDENT_FEE_HISTORY_QUERY_KEY, studentId],
    queryFn: () => getStudentFeeHistory(studentId),
    enabled: Boolean(studentId) && filtersReady && activeTab === TAB_BREAKDOWN && isAllTime,
  })

  const {
    data: payments = [],
    isLoading: paymentsLoading,
    isError: paymentsError,
    error: paymentsErrorValue,
  } = useQuery({
    queryKey: [STUDENT_PAYMENTS_QUERY_KEY, studentId, paymentParams],
    queryFn: () => getStudentPayments(studentId, paymentParams),
    enabled: Boolean(studentId) && filtersReady && activeTab === TAB_HISTORY,
  })

  const termOptions = [
    { value: FEE_DESK_ALL_TIME_TERM, label: 'All time' },
    ...(filterOptions?.terms ?? []).map((item) => ({
      value: item.id,
      label: item.label,
    })),
  ]

  const academicYearOptions = (filterOptions?.academic_years ?? []).map((item) => ({
    value: item.id,
    label: item.academic_year,
  }))

  const allTimeTotals = useMemo(() => {
    const years = feeHistory?.years ?? []
    const totalBilled = years.reduce((sum, year) => sum + Number(year.total_billed || 0), 0)
    const totalPaid = years.reduce((sum, year) => sum + Number(year.total_paid || 0), 0)
    return { totalBilled, totalPaid }
  }, [feeHistory])

  const paidClass = data ? getFeePaymentStatusClass(data.payment_status) : ''
  const allTimePaidClass =
    allTimeTotals.totalBilled <= 0
      ? getFeePaymentStatusClass('no_fees')
      : allTimeTotals.totalPaid >= allTimeTotals.totalBilled
        ? getFeePaymentStatusClass('fully_paid')
        : allTimeTotals.totalPaid > 0
          ? getFeePaymentStatusClass('partially_paid')
          : getFeePaymentStatusClass('owing')

  const breakdownLoading = isAllTime ? historyFeesLoading : feesLoading
  const breakdownError = isAllTime ? historyFeesError : feesError
  const breakdownErrorValue = isAllTime ? historyFeesErrorValue : feesErrorValue

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
          {!filtersReady || breakdownLoading ? (
            <p className="text-sm text-slate-500 py-6">Loading fees…</p>
          ) : breakdownError || (isAllTime ? !feeHistory : !data) ? (
            <p className="text-sm text-red-600 py-6" role="alert">
              {getApiErrorMessage(breakdownErrorValue, 'Unable to load student fees.')}
            </p>
          ) : isAllTime ? (
            <>
              <div className="space-y-1 border-b border-slate-300 pb-4">
                <h3 className="text-lg font-medium text-slate-900">All-time Fees Breakdown</h3>
                <p className={`text-sm font-medium ${allTimePaidClass}`}>
                  Fees Paid · {formatFeeAmount(allTimeTotals.totalPaid)} /{' '}
                  {formatFeeAmount(allTimeTotals.totalBilled)}
                </p>
              </div>
              {(feeHistory?.years ?? []).length === 0 ? (
                <p className="text-sm text-slate-500">No fee history for this student.</p>
              ) : (
                (feeHistory?.years ?? []).map((year) => (
                  <FeeYearBreakdown key={year.academic_year_id} yearFees={year} showYearTitle />
                ))
              )}
            </>
          ) : (
            <>
              <div className="space-y-1 border-b border-slate-300 pb-4">
                <h3 className="text-lg font-medium text-slate-900">
                  {data!.academic_year} Academic Year Fees Breakdown
                </h3>
                <p className={`text-sm font-medium ${paidClass}`}>
                  Fees Paid · {formatFeeAmount(data!.total_paid)} /{' '}
                  {formatFeeAmount(data!.total_billed)}
                </p>
              </div>
              <FeeYearBreakdown yearFees={data!} />
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4  bg-gray-100 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SearchComponent
              value={receiptSearch}
              onChange={setReceiptSearch}
              placeholder="Search by receipt number"
              className="w-full max-w-xs"
              debounceMs={400}
            />
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
            <PaymentHistoryTable
              payments={payments}
              onViewReceipt={(receiptId) => setViewReceiptId(receiptId)}
            />
          )}
        </div>
      )}

      <DownloadPaymentHistoryModal
        open={downloadOpen}
        onClose={() => setDownloadOpen(false)}
        studentId={studentId}
        academicYearOptions={academicYearOptions}
        termOptions={termOptions.filter((item) => item.value !== FEE_DESK_ALL_TIME_TERM)}
      />
      <ReceiptViewModal
        open={Boolean(viewReceiptId)}
        receiptId={viewReceiptId}
        onClose={() => setViewReceiptId(null)}
      />
    </div>
  )
}

export default Fees
