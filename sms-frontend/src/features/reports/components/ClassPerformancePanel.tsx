import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '@iconify/react'
import { Table, TableWrapper } from '@/components/shared'
import GradePieChart from './GradePieChart'
import type { TeacherDeskClass, TeacherDeskStudent } from '../types'
import {
  formatPercent,
  formatResultsCoverage,
  formatScore,
} from '../utils'

type ScoreSort = 'desc' | 'asc'

type ClassPerformancePanelProps = {
  data: TeacherDeskClass
  /** Hide the outer card chrome when already inside a page section. */
  embedded?: boolean
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
                  aria-label={`Sort by overall average ${scoreSort === 'desc' ? 'ascending' : 'descending'}`}
                >
                  Overall avg
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

const ClassPerformancePanel = ({ data }: ClassPerformancePanelProps) => {
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
          <p className="text-xs text-slate-500">With results</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">
            {data.students_with_results}
            <span className="ml-1 text-sm font-normal text-slate-500">
              of {data.students_count}
            </span>
          </p>
        </div>
      </div>

      <GradePieChart
        title={data.mode === 'score_bands' ? 'Score distribution' : 'Grade distribution'}
        mode={data.mode}
        description={
          data.mode === 'score_bands'
            ? data.total_graded > 0
              ? `${formatResultsCoverage(data.students_with_results, data.students_count)} in ${data.display_name}. This class uses positions — showing score ranges (pass mark ${formatScore(data.pass_mark)}%).`
              : `${formatResultsCoverage(data.students_with_results, data.students_count)} in ${data.display_name}. Score ranges appear once results are published (pass mark ${formatScore(data.pass_mark)}%).`
            : `${formatResultsCoverage(data.students_with_results, data.students_count)} in ${data.display_name}, mapped to this level’s grade bands.`
        }
        info={
          data.mode === 'score_bands'
            ? 'This class is set to positions only, so slices are score ranges around the pass mark instead of letter grades. Values are each student’s overall average across published subjects.'
            : 'How many students in this class land in each grade band. Grades come from each student’s overall average (mean of published subjects) mapped to this level’s bands — not individual subject grades.'
        }
        rows={data.grade_distribution}
        totalGraded={data.total_graded}
      />

      <StudentTable students={data.students} studentsCount={data.students_count} />
    </div>
  )
}

export default ClassPerformancePanel
