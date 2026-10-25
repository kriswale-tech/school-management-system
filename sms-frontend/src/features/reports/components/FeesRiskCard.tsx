import { Link } from 'react-router-dom'
import ChartCard from './ChartCard'
import type { FeesAcademicRiskResponse } from '../types'
import { formatCompactFee, formatScore } from '../utils'

type FeesRiskCardProps = {
  data?: FeesAcademicRiskResponse
}

const FeesRiskCard = ({ data }: FeesRiskCardProps) => {
  if (!data?.available) return null

  return (
    <ChartCard
      title="Fees × academic risk"
      description="Debtors whose average is below the pass mark — collection and learning risk overlap."
      info="Students who still owe fees this term and whose overall published average is below the pass mark. Highlights where money and learning risk overlap so you can prioritise follow-up."
      empty={data.at_risk_count === 0}
      emptyTitle="No overlapping risk"
      emptyDescription="No debtors are currently below the academic pass mark."
      bodyClassName="w-full"
    >
      <div className="mb-3 flex flex-wrap gap-4 text-sm text-slate-600">
        <span>Debtors: {data.debtors_count}</span>
        <span>At-risk debtors: {data.at_risk_count}</span>
        {data.pass_mark !== undefined ? (
          <span>Pass mark is set at {formatScore(data.pass_mark)}%</span>
        ) : null}
      </div>
      <ul className="divide-y divide-slate-100">
        {data.results.map((row) => (
          <li key={row.id} className="flex items-center justify-between gap-3 py-2.5">
            <div className="min-w-0">
              <Link
                to={`/students/${row.id}?tab=Performance`}
                className="truncate text-sm font-medium text-sky-700 hover:underline"
              >
                {row.full_name}
              </Link>
              <p className="truncate text-xs text-slate-500">
                {row.student_id}
                {row.class_display_name ? ` · ${row.class_display_name}` : ''}
              </p>
            </div>
            <div className="shrink-0 text-right text-sm">
              <p className="font-medium text-slate-900">{formatCompactFee(row.outstanding_amount)}</p>
              <p className="text-xs text-rose-600">Avg {formatScore(row.average_score)}</p>
            </div>
          </li>
        ))}
      </ul>
    </ChartCard>
  )
}

export default FeesRiskCard
