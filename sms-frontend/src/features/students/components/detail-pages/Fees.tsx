import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Button from '@/components/ui/Button'
import { getApiErrorMessage } from '@/utils'
import { getStudentCurrentYearFees } from '../../services'
import { formatFeeAmount, getFeePaymentStatusClass, STUDENT_FEES_QUERY_KEY } from '../../utils'
import FeeHistoryModal from '../FeeHistoryModal'
import FeeYearBreakdown from '../FeeYearBreakdown'

type FeesProps = {
  studentId: string
}

const Fees = ({ studentId }: FeesProps) => {
  const [historyOpen, setHistoryOpen] = useState(false)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [STUDENT_FEES_QUERY_KEY, studentId],
    queryFn: () => getStudentCurrentYearFees(studentId),
    enabled: Boolean(studentId),
  })

  if (isLoading) {
    return <p className="text-sm text-slate-500 py-6">Loading fees…</p>
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-red-600 py-6" role="alert">
        {getApiErrorMessage(error, 'Unable to load student fees.')}
      </p>
    )
  }

  const paidClass = getFeePaymentStatusClass(data.payment_status)

  return (
    <>
      <div className="space-y-6 bg-gray-100  p-4">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-300 pb-4">
          <div className="space-y-1">
            <h3 className="text-lg font-medium text-slate-900">
              {data.academic_year} Academic Year Fees Breakdown
            </h3>
            <p className={`text-sm font-medium ${paidClass}`}>
              Fees Paid · {formatFeeAmount(data.total_paid)} / {formatFeeAmount(data.total_billed)}
            </p>
          </div>
          <Button variant="ghost" className="w-fit shrink-0" onClick={() => setHistoryOpen(true)}>
            View fee history
          </Button>
        </div>

        <FeeYearBreakdown yearFees={data} />
      </div>

      <FeeHistoryModal
        open={historyOpen}
        studentId={studentId}
        onClose={() => setHistoryOpen(false)}
      />
    </>
  )
}

export default Fees
