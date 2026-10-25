import { Link } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import ChartCard from './ChartCard'
import type { ClassLevelOption, StudentTrendRow } from '../types'
import { CHART_GRID, formatResultsCoverage, formatScore } from '../utils'

type StudentTrendsPanelProps = {
  topStudents: StudentTrendRow[]
  atRiskStudents: StudentTrendRow[]
  passMark?: number
  studentsCount?: number
  studentsWithResults?: number
  belowPassCount?: number
  classLevels: ClassLevelOption[]
  classLevelId: FilterSelection
  onClassLevelChange: (value: FilterSelection) => void
}

const StudentList = ({
  title,
  students,
  tone,
  emptyMessage,
}: {
  title: string
  students: StudentTrendRow[]
  tone: 'good' | 'risk'
  emptyMessage: string
}) => {
  return (
    <div>
      <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
      {students.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{emptyMessage}</p>
      ) : (
        <ul className="mt-2 divide-y divide-slate-100">
          {students.map((student) => (
            <li key={student.id} className="flex items-start justify-between gap-3 py-3">
              <div className="min-w-0">
                <Link
                  to={`/students/${student.id}?tab=Performance`}
                  className="truncate text-sm font-medium text-sky-700 hover:underline"
                >
                  {student.full_name}
                </Link>
                <p className="truncate text-xs text-slate-500">
                  {student.student_id}
                  {student.class_display_name ? ` · ${student.class_display_name}` : ''}
                </p>
                {student.history.length > 1 ? (
                  <div className="mt-2 h-14 w-36">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={student.history}>
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
                        <XAxis dataKey="term_label" hide />
                        <YAxis domain={[0, 100]} hide />
                        <Tooltip
                          formatter={(value) => formatScore(Number(value))}
                          labelFormatter={(label) => String(label)}
                        />
                        <Line
                          type="monotone"
                          dataKey="average_score"
                          stroke={tone === 'good' ? '#059669' : '#e11d48'}
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : null}
              </div>
              <div className="shrink-0 text-right">
                <p className="text-sm font-semibold text-slate-900">
                  {formatScore(student.average_score)}
                </p>
                <p
                  className={`text-xs ${student.is_passing ? 'text-emerald-600' : 'text-rose-600'}`}
                >
                  {student.is_passing ? 'Passing' : 'At risk'}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const StudentTrendsPanel = ({
  topStudents,
  atRiskStudents,
  passMark,
  studentsCount,
  studentsWithResults = 0,
  belowPassCount = 0,
  classLevels,
  classLevelId,
  onClassLevelChange,
}: StudentTrendsPanelProps) => {
  const passMarkLabel =
    passMark !== undefined ? `Pass mark is set at ${formatScore(passMark)}%` : null

  const descriptionParts = [
    studentsCount !== undefined || studentsWithResults > 0
      ? formatResultsCoverage(studentsWithResults, studentsCount)
      : null,
    belowPassCount > 0
      ? `${belowPassCount} below pass mark`
      : studentsWithResults > 0
        ? 'none below pass mark'
        : null,
    passMarkLabel,
  ].filter(Boolean)

  return (
    <ChartCard
      title="Students to watch"
      description={
        descriptionParts.length > 0
          ? descriptionParts.join(' · ')
          : 'Top performers and students below the pass mark.'
      }
      info="Ranks students by overall average (mean of published subject totals). Top performers are the highest averages. Needs attention lists only students below the pass mark from Assessment Settings."
      empty={topStudents.length === 0 && atRiskStudents.length === 0}
      emptyTitle="No students to watch yet"
      emptyDescription="Publish subject results to see top performers and students below the pass mark."
      bodyClassName="w-full"
      actions={
        classLevels.length > 0 ? (
          <FilterComponent
            filterName="Class"
            filterKey="students-class"
            options={classLevels.map((item) => ({ value: item.id, label: item.name }))}
            value={classLevelId}
            placeholder="All classes"
            onChange={onClassLevelChange}
            className="min-w-36"
          />
        ) : null
      }
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <StudentList
          title={`Top performers (${topStudents.length})`}
          students={topStudents}
          tone="good"
          emptyMessage="No top performers to show yet."
        />
        <StudentList
          title={`Needs attention (${belowPassCount})`}
          students={atRiskStudents}
          tone="risk"
          emptyMessage={
            passMark !== undefined
              ? `No students below the pass mark (${formatScore(passMark)}%).`
              : 'No students below the pass mark.'
          }
        />
      </div>
    </ChartCard>
  )
}

export default StudentTrendsPanel
