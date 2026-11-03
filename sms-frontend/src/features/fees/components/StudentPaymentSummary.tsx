import type { StudentPaymentTarget } from '../types'
import { formatFeeAmount } from '../utils'
import { AvatarComponent } from '@/components/ui'

type StudentPaymentSummaryProps = {
  target: StudentPaymentTarget | null
  isLoading?: boolean
}

const StudentPaymentSummary = ({ target, isLoading }: StudentPaymentSummaryProps) => {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm text-slate-500">Loading student details…</p>
      </div>
    )
  }

  if (!target) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4">
        <p className="text-sm text-slate-500">Select student to see details here.</p>
      </div>
    )
  }

  const { student } = target
  const outstandingTerms = target.outstanding_terms ?? []

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
      <div className="flex items-center gap-3">
        <AvatarComponent fullName={student.full_name} size={48} />
        <div className="min-w-0">
          <p className="font-medium text-slate-900 truncate">{student.full_name}</p>
          <p className="text-sm text-slate-500 truncate">
            #{student.student_id}
            {student.class_display ? ` · ${student.class_display}` : ''}
          </p>
        </div>
      </div>

      {target.has_advance ? (
        <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Advance on account:{' '}
          <span className="font-medium">{formatFeeAmount(target.advance_balance)}</span>
        </div>
      ) : null}

      {target.has_outstanding ? (
        <div className="space-y-2 border-t border-slate-200 pt-3">
          <p className="text-sm text-slate-600">
            All-time owing:{' '}
            <span className="font-medium text-red-600">
              {formatFeeAmount(target.all_time_outstanding)}
            </span>
          </p>
          {outstandingTerms.length > 0 ? (
            <ul className="space-y-1 text-sm text-slate-600">
              {outstandingTerms.map((row) => (
                <li key={row.term_id} className="flex justify-between gap-3">
                  <span className="truncate text-slate-500">{row.term_label}</span>
                  <span className="shrink-0 font-medium text-slate-800">
                    {formatFeeAmount(row.balance)}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-slate-500 border-t border-slate-200 pt-3">
          This student has no outstanding fees.
        </p>
      )}
    </div>
  )
}

export default StudentPaymentSummary
