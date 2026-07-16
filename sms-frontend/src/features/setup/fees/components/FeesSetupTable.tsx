import { Icon } from '@iconify/react'

type FeeRow = {
  id: string
  feeItem: string
  amount: number
  appliedToGroups: string
  appliedToStudents: string
}

const DUMMY_FEES: FeeRow[] = [
  {
    id: '1',
    feeItem: 'Tuition Fee',
    amount: 5000,
    appliedToGroups: 'All Classes',
    appliedToStudents: 'All Students',
  },
  {
    id: '2',
    feeItem: 'PTA Levy',
    amount: 150,
    appliedToGroups: 'JHS 1, JHS 2',
    appliedToStudents: 'Boarders',
  },
  {
    id: '3',
    feeItem: 'ICT Fee',
    amount: 300,
    appliedToGroups: 'Primary 4 - Primary 6',
    appliedToStudents: 'All Students',
  },
]

const formatAmount = (amount: number) =>
  new Intl.NumberFormat('en-GH', {
    style: 'currency',
    currency: 'GHS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)

const FeesSetupTable = () => {
  return (
    <div className="form-field-wrapper py-10 bg-slate-50 overflow-x-auto">
      <table className="min-w-full border-collapse text-left text-sm">
        <thead className="bg-slate-200 text-slate-700">
          <tr>
            <th className="px-4 py-3 font-medium">Fee Item</th>
            <th className="px-4 py-3 font-medium">Amount</th>
            <th className="px-4 py-3 font-medium">Applied To (Groups)</th>
            <th className="px-4 py-3 font-medium">Applied To (Students)</th>
            <th className="px-4 py-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {DUMMY_FEES.map((fee) => (
            <tr key={fee.id} className="border-b border-slate-200 ">
              <td className="px-4 py-3 font-medium text-slate-900">{fee.feeItem}</td>
              <td className="px-4 py-3 text-slate-700">{formatAmount(fee.amount)}</td>
              <td className="px-4 py-3 text-slate-700">{fee.appliedToGroups}</td>
              <td className="px-4 py-3 text-slate-700">{fee.appliedToStudents}</td>
              <td className="px-4 py-3">
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    title={`Edit ${fee.feeItem}`}
                    aria-label={`Edit ${fee.feeItem}`}
                    className="flex size-8 shadow-sm bg-white items-center justify-center rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  >
                    <Icon icon="hugeicons:edit-02" className="size-4" />
                  </button>
                  <button
                    type="button"
                    title={`Delete ${fee.feeItem}`}
                    aria-label={`Delete ${fee.feeItem}`}
                    className="flex size-8 shadow-sm bg-white items-center justify-center rounded-full border border-slate-200 text-red-600 hover:bg-red-50 hover:text-red-700"
                  >
                    <Icon icon="hugeicons:delete-02" className="size-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default FeesSetupTable
