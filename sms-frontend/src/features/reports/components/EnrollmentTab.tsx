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
import type { EnrollmentResponse } from '../types'
import { CHART_GRID, CHART_SKY, CHART_TICK, formatPercent } from '../utils'

type EnrollmentTabProps = {
  data?: EnrollmentResponse
}

const reasonLabel = (reason: string) => {
  if (reason === 'dropout') return 'Dropped out'
  if (reason === 'transfer') return 'Transferred'
  if (reason === 'other') return 'Other'
  return reason
}

const EnrollmentTab = ({ data }: EnrollmentTabProps) => {
  if (!data) {
    return (
      <div className="bg-white p-8 custom-shadow-md text-sm text-slate-500">
        Loading enrollment…
      </div>
    )
  }

  const classChart = data.by_class.map((row) => ({
    name: row.display_name,
    students: row.students_count,
  }))

  const leavingClass = data.leaving_this_year_class_name
  const graduatedClass = data.graduated_class_name

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatsCard title="Enrolled this term" value={String(data.enrolled_count)} />
        <StatsCard title="New students" value={String(data.new_students)} />
        <StatsCard
          title="Leaving this year"
          value={String(data.leaving_this_year_count)}
          description={
            leavingClass
              ? `Pupils in ${leavingClass} — the last class this school offers`
              : 'No final-year class set up yet'
          }
        />
        <StatsCard
          title="Retention rate"
          value={formatPercent(data.retention_rate)}
          description={
            data.previous_term_label
              ? `vs ${data.previous_term_label}`
              : 'Needs a previous term to compare'
          }
        />
      </div>

      {data.previous_term_label ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <StatsCard
            title="Retained"
            value={data.retained_count === null ? '—' : String(data.retained_count)}
            description={`Still enrolled after ${data.previous_term_label}`}
          />
          <StatsCard
            title="Graduated"
            value={data.graduated_count === null ? '—' : String(data.graduated_count)}
            description={
              graduatedClass
                ? `Finished ${graduatedClass} and were not enrolled again`
                : 'Finished the last class and were not enrolled again'
            }
          />
          <StatsCard
            title="Marked left"
            value={data.left_count === null ? '—' : String(data.left_count)}
            description="Left early (dropout, transfer, or other)"
          />
        </div>
      ) : (
        <div className="bg-white p-4 custom-shadow-md text-sm text-slate-600">
          Retention compares this term to the previous one. Open a later term (or finish a term
          transition) to see retained / left / graduated splits.
        </div>
      )}

      {data.left_by_reason.length > 0 ? (
        <ChartCard
          title="Left by reason"
          info="Count of students marked left who were enrolled in the previous term, grouped by leave reason (dropout, transfer, other)."
          bodyClassName="w-full"
          empty={false}
        >
          <ul className="divide-y divide-slate-100">
            {data.left_by_reason.map((row) => (
              <li key={row.reason} className="flex justify-between py-2 text-sm">
                <span className="text-slate-600">{reasonLabel(row.reason)}</span>
                <span className="font-medium text-slate-900">{row.count}</span>
              </li>
            ))}
          </ul>
        </ChartCard>
      ) : null}

      <ChartCard
        title="Headcount by class"
        description="Current-term enrollment sizes."
        info="Number of students enrolled in each class for the selected term (active enrollments), so you can compare class sizes at a glance."
        empty={classChart.length === 0}
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
            <YAxis allowDecimals={false} tick={{ fill: CHART_TICK, fontSize: 12 }} width={36} />
            <Tooltip />
            <Bar dataKey="students" fill={CHART_SKY} radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}

export default EnrollmentTab
