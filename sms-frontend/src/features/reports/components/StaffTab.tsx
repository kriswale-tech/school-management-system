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
import type { StaffCapacityResponse, TeacherInsightRow } from '../types'
import { CHART_GRID, CHART_SKY, CHART_TICK } from '../utils'

type StaffTabProps = {
  data?: StaffCapacityResponse
}

const joinList = (items: string[], empty = '—') => {
  if (items.length === 0) return empty
  if (items.length <= 2) return items.join(', ')
  return `${items.slice(0, 2).join(', ')} +${items.length - 2}`
}

const roleLabel = (row: TeacherInsightRow) => {
  if (row.is_class_teacher && row.is_subject_teacher) return 'Both'
  if (row.is_class_teacher) return 'Class teacher'
  if (row.is_subject_teacher) return 'Subject teacher'
  return '—'
}

const StaffTab = ({ data }: StaffTabProps) => {
  if (!data) {
    return (
      <div className="bg-white p-8 custom-shadow-md text-sm text-slate-500">
        Loading teachers…
      </div>
    )
  }

  const loadChart = data.results
    .filter((row) => row.teaching_assignments_count > 0)
    .slice(0, 12)
    .map((row) => ({
      name: row.full_name,
      assignments: row.teaching_assignments_count,
      classTeacher: row.class_teacher_count,
      subjects: row.subjects_taught_count,
    }))

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatsCard title="Teachers" value={String(data.teachers_count)} />
        <StatsCard
          title="Class teachers"
          value={String(data.class_teachers_count)}
          description={`${data.both_roles_count} also teach subjects`}
        />
        <StatsCard
          title="Subject teachers"
          value={String(data.subject_teachers_count)}
          description={
            data.average_assignments === null
              ? 'No teaching assignments yet'
              : `Avg ${data.average_assignments} assignments each`
          }
        />
        <StatsCard
          title="Classes without class teacher"
          value={String(data.classes_without_class_teacher)}
          description={`${data.classes_count} classes this term`}
        />
      </div>

      <ChartCard
        title="Teaching load"
        description="Subject teaching assignments per teacher (top loads)."
        info="Each bar is how many subject×class teaching assignments a teacher holds this term. Use it to spot overloaded or under-used teachers before assigning more work."
        empty={loadChart.length === 0}
        emptyTitle="No teaching assignments yet"
        emptyDescription="Assign teachers to subjects to see load comparison."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={loadChart} margin={{ top: 12, right: 12, left: 0, bottom: 56 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: CHART_TICK, fontSize: 11 }}
              interval={0}
              angle={loadChart.length > 4 ? -30 : 0}
              textAnchor={loadChart.length > 4 ? 'end' : 'middle'}
              height={loadChart.length > 4 ? 64 : 36}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fill: CHART_TICK, fontSize: 12 }}
              width={36}
            />
            <Tooltip
              cursor={{ fill: 'rgba(14, 165, 233, 0.08)' }}
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const row = payload[0]?.payload as {
                  assignments: number
                  classTeacher: number
                  subjects: number
                }
                return (
                  <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
                    <p className="font-medium text-slate-800">{label}</p>
                    <p className="text-slate-600">Assignments: {row.assignments}</p>
                    <p className="text-slate-600">Subjects: {row.subjects}</p>
                    <p className="text-slate-600">Class teacher of: {row.classTeacher}</p>
                  </div>
                )
              }}
            />
            <Bar
              dataKey="assignments"
              fill={CHART_SKY}
              radius={[4, 4, 0, 0]}
              maxBarSize={44}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Teacher insights"
        description="Load and roles for each teacher this term."
        info="One row per teacher with class-teacher or subject-teaching work this term: how many classes they lead, how many students that covers, how many subjects and assignments they teach, and which classes those map to."
        empty={data.results.length === 0}
        emptyTitle="No teacher assignments yet"
        emptyDescription="Assign class teachers or subject teachers for this term to see insights."
        bodyClassName="w-full overflow-x-auto"
      >
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="px-3 py-2 font-medium">Teacher</th>
              <th className="px-3 py-2 font-medium">Role</th>
              <th className="px-3 py-2 font-medium">Class teacher of</th>
              <th className="px-3 py-2 font-medium">CT students</th>
              <th className="px-3 py-2 font-medium">Subjects</th>
              <th className="px-3 py-2 font-medium">Assignments</th>
              <th className="px-3 py-2 font-medium">Teaches in</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((row) => (
              <tr key={row.teacher_id} className="border-b border-slate-100 align-top">
                <td className="px-3 py-2.5 font-medium text-slate-800">
                  <Link
                    to={`/staff/${row.teacher_id}`}
                    className="text-sky-700 hover:text-sky-800 hover:underline"
                  >
                    {row.full_name}
                  </Link>
                </td>
                <td className="px-3 py-2.5 text-slate-700">{roleLabel(row)}</td>
                <td className="px-3 py-2.5 text-slate-700">
                  {row.class_teacher_count === 0 ? (
                    '—'
                  ) : (
                    <span title={row.class_teacher_classes.join(', ')}>
                      {row.class_teacher_count}
                      <span className="mt-0.5 block text-xs font-normal text-slate-500">
                        {joinList(row.class_teacher_classes)}
                      </span>
                    </span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-slate-700">
                  {row.class_teacher_count === 0 ? '—' : row.class_teacher_students}
                </td>
                <td className="px-3 py-2.5 text-slate-700">
                  {row.subjects_taught_count === 0 ? (
                    '—'
                  ) : (
                    <span title={row.subject_names.join(', ')}>
                      {row.subjects_taught_count}
                      <span className="mt-0.5 block text-xs font-normal text-slate-500">
                        {joinList(row.subject_names)}
                      </span>
                    </span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-slate-700">
                  {row.teaching_assignments_count === 0 ? (
                    '—'
                  ) : (
                    <span title={row.assignments.join(', ')}>
                      {row.teaching_assignments_count}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-slate-700">
                  {row.classes_taught_count === 0 ? (
                    '—'
                  ) : (
                    <span title={row.teaching_classes.join(', ')}>
                      {row.classes_taught_count}
                      <span className="mt-0.5 block text-xs font-normal text-slate-500">
                        {joinList(row.teaching_classes)}
                      </span>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ChartCard>
    </div>
  )
}

export default StaffTab
