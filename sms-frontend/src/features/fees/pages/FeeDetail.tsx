import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import ActionBar from '@/components/shared/ActionBar'
import { AvatarComponent, Button } from '@/components/ui'
import DotComponent from '@/components/ui/DotComponent'
import RecordPaymentSlider from '@/features/fees/components/RecordPaymentSlider'
import { getStudentPaymentTarget } from '@/features/fees/services'
import {
  STUDENT_PAYMENT_TARGET_QUERY_KEY,
  formatFeeAmount,
} from '@/features/fees/utils'
import StudentFees from '@/features/students/components/detail-pages/Fees'
import { getStudent } from '@/features/students/services'
import { STUDENT_DETAIL_QUERY_KEY } from '@/features/students/utils'
import { getApiErrorMessage } from '@/utils'

const FeeDetailPage = () => {
  const { studentId } = useParams<{ studentId: string }>()
  const [recordOpen, setRecordOpen] = useState(false)

  const {
    data: student,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: [STUDENT_DETAIL_QUERY_KEY, studentId],
    queryFn: () => getStudent(studentId!),
    enabled: Boolean(studentId),
  })

  const { data: paymentTarget } = useQuery({
    queryKey: [STUDENT_PAYMENT_TARGET_QUERY_KEY, studentId],
    queryFn: () => getStudentPaymentTarget(studentId!),
    enabled: Boolean(studentId),
  })

  return (
    <div className="space-y-6">
      <ActionBar back title="Fee details" />

      <div className="bg-white p-4 custom-shadow-md space-y-6">
        {isLoading ? (
          <p className="text-sm text-slate-500 py-8">Loading student details…</p>
        ) : isError || !student ? (
          <p className="text-sm text-red-600 py-8" role="alert">
            {getApiErrorMessage(error, 'Unable to load student details.')}
          </p>
        ) : (
          <>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-4">
                <AvatarComponent fullName={student.full_name} size={100} />
                <div>
                  <h2 className="text-2xl font-medium mb-1">{student.full_name}</h2>
                  <span className="text-sm text-gray-500">#{student.student_id}</span>
                  {student.class_assignment ? (
                    <>
                      <DotComponent />
                      <span className="text-sm text-gray-500">
                        {student.class_assignment.display_name}
                      </span>
                    </>
                  ) : null}
                  <DotComponent />
                  <span
                    className={
                      student.is_active ? 'text-sm text-green-600' : 'text-sm text-slate-500'
                    }
                  >
                    {student.is_active ? 'Active' : 'Inactive'}
                  </span>
                  {paymentTarget?.has_advance ? (
                    <>
                      <DotComponent />
                      <span className="text-sm font-medium text-emerald-700">
                        Advance: {formatFeeAmount(paymentTarget.advance_balance)}
                      </span>
                    </>
                  ) : null}
                </div>
              </div>
              <Button
                type="button"
                className="py-2 text-sm max-w-fit shrink-0"
                onClick={() => setRecordOpen(true)}
              >
                <Icon
                  icon="hugeicons:plus-sign"
                  className="size-4 bg-white text-black rounded-full p-0.5"
                />
                Record Fees
              </Button>
            </div>

            <StudentFees studentId={student.id} />
          </>
        )}
      </div>

      <RecordPaymentSlider
        open={recordOpen}
        onClose={() => setRecordOpen(false)}
        preselectedStudentId={student?.id}
      />
    </div>
  )
}

export default FeeDetailPage
