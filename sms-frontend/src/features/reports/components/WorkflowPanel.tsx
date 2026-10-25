import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import ChartCard from './ChartCard'
import type { LevelOption, WorkflowResponse } from '../types'
import { CHART_GRID, CHART_TICK, formatPercent } from '../utils'

type WorkflowPanelProps = {
  data?: WorkflowResponse
  levels: LevelOption[]
  levelId: FilterSelection
  onLevelChange: (value: FilterSelection) => void
}

const WorkflowPanel = ({ data, levels, levelId, onLevelChange }: WorkflowPanelProps) => {
  const chartRows = (data?.results ?? []).map((row) => ({
    name: row.display_name,
    students: row.students_count,
    Pending: row.pending_count,
    Ready: row.ready_count,
    Released: row.released_count,
  }))
  const totalStudents = data?.total_students ?? 0

  return (
    <ChartCard
      title="Assessment workflow"
      description={
        totalStudents > 0
          ? `${totalStudents} students across these classes · how far results have moved from class teacher → admin → released.`
          : 'How far results have moved from class teacher → admin → released.'
      }
      info="Stacked counts per class for the selected term: Pending (still with class teacher), Ready (awaiting admin release), and Released (report shared). Hover a class to see its student headcount alongside the pipeline counts."
      empty={!data || data.total_students === 0}
      emptyTitle="No enrolled students"
      emptyDescription="Workflow appears once classes have students for this term."
      actions={
        levels.length > 0 ? (
          <FilterComponent
            filterName="Level"
            filterKey="workflow-level"
            options={levels.map((level) => ({ value: level.id, label: level.name }))}
            value={levelId}
            placeholder="All levels"
            onChange={onLevelChange}
            className="min-w-36"
          />
        ) : null
      }
    >
      <div className="mb-3 flex flex-wrap gap-4 text-sm text-slate-600">
        <span>{totalStudents} students</span>
        <span>Complete: {formatPercent(data?.percent_complete)}</span>
        <span>Released: {formatPercent(data?.percent_released)}</span>
        <span>Pending: {data?.pending_count ?? 0}</span>
        <span>Ready for admin: {data?.ready_count ?? 0}</span>
      </div>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={chartRows} margin={{ top: 8, right: 12, left: 0, bottom: 48 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fill: CHART_TICK, fontSize: 11 }}
            interval={0}
            angle={chartRows.length > 5 ? -25 : 0}
            textAnchor={chartRows.length > 5 ? 'end' : 'middle'}
            height={56}
          />
          <YAxis allowDecimals={false} tick={{ fill: CHART_TICK, fontSize: 12 }} width={36} />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              const row = payload[0]?.payload as {
                students: number
                Pending: number
                Ready: number
                Released: number
              }
              return (
                <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
                  <p className="font-medium text-slate-800">{label}</p>
                  <p className="text-slate-600">{row.students} students</p>
                  <p className="text-slate-600">Pending: {row.Pending}</p>
                  <p className="text-slate-600">Ready: {row.Ready}</p>
                  <p className="text-slate-600">Released: {row.Released}</p>
                </div>
              )
            }}
          />
          <Legend />
          <Bar dataKey="Pending" stackId="a" fill="#94a3b8" maxBarSize={40} />
          <Bar dataKey="Ready" stackId="a" fill="#38bdf8" maxBarSize={40} />
          <Bar dataKey="Released" stackId="a" fill="#0284c7" radius={[4, 4, 0, 0]} maxBarSize={40} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

export default WorkflowPanel
