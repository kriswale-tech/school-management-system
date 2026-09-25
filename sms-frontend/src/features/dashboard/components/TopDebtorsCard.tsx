import { useNavigate } from 'react-router-dom'
import { AvatarComponent } from '@/components/ui'
import { formatFeeAmount } from '@/features/students/utils'
import type { AdminDashboardTopDebtor } from '../types'

type TopDebtorsCardProps = {
  debtors: AdminDashboardTopDebtor[]
}

const TopDebtorsCard = ({ debtors }: TopDebtorsCardProps) => {
  const navigate = useNavigate()

  return (
    <div className="bg-white p-4 custom-shadow-md flex flex-col max-h-80 h-full">
      <div className="flex items-center justify-between gap-3 mb-4 shrink-0">
        <h3 className="text-sm font-medium text-slate-800">Top Debtors</h3>
        <button
          type="button"
          onClick={() => navigate('/fees?debtors=true')}
          className="cursor-pointer text-xs font-medium text-slate-500 transition-colors hover:text-slate-800"
        >
          View all
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {debtors.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">No outstanding balances this term.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {debtors.map((debtor) => (
              <li key={debtor.student_id}>
                <button
                  type="button"
                  onClick={() => navigate(`/fees/${debtor.student_id}`)}
                  className="w-full flex cursor-pointer items-center gap-3 rounded-lg px-2 py-3 text-left transition-colors hover:bg-slate-50"
                >
                  <AvatarComponent fullName={debtor.full_name} size={40} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-900 truncate">{debtor.full_name}</p>
                    <p className="text-xs text-slate-500 truncate">{debtor.class_display}</p>
                  </div>
                  <p className="text-sm font-semibold text-slate-900 shrink-0">
                    {formatFeeAmount(debtor.outstanding_amount)}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default TopDebtorsCard
