import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '@iconify/react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Table, TableWrapper } from '@/components/shared'
import ChartCard from './ChartCard'
import GradePieChart from './GradePieChart'
import SubjectScoreCurveChart from './SubjectScoreCurveChart'
import type { TeacherDeskStudent, TeacherDeskSubject } from '../types'
import {
  CHART_GRID,
  CHART_SKY,
  CHART_TICK,
  formatPercent,
  formatPublishedCoverage,
  formatResultsCoverage,
  formatScore,
} from '../utils'

type ScoreSort = 'desc' | 'asc'

type SubjectPerformancePanelProps = {
  data: TeacherDeskSubject
}

const StudentTable = ({
  students,
  studentsCount,
}: {
  students: TeacherDeskStudent[]
  studentsCount: number
}) => {
  const [scoreSort, setScoreSort] = useState<ScoreSort>('desc')

  const sortedStudents = useMemo(() => {
    const rows = [...students]
    rows.sort((a, b) => {
      const delta = a.average_score - b.average_score
      if (delta !== 0) return scoreSort === 'asc' ? delta : -delta
      return a.full_name.localeCompare(b.full_name)
    })
    return rows
  }, [students, scoreSort])

  if (students.length === 0) {
    return (
      <div className="bg-white p-6 custom-shadow-md text-sm text-slate-500">
        No published results yet
        {studentsCount > 0 ? ` · ${studentsCount} students in this class` : ''}.
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div>
        <h3 className="text-lg font-semibold text-slate-800">Students</h3>
        <p className="text-sm text-slate-500">
          {formatResultsCoverage(students.length, studentsCount)}
        </p>
      </div>
      <TableWrapper>
        <Table>
          <Table.Head>
            <Table.Row className="border-b-0">
              <Table.HeaderCell>Student</Table.HeaderCell>
              <Table.HeaderCell>ID</Table.HeaderCell>
              <Table.HeaderCell>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 font-inherit text-inherit hover:text-slate-900"
                  onClick={() =>
                    setScoreSort((current) => (current === 'desc' ? 'asc' : 'desc'))
                  }
                  aria-label={`Sort by score ${scoreSort === 'desc' ? 'ascending' : 'descending'}`}
                >
                  Score
                  <Icon icon="hugeicons:arrow-up-down" className="size-3.5" />
                </button>
              </Table.HeaderCell>
              <Table.HeaderCell>Grade</Table.HeaderCell>
              <Table.HeaderCell>Status</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {sortedStudents.map((student) => (
              <Table.Row key={student.id}>
                <Table.Cell variant="primary">
                  <Link
                    to={`/students/${student.id}?tab=Performance`}
                    className="font-medium text-sky-700 hover:underline"
                  >
                    {student.full_name}
                  </Link>
                </Table.Cell>
                <Table.Cell>{student.student_id}</Table.Cell>
                <Table.Cell>{formatScore(student.average_score)}</Table.Cell>
                <Table.Cell>{student.grade ?? '—'}</Table.Cell>
                <Table.Cell>
                  <span
                    className={
                      student.is_passing ? 'text-emerald-600' : 'text-rose-600'
                    }
                  >
                    {student.is_passing ? 'Passing' : 'At risk'}
                  </span>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>
    </div>
  )
}

const SubjectPerformancePanel = ({ data }: SubjectPerformancePanelProps) => {
  const history = data.term_history.filter(
    (point): point is { term_id: string; term_label: string; average_score: number } =>
      point.average_score !== null && point.average_score !== undefined,
  )

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <div className="bg-white p-4 custom-shadow-md">
          <p className="text-xs text-slate-500">Students</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">{data.students_count}</p>
        </div>
        <div className="bg-white p-4 custom-shadow-md">
          <p className="text-xs text-slate-500">Average</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">
            {formatScore(data.average_score)}
          </p>
        </div>
        <div className="bg-white p-4 custom-shadow-md">
          <p className="text-xs text-slate-500">Pass rate</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">
            {formatPercent(data.pass_rate)}
          </p>
        </div>
        <div className="bg-white p-4 custom-shadow-md">
          <p className="text-xs text-slate-500">Pass mark</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">
            {formatScore(data.pass_mark)}%
          </p>
        </div>
        <div className="bg-white p-4 custom-shadow-md">
          <p className="text-xs text-slate-500">Published</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">
            {data.score_count}
            <span className="ml-1 text-sm font-normal text-slate-500">
              of {data.students_count}
            </span>
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <GradePieChart
          title={data.mode === 'score_bands' ? 'Score distribution' : 'Grade distribution'}
          mode={data.mode}
          description={
            data.mode === 'score_bands'
              ? data.total_graded > 0
                ? `${formatPublishedCoverage(data.score_count, data.students_count)} for ${data.subject_name}. This class uses positions — showing score ranges (pass mark ${formatScore(data.pass_mark)}%).`
                : `${formatPublishedCoverage(data.score_count, data.students_count)} for ${data.subject_name}. Score ranges appear once results are published (pass mark ${formatScore(data.pass_mark)}%).`
              : `${formatPublishedCoverage(data.score_count, data.students_count)} grades for ${data.subject_name}.`
          }
          info={
            data.mode === 'score_bands'
              ? `This class is set to positions only, so slices are score ranges around the pass mark instead of letter grades for ${data.subject_name}.`
              : `How many students earned each grade in ${data.subject_name} for this class and term, based on published subject totals.`
          }
          rows={data.grade_distribution}
          totalGraded={data.total_graded}
        />
        <ChartCard
          title="Term trend"
          description="Class average for this subject across recent terms."
          info="Line of the class average for this subject across recent terms where scores were published. Helps spot whether performance is rising or falling over time."
          empty={history.length < 2}
          emptyTitle="Not enough term history"
          emptyDescription="Publish this subject in more than one term to see the trend line."
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
              <XAxis
                dataKey="term_label"
                tick={{ fill: CHART_TICK, fontSize: 11 }}
                interval="preserveStartEnd"
              />
              <YAxis domain={[0, 100]} tick={{ fill: CHART_TICK, fontSize: 12 }} width={36} />
              <Tooltip formatter={(value) => formatScore(Number(value))} />
              <Line
                type="monotone"
                dataKey="average_score"
                stroke={CHART_SKY}
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <SubjectScoreCurveChart
        students={data.students}
        subjectName={data.subject_name}
        passMark={data.pass_mark}
        studentsCount={data.students_count}
      />

      <StudentTable students={data.students} studentsCount={data.students_count} />
    </div>
  )
}

export default SubjectPerformancePanel
