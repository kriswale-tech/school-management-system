import type { StudentTermFees, StudentYearFees } from '../types'
import { formatFeeAmount, getFeePaymentStatusClass } from '../utils'

type FeeYearBreakdownProps = {
  yearFees: StudentYearFees
  showYearTitle?: boolean
}

const TermFeeBlock = ({ term }: { term: StudentTermFees }) => {
  const paidClass = getFeePaymentStatusClass(term.payment_status)

  return (
    <div className="space-y-3 bg-white p-4 rounded-md">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="text-base font-medium text-slate-800">{term.term_name}</h4>
        <p className={`text-sm font-medium ${paidClass}`}>
          {formatFeeAmount(term.total_paid)} / {formatFeeAmount(term.total_billed)}
        </p>
      </div>

      <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-500">
              <th className="px-4 py-2.5 font-medium">Fee item</th>
              <th className="px-4 py-2.5 font-medium text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {term.fee_items.length === 0 ? (
              <tr>
                <td colSpan={2} className="px-4 py-3 text-slate-500">
                  No fees billed for this term.
                </td>
              </tr>
            ) : (
              term.fee_items.map((item) => (
                <tr key={item.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 text-slate-800">{item.name}</td>
                  <td className="px-4 py-3 text-right text-slate-800">
                    {formatFeeAmount(item.amount)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
          <tfoot>
            <tr className="border-t border-slate-200 bg-slate-50 font-medium text-slate-900">
              <td className="px-4 py-3">Total</td>
              <td className="px-4 py-3 text-right">{formatFeeAmount(term.total_billed)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

const FeeYearBreakdown = ({ yearFees, showYearTitle = false }: FeeYearBreakdownProps) => {
  return (
    <div className="space-y-6">
      {showYearTitle ? (
        <h3 className="text-lg font-medium text-slate-900">
          {yearFees.academic_year} Academic Year Fees Breakdown
        </h3>
      ) : null}

      {yearFees.terms.length === 0 ? (
        <p className="text-sm text-slate-500">No terms found for this academic year.</p>
      ) : (
        yearFees.terms.map((term) => <TermFeeBlock key={term.term_id} term={term} />)
      )}
    </div>
  )
}

export default FeeYearBreakdown
