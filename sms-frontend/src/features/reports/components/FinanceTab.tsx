import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import StatsCard from '@/components/shared/StatsCard'
import ChartCard from './ChartCard'
import type { FinanceResponse } from '../types'
import { CHART_GRID, CHART_SKY, CHART_TICK, formatCompactFee, formatPercent } from '../utils'

type FinanceTabProps = {
  data?: FinanceResponse
}

const FinanceTab = ({ data }: FinanceTabProps) => {
  if (!data) {
    return (
      <div className="bg-white p-8 custom-shadow-md text-sm text-slate-500">Loading finance…</div>
    )
  }

  if (!data.available) {
    return (
      <div className="bg-white p-6 custom-shadow-md text-sm text-slate-600">
        Finance insights are available to school-wide roles. Teachers see academic and enrollment
        views for their classes instead.
      </div>
    )
  }

  const classChart = data.debtors_by_class.slice(0, 12).map((row) => ({
    name: row.display_name,
    outstanding: Number(row.outstanding_amount.toFixed(0)),
    debtors: row.debtors_count,
  }))

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatsCard title="Collected" value={formatCompactFee(data.total_collected)} />
        <StatsCard title="Outstanding" value={formatCompactFee(data.outstanding)} />
        <StatsCard title="Collection rate" value={formatPercent(data.collection_rate)} />
        <StatsCard title="Debtors" value={String(data.debtors_count)} />
      </div>

      <ChartCard
        title="Outstanding by class"
        description="Classes with the highest fee arrears."
        info="Total unpaid billed fees per class for the selected term. Taller bars mean more arrears in that class (sum of outstanding balances)."
        empty={classChart.length === 0}
        emptyTitle="No debtors"
        emptyDescription="All billed fees are fully paid for this term."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={classChart} margin={{ top: 12, right: 12, left: 0, bottom: 48 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: CHART_TICK, fontSize: 11 }}
              interval={0}
              angle={-25}
              textAnchor="end"
              height={56}
            />
            <YAxis tick={{ fill: CHART_TICK, fontSize: 12 }} width={48} />
            <Tooltip
              formatter={(value) => formatCompactFee(Number(value))}
              labelFormatter={(label) => String(label)}
            />
            <Bar dataKey="outstanding" fill={CHART_SKY} radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Top debtors"
        description="Students with the largest outstanding balances."
        info="Students with the largest unpaid balances this term (billed minus paid), ordered highest first."
        empty={data.top_debtors.length === 0}
        emptyTitle="No debtors"
        bodyClassName="w-full"
      >
        <ul className="divide-y divide-slate-100">
          {data.top_debtors.map((row) => (
            <li key={row.id} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <Link
                  to={`/students/${row.id}`}
                  className="truncate text-sm font-medium text-sky-700 hover:underline"
                >
                  {row.full_name}
                </Link>
                <p className="truncate text-xs text-slate-500">
                  {row.student_id} · {row.class_display_name}
                </p>
              </div>
              <p className="shrink-0 text-sm font-semibold text-slate-900">
                {formatCompactFee(row.outstanding_amount)}
              </p>
            </li>
          ))}
        </ul>
      </ChartCard>
    </div>
  )
}

export default FinanceTab
