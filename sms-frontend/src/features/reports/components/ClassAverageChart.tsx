import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import ChartCard from './ChartCard'
import type { ClassInsightRow, LevelOption } from '../types'
import {
  CHART_GRID,
  CHART_SKY,
  CHART_TICK,
  formatPercent,
  formatResultsCoverage,
  formatScore,
} from '../utils'

type ClassAverageChartProps = {
  rows: ClassInsightRow[]
  levels: LevelOption[]
  levelId: FilterSelection
  onLevelChange: (value: FilterSelection) => void
  studentsCount?: number
  studentsWithResults?: number
}

const ClassAverageChart = ({
  rows,
  levels,
  levelId,
  onLevelChange,
  studentsCount,
  studentsWithResults,
}: ClassAverageChartProps) => {
  const data = rows
    .filter((row) => row.average_score !== null)
    .map((row) => ({
      name: row.display_name,
      average: Number(row.average_score?.toFixed(1)),
      passRate: row.pass_rate,
      students: row.students_with_results,
      enrolled: row.students_count,
      publishedScores: row.published_subject_scores,
    }))

  const coverage =
    studentsCount !== undefined && studentsWithResults !== undefined
      ? formatResultsCoverage(studentsWithResults, studentsCount)
      : null

  return (
    <ChartCard
      title="Class comparison"
      description={
        coverage
          ? `Average overall score by class. ${coverage}.`
          : 'Average overall score by class for published results.'
      }
      info="Each bar is a class’s average overall score for the selected term: the mean of each student’s average across their published subject totals. Hover a bar for pass rate and how many of the class have results so far."
      empty={data.length === 0}
      actions={
        levels.length > 0 ? (
          <FilterComponent
            filterName="Level"
            filterKey="class-chart-level"
            options={levels.map((level) => ({ value: level.id, label: level.name }))}
            value={levelId}
            placeholder="All levels"
            onChange={onLevelChange}
            className="min-w-36"
          />
        ) : null
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 12, left: 0, bottom: 56 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fill: CHART_TICK, fontSize: 11 }}
            interval={0}
            angle={data.length > 6 ? -30 : 0}
            textAnchor={data.length > 6 ? 'end' : 'middle'}
            height={data.length > 6 ? 64 : 36}
          />
          <YAxis domain={[0, 100]} tick={{ fill: CHART_TICK, fontSize: 12 }} width={36} />
          <Tooltip
            cursor={{ fill: 'rgba(14, 165, 233, 0.08)' }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              const row = payload[0]?.payload as {
                average: number
                passRate: number | null
                students: number
                enrolled: number
                publishedScores: number
              }
              return (
                <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
                  <p className="font-medium text-slate-800">{label}</p>
                  <p className="text-slate-600">Avg: {formatScore(row.average)}</p>
                  <p className="text-slate-600">Pass: {formatPercent(row.passRate)}</p>
                  <p className="text-slate-600">
                    {formatResultsCoverage(row.students, row.enrolled)}
                  </p>
                  <p className="text-slate-600">
                    {row.publishedScores} published subject score
                    {row.publishedScores === 1 ? '' : 's'}
                  </p>
                </div>
              )
            }}
          />
          <Bar dataKey="average" fill={CHART_SKY} radius={[4, 4, 0, 0]} maxBarSize={44} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

export default ClassAverageChart
