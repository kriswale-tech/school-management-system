import type { ReactNode } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import ChartCard from './ChartCard'
import type { GradeDistributionMode, GradeDistributionRow } from '../types'
import { CHART_SERIES, formatPercent } from '../utils'

type GradePieChartProps = {
  title?: string
  description?: string
  info?: string
  mode?: GradeDistributionMode
  rows: GradeDistributionRow[]
  totalGraded: number
  emptyTitle?: string
  emptyDescription?: string
  actions?: ReactNode
}

const DEFAULT_GRADE_INFO =
  'Share of letter or number grades among published scores in this view. Each slice is one grade band from the level’s assessment config (counts and percent of graded results).'

const GradePieChart = ({
  title = 'Grade distribution',
  description,
  info = DEFAULT_GRADE_INFO,
  mode = 'grades',
  rows,
  totalGraded,
  emptyTitle = 'No graded scores yet',
  emptyDescription = 'Publish subject results with grades to see the curve.',
  actions,
}: GradePieChartProps) => {
  const isScoreBands = mode === 'score_bands'
  const data = rows
    .filter((row) => row.count > 0)
    .map((row) => ({
      grade: row.grade,
      count: row.count,
      percent: row.percent,
    }))

  return (
    <ChartCard
      title={title}
      description={
        description ??
        (totalGraded > 0
          ? `${totalGraded} graded results in this view.`
          : 'Share of grades (A–F or 1–9) for published scores.')
      }
      info={info}
      empty={data.length === 0}
      emptyTitle={emptyTitle}
      emptyDescription={emptyDescription}
      actions={actions}
      bodyClassName="w-full"
    >
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="grade"
              cx="50%"
              cy="50%"
              innerRadius={56}
              outerRadius={100}
              paddingAngle={2}
            >
              {data.map((entry, index) => (
                <Cell
                  key={entry.grade}
                  fill={CHART_SERIES[index % CHART_SERIES.length]}
                />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const row = payload[0]?.payload as {
                  grade: string
                  count: number
                  percent: number
                }
                return (
                  <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
                    <p className="font-medium text-slate-800">
                      {isScoreBands ? row.grade : `Grade ${row.grade}`}
                    </p>
                    <p className="text-slate-600">Count: {row.count}</p>
                    <p className="text-slate-600">Share: {formatPercent(row.percent)}</p>
                  </div>
                )
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-slate-600">
        {data.map((row, index) => (
          <li key={row.grade} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block size-2.5 rounded-sm"
              style={{ backgroundColor: CHART_SERIES[index % CHART_SERIES.length] }}
            />
            {row.grade} ({row.count})
          </li>
        ))}
      </ul>
    </ChartCard>
  )
}

export default GradePieChart

