import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FormLabel, Modal, SelectField } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { getStudentFeeHistory } from '../services'
import type { StudentYearFees } from '../types'
import { formatFeeAmount, getFeePaymentStatusClass, STUDENT_FEE_HISTORY_QUERY_KEY } from '../utils'
import FeeYearBreakdown from './FeeYearBreakdown'

const ALL_YEARS = 'all'

type FeeHistoryModalProps = {
  open: boolean
  studentId: string
  onClose: () => void
}

const FeeHistoryModal = ({ open, studentId, onClose }: FeeHistoryModalProps) => {
  const [selectedYearId, setSelectedYearId] = useState(ALL_YEARS)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [STUDENT_FEE_HISTORY_QUERY_KEY, studentId],
    queryFn: () => getStudentFeeHistory(studentId),
    enabled: open && Boolean(studentId),
  })

  const years = useMemo(() => data?.years ?? [], [data?.years])

  const yearOptions = useMemo(
    () => [
      { value: ALL_YEARS, label: 'All years' },
      ...years.map((year) => ({
        value: year.academic_year_id,
        label: year.academic_year,
      })),
    ],
    [years],
  )

  const selectedYear: StudentYearFees | null = useMemo(() => {
    if (selectedYearId === ALL_YEARS) return null
    return years.find((year) => year.academic_year_id === selectedYearId) ?? null
  }, [selectedYearId, years])

  const handleClose = () => {
    setSelectedYearId(ALL_YEARS)
    onClose()
  }

  return (
    <Modal open={open} title="Fee history" onClose={handleClose} scrollable className="max-w-3xl">
      <div className="space-y-5">
        <div className="space-y-2">
          <FormLabel label="Academic year" />
          <SelectField
            options={yearOptions}
            value={selectedYearId}
            onChange={setSelectedYearId}
            placeholder="Filter by academic year"
            disabled={isLoading || years.length === 0}
          />
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-500 py-4">Loading fee history…</p>
        ) : isError ? (
          <p className="text-sm text-red-600 py-4" role="alert">
            {getApiErrorMessage(error, 'Unable to load fee history.')}
          </p>
        ) : years.length === 0 ? (
          <p className="text-sm text-slate-500 py-4">No fee history for this student yet.</p>
        ) : selectedYear ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2 rounded-md bg-slate-50 px-4 py-3">
              <span className="text-sm font-medium text-slate-700">
                {selectedYear.academic_year}
              </span>
              <span
                className={`text-sm font-medium ${getFeePaymentStatusClass(selectedYear.payment_status)}`}
              >
                {formatFeeAmount(selectedYear.total_paid)} /{' '}
                {formatFeeAmount(selectedYear.total_billed)}
              </span>
            </div>
            <FeeYearBreakdown yearFees={selectedYear} />
          </div>
        ) : (
          <div className="overflow-hidden rounded-md border border-slate-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-500">
                  <th className="px-4 py-2.5 font-medium">Academic year</th>
                  <th className="px-4 py-2.5 font-medium text-right">Paid / Total</th>
                </tr>
              </thead>
              <tbody>
                {years.map((year) => (
                  <tr
                    key={year.academic_year_id}
                    className="border-b border-slate-100 last:border-0"
                  >
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="text-left font-medium text-slate-800 hover:underline"
                        onClick={() => setSelectedYearId(year.academic_year_id)}
                      >
                        {year.academic_year}
                      </button>
                    </td>
                    <td
                      className={`px-4 py-3 text-right font-medium ${getFeePaymentStatusClass(year.payment_status)}`}
                    >
                      {formatFeeAmount(year.total_paid)} / {formatFeeAmount(year.total_billed)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="px-4 py-2 text-xs text-slate-500 border-t border-slate-100">
              Select a year to view the full term breakdown.
            </p>
          </div>
        )}
      </div>
    </Modal>
  )
}

export default FeeHistoryModal
